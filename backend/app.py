from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
import sys
import builtins
import webbrowser
import threading
import time
import typer
from waitress import serve

# ====== 调试/端口默认值（可被Typer解析的CLI参数覆盖） ======
DEBUG_ENABLED = os.getenv('ETERNITY_DEBUG') == '1'
DEFAULT_PORT = 5001
try:
    DEFAULT_PORT = int(os.getenv('ETERNITY_PORT', '5001'))
except ValueError:
    DEFAULT_PORT = 5001
PORT = DEFAULT_PORT

# 早期识别命令行 --debug，用于模块初始化阶段的调试输出
if any(arg.startswith('--debug') for arg in sys.argv):
    DEBUG_ENABLED = True

# 过滤调试输出：只有在 DEBUG_ENABLED 时才打印以 [DEBUG] 或 [REQUEST] 开头的内容
_original_print = builtins.print


def _debug_filtered_print(*args, **kwargs):
    if DEBUG_ENABLED:
        return _original_print(*args, **kwargs)
    if args:
        first = str(args[0]).lstrip()
        if first.startswith('[DEBUG]') or first.startswith('[REQUEST]' or first.startswith('[ERROR]')):
            return
    return _original_print(*args, **kwargs)

builtins.print = _debug_filtered_print

# 添加当前目录到模块搜索路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# 检查是否为打包环境 (支持 PyInstaller 和 Nuitka)
def is_packaged():
    # PyInstaller 会设置 sys.frozen
    if getattr(sys, 'frozen', False):
        return True
    
    # Nuitka 检测：检查可执行文件的扩展名
    exe_path = sys.argv[0]
    exe_name = os.path.basename(exe_path)
    

    
    # 如果不是 .py 文件，很可能是打包后的可执行文件
    if not exe_name.endswith('.py'):
        return True
    
    return False

IS_PACKAGED = is_packaged()

# 确定静态文件夹路径（仅在打包环境中使用）
def get_static_folder():
    if IS_PACKAGED:
        # 为 PyInstaller 和 Nuitka 提供兼容的路径解决方案
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller: _MEIPASS是解压后的临时目录
            base_path = sys._MEIPASS
        else:
            # Nuitka (standalone): 可执行文件所在目录
            base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        
        static_path = os.path.join(base_path, 'dist')
        print(f"[DEBUG]: 打包环境静态文件路径 - {static_path}")
        print(f"[DEBUG]: 路径是否存在 - {os.path.exists(static_path)}")
        
        return static_path
    else:
        # 开发环境不设置静态文件夹
        return None

static_folder = get_static_folder()

# 创建Flask应用实例
if IS_PACKAGED:
    # 生产打包环境（Nuitka打包）：配置静态文件托管
    app = Flask(__name__, static_folder=static_folder, static_url_path='')
else:
    # 开发环境：不托管静态文件
    app = Flask(__name__)

CORS(app)  # 启用跨域支持


@app.before_request
def _record_request_start_time():
    """记录每个请求的开始时间，便于后续日志打印耗时"""
    request.environ['request_start_time'] = time.perf_counter()


@app.after_request
def _log_request_summary(response):
    """Waitress 环境下手动输出请求摘要"""
    try:
        remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr) or '-'
        path = request.full_path.rstrip('?') if request.full_path else request.path
        start = request.environ.get('request_start_time')
        duration_ms = None
        if start is not None:
            duration_ms = (time.perf_counter() - start) * 1000
        log_line = f"[REQUEST] {remote_addr} {request.method} {path} -> {response.status_code}"
        if duration_ms is not None:
            log_line += f" ({duration_ms:.2f} ms)"
        print(log_line)
    except Exception as log_error:
        print(f"[ERROR] 请求日志记录失败: {log_error}")
    return response


# API状态检查路由
@app.route('/api/status')
def api_status():
    """API服务器状态检查"""
    return jsonify({
        'status': 'ok',
        'message': 'Eternity Backend API Service',
        'mode': 'packaged' if IS_PACKAGED else 'development'
    })

# 导入webshell管理模块
from router_modules.webshellmanager_router.webshellmanager_api import register_all_blueprints

# 注册webshell管理模块的蓝图（API路由优先注册）
register_all_blueprints(app)


# 前端路由处理函数
def handle_frontend_routes():
    """在所有API路由注册后，注册前端路由处理"""
    if IS_PACKAGED:
        # 使用errorhandler来处理404，这样不会干扰已注册的路由
        @app.errorhandler(404)
        def handle_404(e):
            """处理404错误，用于SPA路由支持"""
            from flask import request
            path = request.path[1:]  # 去掉开头的 /
            
            print(f"[DEBUG]: 404处理 - 请求路径: '{request.path}'")
            
            # 如果是API路径，返回正常的404错误
            if request.path.startswith('/api/'):
                print(f"[ERROR]: API路径404: {request.path}")
                return jsonify({'error': 'API endpoint not found'}), 404
            
            try:
                # 检查是否为静态资源文件
                static_extensions = {'.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.json', '.txt'}
                if path:
                    _, ext = os.path.splitext(path.lower())
                    if ext in static_extensions:
                        # 静态资源不存在，返回真正的404
                        return jsonify({'error': f'Static file not found: {path}'}), 404
                
                # 对于前端路由（如 /webshellManager），返回 index.html
                index_path = os.path.join(app.static_folder, 'index.html')
                if os.path.exists(index_path):
                    print(f"[DEBUG]: 返回 index.html 用于前端路由: '{request.path}'")
                    return send_from_directory(app.static_folder, 'index.html')
                else:
                    print(f"[ERROR]: index.html 不存在: {index_path}")
                    return jsonify({
                        'status': 'error',
                        'message': 'Frontend files not found',
                        'static_folder': app.static_folder,
                        'requested_path': request.path
                    }), 404
                    
            except Exception as e:
                print(f"[ERROR]: 404处理出错: {e}")
                return jsonify({
                    'status': 'error',
                    'message': f'Error in 404 handler: {str(e)}',
                    'requested_path': request.path
                }), 500
        
        # 注册根路由
        @app.route('/')
        def serve_index():
            """提供根路径的 index.html"""
            try:
                return send_from_directory(app.static_folder, 'index.html')
            except Exception as e:
                return jsonify({
                    'status': 'error', 
                    'message': f'Cannot serve index.html: {str(e)}',
                    'static_folder': app.static_folder
                }), 500
    else:
        # 开发环境：只提供API状态信息
        @app.route('/')
        def index():
            """开发环境根路由"""
            return jsonify({
                'status': 'ok',
                'message': 'Eternity Backend API Service - Development Mode',
                'note': 'Frontend should be started separately with "npm run dev"',
                'api_docs': '/api/status'
            })

# 在所有API路由注册后，注册前端路由处理
handle_frontend_routes()

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)  # 等待服务器启动
    webbrowser.open(f'http://localhost:{PORT}')

def main(
    debug: bool = typer.Option(
        False,
        "--debug",
        help="启用调试日志输出"
    ),
    port: int = typer.Option(DEFAULT_PORT, "--port", "-p", help="指定服务器端口，默认5001")
):
    """启动 Eternity 后端服务"""
    global DEBUG_ENABLED, PORT

    DEBUG_ENABLED = bool(debug) or os.getenv('ETERNITY_DEBUG') == '1'
    os.environ['ETERNITY_DEBUG'] = '1' if DEBUG_ENABLED else '0'

    try:
        PORT = int(port)
    except (TypeError, ValueError):
        print(f"[DEBUG] 无效的端口号 '{port}'，使用默认端口 {DEFAULT_PORT}")
        PORT = DEFAULT_PORT

    if PORT <= 0 or PORT > 65535:
        print(f"[DEBUG] 端口超出范围 '{PORT}'，使用默认端口 {DEFAULT_PORT}")
        PORT = DEFAULT_PORT

    os.environ['ETERNITY_PORT'] = str(PORT)

    if DEBUG_ENABLED:
        print("Debug logging enabled (ETERNITY_DEBUG=1)")
    print("正在启动 MatouWebshell 应用...")
    
    if IS_PACKAGED:
        # 打包环境
        print("[DEBUG] 运行模式: 编译版本")
        print(f"[DEBUG] 静态文件夹路径: {static_folder}")
        print(f"服务器将运行在: http://localhost:{PORT}")
        
        # 检查静态文件是否存在
        if static_folder and os.path.exists(static_folder):
            print("[DEBUG] 前端文件已找到，将自动托管前端页面")
            
            # 在新线程中延迟打开浏览器
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
        else:
            print("[DEBUG] 前端文件未找到")
            print(f"[DEBUG] 预期路径: {static_folder}")
    else:
        # 开发环境
        print("[DEBUG] 运行模式: 开发环境")
        print(f"[DEBUG] 后端API服务器将运行在: http://localhost:{PORT}")
        print("[DEBUG] 提示: 请在项目根目录运行 'npm run dev' 来启动前端开发服务器")
        print(f"[DEBUG] API状态检查: http://localhost:{PORT}/api/status")
    
    try:
        # 使用 Waitress 启动服务器（生产级WSGI服务器）
        print("服务器启动中...")
        serve(app, host='0.0.0.0', port=PORT)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")


if __name__ == '__main__':
    typer.run(main)

