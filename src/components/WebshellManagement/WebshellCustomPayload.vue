<template>
  <div class="custom-payload-container">
    <el-row :gutter="20">
      <el-col :span="7">
        <el-card shadow="hover" class="plugin-list-card">
          <template #header>
            <div class="card-header">
              <span>插件列表</span>
              <el-button size="small" @click="loadPluginList" :loading="listLoading">刷新</el-button>
            </div>
          </template>

          <div class="plugin-toolbar">
            <el-button type="primary" plain @click="createNewPlugin">新建插件</el-button>
          </div>

          <el-empty v-if="!listLoading && pluginList.length === 0" description="暂无插件" />

          <div v-else class="plugin-list">
            <div
              v-for="plugin in pluginList"
              :key="plugin.pluginName"
              class="plugin-item"
              :class="{ active: selectedPluginName === plugin.pluginName }"
              @click="selectPlugin(plugin.pluginName)"
            >
              <div class="plugin-title">{{ plugin.pluginName }}</div>
              <div class="plugin-meta">类名：{{ plugin.className || '-' }}</div>
              <div class="plugin-meta">更新时间：{{ plugin.updatedAtText || '-' }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="17">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>插件编辑与执行</span>
              <el-tag type="info" size="small">{{ props.currentWebshell?.url || '未选择目标' }}</el-tag>
            </div>
          </template>

          <el-form label-width="110px" class="payload-form">
            <el-form-item label="当前插件">
              <div class="current-plugin-row">
                <el-tag v-if="selectedPluginName" type="success">{{ selectedPluginName }}</el-tag>
                <el-tag v-else type="info">未保存</el-tag>
                <span class="class-name-text">源码类名：{{ currentClassName || '-' }}</span>
              </div>
            </el-form-item>

            <el-form-item label="方法名">
              <el-input
                v-model="form.methodName"
                placeholder="例如：portAlive"
                clearable
              />
            </el-form-item>

            <el-form-item label="参数(JSON格式)">
              <el-input
                v-model="form.paramText"
                type="textarea"
                :rows="6"
                placeholder='例如：{"ip":"192.168.47.123","port":3389}'
              />
            </el-form-item>

            <el-form-item label="Payload源码">
              <el-input
                v-model="form.payloadCode"
                type="textarea"
                :rows="18"
                placeholder="请粘贴完整的 Java Payload 源码"
              />
            </el-form-item>

            <el-form-item>
              <div class="action-row">
                <el-button type="primary" :loading="saveLoading" @click="saveCurrentPlugin">
                  保存插件
                </el-button>
                <el-button type="success" :loading="executing" @click="executePayload">
                  执行当前代码
                </el-button>
                <el-button type="danger" plain :disabled="!selectedPluginName" @click="deleteCurrentPlugin">
                  删除插件
                </el-button>
                <el-button class="ai-generate-button" @click="openAiDialog">
                  <el-icon><Promotion /></el-icon>
                  AI生成插件
                </el-button>
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="hover" class="result-card">
          <template #header>
            <div class="card-header">
              <span>执行结果</span>
              <el-tag :type="executeResult.success ? 'success' : 'info'" size="small">
                {{ executeResult.success ? '成功' : '待执行' }}
              </el-tag>
            </div>
          </template>

          <div class="result-meta">
            <div>插件名：{{ executeResult.pluginName || '-' }}</div>
            <div>实际类名：{{ executeResult.className || '-' }}</div>
            <div>原始类名：{{ executeResult.originalClassName || '-' }}</div>
            <div>方法名：{{ executeResult.methodName || '-' }}</div>
          </div>
          <pre class="result-output">{{ executeResult.output || '暂无执行结果' }}</pre>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog
      v-model="aiDialogVisible"
      width="720px"
      destroy-on-close
      class="ai-generate-dialog"
      :close-on-click-modal="!aiGenerating"
      :close-on-press-escape="!aiGenerating"
      :show-close="!aiGenerating"
    >
      <template #header>
        <div class="ai-dialog-header">
          <div class="ai-dialog-title-row">
            <span class="ai-dialog-icon">
              <el-icon><Promotion /></el-icon>
            </span>
            <div>
              <div class="ai-dialog-title">AI生成插件</div>
              <div class="ai-dialog-subtitle">输入功能需求，自动生成可编译的 Java Payload 源码</div>
            </div>
          </div>
        </div>
      </template>

      <div class="ai-dialog-body">
        <div class="ai-example-row">
          <span class="ai-example-label">示例需求</span>
          <el-tag
            v-for="example in aiRequirementExamples"
            :key="example"
            class="ai-example-tag"
            effect="plain"
            @click="useAiExample(example)"
          >
            {{ example }}
          </el-tag>
        </div>

        <el-input
          v-model="aiRequirement"
          type="textarea"
          :rows="8"
          resize="none"
          maxlength="4000"
          show-word-limit
          placeholder="例如：生成一个端口探测 payload，支持 methodName=portAlive，参数为 ip 和 port，连接成功返回 ok:alive，失败返回 ok:dead，并保留模板既有的执行框架。"
        />

        <div class="ai-dialog-tip">
          建议描述：方法名、参数名、返回格式、异常处理要求，以及是否需要兼容现有模板调用方式。
        </div>

        <div v-if="aiGenerateMessage" class="ai-generate-message">
          <el-alert
            :title="aiGenerateMessage"
            :type="aiGenerateError ? 'error' : 'success'"
            :closable="false"
            show-icon
          />
        </div>
      </div>

      <template #footer>
        <div class="ai-dialog-footer">
          <div class="ai-generating-hint" v-if="aiGenerating">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在生成并编译校验 Java Payload，请稍候...</span>
          </div>
          <div class="ai-dialog-actions">
            <el-button :disabled="aiGenerating" @click="aiDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="aiGenerating" class="ai-confirm-button" @click="generatePayloadByAi">
              生成源码
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, Promotion } from '@element-plus/icons-vue'
import { javaShellApi } from '@/api/api'

const props = defineProps({
  currentWebshell: {
    type: Object,
    default: null,
  },
  visible: {
    type: Boolean,
    default: false,
  },
})

const form = reactive({
  methodName: '',
  paramText: '{\n  "ip": "192.168.47.123",\n  "port": 3389\n}',
  payloadCode: '',
})

const listLoading = ref(false)
const saveLoading = ref(false)
const executing = ref(false)
const pluginList = ref([])
const selectedPluginName = ref('')
const currentClassName = ref('')
const aiDialogVisible = ref(false)
const aiGenerating = ref(false)
const aiRequirement = ref('')
const aiGenerateMessage = ref('')
const aiGenerateError = ref(false)
const aiRequirementExamples = [
  '生成一个端口探测 payload，方法名为 portAlive，参数为 ip 和 port，返回 ok:alive 或 ok:dead',
  '生成一个目录列出 payload，方法名为 listDir，参数为 path，返回目标目录下的文件名列表',
  '生成一个文件读取 payload，方法名为 readFileText，参数为 path，返回文本内容',
]

const executeResult = reactive({
  success: false,
  pluginName: '',
  className: '',
  originalClassName: '',
  methodName: '',
  output: '',
})

const parseClassName = (sourceCode) => {
  const publicMatch = sourceCode.match(/\bpublic\s+class\s+([A-Za-z_][A-Za-z0-9_]*)\b/)
  if (publicMatch) return publicMatch[1]

  const normalMatch = sourceCode.match(/\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b/)
  return normalMatch ? normalMatch[1] : ''
}

const parseParamJson = () => {
  if (!form.paramText.trim()) {
    return {}
  }

  const parsed = JSON.parse(form.paramText)
  if (Array.isArray(parsed) || typeof parsed !== 'object' || parsed === null) {
    throw new Error('参数JSON必须是对象')
  }
  return parsed
}

const resetResult = () => {
  executeResult.success = false
  executeResult.pluginName = ''
  executeResult.className = ''
  executeResult.originalClassName = ''
  executeResult.methodName = ''
  executeResult.output = ''
}

const openAiDialog = () => {
  aiGenerateMessage.value = ''
  aiGenerateError.value = false
  if (!aiRequirement.value.trim()) {
    aiRequirement.value =
      '生成一个端口探测 payload，方法名为 portAlive，参数为 ip 和 port，连接成功返回 ok:alive，失败返回 ok:dead。'
  }
  aiDialogVisible.value = true
}

const useAiExample = (example) => {
  aiRequirement.value = example
}

const formatParamExample = (paramExample) => {
  if (!paramExample || typeof paramExample !== 'object' || Array.isArray(paramExample)) {
    return ''
  }
  return JSON.stringify(paramExample, null, 2)
}

const loadPluginList = async () => {
  listLoading.value = true
  try {
    const response = await javaShellApi.listCustomPayloads()
    if (response.data.status === 'success') {
      pluginList.value = response.data.data || []
    } else {
      ElMessage.error(response.data.message || '获取插件列表失败')
    }
  } catch (error) {
    ElMessage.error(`获取插件列表失败: ${error.response?.data?.message || error.message}`)
  } finally {
    listLoading.value = false
  }
}

const selectPlugin = async (pluginName) => {
  try {
    const response = await javaShellApi.getCustomPayloadDetail({
      pluginName,
    })

    if (response.data.status === 'success') {
      selectedPluginName.value = response.data.data.pluginName || pluginName
      currentClassName.value = response.data.data.className || ''
      form.payloadCode = response.data.data.payloadCode || ''
      ElMessage.success(`已加载插件 ${selectedPluginName.value}`)
    } else {
      ElMessage.error(response.data.message || '获取插件详情失败')
    }
  } catch (error) {
    ElMessage.error(`获取插件详情失败: ${error.response?.data?.message || error.message}`)
  }
}

const saveCurrentPlugin = async () => {
  if (!form.payloadCode.trim()) {
    ElMessage.warning('请输入Payload源码')
    return
  }

  saveLoading.value = true
  try {
    const response = await javaShellApi.saveCustomPayload({
      payloadCode: form.payloadCode,
      oldPluginName: selectedPluginName.value || '',
    })

    if (response.data.status === 'success') {
      selectedPluginName.value = response.data.data.pluginName || ''
      currentClassName.value = response.data.data.className || parseClassName(form.payloadCode)
      ElMessage.success(response.data.message || '插件保存成功')
      await loadPluginList()
    } else {
      ElMessage.error(response.data.message || '插件保存失败')
    }
  } catch (error) {
    ElMessage.error(`插件保存失败: ${error.response?.data?.message || error.message}`)
  } finally {
    saveLoading.value = false
  }
}

const executePayload = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择webshell')
    return
  }
  if (!form.methodName.trim()) {
    ElMessage.warning('请输入方法名')
    return
  }
  if (!form.payloadCode.trim()) {
    ElMessage.warning('请输入Payload源码')
    return
  }

  let param = {}
  try {
    param = parseParamJson()
  } catch (error) {
    ElMessage.error(`参数JSON格式错误: ${error.message}`)
    return
  }

  executing.value = true
  try {
    const response = await javaShellApi.executePayload({
      webshell_id: props.currentWebshell.id,
      payloadCode: form.payloadCode,
      methodName: form.methodName.trim(),
      param,
    })

    if (response.data.status === 'success') {
      executeResult.success = true
      executeResult.pluginName = response.data.data.pluginName || selectedPluginName.value
      executeResult.className = response.data.data.className || ''
      executeResult.originalClassName = response.data.data.originalClassName || ''
      executeResult.methodName = response.data.data.methodName || ''
      executeResult.output = response.data.data.output || ''
      currentClassName.value = response.data.data.originalClassName || parseClassName(form.payloadCode)
      ElMessage.success(response.data.message || 'Payload执行成功')
    } else {
      executeResult.success = false
      executeResult.output = response.data.message || 'Payload执行失败'
      ElMessage.error(response.data.message || 'Payload执行失败')
    }
  } catch (error) {
    executeResult.success = false
    executeResult.output = error.response?.data?.message || error.message
    ElMessage.error(`Payload执行失败: ${error.response?.data?.message || error.message}`)
  } finally {
    executing.value = false
  }
}


const deleteCurrentPlugin = async () => {
  if (!selectedPluginName.value) {
    ElMessage.warning('请先选择一个插件')
    return
  }

  try {
    await ElMessageBox.confirm(`确定要删除插件 ${selectedPluginName.value} 吗？`, '确认', {
      type: 'warning',
    })

    const response = await javaShellApi.deleteCustomPayload({
      pluginName: selectedPluginName.value,
    })

    if (response.data.status === 'success') {
      ElMessage.success(response.data.message || '插件删除成功')
      createNewPlugin()
      await loadPluginList()
    } else {
      ElMessage.error(response.data.message || '插件删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`插件删除失败: ${error.response?.data?.message || error.message}`)
    }
  }
}

const generatePayloadByAi = async () => {
  if (!aiRequirement.value.trim()) {
    ElMessage.warning('请输入要实现的功能需求')
    return
  }

  aiGenerating.value = true
  aiGenerateMessage.value = ''
  aiGenerateError.value = false
  try {
    const response = await javaShellApi.generatePayload({
      requirement: aiRequirement.value.trim(),
    })

    if (response.data.status === 'success') {
      const payloadCode = response.data.data?.payloadCode || ''
      form.payloadCode = payloadCode
      if (response.data.data?.methodName) {
        form.methodName = response.data.data.methodName
      }
      if (response.data.data?.paramExample && Object.keys(response.data.data.paramExample).length > 0) {
        form.paramText = formatParamExample(response.data.data.paramExample)
      }
      currentClassName.value = response.data.data?.className || parseClassName(payloadCode)
      selectedPluginName.value = ''
      resetResult()
      aiGenerateMessage.value = response.data.message || 'AI 已生成源码并回填到编辑框'
      aiGenerateError.value = false
      ElMessage.success(response.data.message || 'AI 生成成功')
      aiDialogVisible.value = false
    } else {
      aiGenerateMessage.value = response.data.message || 'AI 生成失败'
      aiGenerateError.value = true
      ElMessage.error(response.data.message || 'AI 生成失败')
    }
  } catch (error) {
    aiGenerateMessage.value = error.response?.data?.message || error.message
    aiGenerateError.value = true
    ElMessage.error(`AI 生成失败: ${error.response?.data?.message || error.message}`)
  } finally {
    aiGenerating.value = false
  }
}



const createNewPlugin = () => {
  selectedPluginName.value = ''
  currentClassName.value = ''
  form.methodName = ''
  form.paramText = '{\n  "ip": "192.168.47.123",\n  "port": 3389\n}'
  form.payloadCode = ''
  resetResult()
}

watch(
  () => form.payloadCode,
  (newCode) => {
    currentClassName.value = parseClassName(newCode)
  },
)

watch(
  () => props.visible,
  (newValue) => {
    if (newValue) {
      loadPluginList()
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.custom-payload-container {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.plugin-list-card {
  height: 100%;
}

.plugin-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.plugin-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 760px;
  overflow-y: auto;
}

.plugin-item {
  padding: 12px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.plugin-item:hover {
  border-color: #409eff;
  background: #f5f9ff;
}

.plugin-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.plugin-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.plugin-meta {
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
}

.payload-form {
  width: 100%;
}

.current-plugin-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.class-name-text {
  font-size: 13px;
  color: #606266;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.ai-generate-button {
  color: #fff;
  border: none;
  background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%);
  box-shadow: 0 10px 24px rgba(99, 102, 241, 0.28);
}

.ai-generate-button:hover {
  color: #fff;
  border: none;
  background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
}

.ai-dialog-header {
  position: relative;
}

.ai-dialog-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.ai-dialog-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  color: #fff;
  font-size: 20px;
  background: radial-gradient(circle at top left, #a855f7, #2563eb 72%);
  box-shadow: 0 10px 30px rgba(99, 102, 241, 0.35);
}

.ai-dialog-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.ai-dialog-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.ai-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ai-example-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.ai-example-label {
  font-size: 13px;
  font-weight: 600;
  color: #6366f1;
}

.ai-example-tag {
  cursor: pointer;
  border-color: #c7d2fe;
  color: #4f46e5;
  background: #eef2ff;
}

.ai-dialog-tip {
  padding: 12px 14px;
  border: 1px solid #e0e7ff;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.6;
  color: #4b5563;
  background: linear-gradient(180deg, #f8faff 0%, #eef2ff 100%);
}

.ai-generate-message {
  margin-top: 4px;
}

.ai-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ai-generating-hint {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #6366f1;
}

.ai-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-left: auto;
}

.ai-confirm-button {
  min-width: 108px;
  border: none;
  background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%);
}

.result-card {
  margin-top: 20px;
}

.result-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
  color: #606266;
  font-size: 14px;
}

.result-output {
  margin: 0;
  padding: 16px;
  min-height: 180px;
  border-radius: 8px;
  background: #111827;
  color: #e5e7eb;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
}
</style>
