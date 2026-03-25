import os


class AspPayload:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.payload_dir = os.path.join(self.base_dir, "payload")

    def _patch_payload(self, payload_text, secret_key, param_name, cookie_name):
        placeholders = {
            "$SECRET_KEY$": secret_key or "",
            "$PARAM_NAME$": param_name or "",
            "$COOKIE_NAME$": cookie_name or "",
        }

        replaced = {key: 0 for key in placeholders.keys()}
        for key, value in placeholders.items():
            if key in payload_text:
                payload_text = payload_text.replace(key, value)
                replaced[key] += 1

        missing = [k for k, v in replaced.items() if v == 0]
        if missing:
            raise ValueError(f"placeholders not found in payload: {', '.join(missing)}")
        """ with open(os.path.join(self.payload_dir, "mainPayload_patched.asp"), "w", encoding="utf-8", errors="ignore") as file:
            file.write(payload_text) """
        return payload_text

    def getPayload(
        self,
        payload_name,
        secret_key=None,
        param_name=None,
        cookie_name=None
    ):
        payload_file = os.path.join(self.payload_dir, f"{payload_name}.asp")
        with open(payload_file, "r", encoding="utf-8", errors="ignore") as file:
            payload_text = file.read()

        if "mainPayload" in payload_name:
            payload_text = self._patch_payload(
                payload_text, secret_key, param_name, cookie_name
            )

        # Force CRLF line endings for VBScript compatibility
        payload_text = payload_text.replace("\r\n", "\n").replace("\n", "\r\n")

        # Ensure ASCII-only payload to avoid VBScript ExecuteGlobal parse errors.
        payload_text = payload_text.encode("ascii", errors="ignore").decode("ascii")

        return payload_text.encode("utf-8")

def main():
    payload = AspPayload()
    payload_content = payload.getPayload("mainPayload", "3c6e0b8a9c15224a", "pass", "X-Request-ID")
    print(payload_content)



if __name__ == "__main__":
    main()
