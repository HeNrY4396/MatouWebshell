#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebShell管理API v2 - 整合版

这个文件是架构优化后的主入口文件，整合了所有拆分的模块：
- 核心管理功能 (core_management_api.py)
- 通用webshell功能 (generic_shell_api.py) 
- JSP专属功能 (java_shell_api.py)

通过Flask Blueprint实现模块化管理，便于维护和扩展。
"""

from flask import Blueprint
from .core_management_api import core_management_bp
from .java_shell_api import java_shell_bp
from .php_shell_api import php_shell_bp
from .csharp_shell_api import csharp_shell_bp
from .asp_shell_api import asp_shell_bp

# 创建主蓝图，整合所有子模块
webshellmanager_v2_bp = Blueprint('webshell_v2', __name__, url_prefix='/api/webshell')

# 注册所有子蓝图，使用不同的前缀避免路由冲突
def register_all_blueprints(app):
    """
    注册所有webshell管理相关的蓝图到Flask应用
    
    Args:
        app: Flask应用实例
    """
    try:
        # 注册核心管理功能（基础路径）
        app.register_blueprint(core_management_bp)
        print("[DEBUG] 已注册webshell管理功能API")
           
        # 注册JSP专属功能
        app.register_blueprint(java_shell_bp)
        
        # 注册PHP专属功能
        app.register_blueprint(php_shell_bp)

        # 注册CSharp专属功能
        app.register_blueprint(csharp_shell_bp)

        # 注册ASP专属功能
        app.register_blueprint(asp_shell_bp)
                
        return True
        
    except Exception as e:
        print(f"[ERROR] 注册WebShell API模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# 向后兼容性：导出原有的蓝图名称
webshellmanager_bp = webshellmanager_v2_bp


def get_api_statistics():
    """
    获取API统计信息
    
    Returns:
        dict: 包含各模块API数量的统计信息
    """
    return {
        'core_management': {
            'description': '核心管理功能',
            'endpoints': 11,
            'features': ['webshell列表管理', '连接管理', '生成功能', '缓存管理']
        },
        'generic_shell': {
            'description': '通用webshell功能', 
            'endpoints': 13,
            'features': ['命令执行', '文件管理', '压缩解压', '远程下载', '属性设置']
        },
        'java_shell': {
            'description': 'JSP专属功能',
            'endpoints': 21,
            'features': ['内存马管理', '内网穿透', '数据库管理']
        },
        'php_shell': {
            'description': 'PHP专属功能',
            'endpoints': 1,
            'features': ['命令执行']
        },
        'total_endpoints': 46,
        'architecture_benefits': [
            '模块化设计，便于维护',
            '工厂模式，支持多类型webshell',
            '统一接口，易于扩展',
            '类型安全，错误处理完善'
        ]
    }


if __name__ == '__main__':
    # 测试模式：打印API信息
    stats = get_api_statistics()
    print(f"WebShell管理API v2 统计信息:")
    print(f"- 总计API端点: {stats['total_endpoints']} 个")
    for module, info in stats.items():
        if isinstance(info, dict) and 'endpoints' in info:
            print(f"- {info['description']}: {info['endpoints']} 个端点")
            print(f"  功能: {', '.join(info['features'])}")
    print(f"- 架构优势: {', '.join(stats['architecture_benefits'])}")
