"""
全局配置集中管理

从 webshell_config.json 读取并暴露常用配置项的常量，便于各模块直接引用。
不再依赖 core_management_api，避免循环导入。
"""

import json
import os

# 数据与配置文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
GLOBAL_CONFIG_FILE = os.path.join(DATA_DIR, "webshell_config.json")
os.makedirs(DATA_DIR, exist_ok=True)

# 全局配置默认值
DEFAULT_GLOBAL_CONFIG = {
    "upload": {
        "chunkMbSize": 1.0,
        "delaySeconds": 0.5,
        "maxRetries": 5,
        "autoSwitchSize": 10,
        "enableChunkSizeVariation": False,
        "chunkSizeVariationMb": 0.2,
    },
    "download": {
        "chunkKbSize": 512,
        "timeoutSeconds": 1.0,
        "enableChunkSizeVariation": False,
        "chunkSizeVariationKb": 128,
        "autoSwitchSize": 50,
    },
    "general": {
        "requestTimeout": 60,
        "autoRefreshInterval": 0,
        "enableDebugLog": False,
    },
    "jspFunction": {
        "classnameObfuscation": "random",  # random|dictionary|specified|none
        "specifiedClassname": "",
    },
    "llm": {
        "provider": "openai",
        "baseUrl": "",
        "model": "",
        "apiKey": "",
        "temperature": 0.1,
    },
}

# 全局缓存的配置字典
global_config = {}

# 上传配置
UPLOAD_CHUNK_MB_SIZE = DEFAULT_GLOBAL_CONFIG["upload"]["chunkMbSize"]
UPLOAD_DELAY_SECONDS = DEFAULT_GLOBAL_CONFIG["upload"]["delaySeconds"]
UPLOAD_MAX_RETRIES = DEFAULT_GLOBAL_CONFIG["upload"]["maxRetries"]
UPLOAD_AUTO_SWITCH_SIZE = DEFAULT_GLOBAL_CONFIG["upload"]["autoSwitchSize"]
UPLOAD_ENABLE_CHUNK_VARIATION = DEFAULT_GLOBAL_CONFIG["upload"]["enableChunkSizeVariation"]
UPLOAD_CHUNK_VARIATION_MB = DEFAULT_GLOBAL_CONFIG["upload"]["chunkSizeVariationMb"]

# 下载配置
DOWNLOAD_CHUNK_KB_SIZE = DEFAULT_GLOBAL_CONFIG["download"]["chunkKbSize"]
DOWNLOAD_TIMEOUT_SECONDS = DEFAULT_GLOBAL_CONFIG["download"]["timeoutSeconds"]
DOWNLOAD_ENABLE_CHUNK_VARIATION = DEFAULT_GLOBAL_CONFIG["download"]["enableChunkSizeVariation"]
DOWNLOAD_CHUNK_VARIATION_KB = DEFAULT_GLOBAL_CONFIG["download"]["chunkSizeVariationKb"]
DOWNLOAD_AUTO_SWITCH_SIZE = DEFAULT_GLOBAL_CONFIG["download"]["autoSwitchSize"]

# 通用配置
GENERAL_REQUEST_TIMEOUT = DEFAULT_GLOBAL_CONFIG["general"]["requestTimeout"]
GENERAL_AUTO_REFRESH_INTERVAL = DEFAULT_GLOBAL_CONFIG["general"]["autoRefreshInterval"]
GENERAL_ENABLE_DEBUG_LOG = DEFAULT_GLOBAL_CONFIG["general"]["enableDebugLog"]

# JSP功能配置
JSP_CLASSNAME_OBFUSCATION = DEFAULT_GLOBAL_CONFIG["jspFunction"]["classnameObfuscation"]
JSP_SPECIFIED_CLASSNAME = DEFAULT_GLOBAL_CONFIG["jspFunction"]["specifiedClassname"]

# LLM配置
LLM_TEMPERATURE = DEFAULT_GLOBAL_CONFIG["llm"]["temperature"]
LLM_MAX_COMPILE_ATTEMPTS = 3
LLM_BASE_URL = DEFAULT_GLOBAL_CONFIG["llm"]["baseUrl"]
LLM_MODEL = DEFAULT_GLOBAL_CONFIG["llm"]["model"]
LLM_API_KEY = DEFAULT_GLOBAL_CONFIG["llm"]["apiKey"]
LLM_PROVIDER = DEFAULT_GLOBAL_CONFIG["llm"]["provider"]



def _merge_dict(defaults: dict, incoming: dict) -> dict:
    """浅层递归合并字典，incoming优先"""
    result = defaults.copy()
    for k, v in incoming.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _merge_dict(result[k], v)
        else:
            result[k] = v
    return result


def load_global_config() -> dict:
    """加载全局配置"""
    if os.path.exists(GLOBAL_CONFIG_FILE):
        try:
            with open(GLOBAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return _merge_dict(DEFAULT_GLOBAL_CONFIG, raw)
        except Exception as e:
            print(f"[DEBUG] 加载全局配置失败，使用默认值: {e}")
    return DEFAULT_GLOBAL_CONFIG.copy()


def save_global_config(config: dict) -> bool:
    """保存全局配置"""
    try:
        normalized_config = normalize_global_config(config)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(GLOBAL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(normalized_config, f, ensure_ascii=False, indent=2)
        _assign_globals(normalized_config)
        return True
    except Exception as e:
        print(f"[ERROR] 保存全局配置失败: {e}")
        return False


def normalize_global_config(data: dict) -> dict:
    """校验并规范化全局配置"""
    incoming = data or {}
    merged = _merge_dict(DEFAULT_GLOBAL_CONFIG, incoming)

    def _float(val, default):
        try:
            return float(val)
        except Exception:
            return default

    def _int(val, default):
        try:
            return int(val)
        except Exception:
            return default

    up = merged.get("upload", {})
    up["chunkMbSize"] = _float(up.get("chunkMbSize", 1.0), 1.0)
    up["delaySeconds"] = _float(up.get("delaySeconds", 0.5), 0.5)
    up["maxRetries"] = _int(up.get("maxRetries", 5), 5)
    up["autoSwitchSize"] = _int(up.get("autoSwitchSize", 10), 10)
    up["enableChunkSizeVariation"] = bool(up.get("enableChunkSizeVariation", False))
    up["chunkSizeVariationMb"] = _float(up.get("chunkSizeVariationMb", 0.2), 0.2)
    merged["upload"] = up

    dl = merged.get("download", {})
    dl["chunkKbSize"] = _int(dl.get("chunkKbSize", 512), 512)
    dl["timeoutSeconds"] = _float(dl.get("timeoutSeconds", 1.0), 1.0)
    dl["enableChunkSizeVariation"] = bool(dl.get("enableChunkSizeVariation", False))
    dl["chunkSizeVariationKb"] = _int(dl.get("chunkSizeVariationKb", 128), 128)
    dl["autoSwitchSize"] = _int(dl.get("autoSwitchSize", 50), 50)
    merged["download"] = dl

    gen = merged.get("general", {})
    gen["requestTimeout"] = _int(gen.get("requestTimeout", 60), 60)
    gen["autoRefreshInterval"] = _int(gen.get("autoRefreshInterval", 0), 0)
    gen["enableDebugLog"] = bool(gen.get("enableDebugLog", False))
    merged["general"] = gen

    jsp_fn = merged.get("jspFunction", {})
    jsp_fn["classnameObfuscation"] = (jsp_fn.get("classnameObfuscation") or "random").lower()
    if jsp_fn["classnameObfuscation"] not in ["random", "dictionary", "specified", "none"]:
        jsp_fn["classnameObfuscation"] = "random"
    jsp_fn["specifiedClassname"] = (jsp_fn.get("specifiedClassname") or "").strip()
    merged["jspFunction"] = jsp_fn

    llm = merged.get("llm", {})
    llm["provider"] = (llm.get("provider") or "openai").strip()
    if llm["provider"] not in ["openai", "codex_proxy", "gemini_proxy"]:
        llm["provider"] = "openai"
    llm["baseUrl"] = (llm.get("baseUrl") or "").strip()
    llm["model"] = (llm.get("model") or "").strip()
    llm["apiKey"] = (llm.get("apiKey") or "").strip()
    llm["temperature"] = _float(llm.get("temperature", 0.1), 0.1)
    if llm["temperature"] < 0:
        llm["temperature"] = 0.0
    if llm["temperature"] > 2:
        llm["temperature"] = 2.0
    llm.pop("maxCompileAttempts", None)
    merged["llm"] = llm

    return merged


def _assign_globals(cfg: dict):
    global global_config
    global_config = cfg

    up = cfg.get("upload", {})
    down = cfg.get("download", {})
    gen = cfg.get("general", {})

    globals()["UPLOAD_CHUNK_MB_SIZE"] = up.get("chunkMbSize", UPLOAD_CHUNK_MB_SIZE)
    globals()["UPLOAD_DELAY_SECONDS"] = up.get("delaySeconds", UPLOAD_DELAY_SECONDS)
    globals()["UPLOAD_MAX_RETRIES"] = up.get("maxRetries", UPLOAD_MAX_RETRIES)
    globals()["UPLOAD_AUTO_SWITCH_SIZE"] = up.get("autoSwitchSize", UPLOAD_AUTO_SWITCH_SIZE)
    globals()["UPLOAD_ENABLE_CHUNK_VARIATION"] = up.get(
        "enableChunkSizeVariation", UPLOAD_ENABLE_CHUNK_VARIATION
    )
    globals()["UPLOAD_CHUNK_VARIATION_MB"] = up.get("chunkSizeVariationMb", UPLOAD_CHUNK_VARIATION_MB)

    globals()["DOWNLOAD_CHUNK_KB_SIZE"] = down.get("chunkKbSize", DOWNLOAD_CHUNK_KB_SIZE)
    globals()["DOWNLOAD_TIMEOUT_SECONDS"] = down.get("timeoutSeconds", DOWNLOAD_TIMEOUT_SECONDS)
    globals()["DOWNLOAD_ENABLE_CHUNK_VARIATION"] = down.get(
        "enableChunkSizeVariation", DOWNLOAD_ENABLE_CHUNK_VARIATION
    )
    globals()["DOWNLOAD_CHUNK_VARIATION_KB"] = down.get(
        "chunkSizeVariationKb", DOWNLOAD_CHUNK_VARIATION_KB
    )
    globals()["DOWNLOAD_AUTO_SWITCH_SIZE"] = down.get("autoSwitchSize", DOWNLOAD_AUTO_SWITCH_SIZE)

    globals()["GENERAL_REQUEST_TIMEOUT"] = gen.get("requestTimeout", GENERAL_REQUEST_TIMEOUT)
    globals()["GENERAL_AUTO_REFRESH_INTERVAL"] = gen.get(
        "autoRefreshInterval", GENERAL_AUTO_REFRESH_INTERVAL
    )
    globals()["GENERAL_ENABLE_DEBUG_LOG"] = gen.get("enableDebugLog", GENERAL_ENABLE_DEBUG_LOG)

    jsp_fn = cfg.get("jspFunction", {})
    globals()["JSP_CLASSNAME_OBFUSCATION"] = jsp_fn.get(
        "classnameObfuscation", JSP_CLASSNAME_OBFUSCATION
    )
    globals()["JSP_SPECIFIED_CLASSNAME"] = jsp_fn.get(
        "specifiedClassname", JSP_SPECIFIED_CLASSNAME
    )

    llm = cfg.get("llm", {})
    globals()["LLM_PROVIDER"] = llm.get("provider", LLM_PROVIDER)
    globals()["LLM_BASE_URL"] = llm.get("baseUrl", LLM_BASE_URL)
    globals()["LLM_MODEL"] = llm.get("model", LLM_MODEL)
    globals()["LLM_API_KEY"] = llm.get("apiKey", LLM_API_KEY)
    globals()["LLM_TEMPERATURE"] = llm.get("temperature", LLM_TEMPERATURE)
    globals()["LLM_MAX_COMPILE_ATTEMPTS"] = 3


def reload_global_config():
    """重新加载配置并更新导出的常量"""
    cfg = load_global_config()
    _assign_globals(cfg)


# 模块加载时初始化
reload_global_config()
