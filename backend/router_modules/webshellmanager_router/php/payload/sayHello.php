function sayHello($name){
    return "hello, " . $name . "!";
}

$methodName = get("methodName");
$name = get("name");
if($methodName == null || $name == null){
    return "error:methodName or name is null";
}

if($methodName == "sayHello"){
    return sayHello($name);
}else{
    return "error:methodName is not found";
}

