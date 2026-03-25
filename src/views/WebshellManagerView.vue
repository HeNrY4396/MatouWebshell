<template>
  <div class="webshellmanager-container">
    <div class="header">
      <div class="header-content">
        <h2>MatouWebshell</h2>
        <el-button
          type="primary"
          size="large"
          @click="handleOpenGlobalConfig"
          class="config-button"
        >
          <el-icon><Setting /></el-icon>
          全局配置
        </el-button>
      </div>
    </div>

    <!-- webshell列表组件 -->
    <WebshellList
      ref="webshellListRef"
      @openWebshell="handleOpenWebshell"
      @openGenerateDialog="handleOpenGenerateDialog"
    />

    <!-- JSP Webshell详情对话框 -->
    <el-dialog
      v-model="jspWebshellDetailVisible"
      :title="`JSP Webshell详情 - ${currentWebshell?.url || ''}`"
      width="80%"
      top="5vh"
      :close-on-click-modal="false"
      class="webshell-detail-dialog"
      @close="handleDetailDialogClose"
    >
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="目标系统信息" name="systemInfo">
          <WebshellSystemInfo :system-info="systemInfo" />
        </el-tab-pane>

        <el-tab-pane label="命令执行" name="commandExec">
          <WebshellTerminal
            :current-webshell="currentWebshell"
            :system-info="systemInfo"
            :visible="activeTab === 'commandExec'"
            @directory-changed="handleDirectoryChanged"
          />
        </el-tab-pane>

        <el-tab-pane label="文件管理" name="fileManager">
          <WebshellFileManager
            ref="fileManagerRef"
            :current-webshell="currentWebshell"
            :system-info="systemInfo"
            :current-directory="currentDirectory"
            :visible="activeTab === 'fileManager'"
            @directory-changed="handleDirectoryChanged"
          />
        </el-tab-pane>

        <el-tab-pane label="内存马管理" name="memoryShell">
          <WebshellMemoryShell
            :current-webshell="currentWebshell"
            :system-info="systemInfo"
            :visible="activeTab === 'memoryShell'"
          />
        </el-tab-pane>

        <el-tab-pane label="内网穿透" name="natTraversal">
          <WebshellNatTraversal
            :current-webshell="currentWebshell"
            :visible="activeTab === 'natTraversal'"
          />
        </el-tab-pane>

        <el-tab-pane label="数据库管理" name="databaseManager">
          <WebshellDatabaseManager
            :current-webshell="currentWebshell"
            :visible="activeTab === 'databaseManager'"
          />
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- PHP Webshell详情对话框 -->
    <el-dialog
      v-model="phpWebshellDetailVisible"
      :title="`PHP Webshell详情 - ${currentWebshell?.url || ''}`"
      width="80%"
      top="5vh"
      :close-on-click-modal="false"
      class="webshell-detail-dialog"
      @close="handleDetailDialogClose"
    >
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="目标系统信息" name="systemInfo">
          <WebshellSystemInfo :system-info="systemInfo" />
        </el-tab-pane>

        <el-tab-pane label="命令执行" name="commandExec">
          <WebshellTerminal
            :current-webshell="currentWebshell"
            :system-info="systemInfo"
            :visible="activeTab === 'commandExec'"
            @directory-changed="handleDirectoryChanged"
          />
        </el-tab-pane>

        <el-tab-pane label="文件管理" name="fileManager">
          <WebshellFileManager
            ref="fileManagerRef"
            :current-webshell="currentWebshell"
            :system-info="systemInfo"
            :current-directory="currentDirectory"
            :visible="activeTab === 'fileManager'"
            @directory-changed="handleDirectoryChanged"
          />
        </el-tab-pane>

        <el-tab-pane label="数据库管理" name="databaseManager">
          <WebshellDatabaseManager
            :current-webshell="currentWebshell"
            :visible="activeTab === 'databaseManager'"
          />
        </el-tab-pane>

        <el-tab-pane label="内网穿透" name="natTraversal">
          <WebshellNatTraversal
            :current-webshell="currentWebshell"
            :visible="activeTab === 'natTraversal'"
          />
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- CSharp Webshell详情对话框 -->
    <el-dialog
      v-model="csharpWebshellDetailVisible"
      :title="`CSharp Webshell详情 - ${currentWebshell?.url || ''}`"
      width="80%"
      top="5vh"
      :close-on-click-modal="false"
      class="webshell-detail-dialog"
      @close="handleDetailDialogClose"
    >
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="目标系统信息" name="systemInfo">
          <WebshellSystemInfo :system-info="systemInfo" />
        </el-tab-pane>

        <el-tab-pane label="命令执行" name="commandExec">
          <WebshellTerminal
            :current-webshell="currentWebshell"
            :system-info="systemInfo"
            :visible="activeTab === 'commandExec'"
            @directory-changed="handleDirectoryChanged"
          />
        </el-tab-pane>

        <el-tab-pane label="文件管理" name="fileManager">
          <WebshellFileManager
            ref="fileManagerRef"
            :current-webshell="currentWebshell"
            :system-info="systemInfo"
            :current-directory="currentDirectory"
            :visible="activeTab === 'fileManager'"
            @directory-changed="handleDirectoryChanged"
          />
        </el-tab-pane>

        <el-tab-pane label="数据库管理" name="databaseManager">
          <WebshellDatabaseManager
            :current-webshell="currentWebshell"
            :visible="activeTab === 'databaseManager'"
          />
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- ASP Webshell详情对话框 -->
    <el-dialog
      v-model="aspWebshellDetailVisible"
      :title="`ASP Webshell详情 - ${currentWebshell?.url || ''}`"
      width="80%"
      top="5vh"
      :close-on-click-modal="false"
      class="webshell-detail-dialog"
      @close="handleDetailDialogClose"
    >
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="目标系统信息" name="systemInfo">
          <WebshellSystemInfo :system-info="systemInfo" />
        </el-tab-pane>

        <el-tab-pane label="命令执行" name="commandExec">
          <WebshellTerminal
            :current-webshell="currentWebshell"
            :system-info="systemInfo"
            :visible="activeTab === 'commandExec'"
            @directory-changed="handleDirectoryChanged"
          />
        </el-tab-pane>

        <el-tab-pane label="文件管理" name="fileManager">
          <WebshellFileManager
            ref="fileManagerRef"
            :current-webshell="currentWebshell"
            :system-info="systemInfo"
            :current-directory="currentDirectory"
            :visible="activeTab === 'fileManager'"
            @directory-changed="handleDirectoryChanged"
          />
        </el-tab-pane>

        <el-tab-pane label="数据库管理" name="databaseManager">
          <WebshellDatabaseManager
            :current-webshell="currentWebshell"
            :visible="activeTab === 'databaseManager'"
          />
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- 全局配置对话框 -->
    <el-dialog
      v-model="globalConfigVisible"
      title="Webshell Manager 全局配置"
      width="90%"
      top="5vh"
      :close-on-click-modal="false"
      class="global-config-dialog"
      @close="handleGlobalConfigClose"
    >
      <WebshellConfig ref="configRef" />
    </el-dialog>

    <!-- 生成Webshell对话框 -->
    <WebshellGenerator v-model:visible="generateWebshellVisible" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Setting } from '@element-plus/icons-vue'
import WebshellList from '@/components/WebshellManagement/WebshellList.vue'
import WebshellSystemInfo from '@/components/WebshellManagement/WebshellSystemInfo.vue'
import WebshellTerminal from '@/components/WebshellManagement/WebshellTerminal.vue'
import WebshellFileManager from '@/components/WebshellManagement/WebshellFileManager.vue'
import WebshellMemoryShell from '@/components/WebshellManagement/WebshellMemoryShell.vue'
import WebshellNatTraversal from '@/components/WebshellManagement/WebshellNatTraversal.vue'
import WebshellDatabaseManager from '@/components/WebshellManagement/WebshellDatabaseManager.vue'
import WebshellConfig from '@/components/WebshellManagement/WebshellConfig.vue'
import WebshellGenerator from '@/components/WebshellManagement/WebshellGenerator.vue'

// 组件引用
const webshellListRef = ref(null)
const fileManagerRef = ref(null)
const configRef = ref(null)

// 对话框状态
const jspWebshellDetailVisible = ref(false)
const phpWebshellDetailVisible = ref(false)
const csharpWebshellDetailVisible = ref(false)
const aspWebshellDetailVisible = ref(false)
const globalConfigVisible = ref(false)
const generateWebshellVisible = ref(false)
const activeTab = ref('systemInfo')

// 监听对话框状态变化
watch(jspWebshellDetailVisible, (newVal, oldVal) => {
  console.log('webshellDetailVisible 状态变化:', { 旧值: oldVal, 新值: newVal })
  if (newVal) {
    console.log('对话框应该打开了')
  }
})

// webshell相关数据
const currentWebshell = ref(null)
const systemInfo = ref(null)
const currentDirectory = ref('')

// 处理打开webshell事件
const handleOpenWebshell = ({ webshell, systemInfo: sysInfo }) => {
  console.log('handleOpenWebshell 被调用了！')
  console.log('接收到的参数:', { webshell, systemInfo: sysInfo })

  currentWebshell.value = webshell
  systemInfo.value = sysInfo
  activeTab.value = 'systemInfo'

  // 根据 webshell 类型打开对应的详情对话框
  const webshellType = webshell.webshellType?.toLowerCase() || 'jsp'
  console.log('Webshell类型:', webshellType)

  if (webshellType === 'php') {
    phpWebshellDetailVisible.value = true
    console.log('打开PHP详情对话框')
  } else if (webshellType === 'csharp') {
    csharpWebshellDetailVisible.value = true
    console.log('打开CSharp详情对话框')
  } else if (webshellType === 'asp') {
    aspWebshellDetailVisible.value = true
    console.log('打开ASP详情对话框')
  } else if (webshellType === 'jsp' || webshellType === 'java') {
    jspWebshellDetailVisible.value = true
    console.log('打开JSP详情对话框')
  } else {
    // 默认打开 JSP 详情对话框
    jspWebshellDetailVisible.value = true
    console.log('使用默认JSP详情对话框，webshell类型:', webshellType)
  }

  console.log(
    '对话框状态 - JSP:',
    jspWebshellDetailVisible.value,
    'PHP:',
    phpWebshellDetailVisible.value,
    'CSharp:',
    csharpWebshellDetailVisible.value,
    'ASP:',
    aspWebshellDetailVisible.value,
  )

  // 初始化当前目录
  if (sysInfo && sysInfo.CurrentDir) {
    currentDirectory.value = sysInfo.CurrentDir.replace(/\\/g, '/')
  }
}

// 处理打开全局配置事件
const handleOpenGlobalConfig = () => {
  globalConfigVisible.value = true
}

// 处理全局配置对话框关闭
const handleGlobalConfigClose = () => {
  // 可以在这里处理配置保存确认等逻辑
}

// 处理打开生成webshell对话框
const handleOpenGenerateDialog = () => {
  generateWebshellVisible.value = true
}

// 处理目录变化事件
const handleDirectoryChanged = (newDirectory) => {
  currentDirectory.value = newDirectory
}

// 处理详情对话框关闭
const handleDetailDialogClose = () => {
  // 重置状态
  currentWebshell.value = null
  systemInfo.value = null
  currentDirectory.value = ''
  activeTab.value = 'systemInfo'

  // 确保两个对话框都关闭
  jspWebshellDetailVisible.value = false
  phpWebshellDetailVisible.value = false
  csharpWebshellDetailVisible.value = false
  aspWebshellDetailVisible.value = false
}
</script>

<style scoped>
.webshellmanager-container {
  padding: 20px;
}

.header {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}

.header-content h2 {
  margin: 0;
  color: #303133;
  font-size: 28px;
  font-weight: 600;
}

.config-button {
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
  transition: all 0.3s ease;
}

.config-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

.config-button .el-icon {
  margin-right: 8px;
  font-size: 18px;
}

.webshell-detail-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.global-config-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.global-config-dialog :deep(.el-dialog__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 8px 8px 0 0;
}

.global-config-dialog :deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
}

.tab-content {
  padding: 20px;
}

.tab-content h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #333;
}

.tab-content p {
  margin-bottom: 10px;
  line-height: 1.6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }

  .header-content h2 {
    font-size: 24px;
    margin-bottom: 15px;
  }

  .config-button {
    width: 100%;
    justify-content: center;
  }

  .global-config-dialog {
    width: 95% !important;
    margin: 0 auto;
  }
}
</style>
