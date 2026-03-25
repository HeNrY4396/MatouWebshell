import struct
class ReqParameter:
    """PHP请求参数格式化类，类似于JavaShell中的ReqParameter"""
    
    def __init__(self):
        self.parameters = {}
    
    def add(self, key, value):
        """添加参数"""
        if isinstance(value, str):
            self.parameters[key] = value.encode('utf-8')
        else:
            self.parameters[key] = value
    
    def format(self):
        """
        格式化参数为payload.java期望的格式
        
        payload.java的formatParameter()期望的格式：
        1. gzip压缩的数据流
        2. 每个参数的格式：key的字节 + 分隔符(byte=2) + value长度(4字节小端) + value数据
        """
        result = b""
        for key, value in self.parameters.items():
            # 写入key的每个字节
            key_bytes = key.encode('utf-8')
            result += key_bytes
            
            # 写入分隔符 (byte值为2)
            result += bytes([2])
            
            # 写入value长度 (4字节小端字节序)
            value_len = len(value)
            result += struct.pack('<I', value_len)  # '<I' = 小端无符号int
            
            # 写入value数据
            result += value
        
        return result