import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from io import BytesIO
import gzip

class encryptPayload:
    def __init__(self,key):
        self.key = key
        self.cipher = AES.new(self.key, AES.MODE_ECB)
        # 使用pkcs7填充
    
    def encryptAesBase64(self, payload):
        #print(f"[DEBUG] AES密钥: {self.key}")
        
        # 检查payload是否已经是bytes类型
        if isinstance(payload, bytes):
            data_to_encrypt = payload
            #print(f"[DEBUG] 原始payload大小: {len(payload)} bytes")
        else:
            data_to_encrypt = payload.encode('utf-8')
            #print(f"[DEBUG] 原始payload大小: {len(payload)} chars")
            
        #print(f"[DEBUG] 加密前数据大小: {len(data_to_encrypt)} bytes")
        
        # 使用标准PKCS7填充（对于AES 16字节块，PKCS7与PKCS5等效）
        padded_data = pad(data_to_encrypt, AES.block_size)
        #print(f"[DEBUG] 填充后数据大小: {len(padded_data)} bytes")
        
        # AES加密
        encrypted_data = self.cipher.encrypt(padded_data)
        #print(f"[DEBUG] 加密后数据大小: {len(encrypted_data)} bytes")
        
        # Base64编码
        result = base64.b64encode(encrypted_data).decode('utf-8')
        #print(f"[DEBUG] Base64编码后长度: {len(result)} chars")
        
        return result
    
    def encryptAesRaw(self, payload):
        print(f"[DEBUG] AES密钥: {self.key}")
        
        # 检查payload是否已经是bytes类型
        if isinstance(payload, bytes):
            data_to_encrypt = payload
            print(f"[DEBUG] 原始payload大小: {len(payload)} bytes")
        else:
            data_to_encrypt = payload.encode('utf-8')
            print(f"[DEBUG] 原始payload大小: {len(payload)} chars")
            
        print(f"[DEBUG] 加密前数据大小: {len(data_to_encrypt)} bytes")
        
        # 使用标准PKCS7填充（对于AES 16字节块，PKCS7与PKCS5等效）
        padded_data = pad(data_to_encrypt, AES.block_size)
        print(f"[DEBUG] 填充后数据大小: {len(padded_data)} bytes")
        
        # AES加密
        encrypted_data = self.cipher.encrypt(padded_data)
        print(f"[DEBUG] 加密后数据大小: {len(encrypted_data)} bytes")
        
        # 直接返回原始加密数据，不进行Base64编码
        print(f"[DEBUG] 返回原始加密数据大小: {len(encrypted_data)} bytes")
        
        return encrypted_data

    def decryptAesRaw(self, payload):
        try:
            print(f"[DEBUG] 开始解密，原始加密数据大小: {len(payload)} bytes")
            
            # AES解密
            decrypted_padded = self.cipher.decrypt(payload)
            #print(f"[DEBUG] AES解密后数据大小: {len(decrypted_padded)} bytes")
            
            # 移除PKCS7填充
            decrypted_data = unpad(decrypted_padded, AES.block_size)
            #print(f"[DEBUG] 去除填充后数据大小: {len(decrypted_data)} bytes")
            
            return decrypted_data
            
        except Exception as e:
            print(f"[ERROR] 解密失败: {e}")
            raise e
            

    def decryptAesBase64(self, payload):
        try:
            #print(f"[DEBUG] 开始解密，Base64数据长度: {len(payload)} chars")
            
            # 重新添加必要的填充符以正确解码（兼容无填充符的Base64）
            missing_padding = (4 - len(payload) % 4) % 4
            if missing_padding:
                payload += '=' * missing_padding
            
            # Base64解码
            encrypted_data = base64.b64decode(payload.encode('utf-8'))
            #print(f"[DEBUG] Base64解码后数据大小: {len(encrypted_data)} bytes")
            
            # AES解密
            decrypted_padded = self.cipher.decrypt(encrypted_data)
            #print(f"[DEBUG] AES解密后数据大小: {len(decrypted_padded)} bytes")
            
            # 移除PKCS7填充
            decrypted_data = unpad(decrypted_padded, AES.block_size)
            #print(f"[DEBUG] 去除填充后数据大小: {len(decrypted_data)} bytes")
            
            return decrypted_data
            
        except Exception as e:
            print(f"[ERROR] 解密失败: {e}")
            raise e

    def encryptPayloadFile(self,payload_file_path):
        try:
            with open(payload_file_path, "rb") as file:
                payload = file.read()
            encrypted_payload = self.encryptAesBase64(payload)
            print("使用aes密钥:",self.key);
            print(encrypted_payload)
            print("加密后的字节大小是：",len(encrypted_payload))
        except Exception as e:
            print(f"Error encrypting payload file: {e}")
            return None

    def gzip_compress(self, data):
        """gzip压缩"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
            f.write(data)
        return buffer.getvalue()    

    def gzip_decompress(self, data):
        """gzip解压"""
        try:
            return gzip.decompress(data)
        except Exception as e:
            print(f"Gzip解压失败: {e}")
            return data
    
    def encryptXorBase64(self, data: any) -> str:
        """XOR加密后Base64编码 - 一步到位完成加密和编码"""
        
        # 将字符串转换为字节数组进行处理
        if isinstance(data, bytes):
            data_bytes = data
        else:
            data_bytes = data.encode('utf-8')
            
        encrypted = bytearray()
        for i in range(len(data_bytes)):
            # PHP端使用 $i+1&15，&15等价于%16
            key_index = (i + 1) & 15
            if key_index < len(self.key):
                key_byte = self.key[key_index]
            else:
                key_byte = 0  # PHP中超出范围的字符串访问返回空字符串
            
            # 异或加密
            encrypted.append(data_bytes[i] ^ key_byte)
        
        # 直接返回Base64编码的字符串
        return base64.b64encode(bytes(encrypted)).decode('utf-8')
    
    def decryptXorBase64(self, data: any) -> bytes:
        """Base64解码后XOR解密 - 返回bytes数据"""
        
        
        # 如果是字符串，先进行Base64解码
        if isinstance(data, str):
            data_bytes = base64.b64decode(data)
        else:
            data_bytes = data
        
        decrypted = bytearray()
        for i in range(len(data_bytes)):
            # PHP端使用 $i+1&15，&15等价于%16
            key_index = (i + 1) & 15
            if key_index < len(self.key):
                key_byte = self.key[key_index]
            else:
                key_byte = 0  # PHP中超出范围的字符串访问返回空字符串
            
            # 异或解密（XOR是对称的，加密和解密使用相同的操作）
            decrypted.append(data_bytes[i] ^ key_byte)
        
        return bytes(decrypted)
    
    def encryptXorRaw(self, data: any) -> bytes:
        """XOR加密 - 返回原始加密后的bytes数据"""

        
        # 将字符串转换为字节数组进行处理
        if isinstance(data, bytes):
            data_bytes = data
        else:
            data_bytes = data.encode('utf-8')
            
        encrypted = bytearray()
        for i in range(len(data_bytes)):
            # PHP端使用 $i+1&15，&15等价于%16
            key_index = (i + 1) & 15
            if key_index < len(self.key):
                # 如果key是bytes类型，索引返回int；如果是str类型，索引返回str，需要ord()转换
                key_byte = self.key[key_index]
            else:
                key_byte = 0  # PHP中超出范围的字符串访问返回空字符串
            
            # 异或加密
            encrypted.append(data_bytes[i] ^ key_byte)
        
        # 返回原始加密数据
        return bytes(encrypted)
    
    def decryptXorRaw(self, data: bytes) -> bytes:
        """XOR解密 - 解密原始bytes数据，返回解密后的bytes"""

        
        if not isinstance(data, bytes):
            raise TypeError("输入数据必须是bytes类型")
        
        decrypted = bytearray()
        for i in range(len(data)):
            # PHP端使用 $i+1&15，&15等价于%16
            key_index = (i + 1) & 15
            if key_index < len(self.key):   
                key_byte = self.key[key_index]
            else:
                key_byte = 0  # PHP中超出范围的字符串访问返回空字符串
            
            # 异或解密（XOR是对称的，加密和解密使用相同的操作）
            decrypted.append(data[i] ^ key_byte)
        
        return bytes(decrypted)
            
    def printKey(self):
        print(self.key)
    
def main():
    encryptPayload("rebeyond").encryptPayloadFile("request3.class")

