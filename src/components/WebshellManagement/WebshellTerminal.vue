<template>
  <div class="command-panel">
    <div class="terminal-container">
      <div class="terminal-header">
        <span>终端 - {{ currentWebshell?.url || '' }}</span>
        <div class="header-actions">
          <el-button size="small" @click="clearCommandOutput">清空</el-button>
          <el-button size="small" @click="refreshCurrentDirectory">刷新目录</el-button>
        </div>
      </div>
      <div class="terminal-body" ref="terminalBody">
        <div class="terminal-content">
          <!-- 显示命令历史 -->
          <div v-if="commandHistory.length === 0" class="welcome-message">
            WebShell 终端已连接，输入命令开始操作...
          </div>
          <div v-for="(entry, index) in commandHistory" :key="index" class="command-entry">
            <div class="command-line">
              <span class="prompt">{{ entry.directory }}></span>
              <span class="user-input">{{ entry.command }}</span>
            </div>
            <div v-if="entry.output" class="command-output">{{ entry.output }}</div>
            <div v-if="entry.error" class="command-error">{{ entry.error }}</div>
          </div>
          <!-- 当前输入行 -->
          <div class="current-input-line">
            <span class="prompt current-prompt"
              >{{
                formatCurrentDirectory() || (isWindowsSystem() ? 'C:\\Windows\\system32' : '/root')
              }}></span
            >
            <input
              ref="terminalInput"
              v-model="currentCommand"
              type="text"
              class="terminal-input"
              placeholder="输入命令..."
              @keyup.enter="executeCommand"
              @keyup.up="navigateHistory(-1)"
              @keyup.down="navigateHistory(1)"
              :disabled="commandExecuting"
              spellcheck="false"
            />
          </div>
          <!-- 执行中的提示 -->
          <div v-if="commandExecuting" class="executing-indicator">
            <span class="spinner">⠋</span>
            <span>正在执行...</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api/api'

// 定义props
const props = defineProps({
  currentWebshell: {
    type: Object,
    default: null,
  },
  systemInfo: {
    type: Object,
    default: null,
  },
  visible: {
    type: Boolean,
    default: false,
  },
})

// 定义emits
const emit = defineEmits(['directory-changed'])

// 终端相关状态
const currentCommand = ref('')
const commandExecuting = ref(false)
const currentDirectory = ref('')
const commandHistory = ref([])
const historyIndex = ref(-1)
const historyCommands = ref([])
const terminalBody = ref(null)
const terminalInput = ref(null)

// 初始化当前目录
watch(
  () => props.systemInfo,
  (newSystemInfo) => {
    if (newSystemInfo && newSystemInfo.CurrentDir) {
      currentDirectory.value = newSystemInfo.CurrentDir.replace(/\\/g, '/')
    }
  },
  { immediate: true },
)

// 监听visible变化，自动聚焦输入框
watch(
  () => props.visible,
  (newValue) => {
    if (newValue) {
      nextTick(() => {
        if (terminalInput.value) {
          terminalInput.value.focus()
        }
      })
    }
  },
)

// 判断是否为Windows系统
const isWindowsSystem = () => {
  if (!props.systemInfo) return false

  // 优先使用后端检测到的系统类型
  const detectedType = props.systemInfo.DetectedSystemType
  if (detectedType) {
    return detectedType.toLowerCase() === 'windows'
  }
  return false
}

// 路径解析函数
const resolvePath = (currentPath, targetPath) => {
  // 处理绝对路径
  if (targetPath.match(/^[a-zA-Z]:/)) {
    // Windows绝对路径 (C:, D:, etc.)
    return targetPath.replace(/\\/g, '/')
  }

  if (targetPath.startsWith('/')) {
    // Unix绝对路径
    return targetPath
  }

  // 处理相对路径
  let result = currentPath
  const isLinuxPath = currentPath.startsWith('/')

  // 确保路径以 / 结尾
  if (!result.endsWith('/')) {
    result += '/'
  }

  // 分割目标路径
  const parts = targetPath.split(/[/\\]/).filter((part) => part !== '')

  for (const part of parts) {
    if (part === '.') {
      // 当前目录，不变
      continue
    } else if (part === '..') {
      // 上级目录
      const pathParts = result.split('/').filter((p) => p !== '')
      if (pathParts.length > 1) {
        pathParts.pop()
        // 对于Linux系统，确保保持前导斜杠
        if (isLinuxPath) {
          result = '/' + pathParts.join('/') + '/'
        } else {
          result = pathParts.join('/') + '/'
        }
      } else if (pathParts.length === 1) {
        // 根目录或盘符根目录
        if (isLinuxPath) {
          // Linux系统：回到根目录
          result = '/'
        } else {
          // Windows系统：盘符根目录
          result = pathParts[0] + '/'
        }
      } else {
        // 已经在根目录，保持不变
        if (isLinuxPath) {
          result = '/'
        }
      }
    } else {
      // 普通目录名
      result += part + '/'
    }
  }

  return result
}

// 检查是否为cd命令
const isCdCommand = (command) => {
  const trimmed = command.trim()
  return trimmed === 'cd' || trimmed.startsWith('cd ') || trimmed.startsWith('cd\t')
}

// 解析cd命令的目标路径
const parseCdCommand = (command) => {
  const parts = command.trim().split(/\s+/)
  if (parts.length === 1) {
    // 只有 'cd'，返回用户主目录 (在Windows上通常是当前用户目录)
    return '~'
  }
  return parts.slice(1).join(' ')
}

// 格式化当前目录显示
const formatCurrentDirectory = () => {
  if (!currentDirectory.value) return ''

  // 根据系统类型选择路径分隔符
  if (isWindowsSystem()) {
    return currentDirectory.value.replace(/\//g, '\\') // Windows风格
  } else {
    return currentDirectory.value.replace(/\\/g, '/') // Linux/Unix风格
  }
}

/**
 * 检查一段文本输出中是否包含任何预定义的错误信息。
 * 这个版本支持两种模式：
 * 1. 精确匹配：普通的字符串，如 '拒绝访问'。
 * 2. 模糊匹配：使用 '%'作为通配符的字符串，如 '%can't cd to%'。
 */
const hasCommandError = (output) => {
  // 预定义的错误模式列表
  const errorPatterns = [
    // --- 保留原来的精确匹配模式 ---
    '系统找不到指定的路径',
    'The system cannot find the path specified',
    '拒绝访问',
    'Access is denied',
    '目录名无效',
    'The directory name is invalid',
    '找不到文件',
    'File not found',
    '路径不存在',
    'Path does not exist',

    // --- 新增的模糊匹配模式 ---
    // 这是你提到的例子，它可以匹配任何包含 "cd: can't cd" 的字符串
    "%cd: can't cd%",

    // 另一个例子：可以匹配 "sh: ... something ...: command not found"
    '%sh:%command not found%',

    // 匹配 Python 的 "ModuleNotFoundError"
    '%ModuleNotFoundError: No module named%',
  ]

  /**
   * 一个辅助函数，用于转义字符串中的正则表达式特殊字符。
   */
  const escapeRegex = (str) => {
    // $& 代表整个被匹配的字符串
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  }

  // 使用 .some() 遍历所有模式，一旦找到匹配就立即返回 true
  return errorPatterns.some((pattern) => {
    // 判断当前模式是否是模糊模式
    if (pattern.includes('%')) {
      // --- 处理模糊模式 ---
      const regexString = pattern.split('%').map(escapeRegex).join('.*')
      const regex = new RegExp(regexString)
      return regex.test(output)
    } else {
      // --- 处理精确模式 ---
      return output.includes(pattern)
    }
  })
}

// 获取默认目录
const getDefaultDirectory = () => {
  return isWindowsSystem() ? 'C:\\Windows\\system32' : '/root'
}

// 获取主目录路径
const getHomeDirectory = () => {
  if (isWindowsSystem()) {
    return 'C:/Users/' + (props.systemInfo?.CurrentUser || 'Administrator')
  } else {
    return '/home/' + (props.systemInfo?.CurrentUser || 'root')
  }
}

// 添加命令到历史记录
const addToCommandHistory = (command, output = null, error = null, directory = null) => {
  const displayDirectory = directory || formatCurrentDirectory() || getDefaultDirectory()

  commandHistory.value.push({
    directory: displayDirectory,
    command,
    output,
    error,
    timestamp: new Date().toLocaleString(),
  })
}

// 完成命令执行后的清理工作
const finishCommandExecution = () => {
  currentCommand.value = ''
  scrollToBottom()
}

// 执行命令
const executeCommand = async () => {
  if (!currentCommand.value.trim()) {
    ElMessage.warning('请输入要执行的命令')
    return
  }

  if (!props.currentWebshell) {
    ElMessage.error('未选中webshell')
    return
  }

  commandExecuting.value = true
  const originalCommand = currentCommand.value.trim()
  let actualCommand = originalCommand
  const previousDirectory = currentDirectory.value // 保存当前目录状态

  // 保存到历史记录
  if (originalCommand && !historyCommands.value.includes(originalCommand)) {
    historyCommands.value.push(originalCommand)
    // 限制历史记录长度
    if (historyCommands.value.length > 50) {
      historyCommands.value.shift()
    }
  }
  historyIndex.value = -1

  try {
    // 检查是否为cd命令
    if (isCdCommand(originalCommand)) {
      const targetPath = parseCdCommand(originalCommand)

      // 计算新的路径
      const newPath =
        targetPath === '~' ? getHomeDirectory() : resolvePath(currentDirectory.value, targetPath)

      // 构造实际执行的命令：先切换到当前目录，然后执行cd，最后显示新目录
      actualCommand = `cd "${currentDirectory.value}" && cd "${targetPath}" && cd`

      console.log(`[DEBUG] CD命令解析:`)
      console.log(`[DEBUG] 原命令: ${originalCommand}`)
      console.log(`[DEBUG] 目标路径: ${targetPath}`)
      console.log(`[DEBUG] 预期新路径: ${newPath}`)
      console.log(`[DEBUG] 实际执行命令: ${actualCommand}`)
    } else {
      // 非cd命令，需要先切换到当前目录再执行
      if (currentDirectory.value) {
        actualCommand = `cd "${currentDirectory.value}" && ${originalCommand}`
      }
    }

    // 根据 webshell 类型选择对应的 API
    const webshellType = props.currentWebshell.webshellType?.toLowerCase() || 'jsp'
    const executeApi =
      webshellType === 'php'
        ? api.phpShell
        : webshellType === 'csharp'
          ? api.csharpShell
          : webshellType === 'asp'
            ? api.aspShell
          : api.javaShell

    const response = await executeApi.executeCommand({
      webshell_id: props.currentWebshell.id,
      command: actualCommand,
    })

    if (response.data.status === 'success') {
      const output = response.data.data.output || '(无输出)'

      // 处理cd命令的特殊情况
      if (isCdCommand(originalCommand)) {
        if (hasCommandError(output)) {
          // 命令执行失败，保持原有目录不变
          console.log(`[DEBUG] CD命令执行失败，保持原目录: ${previousDirectory}`)
          addToCommandHistory(originalCommand, null, output)
          ElMessage.warning('路径切换失败，当前目录保持不变')
        } else {
          // 命令执行成功，更新目录
          const targetPath = parseCdCommand(originalCommand)
          let newPath =
            targetPath === '~' ? getHomeDirectory() : resolvePath(previousDirectory, targetPath)

          // 从输出中提取实际的目录（如果有的话）
          const outputLines = output.split('\n')
          const lastLine = outputLines[outputLines.length - 1].trim()
          if (lastLine && lastLine.includes(':') && !hasCommandError(lastLine)) {
            // 如果输出包含路径且不是错误信息，使用实际路径
            currentDirectory.value = lastLine.replace(/\\/g, '/')
          } else {
            // 否则使用计算出的路径
            currentDirectory.value = newPath
          }

          console.log(`[DEBUG] 目录已更新为: ${currentDirectory.value}`)

          // 通知父组件目录变化
          emit('directory-changed', currentDirectory.value)

          // 添加到历史记录
          const displayDir = isWindowsSystem()
            ? previousDirectory.replace(/\//g, '\\')
            : previousDirectory.replace(/\\/g, '/')

          addToCommandHistory(
            originalCommand,
            output || '目录切换成功',
            null,
            displayDir || getDefaultDirectory(),
          )
        }
      } else {
        // 非cd命令，直接添加到历史记录
        addToCommandHistory(originalCommand, output)
      }

      finishCommandExecution()
    } else {
      // API 返回失败状态
      const errorMessage = response.data.message || '执行命令失败'
      addToCommandHistory(originalCommand, null, errorMessage)
      ElMessage.error(errorMessage)
      finishCommandExecution()
    }
  } catch (error) {
    console.error('执行命令失败:', error)
    const errorMessage = '执行命令失败: ' + (error.response?.data?.message || error.message)
    addToCommandHistory(originalCommand, null, errorMessage)
    ElMessage.error(errorMessage)
    finishCommandExecution()
  } finally {
    commandExecuting.value = false
  }
}

// 清空命令输出
const clearCommandOutput = () => {
  commandHistory.value = []
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (terminalBody.value) {
      terminalBody.value.scrollTop = terminalBody.value.scrollHeight
    }
  })
}

// 历史记录导航
const navigateHistory = (direction) => {
  if (historyCommands.value.length === 0) return

  if (direction === -1) {
    // 向上箭头，显示上一条命令
    historyIndex.value++
    if (historyIndex.value >= historyCommands.value.length) {
      historyIndex.value = historyCommands.value.length - 1
    }
  } else if (direction === 1) {
    // 向下箭头，显示下一条命令
    historyIndex.value--
    if (historyIndex.value < -1) {
      historyIndex.value = -1
    }
  }

  if (historyIndex.value === -1) {
    currentCommand.value = ''
  } else {
    currentCommand.value =
      historyCommands.value[historyCommands.value.length - 1 - historyIndex.value]
  }
}

// 刷新当前目录
const refreshCurrentDirectory = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('未选中webshell')
    return
  }

  try {
    // 根据 webshell 类型选择对应的 API
    const webshellType = props.currentWebshell.webshellType?.toLowerCase() || 'jsp'
    const executeApi =
      webshellType === 'php'
        ? api.phpShell
        : webshellType === 'csharp'
          ? api.csharpShell
          : webshellType === 'asp'
            ? api.aspShell
          : api.javaShell

    const response = await executeApi.executeCommand({
      webshell_id: props.currentWebshell.id,
      command: 'cd',
    })

    if (response.data.status === 'success') {
      const output = response.data.data.output || ''
      const outputLines = output.split('\n')
      const lastLine = outputLines[outputLines.length - 1].trim()

      if (lastLine && lastLine.includes(':')) {
        currentDirectory.value = lastLine.replace(/\\/g, '/')
        emit('directory-changed', currentDirectory.value)
        ElMessage.success('目录已刷新')
      }
    }
  } catch (error) {
    ElMessage.error('刷新目录失败: ' + (error.response?.data?.message || error.message))
  }
}

// 暴露给父组件的方法
defineExpose({
  getCurrentDirectory: () => currentDirectory.value,
  clearCommandOutput,
  refreshCurrentDirectory,
})
</script>

<style scoped>
.command-panel {
  padding: 20px;
}

.terminal-container {
  border: 1px solid #444;
  border-radius: 8px;
  background-color: #1e1e1e;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: #333;
  color: #fff;
  font-size: 14px;
  border-bottom: 1px solid #555;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.terminal-body {
  height: 500px;
  overflow-y: auto;
  background-color: #1e1e1e;
  color: #fff;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.4;
}

.terminal-content {
  padding: 15px;
}

.welcome-message {
  color: #888;
  font-style: italic;
  margin-bottom: 10px;
}

.command-entry {
  margin-bottom: 15px;
}

.command-line {
  margin-bottom: 5px;
}

.command-line .prompt {
  color: #00ff00;
  font-weight: bold;
}

.command-line .user-input {
  color: #fff;
  margin-left: 5px;
}

.command-output {
  white-space: pre-wrap;
  color: #ccc;
  margin-left: 20px;
  padding: 5px 0;
  word-wrap: break-word;
}

.command-error {
  white-space: pre-wrap;
  color: #ff6b6b;
  margin-left: 20px;
  padding: 5px 0;
  word-wrap: break-word;
}

.current-input-line {
  display: flex;
  align-items: center;
  margin-top: 10px;
}

.current-input-line .prompt {
  color: #00ff00;
  font-weight: bold;
  white-space: nowrap;
  margin-right: 5px;
}

.current-input-line .terminal-input {
  background: transparent;
  border: none;
  outline: none;
  color: #fff;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 14px;
  flex: 1;
  padding: 0;
  margin-left: 5px;
}

.current-input-line .terminal-input::placeholder {
  color: #666;
}

.current-input-line .terminal-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.executing-indicator {
  color: #ffa500;
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.executing-indicator .spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* 滚动条样式 */
.terminal-body::-webkit-scrollbar {
  width: 8px;
}

.terminal-body::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.terminal-body::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.terminal-body::-webkit-scrollbar-thumb:hover {
  background: #666;
}
</style>
