import axios from 'axios'

const API_URL = import.meta.env.DEV ? 'http://localhost:5001/api' : '/api'

// 注意：使用webshell_id极简方案，前端只需传递ID

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 默认30秒超时
})

// 创建专门用于大文件下载的axios实例
const downloadClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5分钟超时，适用于大文件下载
})

// ====== 核心管理API - Core Management APIs ======
// 对应后端 core_management_api.py 模块
// 负责webshell列表管理、连接管理、生成功能、缓存管理
export const coreManagementApi = {
  // ====== WebShell列表管理 ======
  /**
   * 获取所有Webshell列表
   * @returns {Promise} 返回Webshell列表
   */
  getList() {
    return apiClient.get('/webshell/list')
  },

  /**
   * 添加或更新Webshell
   * @param {Object} webshell - Webshell信息
   * @returns {Promise} 返回操作结果
   */
  saveWebshell(webshell) {
    return apiClient.post('/webshell/save', webshell)
  },

  /**
   * 删除Webshell
   * @param {number|string} id - Webshell ID
   * @returns {Promise} 返回操作结果
   */
  deleteWebshell(id) {
    return apiClient.delete(`/webshell/delete/${id}`)
  },

  /**
   * 检查Webshell状态
   * @param {number|string} id - Webshell ID
   * @returns {Promise} 返回Webshell状态
   */
  checkStatus(id) {
    return apiClient.get(`/webshell/check/${id}`)
  },

  /**
   * 获取单个Webshell详情
   * @param {number|string} id - Webshell ID
   * @returns {Promise} 返回Webshell详细信息
   */
  getWebshellDetail(id) {
    return apiClient.get(`/webshell/detail/${id}`)
  },

  // ====== WebShell连接管理 ======
  /**
   * 保持Webshell连接活跃
   * @param {Object} data - 包含url、password和paramName的对象
   * @returns {Promise} 返回操作结果
   */
  keepAlive(data) {
    return apiClient.post('/webshell/keepAlive', data)
  },

  /**
   * 初始化Webshell连接
   * @param {Object} data - 包含url、password和paramName的对象
   * @returns {Promise} 返回操作结果
   */
  openWebshell(data) {
    return apiClient.post('/webshell/openWebshell', data)
  },

  // ====== WebShell生成功能 ======
  /**
   * 生成自定义Webshell
   * @param {Object} data - 包含webshell生成配置的对象
   * @returns {Promise} 返回生成结果
   */
  generateWebshell(data) {
    return apiClient.post('/webshell/generate_webshell', data)
  },

  /**
   * 获取指定类型的webshell模板文件
   * @param {Object} params - { type: 'jsp' | 'php' | 'jspx' }
   * @returns {Promise} 返回模板列表
   */
  getWebshellTemplates(params) {
    return apiClient.get('/webshell/template_files', { params })
  },

  /**
   * 获取全局配置
   * @returns {Promise}
   */
  getGlobalConfig() {
    return apiClient.get('/webshell/globalConfig')
  },

  /**
   * 保存全局配置
   * @param {Object} data
   * @returns {Promise}
   */
  saveGlobalConfig(data) {
    return apiClient.post('/webshell/globalConfig', data)
  },

  /**
   * 获取指定类型的模拟正常业务模板文件
   * @param {Object} params - { type: 'jsp' | 'php' | 'jspx' }
   * @returns {Promise} 返回模板列表
   */
  getNormalTemplates(params) {
    return apiClient.get('/webshell/normal_templates', { params })
  },

  /**
   * 下载生成的webshell文件
   * @param {string} filename - 文件名
   * @returns {Promise} 返回文件下载
   */
  downloadWebshell(filename) {
    return apiClient.get(`/webshell/download_webshell/${filename}`, {
      responseType: 'blob',
    })
  },

  // ====== 缓存管理 ======
  /**
   * 清空WebShell实例缓存
   * @returns {Promise} 返回操作结果
   */
  clearCache() {
    return apiClient.post('/webshell/clearCache')
  },

  /**
   * 清理指定WebShell实例的缓存
   * @param {Object} data - { webshell_id }
   * @returns {Promise} 返回操作结果
   */
  clearCacheById(data) {
    return apiClient.post('/webshell/clearCacheById', data)
  },

  /**
   * 获取缓存状态
   * @returns {Promise} 返回缓存状态信息
   */
  getCacheStatus() {
    return apiClient.get('/webshell/getCacheStatus')
  },

  // ====== 请求格式管理 ======
  /**
   * 复制请求格式模板文件
   * @param {Object} data - 包含webshell_id的对象
   * @returns {Promise} 返回复制结果
   */
  copyRequestFormatTemplate(data) {
    return apiClient.post('/webshell/copyRequestFormatTemplate', data)
  },

  /**
   * 获取默认请求格式模板
   * @returns {Promise} 返回默认模板内容
   */
  getDefaultRequestFormatTemplate() {
    return apiClient.get('/webshell/getDefaultRequestFormatTemplate')
  },

  /**
   * 获取请求格式内容
   * @param {Object} data - 包含webshell_id的对象
   * @returns {Promise} 返回请求格式内容
   */
  getRequestFormatContent(data) {
    return apiClient.post('/webshell/getRequestFormatContent', data)
  },
}

// ====== Java Shell专属功能API - Java Shell APIs ======
// 对应后端 java_shell_api.py 模块
// 负责内存马管理、内网穿透、数据库管理等Java环境专属功能
export const javaShellApi = {
  // ====== 命令执行 ======
  /**
   * 执行命令
   * @param {Object} data - 包含url、password、paramName和command的对象
   * @returns {Promise} 返回命令执行结果
   */
  executeCommand(data) {
    return apiClient.post('/webshell/java/executeCommand', data)
  },

  // ====== 文件浏览和管理 ======
  /**
   * 获取指定目录的文件列表
   * @param {Object} data - 包含url、password、paramName和path的对象
   * @returns {Promise} 返回文件列表
   */
  getFiles(data) {
    return apiClient.post('/webshell/java/getFiles', data)
  },

  /**
   * 删除文件
   * @param {Object} data - 包含url、password、paramName和fileName的对象
   * @returns {Promise} 返回删除结果
   */
  deleteFile(data) {
    return apiClient.post('/webshell/java/deleteFile', data)
  },

  /**
   * 新建文件
   * @param {Object} data - 包含url、password、paramName和fileName的对象
   * @returns {Promise} 返回创建结果
   */
  newFile(data) {
    return apiClient.post('/webshell/java/newFile', data)
  },

  /**
   * 新建目录
   * @param {Object} data - 包含url、password、paramName和dirName的对象
   * @returns {Promise} 返回创建结果
   */
  newDir(data) {
    return apiClient.post('/webshell/java/newDir', data)
  },

  /**
   * 复制文件
   * @param {Object} data - 包含url、password、paramName、srcFileName和destFileName的对象
   * @returns {Promise} 返回复制结果
   */
  copyFile(data) {
    return apiClient.post('/webshell/java/copyFile', data)
  },

  /**
   * 移动文件
   * @param {Object} data - 包含url、password、paramName、srcFileName和destFileName的对象
   * @returns {Promise} 返回移动结果
   */
  moveFile(data) {
    return apiClient.post('/webshell/java/moveFile', data)
  },

  /**
   * 新建文件或目录
   * @param {Object} data - 包含url、password、paramName、name和type的对象
   * @returns {Promise} 返回新建结果
   */
  newFileOrDir(data) {
    return apiClient.post('/webshell/java/newFileOrDir', data)
  },

  // ====== 文件上传下载 ======
  /**
   * 上传文件（支持普通上传和大文件上传）
   * @param {Object} data - 包含url、password、paramName、filePath和fileData的对象
   * @returns {Promise} 返回上传结果
   */
  uploadFile(data) {
    return apiClient.post('/webshell/java/uploadFile', data)
  },

  /**
   * 下载文件（支持普通下载和大文件下载）
   * @param {Object} data - 包含url、password、paramName和fileName的对象
   * @returns {Promise} 返回文件内容
   */
  downloadFile(data) {
    return apiClient.post('/webshell/java/downloadFile', data)
  },

  /**
   * 下载大文件（支持进度回调）
   * @param {Object} data - 包含url、password、paramName和fileName的对象
   * @param {Function} onProgress - 进度回调函数
   * @returns {Promise} 返回下载结果
   */
  downloadLargeFile(data, onProgress) {
    return downloadClient.post('/webshell/java/downloadFile', data, {
      onDownloadProgress: onProgress,
    })
  },

  /**
   * 大文件上传
   * @param {Object} data - 包含url、password、paramName、fileName、fileData和position的对象
   * @returns {Promise} 返回上传结果
   */
  bigFileUpload(data) {
    return apiClient.post('/webshell/java/bigFileUpload', data)
  },

  /**
   * 大文件下载
   * @param {Object} data - 包含url、password、paramName、fileName和savePath的对象
   * @returns {Promise} 返回下载结果
   */
  bigFileDownload(data) {
    return apiClient.post('/webshell/java/bigFileDownload', data)
  },

  // ====== 文件压缩解压 ======
  /**
   * 压缩文件
   * @param {Object} data - 包含url、password、paramName、compressPaths和compressFile的对象
   * @returns {Promise} 返回压缩结果
   */
  zipFiles(data) {
    return apiClient.post('/webshell/java/zip', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 40000, // 因为压缩大文件可能会花多一些时间，所以设置40秒超时
    })
  },

  /**
   * 解压文件
   * @param {Object} data - 包含url、password、paramName、compressFile和extractDir的对象
   * @returns {Promise} 返回解压结果
   */
  unzipFiles(data) {
    return apiClient.post('/webshell/java/unzip', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 40000, // 因为解压大文件可能会花多一些时间，所以设置40秒超时
    })
  },

  // ====== 远程文件下载 ======
  /**
   * 远程下载文件
   * @param {Object} data - 包含url、password、paramName、downloadUrl和savePath的对象
   * @returns {Promise} 返回下载结果
   */
  fileRemoteDownload(data) {
    return apiClient.post('/webshell/java/fileRemoteDownload', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 60000, // 因为远程下载可能会花较长时间，所以设置60秒超时
    })
  },

  // ====== 文件属性设置 ======
  /**
   * 设置文件属性（权限或时间）
   * @param {Object} data - 包含url、password、paramName、filePath、attrType等的对象
   * @returns {Promise} 返回设置结果
   */
  setFileAttr(data) {
    return apiClient.post('/webshell/java/setFileAttr', data)
  },

  // ====== 内存马管理接口 ======
  /**
   * 加载内存马
   * @param {Object} data - 包含webshell连接信息和内存马配置的对象
   * @returns {Promise} 返回加载结果
   */
  loadMemoryShell(data) {
    return apiClient.post('/webshell/java/loadMemoryShell', data, {
      timeout: 30000, // 30秒超时
    })
  },

  /**
   * 卸载内存马
   * @param {Object} data - 包含webshell连接信息和内存马路径的对象
   * @returns {Promise} 返回卸载结果
   */
  unloadMemoryShell(data) {
    return apiClient.post('/webshell/java/unloadMemoryShell', data, {
      timeout: 30000, // 30秒超时
    })
  },

  /**
   * 检查内存马状态
   * @param {Object} data - 包含webshell连接信息和内存马路径的对象
   * @returns {Promise} 返回内存马状态信息
   */
  checkMemoryShellStatus(data) {
    return apiClient.post('/webshell/java/checkMemoryShellStatus', data)
  },

  /**
   * 获取所有Servlet
   * @param {Object} data - 包含webshell连接信息的对象
   * @returns {Promise} 返回所有Servlet信息
   */
  getAllServlet(data) {
    return apiClient.post('/webshell/java/getAllServlet', data, {
      timeout: 30000, // 30秒超时
    })
  },

  // ====== 内存马历史记录管理接口 ======
  /**
   * 保存内存马历史记录
   * @param {Object} data - 包含webshell_url和history_item的对象
   * @returns {Promise} 返回保存结果
   */
  saveMemoryShellHistory(data) {
    return apiClient.post('/webshell/java/saveMemoryShellHistory', data)
  },

  /**
   * 获取内存马历史记录
   * @param {Object} data - 包含webshell_url的对象
   * @returns {Promise} 返回历史记录列表
   */
  getMemoryShellHistory(data) {
    return apiClient.post('/webshell/java/getMemoryShellHistory', data)
  },

  /**
   * 删除单条内存马历史记录
   * @param {Object} data - 包含webshell_url和record_id的对象
   * @returns {Promise} 返回删除结果
   */
  deleteMemoryShellHistory(data) {
    return apiClient.post('/webshell/java/deleteMemoryShellHistory', data)
  },

  /**
   * 清空内存马历史记录
   * @param {Object} data - 包含webshell_url的对象
   * @returns {Promise} 返回清空结果
   */
  clearMemoryShellHistory(data) {
    return apiClient.post('/webshell/java/clearMemoryShellHistory', data)
  },

  // ====== 内网穿透 - 端口映射API ======
  /**
   * 启动端口映射
   * @param {Object} data - 包含webshell连接信息和映射参数的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @param {number} data.localPort - 本地监听端口
   * @param {string} data.targetIp - 内网目标IP
   * @param {number} data.targetPort - 内网目标端口
   * @returns {Promise} 返回端口映射启动结果
   */
  startPortMapping(data) {
    return apiClient.post('/webshell/java/startPortMapping', data, {
      timeout: 60000, // 60秒超时，端口映射可能需要更长时间
    })
  },

  /**
   * 停止端口映射
   * @param {Object} data - 包含webshell连接信息和本地端口的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @param {number} data.localPort - 要停止的本地端口
   * @returns {Promise} 返回端口映射停止结果
   */
  stopPortMapping(data) {
    return apiClient.post('/webshell/java/stopPortMapping', data, {
      timeout: 30000, // 30秒超时
    })
  },

  /**
   * 获取端口映射状态
   * @param {Object} data - 包含webshell连接信息的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @returns {Promise} 返回端口映射状态信息
   */
  getPortMappingStatus(data) {
    return apiClient.post('/webshell/java/getPortMappingStatus', data, {
      timeout: 15000, // 15秒超时
    })
  },

  /**
   * 停止所有端口映射
   * @param {Object} data - 包含webshell连接信息的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @returns {Promise} 返回停止所有端口映射的结果
   */
  stopAllPortMappings(data) {
    return apiClient.post('/webshell/java/stopAllPortMappings', data, {
      timeout: 45000, // 45秒超时，可能需要清理多个映射
    })
  },

  // ====== 内网穿透 - Socks隧道API ======
  /**
   * 启动Socks隧道
   * @param {Object} data - 包含webshell连接信息和隧道参数的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @param {number} data.listenPort - 本地监听端口
   * @param {string} [data.listenIp='127.0.0.1'] - 监听IP，默认127.0.0.1
   * @param {Array} [data.ipWhitelist=[]] - IP白名单数组
   * @returns {Promise} 返回Socks隧道启动结果
   */
  startSocksTunnel(data) {
    return apiClient.post('/webshell/java/startSocksTunnel', data, {
      timeout: 30000, // Socks隧道启动可能需要更长时间
    })
  },

  /**
   * 停止Socks隧道
   * @param {Object} data - 包含webshell连接信息的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @returns {Promise} 返回Socks隧道停止结果
   */
  stopSocksTunnel(data) {
    return apiClient.post('/webshell/java/stopSocksTunnel', data)
  },

  /**
   * 获取Socks隧道状态
   * @param {Object} data - 包含webshell连接信息的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @returns {Promise} 返回Socks隧道状态
   */
  getSocksTunnelStatus(data) {
    return apiClient.post('/webshell/java/getSocksTunnelStatus', data)
  },

  /**
   * 更新Socks隧道IP白名单
   * @param {Object} data - 包含webshell连接信息和白名单的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @param {Array} data.ipWhitelist - IP白名单数组
   * @returns {Promise} 返回白名单更新结果
   */
  updateSocksWhitelist(data) {
    return apiClient.post('/webshell/java/updateSocksWhitelist', data)
  },

  // ====== 内网穿透 - 反连端口桥接API ======
  /**
   * 启动反连端口桥接
   * @param {Object} data - 包含webshell连接信息和桥接参数的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @param {string} data.listenId - 监听器唯一标识
   * @param {number} data.webshellPort - webshell端监听端口
   * @param {string} [data.localIp='127.0.0.1'] - 本地IP地址
   * @param {number} [data.localPort] - 本地端口（可选）
   * @returns {Promise} 返回反连端口桥接启动结果
   */
  startReverseConnect(data) {
    return apiClient.post('/webshell/java/startReverseConnect', data, {
      timeout: 30000, // 反连端口桥接启动可能需要更长时间
    })
  },

  /**
   * 停止反连端口桥接
   * @param {Object} data - 包含webshell连接信息和监听器标识的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @param {string} data.listenId - 监听器唯一标识
   * @returns {Promise} 返回反连端口桥接停止结果
   */
  stopReverseConnect(data) {
    return apiClient.post('/webshell/java/stopReverseConnect', data)
  },

  /**
   * 获取反连端口桥接状态
   * @param {Object} data - 包含webshell连接信息的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @returns {Promise} 返回反连端口桥接状态
   */
  getReverseConnectStatus(data) {
    return apiClient.post('/webshell/java/getReverseConnectStatus', data)
  },

  /**
   * 停止所有反连端口桥接
   * @param {Object} data - 包含webshell连接信息的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @returns {Promise} 返回停止所有反连端口桥接的结果
   */
  stopAllReverseConnects(data) {
    return apiClient.post('/webshell/java/stopAllReverseConnects', data, {
      timeout: 45000, // 45秒超时，可能需要清理多个监听器
    })
  },

  // ====== 数据库管理接口 ======
  /**
   * 测试数据库连接
   * @param {Object} data - 包含数据库连接信息的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @param {string} data.dbType - 数据库类型
   * @param {string} data.host - 数据库主机
   * @param {number} data.port - 数据库端口
   * @param {string} data.username - 数据库用户名
   * @param {string} data.dbPassword - 数据库密码
   * @returns {Promise} 返回测试结果
   */
  testDatabaseConnection(data) {
    return apiClient.post('/webshell/java/testDatabaseConnection', data, {
      timeout: 30000, // 30秒超时
    })
  },

  /**
   * 执行SQL语句
   * @param {Object} data - 包含SQL执行信息的对象
   * @param {string} data.url - webshell URL
   * @param {string} data.password - webshell密码
   * @param {string} data.paramName - webshell参数名
   * @param {string} data.dbType - 数据库类型
   * @param {string} data.host - 数据库主机
   * @param {number} data.port - 数据库端口
   * @param {string} data.username - 数据库用户名
   * @param {string} data.dbPassword - 数据库密码
   * @param {string} data.sql - SQL语句
   * @returns {Promise} 返回执行结果
   */
  executeSql(data) {
    return apiClient.post('/webshell/java/executeSql', data, {
      timeout: 60000, // 60秒超时，SQL执行可能需要较长时间
    })
  },
}

export const phpShellApi = {
  // ====== 命令执行 ======
  /**
   * 执行命令
   * @param {Object} data - 包含webshell_id和command的对象
   * @returns {Promise} 返回命令执行结果
   */
  executeCommand(data) {
    return apiClient.post('/webshell/php/executeCommand', data)
  },

  // ====== 文件浏览和管理 ======
  /**
   * 获取指定目录的文件列表
   * @param {Object} data - 包含webshell_id和path的对象
   * @returns {Promise} 返回文件列表
   */
  getFiles(data) {
    return apiClient.post('/webshell/php/getFiles', data)
  },

  /**
   * 删除文件
   * @param {Object} data - 包含webshell_id和fileName的对象
   * @returns {Promise} 返回删除结果
   */
  deleteFile(data) {
    return apiClient.post('/webshell/php/deleteFile', data)
  },

  /**
   * 新建文件
   * @param {Object} data - 包含webshell_id和fileName的对象
   * @returns {Promise} 返回创建结果
   */
  newFile(data) {
    return apiClient.post('/webshell/php/newFile', data)
  },

  /**
   * 新建目录
   * @param {Object} data - 包含webshell_id和dirName的对象
   * @returns {Promise} 返回创建结果
   */
  newDir(data) {
    return apiClient.post('/webshell/php/newDir', data)
  },

  /**
   * 复制文件
   * @param {Object} data - 包含webshell_id、srcFileName和destFileName的对象
   * @returns {Promise} 返回复制结果
   */
  copyFile(data) {
    return apiClient.post('/webshell/php/copyFile', data)
  },

  /**
   * 移动文件
   * @param {Object} data - 包含webshell_id、srcFileName和destFileName的对象
   * @returns {Promise} 返回移动结果
   */
  moveFile(data) {
    return apiClient.post('/webshell/php/moveFile', data)
  },

  /**
   * 新建文件或目录
   * @param {Object} data - 包含webshell_id、name和type的对象
   * @returns {Promise} 返回新建结果
   */
  newFileOrDir(data) {
    const endpoint = data.type === 'file' ? '/webshell/php/newFile' : '/webshell/php/newDir'
    const param = data.type === 'file' ? { fileName: data.name } : { dirName: data.name }
    return apiClient.post(endpoint, {
      webshell_id: data.webshell_id,
      ...param,
    })
  },

  // ====== 文件上传下载 ======
  /**
   * 上传文件（支持普通上传和大文件上传）
   * @param {Object} data - 包含webshell_id、filePath和fileData的对象
   * @returns {Promise} 返回上传结果
   */
  uploadFile(data) {
    return apiClient.post('/webshell/php/uploadFile', data)
  },

  /**
   * 下载文件（支持普通下载和大文件下载）
   * @param {Object} data - 包含webshell_id和fileName的对象
   * @returns {Promise} 返回文件内容
   */
  downloadFile(data) {
    return apiClient.post('/webshell/php/downloadFile', data)
  },

  /**
   * 下载大文件（支持进度回调）
   * @param {Object} data - 包含webshell_id和fileName的对象
   * @param {Function} onProgress - 进度回调函数
   * @returns {Promise} 返回下载结果
   */
  downloadLargeFile(data, onProgress) {
    return downloadClient.post('/webshell/php/downloadFile', data, {
      onDownloadProgress: onProgress,
    })
  },

  // ====== 文件压缩解压 ======
  /**
   * 压缩文件
   * @param {Object} data - 包含webshell_id、compressPaths和compressFile的对象
   * @returns {Promise} 返回压缩结果
   */
  zipFiles(data) {
    return apiClient.post('/webshell/php/zip', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 40000, // 因为压缩大文件可能会花多一些时间，所以设置40秒超时
    })
  },

  /**
   * 解压文件
   * @param {Object} data - 包含webshell_id、compressFile和extractDir的对象
   * @returns {Promise} 返回解压结果
   */
  unzipFiles(data) {
    return apiClient.post('/webshell/php/unzip', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 40000, // 因为解压大文件可能会花多一些时间，所以设置40秒超时
    })
  },

  // ====== 远程文件下载 ======
  /**
   * 远程下载文件
   * @param {Object} data - 包含webshell_id、downloadUrl和savePath的对象
   * @returns {Promise} 返回下载结果
   */
  fileRemoteDownload(data) {
    return apiClient.post('/webshell/php/fileRemoteDownload', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 60000, // 因为远程下载可能会花较长时间，所以设置60秒超时
    })
  },

  // ====== 文件属性设置 ======
  /**
   * 设置文件属性（权限或时间）
   * @param {Object} data - 包含webshell_id、filePath、attrType等的对象
   * @returns {Promise} 返回设置结果
   */
  setFileAttr(data) {
    return apiClient.post('/webshell/php/setFileAttr', data)
  },

  // ====== 数据库管理接口 ======
  /**
   * 测试数据库连接
   * @param {Object} data - 包含数据库连接信息的对象
   * @param {string} data.webshell_id - webshell ID
   * @param {string} data.dbType - 数据库类型
   * @param {string} data.host - 数据库主机
   * @param {number} data.port - 数据库端口
   * @param {string} data.username - 数据库用户名
   * @param {string} data.dbPassword - 数据库密码
   * @returns {Promise} 返回测试结果
   */
  testDatabaseConnection(data) {
    return apiClient.post('/webshell/php/testDatabaseConnection', data, {
      timeout: 30000, // 30秒超时
    })
  },

  /**
   * 执行SQL语句
   * @param {Object} data - 包含SQL执行信息的对象
   * @param {string} data.webshell_id - webshell ID
   * @param {string} data.dbType - 数据库类型
   * @param {string} data.host - 数据库主机
   * @param {number} data.port - 数据库端口
   * @param {string} data.username - 数据库用户名
   * @param {string} data.dbPassword - 数据库密码
   * @param {string} data.sql - SQL语句
   * @returns {Promise} 返回执行结果
   */
  executeSql(data) {
    return apiClient.post('/webshell/php/executeSql', data, {
      timeout: 60000, // 60秒超时，SQL执行可能需要较长时间
    })
  },

  // ====== 内网穿透 - 端口映射API ======
  /**
   * 启动端口映射
   * @param {Object} data - 包含webshell_id和映射参数的对象
   * @param {string} data.webshell_id - webshell ID
   * @param {number} data.localPort - 本地监听端口
   * @param {string} data.targetIp - 内网目标IP
   * @param {number} data.targetPort - 内网目标端口
   * @returns {Promise} 返回端口映射启动结果
   */
  startPortMapping(data) {
    return apiClient.post('/webshell/php/startPortMapping', data, {
      timeout: 60000, // 60秒超时
    })
  },

  /**
   * 停止端口映射
   * @param {Object} data - 包含webshell_id和本地端口的对象
   * @param {string} data.webshell_id - webshell ID
   * @param {number} data.localPort - 要停止的本地端口
   * @returns {Promise} 返回端口映射停止结果
   */
  stopPortMapping(data) {
    return apiClient.post('/webshell/php/stopPortMapping', data, {
      timeout: 30000, // 30秒超时
    })
  },

  /**
   * 获取端口映射状态
   * @param {Object} data - 包含webshell_id的对象
   * @param {string} data.webshell_id - webshell ID
   * @returns {Promise} 返回端口映射状态信息
   */
  getPortMappingStatus(data) {
    return apiClient.post('/webshell/php/getPortMappingStatus', data, {
      timeout: 15000, // 15秒超时
    })
  },

  /**
   * 停止所有端口映射
   * @param {Object} data - 包含webshell_id的对象
   * @param {string} data.webshell_id - webshell ID
   * @returns {Promise} 返回停止所有端口映射的结果
   */
  stopAllPortMappings(data) {
    return apiClient.post('/webshell/php/stopAllPortMappings', data, {
      timeout: 45000, // 45秒超时
    })
  },

  // ====== 内网穿透 - Socks隧道API ======
  /**
   * 启动Socks隧道
   * @param {Object} data - 包含webshell_id和隧道参数的对象
   * @param {string} data.webshell_id - webshell ID
   * @param {number} data.listenPort - 本地监听端口
   * @param {string} [data.listenIp='127.0.0.1'] - 监听IP
   * @param {Array} [data.ipWhitelist=[]] - IP白名单数组
   * @returns {Promise} 返回Socks隧道启动结果
   */
  startSocksTunnel(data) {
    return apiClient.post('/webshell/php/startSocksTunnel', data, {
      timeout: 30000, // 30秒超时
    })
  },

  /**
   * 停止Socks隧道
   * @param {Object} data - 包含webshell_id的对象
   * @param {string} data.webshell_id - webshell ID
   * @returns {Promise} 返回Socks隧道停止结果
   */
  stopSocksTunnel(data) {
    return apiClient.post('/webshell/php/stopSocksTunnel', data)
  },

  /**
   * 获取Socks隧道状态
   * @param {Object} data - 包含webshell_id的对象
   * @param {string} data.webshell_id - webshell ID
   * @returns {Promise} 返回Socks隧道状态
   */
  getSocksTunnelStatus(data) {
    return apiClient.post('/webshell/php/getSocksTunnelStatus', data)
  },

  /**
   * 更新Socks隧道IP白名单
   * @param {Object} data - 包含webshell_id和白名单的对象
   * @param {string} data.webshell_id - webshell ID
   * @param {Array} data.ipWhitelist - IP白名单数组
   * @returns {Promise} 返回白名单更新结果
   */
  updateSocksWhitelist(data) {
    return apiClient.post('/webshell/php/updateSocksWhitelist', data)
  },
}

export const csharpShellApi = {
  // ====== 命令执行 ======
  executeCommand(data) {
    return apiClient.post('/webshell/csharp/executeCommand', data)
  },

  // ====== 文件浏览和管理 ======
  getFiles(data) {
    return apiClient.post('/webshell/csharp/getFiles', data)
  },

  deleteFile(data) {
    return apiClient.post('/webshell/csharp/deleteFile', data)
  },

  newFile(data) {
    return apiClient.post('/webshell/csharp/newFile', data)
  },

  newDir(data) {
    return apiClient.post('/webshell/csharp/newDir', data)
  },

  copyFile(data) {
    return apiClient.post('/webshell/csharp/copyFile', data)
  },

  moveFile(data) {
    return apiClient.post('/webshell/csharp/moveFile', data)
  },

  newFileOrDir(data) {
    const endpoint = data.type === 'file' ? '/webshell/csharp/newFile' : '/webshell/csharp/newDir'
    const param = data.type === 'file' ? { fileName: data.name } : { dirName: data.name }
    return apiClient.post(endpoint, {
      webshell_id: data.webshell_id,
      ...param,
    })
  },

  // ====== 文件上传下载 ======
  uploadFile(data) {
    return apiClient.post('/webshell/csharp/uploadFile', data)
  },

  downloadFile(data) {
    return apiClient.post('/webshell/csharp/downloadFile', data)
  },

  downloadLargeFile(data, onProgress) {
    return downloadClient.post('/webshell/csharp/downloadFile', data, {
      onDownloadProgress: onProgress,
    })
  },

  // ====== 文件压缩解压 ======
  zipFiles(data) {
    return apiClient.post('/webshell/csharp/zip', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 40000,
    })
  },

  unzipFiles(data) {
    return apiClient.post('/webshell/csharp/unzip', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 40000,
    })
  },

  // ====== 远程文件下载 ======
  fileRemoteDownload(data) {
    return apiClient.post('/webshell/csharp/fileRemoteDownload', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 60000,
    })
  },

  // ====== 文件属性设置 ======
  setFileAttr(data) {
    return apiClient.post('/webshell/csharp/setFileAttr', data)
  },

  // ====== 数据库管理接口 ======
  testDatabaseConnection(data) {
    return apiClient.post('/webshell/csharp/testDatabaseConnection', data, {
      timeout: 30000,
    })
  },

  executeSql(data) {
    return apiClient.post('/webshell/csharp/executeSql', data, {
      timeout: 60000,
    })
  },
}

export const aspShellApi = {
  // ====== 命令执行 ======
  executeCommand(data) {
    return apiClient.post('/webshell/asp/executeCommand', data)
  },

  // ====== 文件浏览和管理 ======
  getFiles(data) {
    return apiClient.post('/webshell/asp/getFiles', data)
  },

  deleteFile(data) {
    return apiClient.post('/webshell/asp/deleteFile', data)
  },

  newFile(data) {
    return apiClient.post('/webshell/asp/newFile', data)
  },

  newDir(data) {
    return apiClient.post('/webshell/asp/newDir', data)
  },

  copyFile(data) {
    return apiClient.post('/webshell/asp/copyFile', data)
  },

  moveFile(data) {
    return apiClient.post('/webshell/asp/moveFile', data)
  },

  newFileOrDir(data) {
    const endpoint = data.type === 'file' ? '/webshell/asp/newFile' : '/webshell/asp/newDir'
    const param = data.type === 'file' ? { fileName: data.name } : { dirName: data.name }
    return apiClient.post(endpoint, {
      webshell_id: data.webshell_id,
      ...param,
    })
  },

  // ====== 文件上传下载 ======
  uploadFile(data) {
    return apiClient.post('/webshell/asp/uploadFile', data)
  },

  downloadFile(data) {
    return apiClient.post('/webshell/asp/downloadFile', data)
  },

  downloadLargeFile(data, onProgress) {
    return downloadClient.post('/webshell/asp/downloadFile', data, {
      onDownloadProgress: onProgress,
    })
  },

  // ====== 文件压缩解压 ======
  zipFiles(data) {
    return apiClient.post('/webshell/asp/zip', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 40000,
    })
  },

  unzipFiles(data) {
    return apiClient.post('/webshell/asp/unzip', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 40000,
    })
  },

  // ====== 远程文件下载 ======
  fileRemoteDownload(data) {
    return apiClient.post('/webshell/asp/fileRemoteDownload', data, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 60000,
    })
  },

  // ====== 文件属性设置 ======
  setFileAttr(data) {
    return apiClient.post('/webshell/asp/setFileAttr', data)
  },

  // ====== 数据库管理接口 ======
  testDatabaseConnection(data) {
    return apiClient.post('/webshell/asp/testDatabaseConnection', data, {
      timeout: 30000,
    })
  },

  executeSql(data) {
    return apiClient.post('/webshell/asp/executeSql', data, {
      timeout: 60000,
    })
  },
}

export default {
  // 分类接口，推荐使用
  coreManagement: coreManagementApi,
  javaShell: javaShellApi,
  phpShell: phpShellApi,
  csharpShell: csharpShellApi,
  aspShell: aspShellApi,
}
