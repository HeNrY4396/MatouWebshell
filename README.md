# 项目简介

MatouWebshell 是一款基于 Vue 3 和 Python 开发的高隐蔽性开源 Webshell 管理与利用平台。项目基于哥斯拉（Godzilla）的设计思路进行二次开发，重点移除了通信流量的强特征，支持用户自定义请求格式与响应加密类型，能够完美伪装成正常业务流量以规避检测。

**💡 二次开发友好**：作为一款完全开源的工具，MatouWebshell 拥有良好的架构和极高的扩展性。你可以根据实战需求，轻松地修改或新增各类语言的 Payload、自定义变量池与代码混淆规则，甚至编写属于你自己的自动化利用模块。

- **🚀 多语言支持**：内置生成与连接 PHP、JSP/JSPX、ASP、C# 类型的 Webshell。
- **🛡️ 极致隐蔽**：支持自定义通信流量格式（如伪装成图片请求等）、响应加密类型、变量池替换以及代码关键字混淆（如 JSPX 的 CDATA+Unicode 编码混淆）。
- **💻 丰富的基础功能**：交互式命令行终端、高级文件管理（支持大文件分块传输、压缩/解压与权限修改）、数据库连接与 SQL 执行。
- **🕸️ 内网穿透**：提供 SOCKS 代理（支持 IP 白名单）、端口映射、反向 DMZ（JSP）等多种内网穿透模式。
- **💉 高级利用**：支持 JSP 内存马（Servlet/Filter）的注入、注册组件信息获取与卸载。
- **🛠️ 极易扩展**：代码结构清晰，方便用户二次开发修改 Payload 或集成各类框架利用链工具。



# 项目运行

## 1. 源码运行

**安装 Python 后端依赖**
```bash
cd backend
pip install -r requirements.txt
```

**安装 Vue 前端依赖**
```bash
npm install
```

**安装 Mono 工具集**（用于修改 C# Payload，可选）
```bash
apt-get install -y --no-install-recommends mono-complete
```

**启动服务**
- 启动前端（项目根目录）：`npm run dev`
- 启动后端（backend 目录）：`python3 app.py`

## 2. ELF 二进制文件运行

由于项目使用 `GLIBC_2.31` 进行编译，建议在对应版本及以上的 Linux 系统上运行。
解压项目至目录，赋予 `app.bin` 可执行权限，支持如下启动参数：
- `--debug`：输出调试信息
- `--port`：指定服务端口

```bash
chmod +x app.bin
./app.bin --debug --port 6324
```
![image-20251216222303128](README/image-20251216222303128-17658949852952.png)	

随后在浏览器中访问：`http://localhost:6324/`
![image-20251216222452609](README/image-20251216222452609.png)	

## 3. Docker 镜像运行

**拉取 Docker 镜像**
```bash
docker pull henry404/matouwebshell
```

**运行 Docker 容器**
```bash
docker run -it --rm -p 5001:5001 -v matou_data:/app/router_modules/webshellmanager_router/data henry404/matouwebshell
```

---

# 📖MatouWebshell功能指南

## 🛡️ Webshell 管理

### 1. Webshell 生成

**基础配置**

- **参数名**：初始化阶段，客户端需将加密的 payload 以表单格式发送至服务端。如 POST 请求：`{参数名}={encryptedPayload}`
- **Webshell 类型**：支持 PHP、JSP/JSPX、ASP 和 C#。
- **CookieName**：相当于 Webshell 的密钥，用于激活 Webshell 的功能开关。
- **标识符替换功能**：替换指定前缀的变量标识符，支持“随机生成”和“变量池文件”。（变量池文件位于 `router_modules/webshellmanager_router/webshell` 目录，**强烈建议用户根据实战场景自行修改变量池文件的标识符**）

![image-20251203132200086](README/image-20251203132200086.png)	

**高级选项**
不同 Webshell 类型对应的高级选项功能不同：
- **PHP**：支持模拟正常业务功能。启用后可选择对应的业务模板，将基础配置的 Payload 无缝嵌入到业务模板中。
![image-20251203133321374](README/image-20251203133321374.png)	

- **JSP/JSPX**：支持强大的关键字混淆功能。JSP 支持 Unicode 编码混淆；JSPX 则支持 Unicode 编码、CDATA 拆分、HTML 实体编码、HTML+Unicode 编码、CDATA+Unicode 编码和 CDATA+HTML 编码。
*示例：对关键字 `getAttribute` 进行 CDATA+Unicode 编码混淆，并可调节 Unicode 编码比率。*
![image-20251203134000016](README/image-20251203134000016.png)		

混淆后的关键字代码效果如下：
```jsp
 if (session.g<![CDATA[\u0065]]><![CDATA[\u0074\u0041\u0074t\u0072i\u0062]]><![CDATA[\u0075t\u0065]]>("$payload$") == null
```



**AI生成业务模板**

输入你想生成什么类型的模板需求，然后点击"AI生成", 生成代码可能需要一些时间(取决于你设置的AI模型生成内容的速度)

![image-20260409151210397](README/image-20260409151210397.png)



生成的模板代码和模板文件名会显示在下方，可点击 “保存至模板目录”将代码文件保存在至后端目录，然后再“基础配置”区域勾选你刚刚生成的模板文件

![image-20260409151546918](README/image-20260409151546918.png)		



### 2. Webshell 连接

**基本参数**
点击“添加 Webshell”按钮填写基本参数。注意：此处的“连接密码”仅用于加密通信流量，是可以随时变化的；而“Cookie 名称”才是真正激活 Webshell 功能的开关。
![image-20251217153806662](README/image-20251217153806662.png)
![image-20251204134922682](README/image-20251204134922682.png)	

**传输与加密（高度自定义）**
用户可以完全自定义通信的请求格式和响应加密类型。例如，选择请求格式为 `form`，响应加密类型为 `aes_base64`。
![image-20260320130007840](README/image-20260320130007840.png)		

**💡 自定义配置扩展**：支持用户通过修改 JSON 配置文件来自定义请求和响应的格式（配置文件存储在 `data` 目录下，以 `request_format_define.json` 命名）。支持多种占位符变量，其中 `${encrypted_data}` 变量为必填项，用于存放加密 Payload。*注：自定义响应格式目前仅支持 JSON 类型。*
![image-20260324234340620](README/image-20260324234340620.png)	
![image-20260324234253280](README/image-20260324234253280.png)	

*示例 1：请求格式为 XML，响应加密类型为 `aes_base64_json`，Payload 数据将使用 `aes_base64` 加密。*
![image-20251022213721485](README/image-20251022213721485.png)

*示例 2：请求格式为 form，响应格式为 PNG（完美伪装成正常图片请求）。*
![image-20251022213611580](README/image-20251022213611580.png)	

---

## 💻 交互式命令行终端

- 支持 `cd` 命令切换目录，切换后的目录会自动同步到文件管理器。
- 支持历史记录导航，按键盘上下箭头即可查看历史命令。
- 提供一键清空终端输出功能。
![image-20251020091635286](README/image-20251020091635286.png)		

---

## 📁 高级文件管理

文件管理器分为三个直观区域：左侧目录树、中间文件列表、顶部地址栏和操作按钮。支持多种目录浏览方式（点击树节点、双击列表、地址栏直达）。
![image-20251020092137582](README/image-20251020092137582.png)

- **上传与下载**：支持普通模式与大文件分块传输模式。在全局设置中，用户可自定义分块大小及请求间隔等参数。
  ![image-20251020092817460](README/image-20251020092817460.png)	
- **编辑文件**：双击文本文件即可在内置编辑器中修改并保存（限制 1MB 以内，不支持二进制文件）。
  ![image-20251204135535672](README/image-20251204135535672.png)	
- **压缩与解压**：支持服务端直接打包压缩文件/文件夹，或对 ZIP 文件进行解压操作。
  ![image-20251022182821430](README/image-20251022182821430.png)
  ![image-20251022182910613](README/image-20251022182910613.png)
- **修改文件权限**：支持修改文件的权限属性和时间属性（修改时间、访问时间）。
  ![image-20251022185821513](README/image-20251022185821513.png)
  ![image-20251022185854937](README/image-20251022185854937.png)	

---

## 🗄️ 数据库管理

输入数据库配置参数并测试连接。内置 SQL 执行面板，点击左侧数据表节点可自动生成查询语句，查询结果直观展示在下方数据网格中。
![image-20251022190832786](README/image-20251022190832786.png)

---

## 🕸️ 内网穿透

允许通过已控制的 Webshell 服务器作为跳板，访问目标内网资源。支持三种模式：
1. **SOCKS 代理**：在本地开启 SOCKS 代理端口，配合浏览器或扫描器自由访问内网。支持**内网白名单 IP 功能**，启用后仅与白名单内的 IP 建立隧道，提升隐蔽性与安全性。
2. **端口映射**：将内网特定端口（如 3306）直接映射到本地，方便使用本地工具直连。
3. **反向 DMZ（仅限 JSP）**：反向代理内网服务，适用于反弹 Shell 等场景。

![image-20251022193417722](README/image-20251022193417722.png)



---

## 💉 内存马注入 (JSP)

### 1. 加载内存马
填写内存马配置信息（Cookie 名称作为内存马的访问密钥，若请求的 Cookie 值不正确，内存马路径将返回正常页面，极具隐蔽性）。加载成功后配置会保存至历史记录。
目前支持：
- **Servlet 内存马**：注册为 Servlet 组件
- **Filter 内存马**：注册为 Filter 组件

![image-20251213034012958](README/image-20251213034012958.png)

### 2. 获取注册组件信息
一键查看当前 Web 应用的所有 Servlet 映射配置信息，辅助判断环境状态。
![image-20251022210523171](README/image-20251022210523171.png)

### 3. 卸载内存马
选择内存马类型，填写路径及 Wrapper/Filter 名称即可实现无痕卸载。
![image-20251022210706163](README/image-20251022210706163.png)	



## 🔗Payload插件管理

在左侧"插件列表"区域可新建插件和查看插件代码，右侧"插件编辑与执行"区域可对插件的代码进行编辑和执行

例如要执行一个对端口存活探测的插件, 对应的方法名是`portAlive`, 方法参数为`{ "ip": "192.168.47.123","port": 3389}`,点击执行代码后下方会显示执行结果

![image-20260409204314206](README/image-20260409204314206.png)	

![image-20260409204105945](README/image-20260409204105945.png)



支持调用AI来生成插件代码, 用户只需输入想实现的功能需求, 例如要实现对文件内容读取, 需求一般要包含方法名, 参数名以及你希望的返回内容形式

![image-20260409204507643](README/image-20260409204507643.png)



AI生成代码后会自动复制到编辑框处，点击保存插件可将插件代码保存至后端目录(`java/payload/custom`)

![image-20260409205012963](README/image-20260409205012963.png)		

​	

## 🧠AIAgent配置

在全局配置LLM配置区域可设置LLM参数，如果你的AI API是通过中转站调用的，可选择Codex Proxy或Gemini Proxy

![image-20260409205657530](README/image-20260409205657530.png)	

​	

---

# 📅 更新日志

### 2026-03-25
-  新增支持 ASP 和 ASPX 类型的 Webshell。
-  兼容 `GLIBC_2.31` 版本的 Linux 系统运行环境。
-  修复调用后端接口提示"NetWork连接失败"

### 2026-04-08

- 支持自定义JavaPayload插件

- 接入AiAgent功能，可在全局配置定义LLM参数，可使用AI生成伪装正常业务Webshell和JavaPayload插件



### 🔮 后续规划
- [x]  接入 AI Agent，实现智能化的 Webshell Payload 动态生成。
- [ ]  集成各类主流框架的利用链工具（如 Shiro、Fastjson 等一键利用）。
- [ ]  还没想好

---

# ❓ 常见问题 (FAQ)

### 1. 提示 `javac` 没有执行权限？
因为项目内置了一个 `javac` 用于动态编译 Java 类文件，在 Linux/macOS 环境下可能需要手动赋予可执行权限：
```bash
chmod +x router_modules/webshellmanager_router/java/payload/jdk/bin/javac
```

