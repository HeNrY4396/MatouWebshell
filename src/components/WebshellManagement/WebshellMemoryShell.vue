<template>
  <div class="memory-shell-container">
    <div class="memory-shell-form">
      <el-form
        :model="memoryShellForm"
        :rules="formRules"
        ref="memoryShellFormRef"
        label-width="120px"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="内存马路径" prop="path">
              <el-input
                v-model="memoryShellForm.path"
                placeholder="请输入内存马路径，如：/test"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密钥" prop="secretKey">
              <el-input
                v-model="memoryShellForm.secretKey"
                placeholder="请输入内存马密钥"
                clearable
                show-password
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="参数名" prop="paramName">
              <el-input
                v-model="memoryShellForm.paramName"
                placeholder="请输入参数名，如：pass"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="内存马类型" prop="payload">
              <el-select
                v-model="memoryShellForm.payload"
                placeholder="请选择内存马类型"
                style="width: 100%"
              >
                <el-option label="SERVLET" value="SERVLET" />
                <el-option label="FILTER" value="FILTER" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Cookie名称" required prop="ck_name">
              <el-input
                v-model="memoryShellForm.ck_name"
                placeholder="请输入Cookie名称"
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </div>

    <div class="memory-shell-actions">
      <el-button
        type="primary"
        :loading="loadingMemoryShell"
        @click="loadMemoryShell"
        :disabled="!isFormValid"
      >
        <el-icon><Upload /></el-icon>
        加载内存马
      </el-button>

      <el-button
        type="danger"
        :loading="unloadingMemoryShell"
        @click="unloadMemoryShell"
        :disabled="!isFormValid"
      >
        <el-icon><Delete /></el-icon>
        卸载内存马
      </el-button>
      <el-button
        type="primary"
        :loading="loadingServlet"
        @click="getAllServlet"
        :disabled="!isFormValid"
      >
        <el-icon><Upload /></el-icon>
        获取所有Servlet和Filter
      </el-button>
      <el-button type="info" @click="showMemoryShellHistory" plain>
        <el-icon><Clock /></el-icon>
        查看历史记录
      </el-button>
    </div>

    <!-- 操作结果展示 -->
    <div class="memory-shell-result" v-if="operationResult">
      <el-alert
        :title="operationResult.type === 'success' ? '操作成功' : '操作失败'"
        :type="operationResult.type"
        :description="operationResult.message"
        show-icon
        :closable="true"
        @close="operationResult = null"
      />
    </div>

    <!-- 内存马状态信息 -->
    <div class="memory-shell-status" v-if="memoryShellStatus">
      <el-card>
        <template #header>
          <div class="card-header">
            <span v-if="memoryShellStatus.type === 'servletInfo'">Servlet信息</span>
            <span v-else>内存马状态</span>
          </div>
        </template>

        <!-- 显示Servlet和Filter信息 -->
        <div v-if="memoryShellStatus.type === 'servletInfo'">
          <el-descriptions :column="3" border style="margin-bottom: 20px">
            <el-descriptions-item label="Servlet总数">
              <el-tag type="success">{{ memoryShellStatus.servletCount || 0 }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Filter总数">
              <el-tag type="info">{{ memoryShellStatus.filterCount || 0 }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">
              {{ memoryShellStatus.updateTime || '未知' }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- Servlet列表 -->
          <div class="servlet-list">
            <h4 style="margin-bottom: 10px">Servlet详细信息：</h4>
            <el-table
              :data="memoryShellStatus.servletList"
              border
              size="small"
              max-height="300"
              style="width: 100%"
            >
              <el-table-column prop="url" label="URL路径" width="200" />
              <el-table-column prop="wrapperName" label="Wrapper名称" width="200" />
              <el-table-column prop="servletClass" label="Servlet类" />
            </el-table>
          </div>
          <!-- Filter列表 -->
          <div class="filter-list" style="margin-top: 20px">
            <h4 style="margin-bottom: 10px">Filter详细信息：</h4>
            <el-table
              :data="memoryShellStatus.filterList || []"
              border
              size="small"
              max-height="300"
              style="width: 100%"
            >
              <el-table-column prop="filterName" label="Filter名称" width="200" />
              <el-table-column prop="urlPatterns" label="URL路径" />
              <template #empty>
                <el-empty description="暂无Filter信息" />
              </template>
            </el-table>
          </div>

          <!-- 原始数据（可展开查看） -->
          <el-collapse style="margin-top: 20px">
            <el-collapse-item title="查看原始数据" name="rawData">
              <pre
                style="
                  background: #f5f5f5;
                  padding: 10px;
                  border-radius: 4px;
                  font-size: 12px;
                  white-space: pre-wrap;
                "
                >{{ memoryShellStatus.rawData }}</pre
              >
            </el-collapse-item>
          </el-collapse>
        </div>

        <!-- 显示内存马状态 -->
        <el-descriptions v-else :column="2" border>
          <el-descriptions-item label="状态">
            <el-tag :type="memoryShellStatus.active ? 'success' : 'danger'">
              {{ memoryShellStatus.active ? '已激活' : '未激活' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="路径">
            {{ memoryShellStatus.path || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="类型">
            {{ memoryShellStatus.payload || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="组件名称">
            {{ memoryShellStatus.component_name || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="加载时间">
            {{ memoryShellStatus.loadTime || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="密钥">
            {{ memoryShellStatus.secretKey || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="参数名">
            {{ memoryShellStatus.paramName || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="Cookie名称">
            {{ memoryShellStatus.cookie_name || '未知' }}
          </el-descriptions-item>
          
        </el-descriptions>
      </el-card>
    </div>
  </div>

  <!-- 卸载内存马对话框 -->
  <el-dialog
    v-model="unloadDialogVisible"
    title="卸载内存马"
    width="500px"
    :close-on-click-modal="false"
  >
    <el-form :model="unloadForm" label-width="120px">
      <el-form-item label="内存马类型">
        <el-radio-group v-model="unloadForm.type">
          <el-radio value="servlet">Servlet类型</el-radio>
          <el-radio value="filter">Filter类型</el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- Servlet 类型的输入框 -->
      <template v-if="unloadForm.type === 'servlet'">
        <el-form-item label="内存马路径" required>
          <el-input
            v-model="unloadForm.urlPattern"
            placeholder="请输入内存马URL路径，如：/test"
            clearable
          />
        </el-form-item>
        <el-form-item label="Wrapper名称" required>
          <el-input v-model="unloadForm.wrapperName" placeholder="请输入Wrapper名称" clearable />
        </el-form-item>
      </template>

      <!-- Filter 类型的输入框 -->
      <template v-if="unloadForm.type === 'filter'">
        <el-form-item label="Filter名称" required>
          <el-input v-model="unloadForm.filterName" placeholder="请输入Filter名称" clearable />
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="unloadDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="unloadingMemoryShell" @click="confirmUnloadMemoryShell">
          确认卸载
        </el-button>
      </span>
    </template>
  </el-dialog>

  <!-- 内存马历史记录对话框 -->
  <el-dialog
    v-model="memoryShellHistoryVisible"
    title="内存马历史记录"
    width="80%"
    :close-on-click-modal="false"
    top="5vh"
  >
    <div class="history-header" style="margin-bottom: 15px">
      <el-alert
        title="历史记录说明"
        type="info"
        description="记录了在此Webshell上成功加载的所有内存马信息，数据保存在服务器中。"
        show-icon
        :closable="false"
      />
    </div>

    <div class="history-actions" style="margin-bottom: 15px">
      <el-button
        type="danger"
        size="small"
        @click="clearAllHistory"
        :disabled="memoryShellHistory.length === 0"
      >
        <el-icon><Delete /></el-icon>
        清空所有记录
      </el-button>
      <el-tag type="info" style="margin-left: 10px">
        共 {{ memoryShellHistory.length }} 条记录
      </el-tag>
    </div>

    <el-table
      :data="memoryShellHistory"
      border
      size="small"
      max-height="500"
      style="width: 100%"
      :empty-text="memoryShellHistory.length === 0 ? '暂无历史记录' : ''"
    >
      <el-table-column prop="path" label="内存马路径" width="150" />
      <el-table-column prop="payload" label="类型" width="150">
        <template #default="scope">
          <el-tag
            :type="scope.row.payload.includes('SERVLET') ? 'success' : 'warning'"
            size="small"
          >
            {{ scope.row.payload }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="componentName" label="组件名称" width="200" />
      <el-table-column prop="cookieName" label="Cookie名称" width="120" />
      <el-table-column prop="cookieValue" label="Cookie值" width="150">
        <template #default="scope">
          <span style="font-family: 'Courier New', monospace; font-size: 12px">
            {{ scope.row.cookieValue }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="loadTime" label="加载时间" width="160" />
      <el-table-column prop="createTime" label="记录时间" width="160" />
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="scope">
          <el-button size="small" type="danger" plain @click="removeFromHistory(scope.row.id)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="memoryShellHistoryVisible = false">关闭</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Delete, Clock } from '@element-plus/icons-vue'
import api from '@/api/api.js'

// Props
const props = defineProps({
  currentWebshell: {
    type: Object,
    required: true,
  },
  systemInfo: {
    type: Object,
    default: () => ({}),
  },
  visible: {
    type: Boolean,
    default: false,
  },
})

// Refs
const memoryShellFormRef = ref()
const loadingMemoryShell = ref(false)
const unloadingMemoryShell = ref(false)
const checkingStatus = ref(false)
const loadingServlet = ref(false)
const operationResult = ref(null)
const memoryShellStatus = ref(null)

// 历史记录相关
const memoryShellHistoryVisible = ref(false)
const memoryShellHistory = ref([])

// Form data
const memoryShellForm = ref({
  path: '/test',
  secretKey: 'rebeyond',
  paramName: 'pass',
  payload: 'SERVLET',
  ck_name: 'JSESSIONID',
})

// Form validation rules
const formRules = {
  path: [
    { required: true, message: '请输入内存马路径', trigger: 'blur' },
    { min: 1, max: 100, message: '路径长度应在 1 到 100 个字符', trigger: 'blur' },
  ],
  secretKey: [
    { required: true, message: '请输入密钥', trigger: 'blur' },
    { min: 1, max: 50, message: '密钥长度应在 1 到 50 个字符', trigger: 'blur' },
  ],
  paramName: [
    { required: true, message: '请输入参数名', trigger: 'blur' },
    { min: 1, max: 20, message: '参数名长度应在 1 到 20 个字符', trigger: 'blur' },
  ],
  payload: [{ required: true, message: '请选择内存马类型', trigger: 'change' }],
}

// Computed
const isFormValid = computed(() => {
  return (
    memoryShellForm.value.path &&
    memoryShellForm.value.secretKey &&
    memoryShellForm.value.paramName &&
    memoryShellForm.value.payload
  )
})

// 历史记录工具函数
const loadHistoryFromServer = async () => {
  try {
    const response = await api.javaShell.getMemoryShellHistory({
      webshell_url: props.currentWebshell.url,
    })

    if (response.data.status === 'success') {
      memoryShellHistory.value = response.data.data || []
    } else {
      console.error('加载历史记录失败:', response.data.message)
      memoryShellHistory.value = []
    }
  } catch (error) {
    console.error('加载历史记录失败:', error)
    memoryShellHistory.value = []
  }
}

const saveHistoryToServer = async (historyItem) => {
  try {
    const response = await api.javaShell.saveMemoryShellHistory({
      webshell_url: props.currentWebshell.url,
      history_item: historyItem,
    })

    if (response.data.status === 'success') {
      // 重新加载历史记录以获取最新数据
      await loadHistoryFromServer()
      return true
    } else {
      console.error('保存历史记录失败:', response.data.message)
      return false
    }
  } catch (error) {
    console.error('保存历史记录失败:', error)
    return false
  }
}

const addToHistory = async (memoryShellInfo) => {
  const historyItem = {
    id: Date.now() + Math.random(), // 唯一ID
    webshellUrl: props.currentWebshell.url,
    path: memoryShellInfo.path,
    payload: memoryShellInfo.payload,
    className: memoryShellInfo.className,
    secretKey: memoryShellForm.value.secretKey,
    paramName: memoryShellForm.value.paramName,
    cookieName: memoryShellInfo.cookie_name,
    cookieValue: memoryShellInfo.cookie_value,
    componentName: memoryShellInfo.component_name,
    loadTime: memoryShellInfo.loadTime,
    createTime: new Date().toLocaleString(),
  }

  // 保存到服务器（后端会处理重复检查和数量限制）
  await saveHistoryToServer(historyItem)
}

const removeFromHistory = async (id) => {
  try {
    const response = await api.javaShell.deleteMemoryShellHistory({
      webshell_url: props.currentWebshell.url,
      record_id: id,
    })

    if (response.data.status === 'success') {
      // 重新加载历史记录
      await loadHistoryFromServer()
      ElMessage.success('记录已删除')
    } else {
      ElMessage.error(response.data.message || '删除记录失败')
    }
  } catch (error) {
    console.error('删除记录失败:', error)
    ElMessage.error('删除记录失败')
  }
}

const clearAllHistory = async () => {
  try {
    const response = await api.javaShell.clearMemoryShellHistory({
      webshell_url: props.currentWebshell.url,
    })

    if (response.data.status === 'success') {
      // 重新加载历史记录
      await loadHistoryFromServer()
      ElMessage.success('所有记录已清空')
    } else {
      ElMessage.error(response.data.message || '清空记录失败')
    }
  } catch (error) {
    console.error('清空记录失败:', error)
    ElMessage.error('清空记录失败')
  }
}

// Methods
const loadMemoryShell = async () => {
  try {
    await memoryShellFormRef.value.validate()

    loadingMemoryShell.value = true
    operationResult.value = null

    const requestData = {
      webshell_id: props.currentWebshell.id,
      memoryShellPath: memoryShellForm.value.path,
      memoryShellSecretKey: memoryShellForm.value.secretKey,
      memoryShellParamName: memoryShellForm.value.paramName,
      memoryShellPayload: memoryShellForm.value.payload,
      memoryShellCookieName: memoryShellForm.value.ck_name,
    }

    const response = await api.javaShell.loadMemoryShell(requestData)

    if (response.data.status === 'success') {
      operationResult.value = {
        type: 'success',
        message: '内存马加载成功！',
      }
      ElMessage.success('内存马加载成功')

      // 添加到历史记录
      addToHistory(response.data.data)

      // 刷新状态
      setTimeout(() => {
        checkMemoryShellStatus()
      }, 1000)
    } else {
      throw new Error(response.data.message || '内存马加载失败')
    }
  } catch (error) {
    console.error('加载内存马失败:', error)
    operationResult.value = {
      type: 'error',
      message: error.message || '内存马加载失败',
    }
    ElMessage.error(error.message || '内存马加载失败')
  } finally {
    loadingMemoryShell.value = false
  }
}

// 卸载对话框的响应式数据
const unloadDialogVisible = ref(false)
const unloadForm = ref({
  type: 'servlet', // 'servlet' 或 'filter'
  urlPattern: '', // servlet类型需要
  wrapperName: '', // servlet类型需要
  filterName: '', // filter类型需要
})

const showUnloadDialog = () => {
  // 重置表单
  unloadForm.value = {
    type: 'servlet',
    urlPattern: '',
    wrapperName: '',
    filterName: '',
  }
  unloadDialogVisible.value = true
}

const confirmUnloadMemoryShell = async () => {
  try {
    // 验证必填字段
    if (unloadForm.value.type === 'servlet') {
      if (!unloadForm.value.urlPattern || !unloadForm.value.wrapperName) {
        ElMessage.error('请填写完整的内存马路径和Wrapper名称')
        return
      }
    } else if (unloadForm.value.type === 'filter') {
      if (!unloadForm.value.filterName) {
        ElMessage.error('请填写Filter名称')
        return
      }
    }

    unloadingMemoryShell.value = true
    operationResult.value = null

    // 构建请求数据
    const requestData = {
      webshell_id: props.currentWebshell.id,
      type: unloadForm.value.type,
    }

    // 根据类型添加不同的参数
    if (unloadForm.value.type === 'servlet') {
      requestData.urlPattern = unloadForm.value.urlPattern
      requestData.wrapperName = unloadForm.value.wrapperName
    } else if (unloadForm.value.type === 'filter') {
      requestData.filterName = unloadForm.value.filterName
    }

    const response = await api.javaShell.unloadMemoryShell(requestData)

    if (response.data.status === 'success') {
      operationResult.value = {
        type: 'success',
        message: '内存马卸载成功！',
      }
      ElMessage.success('内存马卸载成功')
      unloadDialogVisible.value = false

      // 清空状态并刷新
      memoryShellStatus.value = null

      // 延迟刷新状态以确保卸载操作完全完成
      setTimeout(() => {
        checkMemoryShellStatus()
      }, 1000)
    } else {
      throw new Error(response.data.message || '内存马卸载失败')
    }
  } catch (error) {
    console.error('卸载内存马失败:', error)
    operationResult.value = {
      type: 'error',
      message: error.message || '内存马卸载失败',
    }
    ElMessage.error(error.message || '内存马卸载失败')
  } finally {
    unloadingMemoryShell.value = false
  }
}

const unloadMemoryShell = () => {
  showUnloadDialog()
}

const checkMemoryShellStatus = async () => {
  try {
    checkingStatus.value = true

    const requestData = {
      webshell_id: props.currentWebshell.id,
      memoryShellPath: memoryShellForm.value.path,
    }

    const response = await api.javaShell.checkMemoryShellStatus(requestData)

    if (response.data.status === 'success') {
      memoryShellStatus.value = response.data.data
    }
  } catch (error) {
    console.error('检查内存马状态失败:', error)
  } finally {
    checkingStatus.value = false
  }
}

const getAllServlet = async () => {
  try {
    loadingServlet.value = true
    operationResult.value = null

    const requestData = {
      webshell_id: props.currentWebshell.id,
    }

    const response = await api.javaShell.getAllServlet(requestData)

    if (response.data.status === 'success') {
      const servletData = response.data.data

      // 将servlet信息显示在内存马状态区域
      memoryShellStatus.value = {
        active: true,
        servletCount: servletData.servletCount,
        servletList: servletData.servletList,
        filterCount: servletData.filterCount,
        filterList: servletData.filterList,
        rawData: servletData.rawData,
        type: 'servletInfo', // 标识这是servlet信息
        updateTime: new Date().toLocaleString(),
      }

      operationResult.value = {
        type: 'success',
        message: `成功获取 ${servletData.servletCount} 个Servlet，${servletData.filterCount || 0} 个Filter！`,
      }
      ElMessage.success(
        `成功获取 ${servletData.servletCount} 个Servlet，${servletData.filterCount || 0} 个Filter`,
      )
    } else {
      throw new Error(response.data.message || '获取Servlet信息失败')
    }
  } catch (error) {
    console.error('获取所有Servlet失败:', error)
    operationResult.value = {
      type: 'error',
      message: error.message || '获取Servlet信息失败',
    }
    ElMessage.error(error.message || '获取Servlet信息失败')
  } finally {
    loadingServlet.value = false
  }
}

// 显示历史记录对话框
const showMemoryShellHistory = async () => {
  await loadHistoryFromServer()
  memoryShellHistoryVisible.value = true
}

// Lifecycle
onMounted(async () => {
  // 加载历史记录
  await loadHistoryFromServer()

  if (props.visible) {
    checkMemoryShellStatus()
  }
})
</script>

<style scoped>
.memory-shell-container {
  padding: 20px;
}

.memory-shell-form {
  margin-bottom: 20px;
}

.memory-shell-actions {
  text-align: center;
  margin-bottom: 20px;
}

.memory-shell-actions .el-button {
  margin: 0 10px;
  min-width: 120px;
}

.memory-shell-result {
  margin-bottom: 20px;
}

.memory-shell-status {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-descriptions {
  margin-top: 10px;
}
</style>
