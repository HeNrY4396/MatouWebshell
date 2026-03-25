<template>
  <div class="webshell-list">
    <div class="webshell-header">
      <div class="header-buttons">
        <el-button type="primary" size="small" @click="loadWebshellList(true)" :loading="loading">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
        <el-button type="warning" size="small" @click="openGenerateDialog">
          <el-icon><DocumentAdd /></el-icon>生成webshell
        </el-button>
        <el-button type="success" size="small" @click="addWebshell">
          <el-icon><Plus /></el-icon>添加
        </el-button>
        <el-dropdown @command="handleCacheCommand">
          <el-button type="info" size="small">
            缓存管理<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="status">查看缓存状态</el-dropdown-item>
              <el-dropdown-item command="clear">清空缓存</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- Webshell列表 -->
    <div class="table-container">
      <el-table
        :data="webshellList"
        style="width: 100%"
        @row-contextmenu="handleRowRightClick"
        highlight-current-row
        border
        v-loading="loading"
      >
        <el-table-column prop="url" label="URL" min-width="200" />
        <el-table-column prop="systemType" label="系统类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getSystemTypeTag(row.systemType)">
              {{ row.systemType }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="在线状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'danger'">
              {{ row.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="添加时间" width="150">
          <template #default="{ row }">
            {{ formatTimestamp(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openWebshell(row)"> 打开 </el-button>
            <el-button type="info" size="small" @click="checkWebshellStatus(row)">
              检查状态
            </el-button>
            <el-button type="danger" size="small" plain @click="clearCacheForWebshell(row)">
              清除缓存
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 右键菜单 -->
    <div
      v-show="contextMenuVisible"
      class="context-menu"
      :style="{ left: contextMenuX + 'px', top: contextMenuY + 'px' }"
    >
      <ul>
        <li @click="handleContextMenu('add')">
          <el-icon><Plus /></el-icon>添加项
        </li>
        <li @click="handleContextMenu('edit')" :class="{ disabled: !selectedRow }">
          <el-icon><Edit /></el-icon>编辑项
        </li>
        <li @click="handleContextMenu('delete')" :class="{ disabled: !selectedRow }">
          <el-icon><Delete /></el-icon>删除项
        </li>
        <li @click="handleContextMenu('open')" :class="{ disabled: !selectedRow }">
          <el-icon><Right /></el-icon>打开项
        </li>
        <li @click="handleContextMenu('check')" :class="{ disabled: !selectedRow }">
          <el-icon><Refresh /></el-icon>检查状态
        </li>
      </ul>
    </div>

    <!-- 添加/编辑Webshell对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="680px"
      :close-on-click-modal="false"
      class="webshell-dialog"
      destroy-on-close
    >
      <el-form :model="webshellForm" label-width="100px" class="webshell-form" status-icon>
        <!-- 基础信息分组 -->
        <div class="form-section">
          <div class="section-header">
            <span class="title">基础信息</span>
            <span class="subtitle">Webshell 的基本连接参数</span>
          </div>

          <el-form-item label="URL地址" required prop="url">
            <el-input
              v-model="webshellForm.url"
              placeholder="http://example.com/shell.jsp"
              clearable
            >
              <template #prepend>
                <el-select
                  v-model="webshellForm.webshellType"
                  style="width: 100px"
                  @change="onWebshellTypeChange"
                >
                  <el-option label="PHP" value="php" />
                  <el-option label="JSP" value="jsp" />
                  <el-option label="CSHARP" value="csharp" />
                  <el-option label="JSPX" value="jspx" />
                  <el-option label="ASP" value="asp" />
                </el-select>
              </template>
            </el-input>
          </el-form-item>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="连接密码" required prop="password">
                <el-input
                  v-model="webshellForm.password"
                  type="password"
                  show-password
                  placeholder="请输入连接密码"
                  prefix-icon="Key"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="参数名" required prop="paramName">
                <el-input
                  v-model="webshellForm.paramName"
                  placeholder="POST/GET参数名"
                  prefix-icon="Operation"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="Cookie名称" required prop="cookieName">
                <el-input v-model="webshellForm.cookieName" placeholder="请输入Cookie名称" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 传输配置分组 -->
        <div class="form-section">
          <div class="section-header">
            <span class="title">传输与加密</span>
            <span class="subtitle">数据通信的加密方式与请求格式</span>
          </div>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="响应加密类型">
                <el-select
                  v-model="webshellForm.encryptType"
                  @change="onEncryptTypeChange"
                  style="width: 100%"
                >
                  <el-option
                    v-for="option in encryptTypeOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="请求格式">
                <el-select
                  v-model="webshellForm.requestFormat"
                  placeholder="选择请求格式"
                  style="width: 100%"
                >
                  <el-option
                    v-for="format in availableRequestFormats"
                    :key="format.value"
                    :label="format.label"
                    :value="format.value"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="自定义格式">
            <div class="request-content-control">
              <el-button
                :type="hasCustomRequestFormat ? 'primary' : 'default'"
                size="small"
                @click="editRequestFormat"
                :icon="Edit"
                class="edit-btn"
              >
                {{ hasCustomRequestFormat ? '编辑自定义格式' : '自定义格式' }}
              </el-button>

              <transition name="el-fade-in">
                <el-tag
                  v-if="hasCustomRequestFormat"
                  size="small"
                  type="success"
                  effect="light"
                  class="status-tag"
                >
                  <el-icon><CircleCheck /></el-icon> 已启用自定义配置
                </el-tag>
              </transition>
            </div>
            <div class="form-tip" v-if="!hasCustomRequestFormat">
              默认使用标准请求格式，点击上方按钮可进行深度定制
            </div>
          </el-form-item>
        </div>

        <!-- 网络代理分组 -->
        <div class="form-section no-border">
          <div class="section-header">
            <span class="title">网络代理</span>
            <span class="subtitle">通过代理服务器连接 Webshell</span>
          </div>

          <el-row :gutter="24">
            <el-col :span="10">
              <el-form-item label="代理类型">
                <el-radio-group v-model="webshellForm.proxyType" size="small">
                  <el-radio-button label="none">无</el-radio-button>
                  <el-radio-button label="http">HTTP</el-radio-button>
                  <el-radio-button label="socks">SOCKS</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-col>
            <el-col :span="14">
              <el-form-item label="代理地址">
                <el-input
                  v-model="webshellForm.proxyHost"
                  placeholder="127.0.0.1:8080"
                  :disabled="webshellForm.proxyType === 'none'"
                  prefix-icon="Link"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer-actions">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveWebshell" :loading="loading">
            <el-icon><Check /></el-icon> 保存配置
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 请求格式内容编辑对话框 -->
    <el-dialog
      v-model="requestFormatDialogVisible"
      title="编辑请求内容定义"
      width="900px"
      :close-on-click-modal="false"
      class="json-editor-dialog"
    >
      <div class="json-editor-container">
        <!-- 工具栏 -->
        <div class="editor-toolbar">
          <div class="toolbar-left">
            <el-button size="small" @click="formatJSON" :icon="'Document'"> 格式化 </el-button>
            <el-button size="small" @click="validateJSON" :icon="'Check'"> 验证JSON </el-button>
            <el-button size="small" @click="copyToClipboard" :icon="'CopyDocument'">
              复制
            </el-button>
          </div>
          <div class="toolbar-right">
            <el-tag v-if="jsonValidationStatus === 'valid'" type="success" size="small">
              <el-icon><CircleCheck /></el-icon> JSON格式正确
            </el-tag>
            <el-tag v-else-if="jsonValidationStatus === 'invalid'" type="danger" size="small">
              <el-icon><CircleClose /></el-icon> JSON格式错误
            </el-tag>
            <el-tag v-else type="info" size="small">
              <el-icon><QuestionFilled /></el-icon> 未验证
            </el-tag>
          </div>
        </div>

        <!-- 帮助提示 -->
        <el-collapse v-model="activeHelp" class="help-collapse">
          <el-collapse-item name="1">
            <template #title>
              <div class="collapse-title">
                <el-icon><InfoFilled /></el-icon>
                <span>支持的变量说明（点击展开/收起）</span>
              </div>
            </template>
            <div class="variable-help">
              <div class="variable-item">
                <code>${random_ua}</code>
                <span>随机User-Agent</span>
              </div>
              <div class="variable-item">
                <code>${uuid}</code>
                <span>随机UUID</span>
              </div>
              <div class="variable-item">
                <code>${timestamp}</code>
                <span>当前时间戳</span>
              </div>
              <div class="variable-item">
                <code>${session_id}</code>
                <span>会话ID</span>
              </div>
              <div class="variable-item">
                <code>${random}</code>
                <span>随机字符串</span>
              </div>
              <div class="variable-item">
                <code>${encrypted_data}</code>
                <span>加密后的载荷数据（必需）</span>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>

        <!-- JSON 编辑器 -->
        <div class="json-editor-wrapper">
          <div class="line-numbers" ref="lineNumbers"></div>
          <textarea
            ref="jsonTextarea"
            v-model="requestFormatContent"
            class="json-textarea"
            placeholder="请输入请求格式的JSON配置..."
            @input="updateLineNumbers"
            @scroll="syncScroll"
            spellcheck="false"
          ></textarea>
        </div>

        <!-- 错误提示 -->
        <div v-if="jsonError" class="json-error">
          <el-icon><WarnTriangleFilled /></el-icon>
          <span>{{ jsonError }}</span>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="cancelEditRequestFormat">取消</el-button>
          <el-button type="primary" @click="confirmEditRequestFormat">确定并保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Delete,
  Right,
  Refresh,
  DocumentAdd,
  ArrowDown,
  Edit,
  CircleCheck,
  CircleClose,
  QuestionFilled,
  WarnTriangleFilled,
  Check,
} from '@element-plus/icons-vue'
import api from '@/api/api'

// 定义emits
const emit = defineEmits(['openWebshell', 'openGenerateDialog'])

// Webshell列表数据
const webshellList = ref([])
const loading = ref(false)

// 右键菜单相关
const contextMenuVisible = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const selectedRow = ref(null)

// 对话框相关
const dialogVisible = ref(false)
const dialogTitle = ref('添加Webshell')
const webshellForm = reactive({
  id: null,
  url: '',
  password: '',
  paramName: '',
  cookieName: 'X-Request-ID',
  status: 'offline',
  proxyHost: '',
  proxyType: 'none',
  webshellType: 'jsp',
  encryptType: 'aes_base64',
  requestFormat: 'plain',
  requestFormatFile: '',
})

// 请求格式编辑相关
const requestFormatDialogVisible = ref(false)
const requestFormatContent = ref('')
const originalRequestFormatContent = ref('')
const jsonValidationStatus = ref('unknown') // 'valid', 'invalid', 'unknown'
const jsonError = ref('')
const activeHelp = ref([]) // 控制帮助折叠面板
const jsonTextarea = ref(null)
const lineNumbers = ref(null)

// webshell类型对应的加密类型选项
// 所有可用的响应加密类型（统一列表）
const allEncryptTypeOptions = [
  { label: 'xor_base64', value: 'xor_base64' },
  { label: 'xor_base64_json', value: 'xor_base64_json' },
  { label: 'xor_raw', value: 'xor_raw' },
  { label: 'xor_raw_png', value: 'xor_raw_png' },
  { label: 'aes_base64', value: 'aes_base64' },
  { label: 'aes_base64_json', value: 'aes_base64_json' },
  { label: 'aes_raw', value: 'aes_raw' },
  { label: 'aes_raw_png', value: 'aes_raw_png' },
]

// 不同类型支持的响应加密类型（前端限制）
const phpEncryptTypeAllowList = new Set([
  'xor_base64',
  'xor_base64_json',
  'xor_raw',
  'xor_raw_png',
  'aes_base64',
  'aes_base64_json',
  'aes_raw',
  'aes_raw_png',
])

const jspEncryptTypeAllowList = new Set(['aes_base64', 'aes_base64_json', 'aes_raw', 'aes_raw_png'])

const csharpEncryptTypeAllowList = new Set([
  'aes_base64',
  'aes_raw',
])

const aspEncryptTypeAllowList = new Set([
  'xor_base64',
  'xor_raw',
])

const getEncryptTypeAllowListByType = (type) => {
  if (type === 'php') {
    return phpEncryptTypeAllowList
  }

  if (type === 'csharp') {
    return csharpEncryptTypeAllowList
  }

  if (type === 'asp') {
    return aspEncryptTypeAllowList
  }

  return jspEncryptTypeAllowList
}

const encryptTypeOptions = computed(() => {
  const type = (webshellForm.webshellType || 'jsp').toLowerCase()
  const allowSet = getEncryptTypeAllowListByType(type)
  return allEncryptTypeOptions.filter((opt) => allowSet.has(opt.value))
})

const ensureEncryptTypeCompatible = () => {
  const type = (webshellForm.webshellType || 'jsp').toLowerCase()
  const allowSet = getEncryptTypeAllowListByType(type)
  if (!allowSet.has(webshellForm.encryptType)) {
    webshellForm.encryptType = type === 'asp' ? 'xor_base64' : 'aes_base64'
  }
}

// 计算属性：判断是否有自定义请求格式
const hasCustomRequestFormat = computed(() => {
  return requestFormatContent.value.trim() !== ''
})

// 根据加密类型动态显示可用的请求格式
const availableRequestFormats = computed(() => {
  const encryptType = webshellForm.encryptType

  // 所有格式定义
  const allFormats = [
    { label: 'form', value: 'form' },
    { label: 'plain', value: 'plain' },
    { label: 'json', value: 'json' },
    { label: 'xml', value: 'xml' },
    { label: 'plain_binary', value: 'plain_binary' },
    { label: 'png', value: 'png' },
  ]

  // form 格式支持所有响应加密类型
  const formFormat = allFormats.filter((f) => f.value === 'form')

  // 判断加密类型并返回对应的请求格式
  if (
    encryptType === 'xor_base64' ||
    encryptType === 'xor_base64_json' ||
    encryptType === 'aes_base64' ||
    encryptType === 'aes_base64_json'
  ) {
    // xml, plain, json 格式支持这些加密类型
    return allFormats.filter(
      (f) => f.value === 'form' || f.value === 'plain' || f.value === 'json' || f.value === 'xml',
    )
  } else if (
    encryptType === 'xor_raw' ||
    encryptType === 'xor_raw_png' ||
    encryptType === 'aes_raw' ||
    encryptType === 'aes_raw_png'
  ) {
    // plain_binary, png 格式支持这些加密类型
    return allFormats.filter(
      (f) => f.value === 'form' || f.value === 'plain_binary' || f.value === 'png',
    )
  } else {
    // 其他加密类型默认只支持 form 格式
    return formFormat
  }
})

// 加载webshell列表
const loadWebshellList = async (checkStatus = false) => {
  loading.value = true
  try {
    const response = await api.coreManagement.getList()
    webshellList.value = response.data.data || []

    // 刷新每个实例的在线状态
    if (checkStatus === true) {
      await refreshAllStatuses()
    }
  } catch (error) {
    console.error('获取webshell列表失败:', error)
    ElMessage.error('获取webshell列表失败: ' + (error.response?.data?.message || error.message))
  } finally {
    loading.value = false
  }
}

// 处理行右键点击事件
const handleRowRightClick = (row, column, event) => {
  // 阻止默认的右键菜单
  event.preventDefault()

  // 设置选中的行
  selectedRow.value = row

  // 显示自定义右键菜单
  contextMenuVisible.value = true
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
}

// 处理右键菜单点击
const handleContextMenu = (action) => {
  contextMenuVisible.value = false

  switch (action) {
    case 'add':
      addWebshell()
      break
    case 'edit':
      if (selectedRow.value) {
        editWebshell(selectedRow.value)
      }
      break
    case 'delete':
      if (selectedRow.value) {
        deleteWebshell(selectedRow.value)
      }
      break
    case 'open':
      if (selectedRow.value) {
        openWebshell(selectedRow.value)
      }
      break
    case 'check':
      if (selectedRow.value) {
        checkWebshellStatus(selectedRow.value)
      }
      break
  }
}

// 添加Webshell
const addWebshell = () => {
  dialogTitle.value = '添加Webshell'
  // 重置表单
  Object.assign(webshellForm, {
    id: null,
    url: '',
    password: '',
    paramName: '',
    cookieName: 'X-Request-ID',
    status: 'offline',
    proxyHost: '',
    proxyType: 'none',
    webshellType: 'jsp',
    encryptType: 'aes_base64',
    requestFormat: 'plain',
    requestFormatFile: '',
  })
  // 重置请求格式内容
  requestFormatContent.value = ''
  originalRequestFormatContent.value = ''
  // 重置原始参数名
  originalParamName.value = ''
  dialogVisible.value = true
}

// 记录原始参数名（用于检测参数名变化）
const originalParamName = ref('')

// 编辑Webshell
const editWebshell = async (row) => {
  dialogTitle.value = '编辑Webshell'

  try {
    // 获取webshell详情
    const response = await api.coreManagement.getWebshellDetail(row.id)

    if (response.data.status === 'success') {
      const webshellData = response.data.data

      // 填充表单数据
      Object.assign(webshellForm, {
        id: webshellData.id,
        url: webshellData.url,
        password: webshellData.password,
        paramName: webshellData.paramName,
        cookieName: webshellData.cookieName || 'X-Request-ID',
        status: webshellData.status,
        proxyHost: webshellData.proxyHost || '',
        proxyType: webshellData.proxyType || 'none',
        webshellType: webshellData.webshellType || 'jsp',
        encryptType: webshellData.encryptType || 'aes_base64',
        requestFormat: webshellData.requestFormat || 'plain',
        requestFormatFile: webshellData.requestFormatFile || '',
      })

      // 不同 webshellType 支持的 encryptType 不同，自动兼容修正
      ensureEncryptTypeCompatible()

      // 记录原始参数名
      originalParamName.value = webshellData.paramName

      // 如果有自定义的请求格式文件，加载其内容
      if (webshellData.requestFormatFile) {
        try {
          const formatResponse = await api.coreManagement.getRequestFormatContent({
            webshell_id: webshellData.id,
          })
          if (formatResponse.data.status === 'success') {
            requestFormatContent.value = formatResponse.data.data.content
            originalRequestFormatContent.value = formatResponse.data.data.content
          }
        } catch (error) {
          console.warn('加载请求格式内容失败，使用默认模板:', error)
          requestFormatContent.value = ''
          originalRequestFormatContent.value = ''
        }
      } else {
        requestFormatContent.value = ''
        originalRequestFormatContent.value = ''
      }

      dialogVisible.value = true
    } else {
      ElMessage.error(response.data.message || '获取webshell详情失败')
    }
  } catch (error) {
    console.error('获取webshell详情失败:', error)
    ElMessage.error('获取webshell详情失败: ' + (error.response?.data?.message || error.message))
  }
}

// 保存Webshell并添加
const saveWebshell = async () => {
  // 表单验证
  if (!webshellForm.url) {
    ElMessage.warning('请输入URL')
    return
  }
  if (!webshellForm.password) {
    ElMessage.warning('请输入密码')
    return
  }
  if (!webshellForm.paramName) {
    ElMessage.warning('请输入参数名')
    return
  }
  if (!webshellForm.cookieName) {
    ElMessage.warning('请输入Cookie名称')
    return
  }

  try {
    // 如果参数名发生变化，同步更新请求内容中的参数名
    if (
      webshellForm.id &&
      originalParamName.value &&
      originalParamName.value !== webshellForm.paramName
    ) {
      console.log(
        `[DEBUG] 检测到参数名变化: ${originalParamName.value} -> ${webshellForm.paramName}`,
      )
      updateParamNameInRequestContent(originalParamName.value, webshellForm.paramName)
      ElMessage.info('已同步更新请求内容中的参数名')
    }

    // 调用API保存webshell
    const response = await api.coreManagement.saveWebshell({
      id: webshellForm.id,
      url: webshellForm.url,
      password: webshellForm.password,
      paramName: webshellForm.paramName,
      cookieName: webshellForm.cookieName,
      proxyHost: webshellForm.proxyHost,
      proxyType: webshellForm.proxyType,
      webshellType: webshellForm.webshellType,
      encryptType: webshellForm.encryptType,
      requestFormat: webshellForm.requestFormat,
      requestFormatFile: webshellForm.requestFormatFile,
      requestFormatContent: requestFormatContent.value, // 添加请求格式内容
    })

    if (response.data.status === 'success') {
      dialogVisible.value = false

      // 检查是否ID发生了变化
      if (response.data.data.id_changed) {
        console.log(
          `[*] Webshell ID已更新: ${response.data.data.old_id} -> ${response.data.data.new_id}`,
        )
        ElMessage.success('配置已更新，由于关键配置变化已生成新ID')
      } else {
        ElMessage.success(webshellForm.id ? '更新成功' : '添加成功')
      }

      // 重新加载列表
      loadWebshellList()
    } else {
      ElMessage.error(response.data.message || '保存失败')
    }
  } catch (error) {
    console.error('保存webshell失败:', error)
    ElMessage.error('保存失败: ' + (error.response?.data?.message || error.message))
  }
}

// 删除Webshell
const deleteWebshell = (row) => {
  ElMessageBox.confirm(`确定要删除 ${row.url} 吗?`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        const response = await api.coreManagement.deleteWebshell(row.id)

        if (response.data.status === 'success') {
          ElMessage.success('删除成功')
          // 重新加载列表
          loadWebshellList()
        } else {
          ElMessage.error(response.data.message || '删除失败')
        }
      } catch (error) {
        console.error('删除webshell失败:', error)
        ElMessage.error('删除失败: ' + (error.response?.data?.message || error.message))
      }
    })
    .catch(() => {
      // 取消删除
    })
}

// 打开Webshell
const openWebshell = async (row) => {
  ElMessage.info(`准备打开Webshell: ${row.url}`)

  // 调用initPayload接口初始化webshell（极简方案：只传递webshell_id）
  try {
    const response = await api.coreManagement.openWebshell({
      webshell_id: row.id, // 只传递ID，所有配置从后端webshell_list.json中读取
    })

    if (response.data.status === 'success') {
      ElMessage.success('Webshell初始化成功')
      console.log('Webshell初始化成功')
      // 如果检测到了系统类型，更新本地列表中的系统类型显示
      const detectedSystemType = response.data.data.DetectedSystemType
      if (detectedSystemType && detectedSystemType !== 'Unknown') {
        const index = webshellList.value.findIndex((item) => item.id === row.id)
        if (index !== -1) {
          webshellList.value[index].systemType = detectedSystemType
          console.log(`[*] 前端已更新系统类型: ${row.id} -> ${detectedSystemType}`)
        }
      }
      console.log('准备发射事件')
      // 发射事件给父组件，让父组件打开详情对话框
      emit('openWebshell', { webshell: row, systemInfo: response.data.data })
    } else {
      ElMessage.error(response.data.message || 'Webshell初始化失败')
    }
  } catch (error) {
    console.error('Webshell初始化失败:', error)
    ElMessage.error('Webshell初始化失败: ' + (error.response?.data?.message || error.message))

    // 即使API调用失败，也打开详情对话框以便调试
    const mockSystemInfo = {
      CurrentDir: '/tmp',
      SystemType: 'Unknown',
      DetectedSystemType: 'Unknown',
    }
    emit('openWebshell', { webshell: row, systemInfo: mockSystemInfo })
  }
}

// 检查webshell状态
const checkWebshellStatus = async (row) => {
  try {
    const response = await api.coreManagement.checkStatus(row.id)

    if (response.data.status === 'success') {
      // 更新状态
      const index = webshellList.value.findIndex((item) => item.id === row.id)
      if (index !== -1) {
        webshellList.value[index].status = response.data.data.webshell_status
      }
    }
  } catch (error) {
    console.error('检查webshell状态失败:', error)
  }
}

// 刷新所有webshell的在线状态
const refreshAllStatuses = async () => {
  if (!webshellList.value || webshellList.value.length === 0) return
  try {
    await Promise.all(
      webshellList.value.map(async (item) => {
        const resp = await api.coreManagement.checkStatus(item.id)
        if (resp.data.status === 'success') {
          item.status = resp.data.data.webshell_status
        }
      }),
    )
  } catch (error) {
    console.error('批量刷新状态失败:', error)
  }
}

// 打开生成webshell对话框
const openGenerateDialog = () => {
  emit('openGenerateDialog')
}

// webshell类型改变时的处理
const onWebshellTypeChange = (value) => {
  // Webshell 类型改变时，可以保持当前的加密类型
  console.log('[DEBUG] Webshell类型改变:', value)
  // 但当前 encryptType 若不被支持，需要自动回退到默认值（避免保存/连接异常）
  ensureEncryptTypeCompatible()
}

// 加密类型改变时的处理
const onEncryptTypeChange = (value) => {
  console.log('[DEBUG] 加密类型改变:', value)

  // 检查当前请求格式是否兼容新的加密类型
  const currentRequestFormat = webshellForm.requestFormat
  const availableFormats = availableRequestFormats.value.map((f) => f.value)

  // 如果当前请求格式不在可用列表中，重置为 form（form 支持所有加密类型）
  if (!availableFormats.includes(currentRequestFormat)) {
    console.log(`[DEBUG] 当前请求格式 ${currentRequestFormat} 不兼容，重置为 form`)
    webshellForm.requestFormat = 'form'
  }
}

// 编辑请求内容格式定义
const editRequestFormat = async () => {
  console.log('[DEBUG] 用户点击编辑请求内容按钮')
  console.log('[DEBUG] 当前requestFormatContent长度:', requestFormatContent.value?.length || 0)

  // 重置验证状态
  jsonValidationStatus.value = 'unknown'
  jsonError.value = ''

  try {
    // 如果已有自定义内容，直接使用
    if (requestFormatContent.value) {
      console.log('[DEBUG] 使用现有的请求格式内容')
      originalRequestFormatContent.value = requestFormatContent.value
      requestFormatDialogVisible.value = true
      await nextTick()
      updateLineNumbers()
      return
    }

    // 如果没有自定义内容，加载默认模板
    console.log('[DEBUG] 加载默认请求格式模板')
    const response = await api.coreManagement.getDefaultRequestFormatTemplate()
    if (response.data.status === 'success') {
      const defaultContent = JSON.stringify(response.data.data, null, 2)
      requestFormatContent.value = defaultContent
      originalRequestFormatContent.value = defaultContent
      requestFormatDialogVisible.value = true
      console.log('[DEBUG] 默认模板加载成功，内容长度:', defaultContent.length)
      await nextTick()
      updateLineNumbers()
    } else {
      // 如果获取默认模板失败，使用硬编码的默认内容
      const defaultContent = JSON.stringify(
        {
          headers: {
            'User-Agent': '${random_ua}',
            'X-Client-ID': '${uuid}',
            Accept: 'application/json, text/plain, */*',
          },
          json: {
            data: '${encrypted_data}',
            timestamp: '${timestamp}',
          },
          form: {
            pass: '${encrypted_data}',
          },
        },
        null,
        2,
      )
      requestFormatContent.value = defaultContent
      originalRequestFormatContent.value = defaultContent
      requestFormatDialogVisible.value = true
      await nextTick()
      updateLineNumbers()
    }
  } catch (error) {
    console.error('加载请求格式模板失败:', error)
    // 使用硬编码的默认内容
    const defaultContent = JSON.stringify(
      {
        headers: {
          'User-Agent': '${random_ua}',
          'X-Client-ID': '${uuid}',
          Accept: 'application/json, text/plain, */*',
        },
        json: {
          data: '${encrypted_data}',
          timestamp: '${timestamp}',
        },
        form: {
          pass: '${encrypted_data}',
        },
      },
      null,
      2,
    )
    requestFormatContent.value = defaultContent
    originalRequestFormatContent.value = defaultContent
    requestFormatDialogVisible.value = true
    await nextTick()
    updateLineNumbers()
  }
}

// 取消编辑请求格式
const cancelEditRequestFormat = () => {
  console.log('[DEBUG] 用户点击取消编辑请求格式')
  // 恢复原始内容
  requestFormatContent.value = originalRequestFormatContent.value
  requestFormatDialogVisible.value = false
  jsonValidationStatus.value = 'unknown'
  jsonError.value = ''
}

// 格式化 JSON
const formatJSON = () => {
  try {
    const parsed = JSON.parse(requestFormatContent.value)
    requestFormatContent.value = JSON.stringify(parsed, null, 2)
    jsonValidationStatus.value = 'valid'
    jsonError.value = ''
    ElMessage.success('JSON 格式化成功')
    updateLineNumbers()
  } catch (err) {
    jsonValidationStatus.value = 'invalid'
    jsonError.value = `格式化失败: ${err.message}`
    ElMessage.error('JSON 格式错误，无法格式化')
  }
}

// 验证 JSON
const validateJSON = () => {
  try {
    if (!requestFormatContent.value.trim()) {
      jsonValidationStatus.value = 'unknown'
      jsonError.value = 'JSON 内容为空'
      ElMessage.warning('JSON 内容为空')
      return
    }
    JSON.parse(requestFormatContent.value)
    jsonValidationStatus.value = 'valid'
    jsonError.value = ''
    ElMessage.success('JSON 格式正确')
  } catch (err) {
    jsonValidationStatus.value = 'invalid'
    jsonError.value = `第 ${err.message.match(/position (\d+)/) ? err.message.match(/position (\d+)/)[1] : '?'} 位置附近: ${err.message}`
    ElMessage.error('JSON 格式错误')
  }
}

// 复制到剪贴板
const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(requestFormatContent.value)
    ElMessage.success('已复制到剪贴板')
  } catch (err) {
    console.error('复制失败:', err)
    ElMessage.error('复制失败')
  }
}

// 更新行号
const updateLineNumbers = () => {
  if (!lineNumbers.value || !requestFormatContent.value) return

  const lines = requestFormatContent.value.split('\n')
  const lineNumbersHTML = lines.map((_, index) => `<div>${index + 1}</div>`).join('')
  lineNumbers.value.innerHTML = lineNumbersHTML
}

// 同步滚动
const syncScroll = () => {
  if (jsonTextarea.value && lineNumbers.value) {
    lineNumbers.value.scrollTop = jsonTextarea.value.scrollTop
  }
}

// 确认编辑请求格式
const confirmEditRequestFormat = () => {
  console.log('[DEBUG] 用户点击确认编辑请求格式')
  console.log('[DEBUG] 当前requestFormatContent长度:', requestFormatContent.value?.length || 0)
  console.log(
    '[DEBUG] requestFormatContent内容预览:',
    requestFormatContent.value?.substring(0, 100) || 'empty',
  )

  try {
    // 验证JSON格式
    if (requestFormatContent.value.trim()) {
      JSON.parse(requestFormatContent.value)
      console.log('[DEBUG] JSON格式验证通过')
    }

    // 更新原始内容
    originalRequestFormatContent.value = requestFormatContent.value
    requestFormatDialogVisible.value = false

    console.log('[DEBUG] 请求格式内容已确认保存到本地变量')
    ElMessage.success('请求内容定义已保存（将在保存webshell时生效）')
  } catch (err) {
    console.error('JSON格式验证失败:', err)
    ElMessage.error('JSON格式错误，请检查语法')
  }
}

// 更新请求内容中的参数名
const updateParamNameInRequestContent = (oldParamName, newParamName) => {
  if (
    !requestFormatContent.value ||
    !oldParamName ||
    !newParamName ||
    oldParamName === newParamName
  ) {
    return
  }

  try {
    const requestConfig = JSON.parse(requestFormatContent.value)
    let updated = false

    // 遍历所有可能的请求格式类型（form, json, xml, plain等）
    const formatTypes = ['form', 'json', 'xml', 'plain', 'plain_binary', 'png']

    formatTypes.forEach((formatType) => {
      if (requestConfig[formatType] && typeof requestConfig[formatType] === 'object') {
        // 检查是否有旧参数名的字段
        if (oldParamName in requestConfig[formatType]) {
          // 获取旧字段的值
          const fieldValue = requestConfig[formatType][oldParamName]
          // 删除旧字段
          delete requestConfig[formatType][oldParamName]
          // 添加新字段
          requestConfig[formatType][newParamName] = fieldValue
          updated = true
          console.log(`[DEBUG] 已更新 ${formatType} 中的参数名: ${oldParamName} -> ${newParamName}`)
        }
      }
    })

    if (updated) {
      // 更新请求内容
      requestFormatContent.value = JSON.stringify(requestConfig, null, 2)
      console.log('[DEBUG] 请求内容中的参数名已同步更新')
    }
  } catch (err) {
    console.error('更新请求内容中的参数名失败:', err)
  }
}

// 处理缓存管理命令
const handleCacheCommand = (command) => {
  switch (command) {
    case 'status':
      getCacheStatus()
      break
    case 'clear':
      clearCache()
      break
  }
}

// 获取缓存状态
const getCacheStatus = async () => {
  try {
    const response = await api.coreManagement.getCacheStatus()
    if (response.data.status === 'success') {
      const { total_instances, cache_keys, shell_types_count, supported_types } = response.data.data

      // 格式化shell类型统计信息
      const typesInfo =
        Object.entries(shell_types_count || {})
          .map(([type, count]) => `${type}: ${count}个`)
          .join(', ') || '无'

      ElMessageBox.alert(
        `缓存实例数量: ${total_instances || 0}\n` +
          `缓存键列表: ${cache_keys && cache_keys.length > 0 ? cache_keys.join(', ') : '无'}\n` +
          `Shell类型统计: ${typesInfo}\n` +
          `支持的类型: ${supported_types && supported_types.length > 0 ? supported_types.join(', ') : '无'}`,
        '缓存状态',
        {
          confirmButtonText: '确定',
          type: 'info',
        },
      )
    } else {
      ElMessage.error(response.data.message || '获取缓存状态失败')
    }
  } catch (error) {
    console.error('获取缓存状态失败:', error)
    ElMessage.error('获取缓存状态失败: ' + (error.response?.data?.message || error.message))
  }
}

// 清空缓存
const clearCache = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有JavaShell实例缓存吗？这将断开所有现有连接。',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )

    const response = await api.coreManagement.clearCache()
    if (response.data.status === 'success') {
      ElMessage.success('缓存清理成功')
    } else {
      ElMessage.error(response.data.message || '清理缓存失败')
    }
  } catch (error) {
    if (error === 'cancel') {
      // 用户取消操作
      return
    }
    console.error('清理缓存失败:', error)
    ElMessage.error('清理缓存失败: ' + (error.response?.data?.message || error.message))
  }
}

// 清理指定webshell的缓存
const clearCacheForWebshell = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要清理 ${row.url} 的缓存实例吗？`, '确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    const response = await api.coreManagement.clearCacheById({ webshell_id: row.id })
    if (response.data.status === 'success') {
      ElMessage.success(response.data.message || '缓存已清理')
    } else {
      ElMessage.error(response.data.message || '清理缓存失败')
    }
  } catch (error) {
    if (error === 'cancel') return
    console.error('清理缓存失败:', error)
    ElMessage.error('清理缓存失败: ' + (error.response?.data?.message || error.message))
  }
}

// 格式化时间戳为可读格式
const formatTimestamp = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp * 1000)
  return date.toLocaleString()
}

// 根据系统类型获取标签类型
const getSystemTypeTag = (type) => {
  switch (type) {
    case 'Windows':
      return 'primary'
    case 'Linux':
      return 'success'
    case 'macOS':
      return 'warning'
    default:
      return 'info'
  }
}

// 点击页面其他地方关闭右键菜单
const handleClickOutside = () => {
  contextMenuVisible.value = false
}

// 添加和移除全局点击事件监听
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  // 加载webshell列表
  loadWebshellList()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

// 暴露给父组件的方法
defineExpose({
  loadWebshellList,
})
</script>

<style scoped>
.webshell-list {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  position: relative;
}

.webshell-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px 20px 0 20px;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

.table-container {
  padding: 0 20px 20px 20px;
}

.context-menu {
  position: fixed;
  background: #fff;
  border: 1px solid #eee;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  padding: 5px 0;
  z-index: 9999;
}

.context-menu ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.context-menu li {
  padding: 8px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  font-size: 14px;
}

.context-menu li:hover {
  background-color: #f5f7fa;
}

.context-menu li.disabled {
  color: #c0c4cc;
  cursor: not-allowed;
}

.context-menu .el-icon {
  margin-right: 8px;
  font-size: 16px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
  line-height: 1.2;
}

/* JSON 编辑器样式 */
.json-editor-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.toolbar-left {
  display: flex;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
}

.help-collapse {
  border: none;
  background: #fff;
}

.help-collapse :deep(.el-collapse-item__header) {
  background: #f0f9ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  padding: 0 15px;
  font-size: 13px;
  color: #0369a1;
}

.help-collapse :deep(.el-collapse-item__wrap) {
  border: none;
  background: #f0f9ff;
  border-radius: 0 0 6px 6px;
}

.help-collapse :deep(.el-collapse-item__content) {
  padding: 15px;
}

.collapse-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.variable-help {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.variable-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  background: #fff;
  border-radius: 4px;
  border: 1px solid #e0e7ff;
}

.variable-item code {
  background: #e0e7ff;
  color: #4338ca;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Courier New', monospace;
  font-size: 13px;
  font-weight: 500;
}

.variable-item span {
  color: #64748b;
  font-size: 12px;
}

.json-editor-wrapper {
  display: flex;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background: #1e1e1e;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.line-numbers {
  min-width: 50px;
  padding: 15px 8px;
  background: #252526;
  color: #858585;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  text-align: right;
  user-select: none;
  overflow: hidden;
  border-right: 1px solid #3e3e42;
}

.line-numbers div {
  height: 20.8px;
}

.json-textarea {
  flex: 1;
  padding: 15px;
  border: none;
  outline: none;
  resize: none;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #1e1e1e;
  color: #d4d4d4;
  min-height: 500px;
  overflow-y: auto;
  overflow-x: auto;
  white-space: pre;
  tab-size: 2;
}

.json-textarea::placeholder {
  color: #6a6a6a;
}

.json-textarea::-webkit-scrollbar {
  width: 12px;
  height: 12px;
}

.json-textarea::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.json-textarea::-webkit-scrollbar-thumb {
  background: #424242;
  border-radius: 6px;
}

.json-textarea::-webkit-scrollbar-thumb:hover {
  background: #4e4e4e;
}

.json-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 15px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 13px;
}

.json-error .el-icon {
  font-size: 18px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 对话框样式优化 */
.form-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px dashed #e4e7ed;
}

.form-section:last-child,
.form-section.no-border {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.section-header {
  margin-bottom: 18px;
  display: flex;
  flex-direction: column;
}

.section-header .title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  margin-bottom: 4px;
}

.section-header .title::before {
  content: '';
  display: inline-block;
  width: 3px;
  height: 14px;
  background: #409eff;
  margin-right: 8px;
  border-radius: 2px;
}

.section-header .subtitle {
  font-size: 12px;
  color: #909399;
  margin-left: 12px; /* 对齐 title 文字 */
}

.request-content-control {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dialog-footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 10px;
}

/* 优化输入框组合样式 */
:deep(.el-input-group__prepend) {
  background-color: #f5f7fa;
  padding: 0 10px;
}

:deep(.el-input-group__prepend .el-select) {
  margin: 0;
}
</style>
