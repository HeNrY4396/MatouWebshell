#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
import base64
import hashlib
import json
import os
import random
import string
from typing import Tuple
from .ReqParameter import ReqParameter


class BaseShell(ABC):
    """
    Webshell基类，定义所有类型webshell都需要实现的通用接口
    """
    
    def __init__(self, url: str, param_name: str, secret_key: str):
        """
        初始化webshell连接
        
        Args:
            url: webshell的URL地址
            param_name: 参数名称
            secret_key: 连接密钥
        """
        self.url = url
        self.param_name = param_name  
        self.secret_key = secret_key
        self.is_connected = False
    
    # ====== 核心抽象方法 - 所有webshell都必须实现 ======
    
    @abstractmethod
    def send_http_request(self, encrypted_data, is_init_request=False):
        """
        发送HTTP请求
        
        Args:
            encrypted_data: 加密的请求数据
            is_init_request: 是否是初始化请求
        """
        pass
    
    def eval_func(self, class_name: str, func_name: str, parameter: ReqParameter):
        """
        调用服务端函数的通用方法
        
        Args:
            class_name: 类名
            func_name: 方法名
            parameter: 参数
        """
    # ====== 工具方法 ======
    def parse_file_list_text(self, files_text: str) -> list[dict]:
        """解析get_files返回的文件列表文本"""
        try:
            lines = files_text.strip().split('\n')
            file_list = []
            
            if len(lines) <= 1:
                return file_list
            
            # 第一行是目录路径，从第二行开始解析文件信息
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # 使用正则表达式分割，处理文件名中可能包含空格的情况
                    import re
                    parts = re.split(r'\s+', line, maxsplit=5)
                    
                    if len(parts) < 5:
                        continue
                    
                    file_name = parts[0]
                    file_type = parts[1]  # 0=目录, 1=文件
                    date = parts[2]
                    time = parts[3] 
                    size = parts[4]
                    permission = parts[5] if len(parts) > 5 else 'Unknown'
                    
                    # 构造文件信息
                    file_info = {
                        'name': file_name,
                        'isDirectory': file_type == '0',
                        'lastModified': f"{date} {time}",
                        'size': int(size) if size.isdigit() else 0,
                        'permission': permission
                    }
                    
                    file_list.append(file_info)
                    
                except Exception as parse_error:
                    print(f"[WARNING] 解析文件行失败: {line}, 错误: {parse_error}")
                    continue
            
            return file_list
            
        except Exception as e:
            print(f"[ERROR] 解析文件列表失败: {e}")
            return []
    def _decode_response_text(self, data: bytes) -> str:
        """
        优先使用UTF-8解码，失败时回退到GBK（适配中文系统）
        """
        if data is None:
            return ""
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return data.decode('gbk', errors='ignore')
            
    def _generate_random_cookie(self, length: int = 32) -> str:
        """生成随机cookie值"""
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    def _load_request_format_config(self, config_key: str | None = None):
        """
        Load request/response format config and optionally return a nested value.

        Args:
            config_key: dot-separated path like "response.json_template".

        Returns:
            Full config dict when config_key is None; otherwise the value at the path.
        """
        config = None
        config_file = getattr(self, "request_format_file", None)
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as handle:
                    config = json.load(handle)
            except Exception as exc:
                print(f"[ERROR] Failed to load request format config: {exc}")
                config = None
            if not isinstance(config, dict):
                print(f"[WARNING] Request format config is not an object: {config_file}")
                config = None
        elif config_file:
            print(f"[WARNING] Request format config file not found: {config_file}")

        if config_key is None:
            return config

        if not isinstance(config, dict):
            return None

        parts = [p for p in config_key.split('.') if p]
        current = config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _hex_to_base64(self, hex_str: str) -> str:
        """16进制字符串转Base64编码（用于标记编码），并移除 '=' 填充符"""
        try:
            bytes_data = bytes.fromhex(hex_str)
            return base64.b64encode(bytes_data).decode("utf-8").rstrip("=")
        except Exception:
            return hex_str

    def _generate_marker(self, cookie_value: str, secret_key: str) -> Tuple[str, str]:
        """
        生成左右标记（Base64字符串，去除 '='）

        Returns:
            tuple: (左标记, 右标记)
        """
        marker_string = cookie_value + secret_key
        md5_hash = hashlib.md5(marker_string.encode()).hexdigest()
        left_hex = md5_hash[:16]
        right_hex = md5_hash[16:]
        return self._hex_to_base64(left_hex), self._hex_to_base64(right_hex)

    def _generate_binary_marker(self, cookie_value: str, secret_key: str) -> Tuple[bytes, bytes]:
        """
        生成二进制标记

        Returns:
            tuple: (左标记bytes, 右标记bytes)
        """
        marker_string = cookie_value + secret_key
        md5_hash = hashlib.md5(marker_string.encode()).hexdigest()
        return bytes.fromhex(md5_hash[:16]), bytes.fromhex(md5_hash[16:])
    
    def get_shell_type(self) -> str:
        """
        获取webshell类型
        
        Returns:
            str: webshell类型标识（如"jsp", "php", "asp"等）
        """
        return self.__class__.__name__.lower().replace('shell', '')
    
    def is_file_operation_supported(self, operation: str) -> bool:
        """
        检查是否支持特定的文件操作
        
        Args:
            operation: 操作名称
            
        Returns:
            bool: True表示支持，False表示不支持
        """
        supported_operations = {
            'upload': True,
            'download': True,
            'delete': True,
            'copy': True,
            'move': True,
            'new_file': True,
            'new_dir': True,
            'big_upload': hasattr(self, 'big_file_upload'),
            'big_download': hasattr(self, 'big_file_download'),
            'zip': hasattr(self, 'zip'),
            'unzip': hasattr(self, 'unzip'),
            'remote_download': hasattr(self, 'file_remote_download'),
            'set_permission': hasattr(self, 'set_file_permission'),
            'set_time': hasattr(self, 'set_file_time')
        }
        return supported_operations.get(operation, False)
    
    def __str__(self):
        return f"{self.__class__.__name__}(url={self.url}, param={self.param_name})"
    
    def __repr__(self):
        return self.__str__()
