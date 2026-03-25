<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="updateVisible"
    title="生成 Webshell"
    width="580px"
    :close-on-click-modal="false"
    class="generate-webshell-dialog"
    @open="handleOpen"
    destroy-on-close
  >
    <el-form
      ref="formRef"
      :model="generateForm"
      label-width="100px"
      class="generate-form"
      status-icon
    >
      <div class="form-section">
        <div class="section-title">基础配置</div>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="参数名" required prop="paramName">
              <el-input v-model="generateForm.paramName" placeholder="例如: pass" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="类型" required prop="webshellType">
              <el-select
                v-model="generateForm.webshellType"
                placeholder="选择类型"
                style="width: 100%"
              >
                <el-option label="PHP" value="php" />
                <el-option label="JSP" value="jsp" />
                <el-option label="JSPX" value="jspx" />
                <el-option label="ASP" value="asp" />
                <el-option label="CSHARP" value="csharp" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="模板文件" required prop="templateName">
          <el-select
            v-model="generateForm.templateName"
            placeholder="选择模板文件"
            :loading="templateLoading"
            :disabled="templateLoading || templateOptions.length === 0"
            style="width: 100%"
          >
            <el-option
              v-for="template in templateOptions"
              :key="template"
              :label="template"
              :value="template"
            />
          </el-select>
          <div class="form-tip" v-if="generateForm.templateName">
            <el-icon class="tip-icon"><InfoFilled /></el-icon>
            <span>基于所选模板生成，不同模板包含不同特性</span>
          </div>
        </el-form-item>

        <el-form-item label="CookieName" required prop="cookieName">
          <el-input
            v-model="generateForm.cookieName"
            placeholder="例如PHPSESSID或JSESSIONID"
            clearable
          />
          <div class="form-tip">
            <el-icon class="tip-icon"><InfoFilled /></el-icon>
            <span>相当于激活webshell功能的开关</span>
          </div>
        </el-form-item>

        <el-form-item v-if="isCsharpType" label="类名" required prop="className">
          <el-input
            v-model="generateForm.className"
            placeholder="例如: GKD"
            clearable
          />
          <div class="form-tip">
            <el-icon class="tip-icon"><InfoFilled /></el-icon>
            <span>用于 Assembly.CreateInstance() 的实例化类名</span>
          </div>
        </el-form-item>
      </div>

      <div class="form-section">
        <div class="section-title">
          <span>高级选项</span>
          <el-tooltip content="配置变量替换和混淆策略以增强免杀效果" placement="top">
            <el-icon class="title-icon"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>

        <el-form-item v-if="isPhpType" label="模拟正常业务">
          <div class="normal-template-control">
            <el-switch
              v-model="generateForm.normalTemplate.enabled"
              active-text="启用"
              inactive-text="关闭"
              inline-prompt
              :disabled="normalTemplateOptions.length === 0"
            />
            <el-select
              v-if="generateForm.normalTemplate.enabled"
              v-model="generateForm.normalTemplate.template"
              placeholder="选择业务模板"
              class="normal-template-select"
              :loading="normalTemplateLoading"
              :disabled="normalTemplateOptions.length === 0"
              clearable
            >
              <el-option
                v-for="template in normalTemplateOptions"
                :key="template"
                :label="template"
                :value="template"
              />
            </el-select>
          </div>
          <div class="form-tip">
            <el-icon class="tip-icon"><InfoFilled /></el-icon>
            <span>
              将上述生成的webshell内容嵌入到正常业务页面模板中，增加隐蔽性（正常业务模板来源于
              webshell/normal_template）
            </span>
          </div>
        </el-form-item>

        <transition name="expand">
          <div v-if="isJspType" class="obfuscation-panel">
            <div class="panel-header">JSP 混淆配置</div>
            <div class="panel-body">
              <el-form-item label="启用混淆" label-width="90px">
                <el-switch
                  v-model="generateForm.obfuscation.enabled"
                  inline-prompt
                  active-text="启用"
                  inactive-text="关闭"
                />
              </el-form-item>

              <transition name="expand">
                <div v-if="generateForm.obfuscation.enabled">
                  <el-form-item label="混淆模式" label-width="90px">
                    <el-select v-model="generateForm.obfuscation.method" style="width: 100%">
                      <el-option label="Unicode" value="unicode" />
                    </el-select>
                  </el-form-item>

                  <el-form-item label="关键字" label-width="90px">
                    <el-select
                      v-model="generateForm.obfuscation.keywords"
                      placeholder="输入关键字回车添加"
                      multiple
                      filterable
                      allow-create
                      default-first-option
                      style="width: 100%"
                      collapse-tags
                      collapse-tags-tooltip
                    >
                      <el-option
                        v-for="keyword in keywordSuggestions"
                        :key="keyword"
                        :label="keyword"
                        :value="keyword"
                      />
                    </el-select>
                  </el-form-item>

                  <el-form-item label="混淆比率" label-width="90px">
                    <div class="slider-wrap">
                      <el-slider
                        v-model="generateForm.obfuscation.unicodeRatio"
                        :min="0.1"
                        :max="1.0"
                        :step="0.1"
                        show-input
                        :show-input-controls="false"
                        input-size="small"
                      />
                    </div>
                  </el-form-item>
                </div>
              </transition>
            </div>
          </div>
        </transition>

        <transition name="expand">
          <div v-if="isJspxType" class="obfuscation-panel">
            <div class="panel-header">JSPX 混淆配置</div>
            <div class="panel-body">
              <el-form-item label="启用混淆" label-width="90px">
                <el-switch
                  v-model="generateForm.obfuscation.enabled"
                  inline-prompt
                  active-text="启用"
                  inactive-text="关闭"
                />
              </el-form-item>

              <transition name="expand">
                <div v-if="generateForm.obfuscation.enabled">
                  <el-form-item label="混淆模式" label-width="90px">
                    <el-select
                      v-model="generateForm.obfuscation.method"
                      placeholder="选择混淆模式"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="option in obfuscationMethodOptions.filter((o) => o.value !== 'none')"
                        :key="option.value"
                        :label="option.label"
                        :value="option.value"
                      />
                    </el-select>
                  </el-form-item>

                  <el-form-item label="关键字" label-width="90px">
                    <el-select
                      v-model="generateForm.obfuscation.keywords"
                      placeholder="输入关键字回车添加"
                      multiple
                      filterable
                      allow-create
                      default-first-option
                      style="width: 100%"
                      collapse-tags
                      collapse-tags-tooltip
                    >
                      <el-option
                        v-for="keyword in keywordSuggestions"
                        :key="keyword"
                        :label="keyword"
                        :value="keyword"
                      />
                    </el-select>
                  </el-form-item>

                  <el-form-item v-if="needsUnicodeRatio" label="Unicode" label-width="90px">
                    <div class="slider-wrap">
                      <el-slider
                        v-model="generateForm.obfuscation.unicodeRatio"
                        :min="0.1"
                        :max="1.0"
                        :step="0.1"
                        show-input
                        :show-input-controls="false"
                        input-size="small"
                      />
                    </div>
                  </el-form-item>

                  <el-form-item v-if="needsHtmlRatio" label="HTML实体" label-width="90px">
                    <div class="slider-wrap">
                      <el-slider
                        v-model="generateForm.obfuscation.htmlRatio"
                        :min="0.1"
                        :max="1.0"
                        :step="0.1"
                        show-input
                        :show-input-controls="false"
                        input-size="small"
                      />
                    </div>
                  </el-form-item>
                </div>
              </transition>
            </div>
          </div>
        </transition>

        <!-- 高级选项：标识符替换（开关 + 详细配置） -->
        <div class="obfuscation-panel">
          <div class="panel-header">标识符替换配置</div>
          <div class="panel-body">
            <el-form-item label="启用替换" label-width="90px">
              <div class="identifier-toggle">
                <el-switch
                  v-model="generateForm.identifierReplace.enabled"
                  inline-prompt
                  active-text="启用"
                  inactive-text="关闭"
                />
                <span class="toggle-text">对指定前缀变量进行替换</span>
              </div>
            </el-form-item>

            <transition name="expand">
              <div v-if="generateForm.identifierReplace.enabled">
                <el-form-item label="替换模式" label-width="90px">
                  <div class="identifier-wrap">
                    <el-select
                      v-model="generateForm.identifierReplace.method"
                      placeholder="模式"
                      style="width: 130px"
                    >
                      <el-option label="随机生成" value="random" />
                      <el-option label="变量池文件" value="file" />
                    </el-select>
                    <el-input
                      v-model="generateForm.identifierReplace.prefix"
                      placeholder="变量前缀"
                      style="flex: 1"
                      maxlength="8"
                    >
                      <template #prepend>前缀</template>
                    </el-input>
                  </div>
                </el-form-item>
                <div class="form-tip">
                  <el-icon class="tip-icon"><InfoFilled /></el-icon>
                  <span>仅替换以指定前缀开头的变量名（如默认的 $_）</span>
                </div>
              </div>
            </transition>
          </div>
        </div>
      </div>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="handleGenerateWebshell" :loading="generatingWebshell">
          <el-icon class="el-icon--left"><Download /></el-icon>生成
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, QuestionFilled, Download } from '@element-plus/icons-vue'
import api from '@/api/api'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:visible'])

const updateVisible = (val) => {
  emit('update:visible', val)
}

const closeDialog = () => {
  emit('update:visible', false)
}

// 生成webshell相关
const generateForm = ref({
  paramName: '',
  webshellType: 'jsp',
  templateName: '',
  cookieName: '',
  className: '',
  identifierReplace: {
    enabled: false,
    method: 'random',
    prefix: '$_',
  },
  obfuscation: {
    enabled: false,
    method: 'cdata',
    keywords: [],
    unicodeRatio: 0.5,
    htmlRatio: 0.3,
  },
  normalTemplate: {
    enabled: false,
    template: '',
  },
})
const generatingWebshell = ref(false)
const templateOptions = ref([])
const templateLoading = ref(false)
const normalTemplateOptions = ref([])
const normalTemplateLoading = ref(false)

const obfuscationMethodOptions = [
  { label: '无', value: 'none' },
  { label: 'CDATA 拆分', value: 'cdata' },
  { label: 'Unicode 编码', value: 'unicode' },
  { label: 'HTML 实体编码', value: 'html' },
  { label: 'HTML + Unicode 组合', value: 'html_unicode' },
  { label: 'CDATA + Unicode 组合', value: 'cdata_unicode' },
  { label: 'CDATA + HTML 组合', value: 'cdata_html' },
]

const keywordSuggestions = [
  'request',
  'session',
  'getParameter',
  'getAttribute',
  'setAttribute',
  'getMethod',
  'ClassLoader',
  'defineClass',
  'Base64',
  'payload',
]

const isPhpType = computed(() => generateForm.value.webshellType === 'php')
const isJspxType = computed(() => generateForm.value.webshellType === 'jspx')
const isJspType = computed(() => generateForm.value.webshellType === 'jsp')
const isCsharpType = computed(() => generateForm.value.webshellType === 'csharp')
const needsUnicodeRatio = computed(() => {
  if (!generateForm.value.obfuscation.enabled) return false
  if (!isJspxType.value && !isJspType.value) return false
  const method = generateForm.value.obfuscation.method
  return ['unicode', 'html_unicode', 'cdata_unicode'].includes(method)
})

const needsHtmlRatio = computed(() => {
  if (!generateForm.value.obfuscation.enabled) return false
  if (!isJspxType.value) return false
  const method = generateForm.value.obfuscation.method
  return ['html', 'html_unicode', 'cdata_html'].includes(method)
})

const fetchTemplateOptions = async (type) => {
  if (!type) return
  templateLoading.value = true
  try {
    const response = await api.coreManagement.getWebshellTemplates({ type })
    if (response.data.status === 'success') {
      const templates = response.data.data.templates || []
      templateOptions.value = templates
      if (!templates.length) {
        generateForm.value.templateName = ''
      } else if (!templates.includes(generateForm.value.templateName)) {
        generateForm.value.templateName = templates[0]
      }
    } else {
      templateOptions.value = []
      generateForm.value.templateName = ''
      ElMessage.error(response.data.message || '获取模板文件失败')
    }
  } catch (error) {
    templateOptions.value = []
    generateForm.value.templateName = ''
    console.error('获取模板文件失败:', error)
    ElMessage.error('获取模板文件失败: ' + (error.response?.data?.message || error.message))
  } finally {
    templateLoading.value = false
  }
}

const fetchNormalTemplateOptions = async (type) => {
  if (!type) return
  // normal_template 目前后端只支持这些类型
  if (!['php', 'jsp', 'jspx', 'asp'].includes(type)) {
    normalTemplateOptions.value = []
    generateForm.value.normalTemplate.enabled = false
    generateForm.value.normalTemplate.template = ''
    return
  }
  normalTemplateLoading.value = true
  try {
    const response = await api.coreManagement.getNormalTemplates({ type })
    if (response.data.status === 'success') {
      const templates = response.data.data.templates || []
      normalTemplateOptions.value = templates
      if (!templates.length) {
        generateForm.value.normalTemplate.enabled = false
        generateForm.value.normalTemplate.template = ''
      } else if (
        generateForm.value.normalTemplate.enabled &&
        !templates.includes(generateForm.value.normalTemplate.template)
      ) {
        generateForm.value.normalTemplate.template = templates[0]
      }
    } else {
      normalTemplateOptions.value = []
      generateForm.value.normalTemplate.enabled = false
      generateForm.value.normalTemplate.template = ''
      ElMessage.error(response.data.message || '获取模拟模板失败')
    }
  } catch (error) {
    normalTemplateOptions.value = []
    generateForm.value.normalTemplate.enabled = false
    generateForm.value.normalTemplate.template = ''
    console.error('获取模拟模板失败:', error)
    ElMessage.error('获取模拟模板失败: ' + (error.response?.data?.message || error.message))
  } finally {
    normalTemplateLoading.value = false
  }
}

watch(
  () => generateForm.value.webshellType,
  (type) => {
    if (!props.visible) return
    generateForm.value.templateName = ''
    templateOptions.value = []
    normalTemplateOptions.value = []
    generateForm.value.normalTemplate.enabled = false
    generateForm.value.normalTemplate.template = ''
    generateForm.value.className = ''
    // CookieName 默认值（仍要求非空）
    if (type === 'php') {
      if (!generateForm.value.cookieName) generateForm.value.cookieName = 'PHPSESSID'
    } else {
      if (!generateForm.value.cookieName) generateForm.value.cookieName = 'JSESSIONID'
    }
    fetchTemplateOptions(type)
    fetchNormalTemplateOptions(type)
    // 重置混淆：默认关闭
    generateForm.value.obfuscation.enabled = false
    generateForm.value.obfuscation.keywords = []
    generateForm.value.obfuscation.unicodeRatio = 0.5
    generateForm.value.obfuscation.htmlRatio = 0.3
    generateForm.value.obfuscation.method = 'none'
  },
)

watch(
  () => generateForm.value.obfuscation.enabled,
  (enabled) => {
    if (!enabled) {
      generateForm.value.obfuscation.method = 'none'
      return
    }
    // 启用时给一个合理默认
    if (isJspType.value) {
      generateForm.value.obfuscation.method = 'unicode'
    } else if (isJspxType.value) {
      generateForm.value.obfuscation.method =
        generateForm.value.obfuscation.method === 'none'
          ? 'cdata'
          : generateForm.value.obfuscation.method
      if (generateForm.value.obfuscation.method === 'none')
        generateForm.value.obfuscation.method = 'cdata'
    }
  },
)

// 初始化/重置表单
const handleOpen = () => {
  // 重置表单
  generateForm.value = {
    paramName: '',
    webshellType: 'jsp',
    templateName: '',
    cookieName: '',
    className: '',
    identifierReplace: {
      enabled: false,
      method: 'random',
      prefix: '$_',
    },
    obfuscation: {
      enabled: false,
      method: 'cdata',
      keywords: [],
      unicodeRatio: 0.5,
      htmlRatio: 0.3,
    },
    normalTemplate: {
      enabled: false,
      template: '',
    },
  }
  templateOptions.value = []
  normalTemplateOptions.value = []
  fetchTemplateOptions(generateForm.value.webshellType)
  fetchNormalTemplateOptions(generateForm.value.webshellType)
}

// 处理生成webshell
const handleGenerateWebshell = async () => {
  // 表单验证
  if (!generateForm.value.paramName) {
    ElMessage.warning('请输入参数名')
    return
  }
  if (!generateForm.value.webshellType) {
    ElMessage.warning('请选择Webshell类型')
    return
  }
  if (!generateForm.value.templateName) {
    ElMessage.warning('请选择模板文件')
    return
  }

  const cookieName = (generateForm.value.cookieName || '').trim()
  if (!cookieName) {
    ElMessage.warning('请输入 CookieName')
    return
  }

  if (isCsharpType.value) {
    const className = (generateForm.value.className || '').trim()
    if (!className) {
      ElMessage.warning('请输入类名')
      return
    }
  }

  const requestPayload = {
    param_name: generateForm.value.paramName,
    webshell_type: generateForm.value.webshellType,
    template_name: generateForm.value.templateName,
  }

  if (generateForm.value.identifierReplace?.enabled) {
    if (!generateForm.value.identifierReplace?.method) {
      ElMessage.warning('请选择标识符替换模式')
      return
    }
    const prefix = generateForm.value.identifierReplace?.prefix?.trim()
    if (!prefix) {
      ElMessage.warning('请输入标识符前缀')
      return
    }
    requestPayload.identifier_replace_method = generateForm.value.identifierReplace.method
    requestPayload.identifier_replace_prefix = prefix
  }

  requestPayload.cookie_name = cookieName
  requestPayload.normal_template = 'none'

  if (isCsharpType.value) {
    requestPayload.class_name = (generateForm.value.className || '').trim()
  }

  if (generateForm.value.webshellType === 'jspx') {
    const method = generateForm.value.obfuscation.method
    const keywords = (generateForm.value.obfuscation.keywords || [])
      .map((item) => (typeof item === 'string' ? item.trim() : item))
      .filter((item) => item && item.length > 0)
    if (generateForm.value.obfuscation.enabled && keywords.length === 0) {
      ElMessage.warning('请至少添加一个需要混淆的关键字')
      return
    }

    const unicodeRatio = Number(generateForm.value.obfuscation.unicodeRatio || 0)
    const htmlRatio = Number(generateForm.value.obfuscation.htmlRatio || 0)

    if (['unicode', 'html_unicode', 'cdata_unicode'].includes(method)) {
      if (Number.isNaN(unicodeRatio) || unicodeRatio < 0.1 || unicodeRatio > 1) {
        ElMessage.warning('Unicode比率需要在 0.1 - 1.0 之间')
        return
      }
    }
    if (['html', 'html_unicode', 'cdata_html'].includes(method)) {
      if (Number.isNaN(htmlRatio) || htmlRatio < 0.1 || htmlRatio > 1) {
        ElMessage.warning('HTML比率需要在 0.1 - 1.0 之间')
        return
      }
    }

    if (generateForm.value.obfuscation.enabled) {
      Object.assign(requestPayload, {
        obfuscation_method: method,
        keywords,
        unicode_ratio: unicodeRatio,
        html_ratio: htmlRatio,
      })
    } else {
      requestPayload.obfuscation_method = 'none'
    }
  } else if (generateForm.value.webshellType === 'jsp') {
    const method = generateForm.value.obfuscation.method
    if (generateForm.value.obfuscation.enabled) {
      const keywords = (generateForm.value.obfuscation.keywords || [])
        .map((item) => (typeof item === 'string' ? item.trim() : item))
        .filter((item) => item && item.length > 0)
      if (keywords.length === 0) {
        ElMessage.warning('请至少添加一个需要混淆的关键字')
        return
      }

      const unicodeRatio = Number(generateForm.value.obfuscation.unicodeRatio || 0)
      if (Number.isNaN(unicodeRatio) || unicodeRatio < 0.1 || unicodeRatio > 1) {
        ElMessage.warning('Unicode比率需要在 0.1 - 1.0 之间')
        return
      }

      Object.assign(requestPayload, {
        obfuscation_method: method,
        keywords,
        unicode_ratio: unicodeRatio,
      })
    } else {
      requestPayload.obfuscation_method = 'none'
    }
  } else if (generateForm.value.webshellType === 'php') {
    if (generateForm.value.normalTemplate.enabled) {
      if (!generateForm.value.normalTemplate.template) {
        ElMessage.warning('请选择模拟正常业务模板')
        return
      }
      requestPayload.normal_template = generateForm.value.normalTemplate.template
    }
  }

  generatingWebshell.value = true

  try {
    // 调用后端API生成webshell
    const response = await api.coreManagement.generateWebshell(requestPayload)

    if (response.data.status === 'success') {
      const webshellContent = response.data.data

      // 根据类型确定文件名和MIME类型
      const fileExtension =
        generateForm.value.webshellType === 'php'
          ? 'php'
          : generateForm.value.webshellType === 'jsp'
            ? 'jsp'
            : generateForm.value.webshellType === 'jspx'
              ? 'jspx'
              : generateForm.value.webshellType === 'asp'
                ? 'asp'
                : 'aspx'
      const fileName = `shell.${fileExtension}`

      // 创建Blob对象
      const blob = new Blob([webshellContent], { type: 'text/plain;charset=utf-8' })

      // 创建下载链接
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = fileName

      // 触发下载
      document.body.appendChild(link)
      link.click()

      // 清理
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      ElMessage.success('Webshell生成成功，已开始下载')
      closeDialog()
    } else {
      ElMessage.error(response.data.message || 'Webshell生成失败')
    }
  } catch (error) {
    console.error('生成webshell失败:', error)
    ElMessage.error('生成webshell失败: ' + (error.response?.data?.message || error.message))
  } finally {
    generatingWebshell.value = false
  }
}
</script>

<style scoped>
.generate-webshell-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.generate-form {
  padding: 20px 30px 10px;
}

.form-section {
  margin-bottom: 24px;
}

.form-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-left: 10px;
  border-left: 3px solid #409eff;
  display: flex;
  align-items: center;
  gap: 6px;
}

.title-icon {
  font-size: 14px;
  color: #909399;
  cursor: help;
}

.identifier-wrap {
  display: flex;
  gap: 10px;
  width: 100%;
}

.identifier-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.toggle-text {
  font-size: 13px;
  color: #606266;
}

.obfuscation-panel {
  margin-top: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background-color: #fafafa;
  overflow: hidden;
}

.panel-header {
  padding: 10px 15px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.panel-body {
  padding: 15px 15px 0;
}

.slider-wrap {
  padding-right: 15px;
  padding-left: 5px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 4px;
}

.tip-icon {
  font-size: 13px;
  color: #409eff;
}

.normal-template-control {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.normal-template-select {
  flex: 1;
  width: 100%;
  min-width: 280px;
}

.dialog-footer {
  padding: 15px 20px 20px;
  text-align: right;
  background-color: #fff;
  border-top: 1px solid #f0f2f5;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  max-height: 500px;
  opacity: 1;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
  margin-top: 0;
}

/* Custom Input Styles */
:deep(.el-input-group__prepend) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 500;
}

:deep(.el-select .el-input__wrapper),
:deep(.el-input .el-input__wrapper) {
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

:deep(.el-select .el-input__wrapper:hover),
:deep(.el-input .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

:deep(.el-select .el-input.is-focus .el-input__wrapper),
:deep(.el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px #409eff inset !important;
}
</style>
