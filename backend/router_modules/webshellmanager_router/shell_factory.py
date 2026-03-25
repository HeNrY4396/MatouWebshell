#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebShell工厂模式实现

这个模块实现了工厂模式来创建和管理不同类型的WebShell实例。
支持JSP、PHP、ASP等多种类型的webshell，并提供统一的实例管理和缓存机制。
"""

import hashlib
import os
from typing import Dict, Type, Optional, Any
from .base_shell import BaseShell


class WebShellTypeNotSupportedError(Exception):
    """不支持的webshell类型异常"""
    pass


class WebShellFactory:
    """
    WebShell工厂类
    
    负责根据webshell类型创建对应的实例，并提供缓存机制。
    支持动态注册新的webshell类型。
    """
    
    def __init__(self):
        self._shell_classes: Dict[str, Type[BaseShell]] = {}
        self._instances: Dict[str, BaseShell] = {}
        self._register_default_shells()

    
    def _register_default_shells(self):
        """注册默认的webshell类型"""
        # 分别注册每个Shell类型，让它们相互独立
        
        # 注册JavaShell (JSP类型)
        try:
            from .java.javaShell import JavaShell
            self.register_shell_type('jsp', JavaShell)
            self.register_shell_type('java', JavaShell)  # 别名
        except ImportError as e:
            print(f"[WARNING] 无法导入JavaShell: {e}")
        
        # 注册PhpShell (PHP类型)
        try:
            from .php.phpShell import PhpShell
            self.register_shell_type('php', PhpShell)
        except ImportError as e:
            print(f"[WARNING] 无法导入PhpShell: {e}")

        # 注册CsharpShell (CSharp类型)
        try:
            from .csharp.csharpShell import CsharpShell
            self.register_shell_type('csharp', CsharpShell)
        except ImportError as e:
            print(f"[WARNING] 无法导入CsharpShell: {e}")

        # 注册AspShell (ASP类型)
        try:
            from .asp.aspShell import AspShell
            self.register_shell_type('asp', AspShell)
        except ImportError as e:
            print(f"[WARNING] 无法导入AspShell: {e}")
        
        
 
    def register_shell_type(self, shell_type: str, shell_class: Type[BaseShell]):
        """
        注册新的webshell类型
        
        Args:
            shell_type: webshell类型标识（如 'jsp', 'php', 'asp'）
            shell_class: 对应的Shell类（必须继承自BaseShell）
        
        Raises:
            TypeError: 如果shell_class不是BaseShell的子类
        """
        if not issubclass(shell_class, BaseShell):
            raise TypeError(f"Shell类 {shell_class.__name__} 必须继承自BaseShell")
        
        shell_type_lower = shell_type.lower()
        self._shell_classes[shell_type_lower] = shell_class
    
    def get_supported_types(self) -> list:
        """获取所有支持的webshell类型"""
        return list(self._shell_classes.keys())
    
    def _generate_instance_key(self, url: str, param_name: str, password: str) -> str:
        """
        生成webshell实例的唯一标识
        
        Args:
            url: webshell URL
            param_name: 参数名
            password: 密码
            
        Returns:
            str: 实例的唯一标识
        """
        key_string = f"{url}_{param_name}_{password}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def remove_instance(self, url: str, param_name: str, password: str) -> bool:
        """
        移除缓存的webshell实例
        
        Args:
            url: webshell URL
            param_name: 参数名
            password: 密码
            
        Returns:
            bool: 移除成功返回True，实例不存在返回False
        """
        instance_key = self._generate_instance_key(url, param_name, password)
        if instance_key in self._instances:
            del self._instances[instance_key]
            print(f"[DEBUG] 移除webshell实例: {instance_key}")
            return True
        return False
    
    def remove_instance_by_id(self, webshell_id: str) -> bool:
        """
        通过webshell_id移除缓存实例
        """
        if not webshell_id:
            return False
        if webshell_id in self._instances:
            del self._instances[webshell_id]
            print(f"[DEBUG] 移除webshell实例(通过ID): {webshell_id}")
            return True
        return False
    
    def has_instance(self, instance_key: str) -> bool:
        """
        判断缓存中是否存在指定键的实例
        """
        return instance_key in self._instances
    
    def clear_all_instances(self) -> int:
        """
        清空所有缓存的webshell实例
        
        Returns:
            int: 清空的实例数量
        """
        count = len(self._instances)
        self._instances.clear()
        print(f"[DEBUG] 清空webshell缓存，共移除 {count} 个实例")
        return count
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        获取缓存状态
        
        Returns:
            dict: 包含缓存统计信息的字典
        """
        cache_keys = []
        shell_types = {}
        
        # 生成缓存键的摘要信息（不暴露敏感信息）
        for key, instance in self._instances.items():
            cache_keys.append(key[:8] + '...')  # 只显示前8个字符
            shell_type = instance.get_shell_type()
            shell_types[shell_type] = shell_types.get(shell_type, 0) + 1
        
        return {
            'total_instances': len(self._instances),
            'cache_keys': cache_keys,
            'shell_types_count': shell_types,
            'supported_types': self.get_supported_types()
        }


# 全局工厂实例
_global_factory = WebShellFactory()
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

def remove_webshell_instance(url: str, param_name: str, password: str) -> bool:
    """移除缓存的webshell实例的便利函数"""
    return _global_factory.remove_instance(url, param_name, password)


def remove_webshell_instance_by_id(webshell_id: str) -> bool:
    """通过webshell_id移除缓存实例的便利函数"""
    return _global_factory.remove_instance_by_id(webshell_id)


def is_webshell_instance_cached(webshell_id: str) -> bool:
    """判断指定webshell_id的实例是否已缓存"""
    return _global_factory.has_instance(webshell_id)


def clear_webshell_cache() -> int:
    """清空所有缓存的webshell实例的便利函数"""
    return _global_factory.clear_all_instances()


def get_webshell_cache_status() -> Dict[str, Any]:
    """获取缓存状态的便利函数"""
    return _global_factory.get_cache_status()


def register_webshell_type(shell_type: str, shell_class: Type[BaseShell]):
    """注册新webshell类型的便利函数"""
    _global_factory.register_shell_type(shell_type, shell_class)


def get_supported_webshell_types() -> list:
    """获取支持的webshell类型的便利函数"""
    return _global_factory.get_supported_types()


# 简化的辅助函数 - 通过webshell_id获取配置
def get_webshell_config_by_id(webshell_id: str) -> Optional[Dict[str, Any]]:
    """
    根据webshell_id获取完整配置（用户建议的简化方案）
    
    Args:
        webshell_id: webshell列表中的ID字段
        
    Returns:
        dict: 包含所有webshell配置的字典，找不到时返回None
    """
    try:
        import json
        import os
        
        # 获取webshell列表文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, 'data')
        webshell_list_file = os.path.join(data_dir, 'webshell_list.json')
        
        if not os.path.exists(webshell_list_file):
            print(f"[DEBUG] webshell列表文件不存在")
            return None
        
        # 读取webshell列表
        with open(webshell_list_file, 'r', encoding='utf-8') as f:
            webshell_list = json.load(f)
        
        # 查找匹配的webshell（通过ID直接匹配）
        for webshell in webshell_list:
            if webshell.get('id') == webshell_id:
                print(f"[DEBUG] 通过ID找到webshell: {webshell.get('url')}")
                return webshell
        
        print(f"[DEBUG] 未找到ID对应的webshell: {webshell_id}")
        return None
        
    except Exception as e:
        print(f"[ERROR] 根据ID获取webshell配置时出错: {e}")
        return None

def get_or_create_webshell_instance_by_id(webshell_id: str) -> Optional[BaseShell]:
    """
    通过webshell_id创建实例（用户建议的极简方案）
    
    只传递一个webshell_id参数，从webshell_list.json中获取所有配置，
    包括url、paramName、password、proxyType、proxyHost、encryptType等。
    
    Args:
        webshell_id: webshell列表中的ID字段
        
    Returns:
        BaseShell: webshell实例，创建失败时返回None
    """
    try:
        # 检查是否已经存在缓存的实例
        if webshell_id in _global_factory._instances:
            print(f"[DEBUG] 重用现有实例: {webshell_id}")
            return _global_factory._instances[webshell_id]
        
        # 根据ID获取完整配置
        config = get_webshell_config_by_id(webshell_id)
        if not config:
            print(f"[ERROR] 无法通过ID获取webshell配置: {webshell_id}")
            return None
        
        # 提取基本参数
        url = config.get('url')
        param_name = config.get('paramName')
        password = config.get('password')
        shell_type = config.get('webshellType', 'jsp')
        proxy_type = config.get('proxyType', 'none')
        proxy_host = config.get('proxyHost', '')
        response_encrypt_type = config.get('encryptType', 'aes_base64')
        request_format = config.get('requestFormat', 'plain')
        request_format_file = config.get('requestFormatFile', '')
        cookie_name = config.get('cookieName', 'X-Request-ID')
        
        if not all([url, param_name, password]):
            print(f"[ERROR] webshell基本参数不完整: {config}")
            return None
        
        print(f"[DEBUG] 通过ID创建{shell_type}实例: {webshell_id}")
        
        # 获取shell类
        shell_type_lower = shell_type.lower()
        if shell_type_lower not in _global_factory._shell_classes:
            print(f"[ERROR] 不支持的webshell类型: {shell_type}")
            return None
        
        shell_class = _global_factory._shell_classes[shell_type_lower]
        shell = shell_class(url, param_name, password)
        shell.response_encrypt_type = response_encrypt_type
        shell.cookie_name = cookie_name
        
        # 应用代理配置
        if proxy_type != 'none' and proxy_host:
            if proxy_type == 'http':
                shell.session.proxies = {
                    "http": f"http://{proxy_host}",
                    "https": f"http://{proxy_host}"
                }
                print(f"[DEBUG] 设置HTTP代理: {proxy_host}")
            elif proxy_type == 'socks':
                shell.session.proxies = {
                    "http": f"socks5://{proxy_host}",
                    "https": f"socks5://{proxy_host}"
                }
                print(f"[DEBUG] 设置SOCKS代理: {proxy_host}")
            else:
                # 确保没有代理
                shell.session.proxies = None
                print("[DEBUG] 清除代理设置")

        # 应用配置（从JSON中读取的配置）
        request_format_file_path = None  # 初始化为 None
        if request_format_file:
            request_format_file_path = os.path.join(DATA_DIR, request_format_file)
            if os.path.exists(request_format_file_path):
                print(f"[DEBUG] 找到请求格式定义文件: {request_format_file_path}")
            else:
                print(f"[DEBUG] 请求格式定义文件不存在: {request_format_file_path}")
                request_format_file_path = None
        shell.request_format = request_format
        shell.request_format_file = request_format_file_path
        
        # 传递webshell_id、请求格式和请求格式文件
        shell.init_payload(f"mainPayload_{response_encrypt_type}")
        print(f"[DEBUG] {shell_type}实例已初始化")
       
          
        # 缓存实例（直接使用webshell_id作为缓存键）
        _global_factory._instances[webshell_id] = shell
        print(f"[DEBUG] 实例已缓存，当前缓存数量: {len(_global_factory._instances)}")
        
        return shell
        
    except Exception as e:
        print(f"[ERROR] 通过ID创建webshell实例失败: {e}")
        import traceback
        traceback.print_exc()
        return None
