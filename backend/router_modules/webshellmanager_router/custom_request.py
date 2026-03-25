#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自定义请求构建器
实现不同加密类型的请求格式自定义功能
"""

import hashlib
import base64
import time
import json
import random
import uuid
import struct
import os
from urllib.parse import urlencode
from typing import Tuple, Optional, Dict, Any


class CustomRequestBuilder:
    """自定义请求构建器"""
    
    # 请求格式到 Content-Type 映射
    CONTENT_TYPE_MAPPING = {
        "form": "application/x-www-form-urlencoded",
        "plain": "text/plain", 
        "json": "application/json",
        "xml": "application/xml",
        "png": "image/png",
        "plain_binary": "application/octet-stream"
    }
    
    def __init__(self, secret_key: str, param_name: str = "pass", config_file: str = None):
        """
        初始化请求构建器
        
        Args:
            secret_key: 通信密钥
            param_name: 参数名（用于表单格式）
            config_file: 自定义配置文件路径（JSON格式）
        """
        self.secret_key = secret_key
        self.param_name = param_name
        self.custom_config = self._load_config(config_file) if config_file else None
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """
        加载自定义配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            配置字典，加载失败时返回None
        """
        try:
            if not os.path.exists(config_file):
                print(f"[WARNING] 配置文件不存在: {config_file}")
                return None
                
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"[DEBUG] 已加载自定义请求配置: {config_file}")
                return config
                
        except Exception as e:
            print(f"[ERROR] 加载配置文件失败 {config_file}: {e}")
            return None
    
    def _get_random_user_agent(self) -> str:
        """
        获取随机User-Agent字符串
        
        Returns:
            随机选择的User-Agent字符串
        """
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", 
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
        ]
        return random.choice(user_agents)

    def _replace_variables(self, text: str, encrypted_data: str = None) -> str:
        """
        替换文本中的动态变量
        
        支持的变量:
        - ${timestamp}: 当前时间戳（毫秒）
        - ${session_id}: 随机会话ID
        - ${random}: 随机数
        - ${uuid}: UUID字符串
        - ${random_ua}: 随机User-Agent
        - ${encrypted_data}: 加密数据（需要单独传入）
        
        Args:
            text: 包含变量的文本
            encrypted_data: 加密数据，用于替换${encrypted_data}占位符
            
        Returns:
            替换后的文本
        """
        if not text or "${" not in text:
            return text
            
        # 替换动态变量
        replacements = {
            "${timestamp}": str(int(time.time() * 1000)),
            "${session_id}": f"sess_{random.randint(100000, 999999)}",
            "${random}": str(random.randint(10000, 99999)),
            "${uuid}": str(uuid.uuid4()),
            "${random_ua}": self._get_random_user_agent()
        }
        
        # 如果提供了加密数据，添加到替换列表中
        if encrypted_data is not None:
            replacements["${encrypted_data}"] = encrypted_data
        
        result = text
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
            
        return result
    
    def _process_config_value(self, value, encrypted_data: str = None):
        """
        处理配置值中的占位符（支持字符串、数字、布尔值、列表等类型）
        
        Args:
            value: 配置值（可以是任意类型）
            encrypted_data: 加密数据，用于替换${encrypted_data}占位符
            
        Returns:
            处理后的值
        """
        if isinstance(value, str):
            return self._replace_variables(value, encrypted_data)
        elif isinstance(value, dict):
            result = {}
            for k, v in value.items():
                result[k] = self._process_config_value(v, encrypted_data)
            return result
        elif isinstance(value, list):
            return [self._process_config_value(item, encrypted_data) for item in value]
        else:
            return value  # 数字、布尔值等直接返回
    
    def get_custom_headers(self, encrypted_data: str = None) -> Dict[str, str]:
        """
        从配置文件中获取自定义HTTP请求头
        
        Args:
            encrypted_data: 加密数据，用于替换占位符
            
        Returns:
            自定义请求头字典
        """
        custom_headers = {}
        
        if self.custom_config and "headers" in self.custom_config:
            headers_config = self.custom_config["headers"]
            
            # 处理所有头部字段中的占位符
            for header_name, header_value in headers_config.items():
                processed_value = self._process_config_value(header_value, encrypted_data)
                custom_headers[header_name] = str(processed_value)
            
            """ print(f"[DEBUG] 应用自定义请求头，共{len(custom_headers)}个字段")
            for name, value in custom_headers.items():
                if name.lower() == 'user-agent':
                    print(f"[DEBUG] 自定义User-Agent: {value[:50]}...")
                elif name.lower() == 'cookie':
                    print(f"[DEBUG] 自定义Cookie: {value}")
                else:
                    print(f"[DEBUG] 自定义Header - {name}: {value}") """
        
        return custom_headers
    
    def get_content_type(self, request_format: str) -> str:
        """
        根据请求格式获取对应的 Content-Type
        
        Args:
            request_format: 请求格式
            
        Returns:
            Content-Type 字符串
        """
        try:
            return self.CONTENT_TYPE_MAPPING[request_format]
        except KeyError:
            # 如果没有找到映射，返回默认值
            print(f"[WARNING] 未找到 {request_format} 的 Content-Type 映射，使用默认值")
            return "text/plain"
    
    def hex_to_base64(self, hex_str: str) -> str:
        """
        16进制字符串转Base64编码（用于标记编码）
        
        Args:
            hex_str: 16进制字符串
            
        Returns:
            Base64编码后的字符串
        """
        try:
            # 将16进制字符串转换为字节数组
            bytes_data = bytes.fromhex(hex_str)
            # 进行Base64编码并移除填充符
            b64_encoded = base64.b64encode(bytes_data).decode('utf-8')
            # 移除末尾的填充符以减少特征
            return b64_encoded.rstrip('=')
        except Exception as e:
            print(f"[ERROR] 16进制转Base64失败: {e}")
            # 如果转换失败，返回原16进制字符串
            return hex_str

    def _calculate_crc32(self, data: bytes) -> int:
        """
        计算PNG块的CRC32校验和
        
        Args:
            data: 要计算CRC32的数据（块类型+块数据）
            
        Returns:
            CRC32校验和
        """
        import zlib
        return zlib.crc32(data) & 0xffffffff



    def create_aes_base64_form_request(self, encrypted_data: str) -> Tuple[str, str]:
        """
        创建 aes_base64 表单格式的请求体
        
        Args:
            encrypted_data: Base64编码的加密数据
            
        Returns:
            (request_body, content_type): 请求体和内容类型元组
        """
        content_type = self.get_content_type("form")
        
        # 检查是否有自定义配置
        if self.custom_config and "form" in self.custom_config:
            form_config = self.custom_config["form"]
            
            # 处理整个Form配置，替换所有占位符
            form_data = self._process_config_value(form_config, encrypted_data)
            
            # 确保所有值都是字符串类型（URL编码需要）
            for key, value in form_data.items():
                if not isinstance(value, str):
                    form_data[key] = str(value)
            
            print(f"[DEBUG] 使用自定义Form配置，处理占位符完成")
            
        else:
            # 使用默认配置
            form_data = {self.param_name: encrypted_data}
            print(f"[DEBUG] 使用默认Form配置")
        
        return urlencode(form_data), content_type

    def create_aes_base64_plain_request(self, encrypted_data: str) -> Tuple[str, str]:
        """
        创建 aes_base64 纯加密格式的请求体
        
        Args:
            encrypted_data: Base64编码的加密数据（已包含标记）
            
        Returns:
            (request_body, content_type): 请求体和内容类型元组
        """
        content_type = self.get_content_type("plain")
        
        # 检查是否有自定义配置
        if self.custom_config and "plain" in self.custom_config:
            plain_config = self.custom_config["plain"]
            
            # 如果配置中直接有模板字符串（支持${encrypted_data}占位符）
            if "template" in plain_config:
                template = plain_config["template"]
                request_body = self._replace_variables(template, encrypted_data)
                
                print(f"[DEBUG] 使用自定义Plain模板，处理占位符完成")
                return request_body, content_type
            else:
                # 向后兼容：使用prefix和suffix方式
                prefix = plain_config.get("prefix", "")
                suffix = plain_config.get("suffix", "")
                
                # 处理动态变量替换
                if prefix:
                    prefix = self._replace_variables(prefix, encrypted_data)
                if suffix:
                    suffix = self._replace_variables(suffix, encrypted_data)
                
                # 构建完整的请求体
                request_body = prefix + encrypted_data + suffix
                
                print(f"[DEBUG] 使用自定义Plain配置（兼容模式），前缀长度: {len(prefix)}, 后缀长度: {len(suffix)}")
                return request_body, content_type
            
        else:
            # 使用默认配置（无前后缀）
            print(f"[DEBUG] 使用默认Plain配置")
            return encrypted_data, content_type

    def create_request_body(self, encrypted_data, 
                           request_format: str = "form"):
        """
        根据请求格式创建自定义请求体的统一入口
        
        Args:
            encrypted_data: 加密数据（可能已包含标记），可以是str或bytes
            request_format: 请求格式类型 ("form", "plain", "json", "xml", "png", "plain_binary")
            
        Returns:
            (request_body, content_type): 请求体和内容类型元组
        """
        # 根据请求格式调用相应的方法
        
        if request_format == "form":
            method_name = "create_aes_base64_form_request"
        elif request_format == "plain":
            method_name = "create_aes_base64_plain_request"
        elif request_format == "json":
            method_name = "create_aes_base64_json_request"
        elif request_format == "xml":
            method_name = "create_aes_base64_xml_request"
        elif request_format == "png":
            method_name = "create_aes_raw_png_request"
        elif request_format == "plain_binary":
            method_name = "create_aes_raw_plain_binary_request"
        else:
            method_name = "create_aes_base64_form_request"
        
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(encrypted_data)
        else:
            # 如果没有找到对应的方法，默认使用表单格式
            print(f"[WARNING] 未找到 {request_format} 格式的处理方法，使用默认表单格式")
            return self.create_aes_base64_form_request(encrypted_data)

    def create_aes_base64_json_request(self, encrypted_data: str) -> Tuple[str, str]:
        """
        创建 aes_base64 JSON格式的请求体
        
        Args:
            encrypted_data: Base64编码的加密数据（可能已包含标记）
            
        Returns:
            (request_body, content_type): 请求体和内容类型元组
        """
        content_type = self.get_content_type("json")
        
        # 检查是否有自定义配置
        if self.custom_config and "json" in self.custom_config:
            json_config = self.custom_config["json"]
            
            # 处理整个JSON配置，替换所有占位符
            json_template = self._process_config_value(json_config, encrypted_data)
            
            print(f"[DEBUG] 使用自定义JSON配置，处理占位符完成")
            
        else:
            # 使用默认模板
            json_template = {
                "username": f"user_{random.randint(1000, 9999)}",
                "data": encrypted_data
            }
            print(f"[DEBUG] 使用默认JSON模板")
        
        return json.dumps(json_template), content_type

    def create_aes_base64_xml_request(self, encrypted_data: str) -> Tuple[str, str]:
        """
        创建 aes_base64 XML格式的请求体
        
        Args:
            encrypted_data: Base64编码的加密数据（可能已包含标记）
            
        Returns:
            (request_body, content_type): 请求体和内容类型元组
        """
        content_type = self.get_content_type("xml")
        
        # 检查是否有自定义配置
        if self.custom_config and "xml" in self.custom_config:
            xml_config = self.custom_config["xml"]
            
            # 如果配置中有template字段，直接使用模板
            if "template" in xml_config:
                xml_template = xml_config["template"]
                # 替换模板中的所有占位符
                xml_body = self._replace_variables(xml_template, encrypted_data)
                
                print(f"[DEBUG] 使用自定义XML模板，处理占位符完成")
                return xml_body, content_type
            else:
                # 如果没有template字段，按照旧的方式处理（向后兼容）
                data_placeholder = xml_config.get("data_placeholder", "${encrypted_data}")
                xml_template = xml_config.get("template", "")
                
                if xml_template and data_placeholder:
                    xml_body = xml_template.replace(data_placeholder, encrypted_data)
                    xml_body = self._replace_variables(xml_body)
                    
                    print(f"[DEBUG] 使用自定义XML模板（兼容模式），数据占位符: {data_placeholder}")
                    return xml_body, content_type
                
        # 使用默认模板
        timestamp = int(time.time() * 1000)
        session_id = f"sess_{random.randint(100000, 999999)}"
        xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<request>
    <meta>
        <timestamp>{timestamp}</timestamp>
        <sessionId>{session_id}</sessionId>
    </meta>
    <data>
        <content><![CDATA[{encrypted_data}]]></content>
    </data>
</request>"""
        print(f"[DEBUG] 使用默认XML模板")
        return xml_template, content_type

    def create_aes_raw_plain_binary_request(self, encrypted_data: bytes) -> Tuple[str, str]:
        """
        创建 aes_raw 纯二进制格式的请求体
        
        Args:
            encrypted_data: 二进制加密数据（可能已包含标记）
            
        Returns:
            (request_body, content_type): 请求体和内容类型元组
        """
        return encrypted_data, "application/octet-stream"

    def create_aes_raw_png_request(self, encrypted_data: bytes) -> Tuple[bytes, str]:
        """
        创建 aes_raw PNG图片格式的请求体
        将二进制加密数据伪装成PNG图片格式
        
        Args:
            encrypted_data: 二进制加密数据（已包含左右标记）
            
        Returns:
            (request_body, content_type): 请求体和内容类型元组
        """
        content_type = self.get_content_type("png")
        
        # PNG文件头（8字节）
        PNG_SIGNATURE = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        
        # 创建一个最小的有效PNG图片结构
        # IHDR块 - 图片头信息（1x1像素的透明图片）
        ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)  # 宽1高1，RGBA格式
        ihdr_crc = self._calculate_crc32(b'IHDR' + ihdr_data)
        ihdr_chunk = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
        
        # IDAT块 - 图片数据（最小的1x1透明像素数据）
        # 对于1x1的RGBA图片，压缩后的数据很小
        import zlib
        pixel_data = bytes([0, 0, 0, 0, 0])  # 滤波器类型0 + 4字节透明像素(RGBA)
        compressed_data = zlib.compress(pixel_data, 9)
        idat_crc = self._calculate_crc32(b'IDAT' + compressed_data)
        idat_chunk = struct.pack('>I', len(compressed_data)) + b'IDAT' + compressed_data + struct.pack('>I', idat_crc)
        
        # 自定义载荷分隔符（8字节，类似PNG签名但不同）
        PNG_PAYLOAD_SEPARATOR = bytes([0x89, 0x50, 0x4C, 0x44, 0x0D, 0x0A, 0x1A, 0x0A])  # "PLDA" instead of "PNG"
        
        # IEND块 - 图片结束标记
        iend_crc = self._calculate_crc32(b'IEND')
        iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
        
        # 构建完整的PNG伪装请求
        png_fake_request = (
            PNG_SIGNATURE +           # PNG文件签名
            ihdr_chunk +              # 图片头信息
            idat_chunk +              # 最小图片数据
            iend_chunk +              # 图片结束
            PNG_PAYLOAD_SEPARATOR +   # 载荷分隔符
            encrypted_data            # 实际的加密载荷
        )
        
        print(f"[DEBUG] PNG伪装请求构建完成:")
        print(f"[DEBUG] - PNG头部长度: {len(PNG_SIGNATURE)} bytes")
        print(f"[DEBUG] - IHDR块长度: {len(ihdr_chunk)} bytes") 
        print(f"[DEBUG] - IDAT块长度: {len(idat_chunk)} bytes")
        print(f"[DEBUG] - IEND块长度: {len(iend_chunk)} bytes")
        print(f"[DEBUG] - 载荷分隔符长度: {len(PNG_PAYLOAD_SEPARATOR)} bytes")
        print(f"[DEBUG] - 加密载荷长度: {len(encrypted_data)} bytes")
        print(f"[DEBUG] - 总请求长度: {len(png_fake_request)} bytes")
        
        return png_fake_request, content_type


# 使用示例
def main():
    """测试函数"""
    builder = CustomRequestBuilder(secret_key="rebeyond", param_name="pass")
    
    # 模拟加密数据
    test_data = "dGVzdCBkYXRh"  # "test data" 的 base64
    
    # 测试 aes_base64 表单格式
    form_body, form_ct = builder.create_request_body(
        encrypted_data=test_data,
        request_format="form"
    )
    print(f"表单格式:")
    print(f"Content-Type: {form_ct}")
    print(f"Body: {form_body}")
    print()
    
    # 测试 aes_base64 纯加密格式
    plain_body, plain_ct = builder.create_request_body(
        encrypted_data=test_data,
        request_format="plain"
    )
    print(f"纯加密格式:")
    print(f"Content-Type: {plain_ct}")
    print(f"Body: {plain_body}")
    print()
    
    # 测试 JSON 格式
    json_body, json_ct = builder.create_request_body(
        encrypted_data=test_data,
        request_format="json"
    )
    print(f"JSON格式:")
    print(f"Content-Type: {json_ct}")
    print(f"Body: {json_body}")
    print()
    
    # 测试 XML 格式
    xml_body, xml_ct = builder.create_request_body(
        encrypted_data=test_data,
        request_format="xml"
    )
    print(f"XML格式:")
    print(f"Content-Type: {xml_ct}")
    print(f"Body: {xml_body[:200]}...")  # 只显示前200个字符
    print()
    
    # 测试PNG格式（二进制数据）
    test_binary_data = b"binary_test_data_with_markers"
    try:
        png_body, png_ct = builder.create_request_body(
            encrypted_data=test_binary_data,
            request_format="png"
        )
        print(f"PNG格式:")
        print(f"Content-Type: {png_ct}")
        print(f"Body长度: {len(png_body)} bytes")
        print(f"前20字节 (hex): {png_body[:20].hex()}")
        print()
    except Exception as e:
        print(f"PNG格式测试失败: {e}")
        print()
    
    # 测试所有格式类型的 Content-Type 映射
    print("=== Content-Type 映射测试 ===")
    test_formats = ["form", "plain", "json", "xml", "png", "plain_binary"]
    for fmt in test_formats:
        ct = builder.get_content_type(fmt)
        print(f"{fmt}: {ct}")


if __name__ == "__main__":
    main()
