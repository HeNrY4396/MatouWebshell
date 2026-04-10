<template>
  <div class="webshell-config-panel">
    <div class="config-header">
      <h3>Webshell Manager 全局配置</h3>
      <p class="config-description">在这里设置全局配置参数，避免每次操作时重复配置</p>
    </div>

    <el-tabs v-model="activeConfigTab" type="border-card" class="config-tabs">
      <!-- 大文件上传参数配置 -->
      <el-tab-pane label="大文件上传参数" name="bigUpload">
        <div class="config-section">
          <div class="section-header">
            <h4>大文件上传配置</h4>
            <p class="section-description">
              配置大文件上传的默认参数，这些参数将作为上传时的默认值使用
            </p>
          </div>

          <el-form :model="uploadConfig" label-width="150px" class="config-form">
            <el-form-item label="默认块大小">
              <div class="form-item-content">
                <el-input-number
                  v-model="uploadConfig.chunkMbSize"
                  :min="0.1"
                  :max="50"
                  :step="0.1"
                  :precision="1"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">MB</span>
                <div class="field-help">
                  建议值：小文件(&lt; 50MB): 1-2MB；中等文件(50-500MB): 2-5MB；大文件(&gt; 500MB):
                  5-10MB
                </div>
              </div>
            </el-form-item>

            <el-form-item label="上传间隔时间">
              <div class="form-item-content">
                <el-input-number
                  v-model="uploadConfig.delaySeconds"
                  :min="0"
                  :max="10"
                  :step="0.1"
                  :precision="1"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">秒</span>
                <div class="field-help">块与块之间的上传间隔时间，避免服务器压力过大</div>
              </div>
            </el-form-item>

            <el-form-item label="最大重试次数">
              <div class="form-item-content">
                <el-input-number
                  v-model="uploadConfig.maxRetries"
                  :min="1"
                  :max="20"
                  :step="1"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">次</span>
                <div class="field-help">单个块上传失败时的重试次数</div>
              </div>
            </el-form-item>

            <el-form-item label="自动切换阈值">
              <div class="form-item-content">
                <el-input-number
                  v-model="uploadConfig.autoSwitchSize"
                  :min="1"
                  :max="1000"
                  :step="1"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">MB</span>
                <div class="field-help">文件大小超过此阈值时，自动建议使用大文件上传模式</div>
              </div>
            </el-form-item>

            <el-form-item label="块大小浮动">
              <div class="form-item-content">
                <el-switch
                  v-model="uploadConfig.enableChunkSizeVariation"
                  active-text="启用"
                  inactive-text="关闭"
                  style="margin-right: 15px"
                />
                <div class="field-help">
                  启用后块大小将在基础值上下浮动，避免被检测系统识别固定模式
                </div>
              </div>
            </el-form-item>

            <el-form-item
              label="浮动范围"
              v-if="uploadConfig.enableChunkSizeVariation"
              class="variation-range-item"
            >
              <div class="form-item-content">
                <el-input-number
                  v-model="uploadConfig.chunkSizeVariationMb"
                  :min="0.01"
                  :max="5"
                  :step="0.01"
                  :precision="2"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">MB</span>
                <div class="field-help">
                  块大小浮动范围。例如：基础块大小1MB，浮动范围0.2MB，实际块大小将在0.8MB-1.2MB之间随机变化
                </div>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveUploadConfig">保存配置</el-button>
              <el-button @click="resetUploadConfig">重置为默认值</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- 大文件下载参数配置 -->
      <el-tab-pane label="大文件下载参数" name="bigDownload">
        <div class="config-section">
          <div class="section-header">
            <h4>大文件下载配置</h4>
            <p class="section-description">配置大文件下载的默认参数</p>
          </div>

          <el-form :model="downloadConfig" label-width="150px" class="config-form">
            <el-form-item label="默认块大小">
              <div class="form-item-content">
                <el-input-number
                  v-model="downloadConfig.chunkKbSize"
                  :min="8"
                  :max="10240"
                  :step="64"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">KB</span>
                <div class="field-help">
                  建议值：小文件(&lt; 10MB): 64-256KB；中等文件(10-100MB): 512KB-2MB；大文件(&gt;
                  100MB): 2-8MB
                </div>
              </div>
            </el-form-item>

            <el-form-item label="下载请求间隔">
              <div class="form-item-content">
                <el-input-number
                  v-model="downloadConfig.timeoutSeconds"
                  :min="0.1"
                  :max="30"
                  :step="0.1"
                  :precision="1"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">秒</span>
                <div class="field-help">下载每个块之间的等待时间，用于避免请求过于频繁</div>
              </div>
            </el-form-item>

            <el-form-item label="启用块大小浮动">
              <div class="form-item-content">
                <el-switch
                  v-model="downloadConfig.enableChunkSizeVariation"
                  active-text="启用"
                  inactive-text="禁用"
                />
                <div class="field-help">
                  启用后每个下载块的大小会在基础值附近随机浮动，增加隐蔽性
                </div>
              </div>
            </el-form-item>

            <el-form-item label="块大小浮动范围" v-show="downloadConfig.enableChunkSizeVariation">
              <div class="form-item-content">
                <el-input-number
                  v-model="downloadConfig.chunkSizeVariationKb"
                  :min="8"
                  :max="1024"
                  :step="8"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">KB</span>
                <div class="field-help">块大小浮动的范围，实际块大小 = 基础块大小 ± 浮动范围</div>
              </div>
            </el-form-item>

            <el-form-item label="自动切换阈值">
              <div class="form-item-content">
                <el-input-number
                  v-model="downloadConfig.autoSwitchSize"
                  :min="1"
                  :max="1000"
                  :step="1"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">MB</span>
                <div class="field-help">文件大小超过此阈值时，自动建议使用大文件下载模式</div>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveDownloadConfig">保存配置</el-button>
              <el-button @click="resetDownloadConfig">重置为默认值</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- JSP功能配置 -->
      <el-tab-pane label="JSP功能配置" name="jspFunction">
        <div class="config-section">
          <div class="section-header">
            <h4>JSP功能配置</h4>
            <p class="section-description">配置JSP功能的相关参数</p>
          </div>
          <el-form :model="jspFunctionConfig" label-width="180px" class="config-form">
            <el-form-item label="类名混淆模式">
              <el-radio-group v-model="jspFunctionConfig.classnameObfuscation">
                <el-radio label="random">随机类名</el-radio>
                <el-radio label="dictionary">类名字典</el-radio>
                <el-radio label="specified">指定类名</el-radio>
                <el-radio label="none">原始类名</el-radio>
              </el-radio-group>
              <div class="field-help">控制Java Payload类名的混淆方式</div>
            </el-form-item>
            <el-form-item
              label="指定类名"
              v-if="jspFunctionConfig.classnameObfuscation === 'specified'"
            >
              <el-input
                v-model="jspFunctionConfig.specifiedClassname"
                placeholder="如：com.example.MyPayload 或 MyPayload"
              />
              <div class="field-help">当选择“指定类名”时必填，支持含包名的完整类名</div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveJspFunctionConfig">保存配置</el-button>
              <el-button @click="resetJspFunctionConfig">重置为默认值</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- 通用设置 -->
      <el-tab-pane label="LLM配置" name="llm">
        <div class="config-section">
          <div class="section-header">
            <h4>AI 生成配置</h4>
            <p class="section-description">配置 Java Payload AI 生成功能所使用的 LLM 参数</p>
          </div>

          <el-form :model="llmConfig" label-width="180px" class="config-form">
            <el-form-item label="Provider">
              <el-radio-group v-model="llmConfig.provider">
                <el-radio label="openai">OpenAI Compatible</el-radio>
                <el-radio label="codex_proxy">Codex Proxy</el-radio>
                <el-radio label="gemini_proxy">Gemini Proxy</el-radio>
              </el-radio-group>
              <div class="field-help">选择后端 AI 生成接口使用的模型接入方式</div>
            </el-form-item>

            <el-form-item label="Base URL">
              <el-input
                v-model="llmConfig.baseUrl"
                placeholder="如：https://api.openai.com/v1 或你的中转地址"
              />
              <div class="field-help">填写兼容 OpenAI Chat Completions 的接口地址</div>
            </el-form-item>

            <el-form-item label="模型名称">
              <el-input
                v-model="llmConfig.model"
                placeholder="如：gpt-4.1、gpt-5、gpt-5.2-codex"
              />
              <div class="field-help">后端生成 Java Payload 时会使用这里配置的模型</div>
            </el-form-item>

            <el-form-item label="API Key">
              <el-input
                v-model="llmConfig.apiKey"
                type="password"
                show-password
                placeholder="请输入 LLM API Key"
              />
              <div class="field-help">仅保存在本地全局配置中，不会在前端直接调用模型</div>
            </el-form-item>

            <el-form-item label="Temperature">
              <div class="form-item-content">
                <el-input-number
                  v-model="llmConfig.temperature"
                  :min="0"
                  :max="2"
                  :step="0.1"
                  :precision="1"
                  controls-position="right"
                  style="width: 180px"
                />
                <div class="field-help">建议 0.1 到 0.4，偏低可提升 Payload 生成稳定性</div>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveLlmConfig">保存配置</el-button>
              <el-button @click="resetLlmConfig">重置为默认值</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <el-tab-pane label="通用设置" name="general">
        <div class="config-section">
          <div class="section-header">
            <h4>通用配置</h4>
            <p class="section-description">其他通用设置选项</p>
          </div>

          <el-form :model="generalConfig" label-width="150px" class="config-form">
            <el-form-item label="请求超时时间">
              <div class="form-item-content">
                <el-input-number
                  v-model="generalConfig.requestTimeout"
                  :min="5"
                  :max="300"
                  :step="5"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">秒</span>
                <div class="field-help">HTTP请求的超时时间</div>
              </div>
            </el-form-item>

            <el-form-item label="自动刷新间隔">
              <div class="form-item-content">
                <el-input-number
                  v-model="generalConfig.autoRefreshInterval"
                  :min="0"
                  :max="300"
                  :step="5"
                  controls-position="right"
                  style="width: 180px"
                />
                <span class="unit-label">秒</span>
                <div class="field-help">文件列表自动刷新间隔，0表示不自动刷新</div>
              </div>
            </el-form-item>

            <el-form-item label="启用调试日志">
              <el-switch
                v-model="generalConfig.enableDebugLog"
                active-text="开启"
                inactive-text="关闭"
              />
              <div class="field-help">开启后将在控制台输出详细的调试信息</div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="saveGeneralConfig">保存配置</el-button>
              <el-button @click="resetGeneralConfig">重置为默认值</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 配置操作按钮 -->
    <div class="config-actions">
      <el-button type="success" @click="exportConfig">导出配置</el-button>
      <el-button type="warning" @click="importConfig">导入配置</el-button>
      <el-button type="danger" @click="clearAllConfig">清空所有配置</el-button>
    </div>

    <!-- 隐藏的文件输入框用于导入配置 -->
    <input
      ref="fileInput"
      type="file"
      accept=".json"
      style="display: none"
      @change="handleImportFile"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api/api'

// 活跃的配置标签页
const activeConfigTab = ref('bigUpload')

// 默认配置
const DEFAULT_CONFIG = {
  upload: {
    chunkMbSize: 1.0,
    delaySeconds: 0.5,
    maxRetries: 5,
    autoSwitchSize: 10,
    enableChunkSizeVariation: false,
    chunkSizeVariationMb: 0.2,
  },
  download: {
    chunkKbSize: 512,
    timeoutSeconds: 1.0,
    enableChunkSizeVariation: false,
    chunkSizeVariationKb: 128,
    autoSwitchSize: 50,
  },
  general: {
    requestTimeout: 60,
    autoRefreshInterval: 0,
    enableDebugLog: false,
  },
  jspFunction: {
    classnameObfuscation: 'random',
    specifiedClassname: '',
  },
  llm: {
    provider: 'openai',
    baseUrl: '',
    model: '',
    apiKey: '',
    temperature: 0.1,
  },
}

// 状态
const uploadConfig = ref({ ...DEFAULT_CONFIG.upload })
const downloadConfig = ref({ ...DEFAULT_CONFIG.download })
const generalConfig = ref({ ...DEFAULT_CONFIG.general })
const jspFunctionConfig = ref({ ...DEFAULT_CONFIG.jspFunction })
const llmConfig = ref({ ...DEFAULT_CONFIG.llm })
const loading = ref(false)

// 文件输入框引用
const fileInput = ref(null)

const mergeConfig = (base, incoming) => {
  const result = { ...base }
  Object.keys(incoming || {}).forEach((key) => {
    const val = incoming[key]
    if (val && typeof val === 'object' && !Array.isArray(val) && typeof base[key] === 'object') {
      result[key] = mergeConfig(base[key], val)
    } else {
      result[key] = val
    }
  })
  return result
}

const normalizeConfig = (cfg) => {
  const merged = mergeConfig(DEFAULT_CONFIG, cfg || {})
  merged.upload.chunkMbSize = Number(merged.upload.chunkMbSize ?? 1) || 1
  merged.upload.delaySeconds = Number(merged.upload.delaySeconds ?? 0.5) || 0.5
  merged.upload.maxRetries = Number.parseInt(merged.upload.maxRetries ?? 5) || 5
  merged.upload.autoSwitchSize = Number.parseInt(merged.upload.autoSwitchSize ?? 10) || 10
  merged.upload.enableChunkSizeVariation = !!merged.upload.enableChunkSizeVariation
  merged.upload.chunkSizeVariationMb = Number(merged.upload.chunkSizeVariationMb ?? 0.2) || 0.2

  merged.download.chunkKbSize = Number.parseInt(merged.download.chunkKbSize ?? 512) || 512
  merged.download.timeoutSeconds = Number(merged.download.timeoutSeconds ?? 1) || 1
  merged.download.enableChunkSizeVariation = !!merged.download.enableChunkSizeVariation
  merged.download.chunkSizeVariationKb =
    Number.parseInt(merged.download.chunkSizeVariationKb ?? 128) || 128
  merged.download.autoSwitchSize = Number.parseInt(merged.download.autoSwitchSize ?? 50) || 50

  merged.general.requestTimeout = Number.parseInt(merged.general.requestTimeout ?? 60) || 60
  merged.general.autoRefreshInterval = Number.parseInt(merged.general.autoRefreshInterval ?? 0) || 0
  merged.general.enableDebugLog = !!merged.general.enableDebugLog

  merged.jspFunction.classnameObfuscation = (
    merged.jspFunction.classnameObfuscation || 'random'
  ).toLowerCase()
  if (
    !['random', 'dictionary', 'specified', 'none'].includes(merged.jspFunction.classnameObfuscation)
  ) {
    merged.jspFunction.classnameObfuscation = 'random'
  }
  merged.jspFunction.specifiedClassname = (merged.jspFunction.specifiedClassname || '').trim()

  merged.llm.provider = (merged.llm.provider || 'openai').trim()
  if (!['openai', 'codex_proxy', 'gemini_proxy'].includes(merged.llm.provider)) {
    merged.llm.provider = 'openai'
  }
  merged.llm.baseUrl = (merged.llm.baseUrl || '').trim()
  merged.llm.model = (merged.llm.model || '').trim()
  merged.llm.apiKey = (merged.llm.apiKey || '').trim()
  merged.llm.temperature = Number(merged.llm.temperature ?? 0.1)
  if (Number.isNaN(merged.llm.temperature)) {
    merged.llm.temperature = 0.1
  }
  merged.llm.temperature = Math.min(2, Math.max(0, merged.llm.temperature))
  merged.llm = {
    provider: merged.llm.provider,
    baseUrl: merged.llm.baseUrl,
    model: merged.llm.model,
    apiKey: merged.llm.apiKey,
    temperature: merged.llm.temperature,
  }

  return merged
}

// 组件挂载时加载配置（从后端）
onMounted(() => {
  loadAllConfigs()
})

// 加载所有配置
const loadAllConfigs = async () => {
  loading.value = true
  try {
    const resp = await api.coreManagement.getGlobalConfig()
    if (resp.data?.status === 'success') {
      const cfg = normalizeConfig(resp.data.data || {})
      uploadConfig.value = cfg.upload
      downloadConfig.value = cfg.download
      generalConfig.value = cfg.general
      jspFunctionConfig.value = cfg.jspFunction
      llmConfig.value = cfg.llm
    } else {
      resetAllToDefault()
    }
  } catch (error) {
    console.error('[CONFIG] 加载全局配置失败，使用默认值:', error)
    resetAllToDefault()
  } finally {
    loading.value = false
  }
}

const saveAllConfigs = async () => {
  try {
    const payload = normalizeConfig({
      upload: uploadConfig.value,
      download: downloadConfig.value,
      general: generalConfig.value,
      jspFunction: jspFunctionConfig.value,
      llm: llmConfig.value,
    })
    const resp = await api.coreManagement.saveGlobalConfig(payload)
    if (resp.data?.status === 'success') {
      ElMessage.success('配置保存成功')
    } else {
      ElMessage.error(resp.data?.message || '配置保存失败')
    }
  } catch (error) {
    console.error('[CONFIG] 配置保存失败:', error)
    ElMessage.error('配置保存失败')
  }
}

// 分组保存入口
const saveUploadConfig = () => saveAllConfigs()
const saveDownloadConfig = () => saveAllConfigs()
const saveGeneralConfig = () => saveAllConfigs()
const saveJspFunctionConfig = () => saveAllConfigs()
const saveLlmConfig = () => saveAllConfigs()

// 重置上传配置
const resetUploadConfig = () => {
  uploadConfig.value = { ...DEFAULT_CONFIG.upload }
  ElMessage.info('上传配置已重置为默认值')
}

// 重置下载配置
const resetDownloadConfig = () => {
  downloadConfig.value = { ...DEFAULT_CONFIG.download }
  ElMessage.info('下载配置已重置为默认值')
}

// 重置通用配置
const resetGeneralConfig = () => {
  generalConfig.value = { ...DEFAULT_CONFIG.general }
  ElMessage.info('通用配置已重置为默认值')
}

const resetJspFunctionConfig = () => {
  jspFunctionConfig.value = { ...DEFAULT_CONFIG.jspFunction }
  ElMessage.info('JSP配置已重置为默认值')
}

const resetLlmConfig = () => {
  llmConfig.value = { ...DEFAULT_CONFIG.llm }
  ElMessage.info('LLM配置已重置为默认值')
}

const resetAllToDefault = () => {
  resetUploadConfig()
  resetDownloadConfig()
  resetGeneralConfig()
  resetJspFunctionConfig()
  resetLlmConfig()
}

// 导出配置
const exportConfig = () => {
  try {
    const allConfig = {
      upload: uploadConfig.value,
      download: downloadConfig.value,
      general: generalConfig.value,
      jspFunction: jspFunctionConfig.value,
      llm: llmConfig.value,
      exportTime: new Date().toISOString(),
    }

    const blob = new Blob([JSON.stringify(allConfig, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = `webshell_config_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    URL.revokeObjectURL(url)
    ElMessage.success('配置导出成功')
  } catch (error) {
    console.error('[CONFIG] 导出配置失败:', error)
    ElMessage.error('导出配置失败')
  }
}

// 导入配置
const importConfig = () => {
  fileInput.value?.click()
}

// 处理导入文件
const handleImportFile = (event) => {
  const file = event.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const config = JSON.parse(e.target.result)

      if (!config.upload && !config.download && !config.general && !config.llm) {
        ElMessage.error('无效的配置文件格式')
        return
      }

      const merged = normalizeConfig({
        upload: config.upload,
        download: config.download,
        general: config.general,
        jspFunction: config.jspFunction,
        llm: config.llm,
      })
      uploadConfig.value = merged.upload
      downloadConfig.value = merged.download
      generalConfig.value = merged.general
      jspFunctionConfig.value = merged.jspFunction
      llmConfig.value = merged.llm
      ElMessage.success('配置导入成功，已加载到面板')
    } catch (error) {
      console.error('[CONFIG] 导入配置失败:', error)
      ElMessage.error('导入配置失败：文件格式错误')
    }
  }

  reader.readAsText(file)
  event.target.value = '' // 清空文件输入框
}

// 清空所有配置
const clearAllConfig = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有配置吗？此操作将删除所有保存的配置数据，且无法恢复。',
      '确认清空',
      {
        confirmButtonText: '确定清空',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )

    resetAllToDefault()
    await saveAllConfigs()

    ElMessage.info('所有配置已清空并重置为默认值')
  } catch {
    // 用户取消操作
  }
}

// 获取上传/下载/通用配置（供其他组件调用）
const getUploadConfig = () => ({ ...uploadConfig.value })
const getDownloadConfig = () => ({ ...downloadConfig.value })
const getGeneralConfig = () => ({ ...generalConfig.value })
const getJspFunctionConfig = () => ({ ...jspFunctionConfig.value })
const getLlmConfig = () => ({ ...llmConfig.value })

// 暴露方法给父组件
defineExpose({
  getUploadConfig,
  getDownloadConfig,
  getGeneralConfig,
  getJspFunctionConfig,
  getLlmConfig,
})

console.log('WebshellConfig 组件已加载')
</script>

<style scoped>
.webshell-config-panel {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.config-header {
  margin-bottom: 20px;
  text-align: center;
}

.config-header h3 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 24px;
}

.config-description {
  color: #606266;
  font-size: 14px;
  margin: 0;
}

.config-tabs {
  margin-bottom: 20px;
}

.config-section {
  padding: 20px;
}

.section-header {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e4e7ed;
}

.section-header h4 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 18px;
}

.section-description {
  color: #606266;
  font-size: 14px;
  margin: 0;
  line-height: 1.5;
}

.config-form {
  max-width: 600px;
}

.form-item-content {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.unit-label {
  margin-left: 8px;
  color: #909399;
  font-size: 14px;
  min-width: 30px;
}

.field-help {
  width: 100%;
  margin-top: 5px;
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.config-actions {
  text-align: center;
  padding: 20px;
  border-top: 1px solid #e4e7ed;
}

.config-actions .el-button {
  margin: 0 10px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .webshell-config-panel {
    padding: 10px;
  }

  .config-form {
    max-width: 100%;
  }

  .config-actions .el-button {
    margin: 5px;
    width: calc(100% - 10px);
  }
}

/* 自定义标签页样式 */
.config-tabs :deep(.el-tabs__content) {
  padding: 0;
}

.config-tabs :deep(.el-tab-pane) {
  background-color: #fff;
  border-radius: 0 0 8px 8px;
}

/* 表单项样式调整 */
.config-form :deep(.el-form-item) {
  margin-bottom: 25px;
}

.config-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #303133;
}

.config-form :deep(.el-form-item__content) {
  align-items: flex-start;
}

/* 浮动范围表单项样式 */
.variation-range-item {
  background-color: #f8f9fa;
  border-radius: 6px;
  padding: 15px;
  margin-left: 20px;
  border-left: 3px solid #409eff;
  transition: all 0.3s ease;
}

.variation-range-item:hover {
  background-color: #f0f2f5;
}

.variation-range-item :deep(.el-form-item__label) {
  color: #409eff;
  font-weight: 600;
}

/* 输入框样式 */
.config-form :deep(.el-input-number) {
  width: 180px;
}

.config-form :deep(.el-switch) {
  margin-right: 10px;
}
</style>
