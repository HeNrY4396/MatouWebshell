import re
import os
import random
import xml.etree.ElementTree as ET
import string

current_dir = os.path.dirname(os.path.abspath(__file__))
jsp_file = os.path.join(current_dir, "webshell", "jsp", "shell1.jsp")
jspx_file = os.path.join(current_dir, "webshell", "jspx", "shell1.jspx") 
php_file = os.path.join(current_dir, "webshell", "php", "shell1.php")
variable_file = os.path.join(current_dir, "webshell", "variable.txt")

_HTML_ENCODABLE_CHARS = frozenset(string.ascii_letters + '&<>"\' ')

#--------------------------------通用方法--------------------------------#
def get_file_content(file_path):
    """
    获取文件内容
    """
    with open(file_path, "r") as file:
        return file.read()

def _find_sensitive_variables(content, prefix="$_"):
    """
    提取所有以 `prefix` 开头的变量名，保持首次出现的顺序。
    """
    escaped_prefix = re.escape(prefix)
    pattern = re.compile(fr'{escaped_prefix}[A-Za-z0-9_]+')
    seen = set()
    ordered_vars = []
    for match in pattern.finditer(content or ""):
        var_name = match.group(0)
        if var_name not in seen:
            seen.add(var_name)
            ordered_vars.append(var_name)
    return ordered_vars

def _generate_random_variable(existing_names, min_len=6, max_len=12):
    """
    生成不会冲突的随机变量名（不带 `$_` 前缀），并确保符合 Java 变量名规范（首字符不能为数字）。
    """
    first_alphabet = string.ascii_letters + "_"
    rest_alphabet = string.ascii_letters + string.digits + "_"
    for _ in range(200):
        rand_len = random.randint(min_len, max_len)
        first = random.choice(first_alphabet)
        rest = ''.join(random.choice(rest_alphabet) for _ in range(rand_len - 1)) if rand_len > 1 else ""
        candidate = first + rest
        if candidate not in existing_names:
            return candidate
    raise RuntimeError("无法生成唯一的随机变量名，请重试。")

def _normalize_candidate(name):
    """
    规范化 variable.txt 中的一行，去除 `$_` 前缀，返回合法变量名。
    """
    if not name:
        return None

    cleaned = re.sub(r'[^A-Za-z0-9_]', '', name)
    if not cleaned:
        return None

    if cleaned.startswith("$_"):
        cleaned = cleaned[2:]
    elif cleaned.startswith("_"):
        cleaned = cleaned[1:]

    return cleaned or "var"

def _load_variable_pool():
    """
    从 variable.txt 中读取变量候选列表（去重）。
    """
    if not os.path.isfile(variable_file):
        return []

    pool = []
    seen = set()
    try:
        with open(variable_file, "r", encoding="utf-8") as handle:
            for line in handle:
                candidate = _normalize_candidate(line.strip())
                if candidate and candidate not in seen:
                    pool.append(candidate)
                    seen.add(candidate)
    except OSError:
        return []

    return pool

def patch_variable(content, method="random", prefix="$_"):
    """
    替换 JSP 内容里所有以 `prefix` 开头的变量名。

    :param content: 原始 JSP 内容
    :param method: 处理模式，可选 "random"（随机生成）或 "file"（从 variable.txt 读取）
    :param prefix: 变量名前缀，默认为 "$_"
    :return: 替换后的内容
    """
    if not isinstance(content, str) or not content:
        return content

    method = (method or "random").lower()
    if method not in {"random", "file", "variable_file"}:
        method = "random"

    sensitive_vars = _find_sensitive_variables(content, prefix=prefix)
    if not sensitive_vars:
        return content

    candidate_pool = _load_variable_pool() if method in {"file", "variable_file"} else []
    reserved_names = {var[len(prefix):] for var in sensitive_vars}
    used_names = set(reserved_names)
    mapping = {}
    pool_index = 0

    for original in sensitive_vars:
        replacement = None
        if method in {"file", "variable_file"} and pool_index < len(candidate_pool):
            while pool_index < len(candidate_pool):
                candidate = candidate_pool[pool_index]
                pool_index += 1
                if candidate not in used_names:
                    replacement = candidate
                    break
        if not replacement:
            replacement = _generate_random_variable(used_names)

        used_names.add(replacement)
        mapping[original] = replacement

    escaped_prefix = re.escape(prefix)
    pattern = re.compile(fr'{escaped_prefix}[A-Za-z0-9_]+')
    return pattern.sub(lambda match: mapping.get(match.group(0), match.group(0)), content)

def code_compress(content):
    """
    压缩webshell配置文件：移除换行符，将连续的多个空格变成单个空格
    
    :param content: 原始webshell配置文件内容
    :return: 压缩后的webshell配置文件（一行）
    """
 
    # 移除所有换行符（\n和\r）
    compressed = content.replace('\n', ' ').replace('\r', ' ')
    
    # 将连续的多个空格（包括制表符等空白字符）替换为单个空格
    compressed = re.sub(r'\s+', ' ', compressed)
    
    # 去除首尾空格
    compressed = compressed.strip()
    
    return compressed

def repalce_content(content, replace_dict):
    """
    替换文件中的内容
    """
    if not isinstance(content, str) or not replace_dict:
        return content
    for key, value in replace_dict.items():
        content = content.replace(key, value)
    return content


def is_valid_xml(xml_content):
    """
    检测一个字符串是否可以被XML解析器成功解析。
    """
    if not isinstance(xml_content, str):
        return False

    wrapped_content = f"<dummy_root>{xml_content}</dummy_root>"
    try:
        ET.fromstring(wrapped_content)
        return True
    except (ET.ParseError, ValueError):
        return False
    except Exception:
        return False


def _sorted_keywords(keywords):
    """
    将关键字按长度降序排序，过滤掉空值。
    """
    if not keywords:
        return []
    return [kw for kw in sorted(keywords, key=len, reverse=True) if kw]


def _compile_keyword_pattern(keywords):
    """
    根据关键字构建正则，确保较长的关键字优先匹配。
    """
    keywords = _sorted_keywords(keywords)
    if not keywords:
        return None
    escaped = "|".join(re.escape(keyword) for keyword in keywords)
    return re.compile(escaped)


def _is_in_spans(start, end, spans):
    """
    判断当前匹配是否处于指定的区间内。
    """
    if not spans:
        return False
    return any(start < span_end and end > span_start for span_start, span_end in spans)


def _replace_keywords(content, keywords, transform, skip_spans=None):
    """
    统一的关键字替换逻辑，支持传入转换函数和跳过区域。
    """
    if not isinstance(content, str) or not content:
        return content
    pattern = _compile_keyword_pattern(keywords)
    if not pattern:
        return content

    def _replacement(match):
        start, end = match.span()
        if skip_spans and _is_in_spans(start, end, skip_spans):
            return match.group(0)
        return transform(match.group(0))

    return pattern.sub(_replacement, content)


def _split_keyword_parts(keyword, min_length=5):
    """
    将关键字拆分成多个部分，供各类混淆算法复用。
    """
    if not keyword or len(keyword) < min_length:
        return [keyword or ""]

    max_splits = max(1, min(3, len(keyword) // 3))
    split_points = sorted(random.sample(range(1, len(keyword)), random.randint(1, max_splits)))
    parts = []
    last_index = 0
    for point in split_points:
        parts.append(keyword[last_index:point])
        last_index = point
    parts.append(keyword[last_index:])
    return parts


def _encode_html_segment(text, ratio):
    """
    随机对片段进行HTML实体编码。
    """
    if not text:
        return text
    encoded = []
    for char in text:
        if char in _HTML_ENCODABLE_CHARS and random.random() < ratio:
            encoded.append(char_to_html_entity(char))
        else:
            encoded.append(char)
    return ''.join(encoded)

def xor_base64(content, key):
    """
    对内容进行XOR加密后，再Base64编码
    :param content: 要加密的字符串或bytes
    :param key: 密钥，字符串或bytes
    :return: 加密后的Base64字符串
    """
    import base64
    # 处理参数类型
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    else:
        content_bytes = content
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    else:
        key_bytes = key

    key_len = len(key_bytes)
    encrypted = bytearray()
    for i, b in enumerate(content_bytes):
        # 按照key循环异或
        encrypted.append(b ^ key_bytes[i % key_len])
    # base64编码返回字符串
    return base64.b64encode(encrypted).decode("utf-8")
#--------------------------------JSP混淆方法--------------------------------#
def encode_jsp_unicode(content):
    """
    对JSP文件进行Unicode编码混淆
    保留 <%@ page ... %> 标签完整不变
    对 <%! ... %> 和 <% ... %> 标签内的内容进行Unicode编码，但保留标签符号
    
    :param content: JSP文件内容
    :return: Unicode编码后的JSP内容
    """
    
    # 先保护 <%@ page ... %> 标签，不对其进行任何处理
    # 使用正则表达式匹配并替换 <%! ... %> 和 <% ... %> 的内容
    
    def replace_jsp_content(match):
        """处理匹配到的JSP标签"""
        tag_start = match.group(1)  # <%! 或 <%
        tag_content = match.group(2)  # 标签内的内容
        
        # 对标签内容进行Unicode编码
        encoded_content = char_to_unicode(tag_content)
        
        # 返回：标签开始符号 + 编码后的内容 + 标签结束符号
        return tag_start + encoded_content + '%>'
    
    
    pattern = r'(<%(?!@)[!]?)(.*?)(%>)'
    
    # 替换所有匹配到的 <%! ... %> 和 <% ... %>
    result = re.sub(pattern, replace_jsp_content, content, flags=re.DOTALL)
    
    return result

def encode_html_entities(content: str) -> str:
    """
    对字符串内容进行十六进制实体编码 (&#x...; 格式)。
    
    编码规则:
    1. 编码所有字母 (a-z, A-Z)
    2. 编码5个XML特殊字符 (&, <, >, ", ')
    3. 编码普通空格 (' ') 为 &#x20;
    4. 其他所有字符 (数字, 句号, 括号, 换行等) 保持不变。
    """

    # 1. 准备翻译表（字典）
    translation_table = {}

    # 2. 添加 6 个XML特殊字符
    special_chars = {
        '&': '&#x26;',
        '<': '&#x3c;',
        '>': '&#x3e;',
        '"': '&#x22;',
        "'": '&#x27;',
        ' ': '&#x20;',
    }
    for char, replacement in special_chars.items():
        translation_table[ord(char)] = replacement
        
    # 3. 添加所有字母
    for char in string.ascii_letters:
        hex_value = hex(ord(char))[2:]
        translation_table[ord(char)] = f"&#x{hex_value};"

    # 4. 使用 str.translate() 一次性高效完成所有替换
    return content.translate(translation_table)

def char_to_unicode(input_string):
    escaped_chars = [f'\\u{ord(char):04x}' for char in input_string]
    # 将列表中的所有转义序列连接成一个字符串
    return "".join(escaped_chars)

def obfuscate_keyword(keyword):
    """
    对单个关键字进行随机CDATA拆分混淆
    确保随机拆分点能覆盖整个关键字，达到更好的混淆效果
    """
    parts = _split_keyword_parts(keyword)
    if len(parts) == 1:
        return parts[0]

    result = parts[0]
    for part in parts[1:]:
        result += '<![CDATA[' + part + ']]>'

    return result

def obfuscate_single_keyword(keyword, unicode_ratio=0.5):
    """
    对单个关键字进行CDATA拆分+Unicode编码组合混淆
    
    :param keyword: 要混淆的关键字
    :param unicode_ratio: Unicode编码比例
    :return: 混淆后的关键字
    """
    parts = _split_keyword_parts(keyword)
    if not parts:
        return keyword

    result = random_unicode_encode(parts[0], unicode_ratio)
    for part in parts[1:]:
        encoded_part = random_unicode_encode(part, unicode_ratio)
        result += '<![CDATA[' + encoded_part + ']]>'

    return result

def char_to_html_entity(char):
    """
    将单个字符转换为HTML实体编码（十六进制格式）
    
    :param char: 单个字符
    :return: HTML实体编码后的字符串
    """
    hex_value = hex(ord(char))[2:]
    return f"&#x{hex_value};"

def random_html_unicode_encode(text, html_ratio=0.3, unicode_ratio=0.3):
    """
    对文本进行HTML实体编码和Unicode编码的混合编码
    每个字符随机选择：HTML编码、Unicode编码、或保持不变
    
    HTML编码规则：只对26个字母(a-z, A-Z)和6个特殊字符(&, <, >, ", ', 空格)进行编码
    Unicode编码规则：对所有字符都可以进行编码
    
    :param text: 要编码的文本
    :param html_ratio: HTML实体编码比例（0.0-1.0）
    :param unicode_ratio: Unicode编码比例（0.0-1.0）
    :return: 混合编码后的文本
    """
    if not text:
        return text
    
    html_encodable_chars = _HTML_ENCODABLE_CHARS

    result = []
    for char in text:
        rand = random.random()
        
        # 根据概率决定使用哪种编码
        if rand < html_ratio and char in html_encodable_chars:
            # HTML实体编码（仅对字母和特殊字符）
            result.append(char_to_html_entity(char))
        elif rand < html_ratio + unicode_ratio:
            # Unicode编码（对所有字符）
            result.append(f'\\u{ord(char):04x}')
        else:
            # 保持原样
            result.append(char)
    
    return ''.join(result)

def random_unicode_encode(text, ratio=0.5):
    """
    对文本中的字符进行随机Unicode编码
    
    :param text: 要编码的文本
    :param ratio: 编码比例（0.0-1.0）
    :return: 编码后的文本
    """
    if not text or ratio <= 0:
        return text
    
    result = []
    for char in text:
        # 随机决定是否编码这个字符
        if random.random() < ratio:
            # 编码为\uXXXX格式（注意是4位十六进制）
            result.append(f'\\u{ord(char):04x}')
        else:
            result.append(char)
    
    return ''.join(result)

def CDATA_Obfuscation(content, keywords):
    """
    对内容中的指定关键字进行混淆，并使用CDATA标签进行包装。
    避免对已存在的CDATA块内容进行混淆，防止嵌套错误。
    """
    if not isinstance(content, str) or not content:
        return content

    cdata_pattern = re.compile(r'<!\[CDATA\[.*?\]\]>', re.DOTALL)
    cdata_blocks = [(match.start(), match.end()) for match in cdata_pattern.finditer(content)]
    return _replace_keywords(content, keywords, obfuscate_keyword, skip_spans=cdata_blocks)
  
def Unicode_Obfuscation(content, keywords, unicode_ratio=0.5):
    """
    Unicode编码混淆：对关键字的随机字符进行Unicode编码
    
    :param content: 要混淆的内容
    :param keywords: 关键字列表
    :param unicode_ratio: Unicode编码比例（0.0-1.0），默认0.5表示随机编码50%的字符
                          当ratio=1时，对关键字所有字符进行编码
    :return: 混淆后的内容
    """
    return _replace_keywords(
        content,
        keywords,
        lambda keyword: random_unicode_encode(keyword, unicode_ratio),
    )

def HtmlEntities_Obfuscation(content, keywords, html_ratio=0.5):
    """
    HTML实体编码混淆：对关键字的随机字符进行HTML实体编码
    
    HTML编码规则：只对26个字母(a-z, A-Z)和6个特殊字符(&, <, >, ", ', 空格)进行编码
    
    :param content: 要混淆的内容
    :param keywords: 关键字列表
    :param html_ratio: HTML实体编码比例（0.0-1.0），默认0.5表示随机编码50%的可编码字符
                       当ratio=1时，对关键字中所有可编码字符进行编码
    :return: 混淆后的内容
    
    示例：getParameter (ratio=0.5) → &#x67;e&#x74;P&#x61;r&#x61;m&#x65;ter
    """
    return _replace_keywords(
        content,
        keywords,
        lambda keyword: _encode_html_segment(keyword, html_ratio),
    )

def HtmlEntities_Unicode_Obfuscation(content, keywords, html_ratio=0.3, unicode_ratio=0.3):
    """
    HTML实体编码和Unicode编码的组合混淆
    只对关键字本身进行混淆，不影响其他代码
    
    :param content: 要混淆的内容
    :param keywords: 关键字列表
    :param html_ratio: HTML实体编码比例（0.0-1.0），默认0.3
    :param unicode_ratio: Unicode编码比例（0.0-1.0），默认0.3
    :return: 混淆后的内容
    
    示例：getParameter → \u0067&#x65;t\u0050&#x61;rameter
    """
    return _replace_keywords(
        content,
        keywords,
        lambda keyword: random_html_unicode_encode(keyword, html_ratio, unicode_ratio),
    )

def CDATA_Unicode_Obfuscation(content, keywords, unicode_ratio=0.5):
    """
    组合混淆：对每个关键字进行CDATA拆分+Unicode编码
    只对关键字本身进行混淆，不影响其他代码
    
    :param content: 要混淆的内容
    :param keywords: 关键字列表
    :param unicode_ratio: Unicode编码比例（0.0-1.0），默认0.5表示随机编码50%的字符
    :return: 混淆后的内容
    """
    return _replace_keywords(
        content,
        keywords,
        lambda keyword: obfuscate_single_keyword(keyword, unicode_ratio),
    )

def obfuscate_single_keyword_html(keyword, html_ratio=0.5):
    """
    对单个关键字进行CDATA拆分+HTML实体编码组合混淆
    注意：CDATA标签内的内容不能进行HTML编码，只对标签外的内容进行HTML编码
    
    :param keyword: 要混淆的关键字
    :param html_ratio: HTML实体编码比例
    :return: 混淆后的关键字
    """
    parts = _split_keyword_parts(keyword)
    if len(parts) == 1:
        return _encode_html_segment(parts[0], html_ratio)

    result = _encode_html_segment(parts[0], html_ratio)
    for part in parts[1:]:
        result += '<![CDATA[' + part + ']]>'

    return result

def CDATA_HtmlEntities_Obfuscation(content, keywords, html_ratio=0.3):
    """
    CDATA拆分+HTML实体编码的组合混淆
    只对关键字本身进行混淆，不影响其他代码
    注意：CDATA标签内的内容不能进行HTML编码，只对标签外的内容进行HTML编码
    
    :param content: 要混淆的内容
    :param keywords: 关键字列表
    :param html_ratio: HTML实体编码比例（0.0-1.0），默认0.3表示随机编码30%的可编码字符
    :return: 混淆后的内容
    
    示例：request.getParameter → r&#x65;q&#x75;<![CDATA[est.get]]>P&#x61;r&#x61;meter
    """
    return _replace_keywords(
        content,
        keywords,
        lambda keyword: obfuscate_single_keyword_html(keyword, html_ratio),
    )

def jspx_obfuscation(content, keywords, method="cdata", unicode_ratio=0.5, html_ratio=0.3):
    """
    JSPX文件混淆：对JSPX文件进行混淆
    
    :param content: 要混淆的JSPX文件内容
    :param keywords: 关键字列表
    :param method: 混淆方法，可选值为"cdata"、"unicode"、"html"、"html_unicode"、"cdata_unicode"、"cdata_html"
    :param unicode_ratio: Unicode编码比例（0.0-1.0），默认0.5表示随机编码50%的字符
    :param html_ratio: HTML实体编码比例（0.0-1.0），默认0.3表示随机编码30%的可编码字符
    :return: 混淆后的JSPX文件内容
    """
    # 获取scriptlet标签和declaration标签内的内容
    scriptlet_match = re.search(r'<jsp:scriptlet>(.*?)</jsp:scriptlet>', content, re.DOTALL)
    declaration_match = re.search(r'<jsp:declaration>(.*?)</jsp:declaration>', content, re.DOTALL)
    scriptlet_content = scriptlet_match.group(1).strip() if scriptlet_match else None
    declaration_content = declaration_match.group(1).strip() if declaration_match else None

    # 对scriptlet标签和declaration标签内的内容进行混淆

    if method == "cdata":
        scriptlet_content = CDATA_Obfuscation(scriptlet_content, keywords)
        declaration_content = CDATA_Obfuscation(declaration_content, keywords)
    elif method == "unicode":
        scriptlet_content = Unicode_Obfuscation(scriptlet_content, keywords, unicode_ratio)
        declaration_content = Unicode_Obfuscation(declaration_content, keywords, unicode_ratio)
    elif method == "html":
        scriptlet_content = HtmlEntities_Obfuscation(scriptlet_content, keywords, html_ratio)
        declaration_content = HtmlEntities_Obfuscation(declaration_content, keywords, html_ratio)
    elif method == "html_unicode":
        scriptlet_content = HtmlEntities_Unicode_Obfuscation(scriptlet_content, keywords, html_ratio, unicode_ratio)
        declaration_content = HtmlEntities_Unicode_Obfuscation(declaration_content, keywords, html_ratio, unicode_ratio)
    elif method == "cdata_unicode":
        scriptlet_content = CDATA_Unicode_Obfuscation(scriptlet_content, keywords, unicode_ratio)
        declaration_content = CDATA_Unicode_Obfuscation(declaration_content, keywords, unicode_ratio)
    elif method == "cdata_html":
        scriptlet_content = CDATA_HtmlEntities_Obfuscation(scriptlet_content, keywords, html_ratio)
        declaration_content = CDATA_HtmlEntities_Obfuscation(declaration_content, keywords, html_ratio)

    # 将混淆后的内容替换回原内容
    if scriptlet_content:
        content = content.replace(scriptlet_match.group(1), scriptlet_content)
    if declaration_content:
        content = content.replace(declaration_match.group(1), declaration_content)
    return content

#--------------------------------PHP混淆方法--------------------------------#


def main():
    """
    测试不同的混淆方法
    """
    # 定义需要混淆的关键字
    keywords_to_obfuscate = [
        "getParameter",
        "getAttribute",
        "setAttribute",
        "getMethod",
    ]

    jsp_content = get_file_content(jsp_file)
    php_content = get_file_content(php_file)
    jspx_content = get_file_content(jspx_file)
    
    # 获取scriptlet标签内的内容
    """ scriptlet_match = re.search(r'<jsp:scriptlet>(.*?)</jsp:scriptlet>', jsp_content, re.DOTALL)
    if scriptlet_match:
        scriptlet_content = scriptlet_match.group(1).strip()
    else:
        print("未找到<jsp:scriptlet>标签")
        return """
    
    
    # 测试1: Unicode混淆
    """ print("="*20 + " 测试1: Unicode混淆 (ratio=0.5) " + "="*20)
    obfuscated_content_1 = Unicode_Obfuscation(
        jsp_content,
        keywords_to_obfuscate,
        unicode_ratio=1.0
    )
    print(obfuscated_content_1)
    print("="*60 + "\n") """
    
    # 测试2: HTML实体混淆
    """ print("="*20 + " 测试2: HTML实体混淆 (ratio=0.5) " + "="*20)
    obfuscated_content_2 = HtmlEntities_Obfuscation(
        jspx_content,
        keywords_to_obfuscate,
        html_ratio=0.5
    )
    print(obfuscated_content_2)
    print("="*60 + "\n") """
    
    # 测试3: HTML实体+Unicode组合混淆
    """ print("="*20 + " 测试3: HTML实体+Unicode组合混淆 " + "="*20)
    obfuscated_content_3 = HtmlEntities_Unicode_Obfuscation(
        jspx_content, 
        keywords_to_obfuscate, 
        html_ratio=0.3, 
        unicode_ratio=0.3
    )
    print(obfuscated_content_3)
    print("="*60 + "\n") """

    # 测试CDATA混淆
    """ print("="*20 + " 测试CDATA混淆 " + "="*20)
    obfuscated_content_4 = CDATA_Obfuscation(
        jspx_content,
        keywords_to_obfuscate,
    )
    print(obfuscated_content_4)
    print("="*60 + "\n") """

    # 测试CDATA+Unicode混淆
    print("="*20 + " 测试CDATA+Unicode混淆 " + "="*20)
    obfuscated_content_5 = CDATA_Unicode_Obfuscation(
        jspx_content,
        keywords_to_obfuscate,
        unicode_ratio=0.5
    )
    print(obfuscated_content_5)
    print("="*60 + "\n")

    # 测试CDATA+HTML实体混淆
    """ print("="*20 + " 测试CDATA+HTML实体混淆 " + "="*20)
    obfuscated_content_6 = CDATA_HtmlEntities_Obfuscation(
        scriptlet_content,
        keywords_to_obfuscate,
        html_ratio=0.5
    )
    print(obfuscated_content_6)
    print("="*60 + "\n") """

    # 测试CDATA+HTML实体混淆
    """ print("="*20 + " 测试CDATA+HTML实体混淆 " + "="*20)
    obfuscated_content_6 = jspx_obfuscation(
        jsp_content,
        keywords_to_obfuscate,
        method="cdata_html",
        html_ratio=0.5
    )
    print(obfuscated_content_6)
    print("="*60 + "\n") """

    # 测试修改变量
    """ print("="*20 + " 测试修改变量 " + "="*20)
    obfuscated_content_7 = patch_variable(
        jsp_content,
        method="random",
        prefix="$_"
    )
    print(obfuscated_content_7)
    print("="*60 + "\n") """

    # 测试XOR+Base64
    """ print("="*20 + " 测试XOR+Base64 " + "="*20)
    php_content = repalce_content(php_content, {"$param$": "pass"}).replace("<?php", "")
    print(php_content)
    xor_base64_content = xor_base64(php_content, "db_secret_salt")
    print(xor_base64_content)
    print("="*60 + "\n") """

    # 测试代码压缩
    """ print("="*20 + " 测试代码压缩 " + "="*20)
    code_compressed_content = code_compress(php_content)
    print(code_compressed_content)
    print("="*60 + "\n") """

if __name__ == "__main__":
    main()
