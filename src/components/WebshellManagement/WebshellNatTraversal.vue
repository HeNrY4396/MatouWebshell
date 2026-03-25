<template>
  <div class="nat-traversal-container">
    <!-- 端口映射区域 -->
    <el-card class="module-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="module-title">📡 端口映射</span>
          <div class="status-indicator">
            <el-tag :type="portMappingStatus.isActive ? 'success' : 'info'" size="small">
              {{ portMappingStatus.isActive ? '运行中' : '未启动' }}
            </el-tag>
          </div>
        </div>
      </template>

      <div class="module-content">
        <el-form
          :model="portMappingForm"
          :rules="portMappingRules"
          ref="portMappingFormRef"
          label-width="100px"
          size="default"
        >
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="本地端口" prop="localPort">
                <el-input-number
                  v-model="portMappingForm.localPort"
                  :min="1024"
                  :max="65535"
                  placeholder="本地监听端口"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="目标IP" prop="targetIp">
                <el-input v-model="portMappingForm.targetIp" placeholder="内网目标IP" clearable />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="目标端口" prop="targetPort">
                <el-input-number
                  v-model="portMappingForm.targetPort"
                  :min="1"
                  :max="65535"
                  placeholder="目标端口"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <div class="button-group">
          <el-button
            type="primary"
            icon="Play"
            @click="startPortMapping"
            :loading="portMappingStatus.starting"
          >
            启动映射
          </el-button>
          <el-button
            type="danger"
            icon="VideoStop"
            @click="stopAllPortMappings"
            :loading="portMappingStatus.stopping"
            :disabled="portMappingStatus.mappings.length === 0"
          >
            停止所有映射
          </el-button>
          <el-button
            type="warning"
            icon="Refresh"
            @click="getPortMappingStatus"
            :loading="portMappingStatus.refreshing"
          >
            刷新状态
          </el-button>
        </div>

        <!-- 端口映射状态显示 -->
        <div
          v-if="portMappingStatus.mappings && portMappingStatus.mappings.length > 0"
          class="status-display"
        >
          <el-divider content-position="left">当前映射</el-divider>
          <div class="mapping-list">
            <div
              v-for="mapping in portMappingStatus.mappings"
              :key="mapping.mapping_id"
              class="mapping-item"
            >
              <span class="mapping-info">{{ mapping.local_port }} → {{ mapping.target }}</span>
              <div class="mapping-actions">
                <el-tag type="success" size="small">已连接</el-tag>
                <el-button
                  type="danger"
                  link
                  icon="Close"
                  size="small"
                  @click="stopSpecificMapping(mapping.local_port)"
                >
                  停止
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- Socks隧道区域 -->
    <el-card class="module-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="module-title">🌐 Socks隧道</span>
          <div class="status-indicator">
            <el-tag :type="socksTunnelStatus.isActive ? 'success' : 'info'" size="small">
              {{ socksTunnelStatus.isActive ? '运行中' : '未启动' }}
            </el-tag>
          </div>
        </div>
      </template>

      <div class="module-content">
        <el-form
          :model="socksTunnelForm"
          :rules="socksTunnelRules"
          ref="socksTunnelFormRef"
          label-width="100px"
          size="default"
        >
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="本地端口" prop="localPort">
                <el-input-number
                  v-model="socksTunnelForm.localPort"
                  :min="1024"
                  :max="65535"
                  placeholder="SOCKS代理监听端口"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="SOCKS版本" prop="socksVersion">
                <el-select
                  v-model="socksTunnelForm.socksVersion"
                  placeholder="选择SOCKS版本"
                  style="width: 100%"
                >
                  <el-option label="SOCKS5" value="5" />
                  <el-option label="SOCKS4" value="4" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="24">
              <el-form-item label="IP白名单">
                <div class="whitelist-control">
                  <el-switch
                    v-model="socksTunnelForm.enableWhitelist"
                    active-text="启用IP白名单"
                    inactive-text="允许所有IP"
                    style="margin-right: 16px"
                  />
                  <span class="whitelist-help-text">启用后仅允许白名单内的IP地址访问</span>
                </div>

                <el-input
                  v-if="socksTunnelForm.enableWhitelist"
                  v-model="socksTunnelForm.ipWhitelist"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入允许访问的IP地址或网段，每行一个&#10;支持格式：&#10;192.168.1.100 (单个IP)&#10;192.168.1.0/24 (C类网段)&#10;172.16.0.0/16 (B类网段)&#10;10.0.0.0/8 (A类网段)"
                  style="margin-top: 8px"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <div class="button-group">
          <el-button
            type="primary"
            icon="Play"
            @click="startSocksTunnel"
            :loading="socksTunnelStatus.starting"
            :disabled="socksTunnelStatus.isActive"
          >
            启动隧道
          </el-button>
          <el-button
            type="danger"
            icon="VideoStop"
            @click="stopSocksTunnel"
            :loading="socksTunnelStatus.stopping"
            :disabled="!socksTunnelStatus.isActive"
          >
            停止隧道
          </el-button>
          <el-button
            type="info"
            icon="Setting"
            @click="updateWhitelist"
            :loading="socksTunnelStatus.updatingWhitelist"
            :disabled="!socksTunnelStatus.isActive"
          >
            更新白名单
          </el-button>
          <el-button
            type="warning"
            icon="Refresh"
            @click="getSocksTunnelStatus"
            :loading="socksTunnelStatus.refreshing"
          >
            刷新状态
          </el-button>
        </div>

        <!-- Socks隧道状态显示 -->
        <div v-if="socksTunnelStatus.isActive" class="status-display">
          <el-divider content-position="left">代理配置</el-divider>
          <div class="proxy-config">
            <p><strong>代理地址:</strong> 0.0.0.0:{{ socksTunnelForm.localPort }}</p>
            <p><strong>协议类型:</strong> SOCKS{{ socksTunnelForm.socksVersion }}</p>
            <p><strong>活跃连接:</strong> {{ socksTunnelStatus.activeConnections || 0 }}</p>
            <p>
              <strong>IP白名单:</strong>
              <el-tag v-if="!socksTunnelForm.enableWhitelist" type="warning" size="small">
                未启用（允许所有IP）
              </el-tag>
              <span v-else-if="socksTunnelForm.ipWhitelist">
                <el-tag
                  v-for="ip in parseWhitelist(socksTunnelForm.ipWhitelist)"
                  :key="ip"
                  type="success"
                  size="small"
                  style="margin-right: 4px; margin-bottom: 4px"
                >
                  {{ ip }}
                </el-tag>
              </span>
              <el-tag v-else type="info" size="small">已启用但未配置</el-tag>
            </p>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 反连端口区域 (仅 JSP/Java 支持) -->
    <el-card v-if="!isPhpWebshell" class="module-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="module-title">🔄 反连端口桥接</span>
          <div class="status-indicator">
            <el-tag :type="reverseConnectStatus.isActive ? 'success' : 'info'" size="small">
              {{ reverseConnectStatus.isActive ? '监听中' : '未启动' }}
            </el-tag>
          </div>
        </div>
      </template>

      <div class="module-content">
        <el-form
          :model="reverseConnectForm"
          :rules="reverseConnectRules"
          ref="reverseConnectFormRef"
          label-width="100px"
          size="default"
        >
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="监听端口" prop="listenPort">
                <el-input-number
                  v-model="reverseConnectForm.listenPort"
                  :min="1024"
                  :max="65535"
                  placeholder="反连监听端口"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="转发IP" prop="localIp">
                <el-input
                  v-model="reverseConnectForm.localIp"
                  placeholder="本地转发IP"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="转发端口" prop="localPort">
                <el-input-number
                  v-model="reverseConnectForm.localPort"
                  :min="1024"
                  :max="65535"
                  placeholder="本地转发端口"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <div class="button-group">
          <el-button
            type="primary"
            icon="Play"
            @click="startReverseConnect"
            :loading="reverseConnectStatus.starting"
          >
            启动监听
          </el-button>
          <el-button
            type="danger"
            icon="VideoStop"
            @click="stopAllReverseConnects"
            :loading="reverseConnectStatus.stopping"
          >
            停止所有监听
          </el-button>
          <el-button
            type="warning"
            icon="Refresh"
            @click="getReverseConnectStatus"
            :loading="reverseConnectStatus.refreshing"
          >
            刷新状态
          </el-button>
        </div>

        <!-- 反连状态显示 -->
        <div
          v-if="reverseConnectStatus.listeners && reverseConnectStatus.listeners.length > 0"
          class="status-display"
        >
          <el-divider content-position="left">当前监听</el-divider>
          <div class="listener-list">
            <div
              v-for="listener in reverseConnectStatus.listeners"
              :key="listener.listen_id"
              class="listener-item"
            >
              <span class="listener-info">
                端口: {{ listener.webshell_port }} → {{ listener.local_ip || '127.0.0.1' }}:{{
                  listener.local_port
                }}
              </span>
              <div class="listener-actions">
                <el-tag type="success" size="small">监听中</el-tag>
                <el-tag type="info" size="small">等待: {{ listener.connection_count || 0 }}</el-tag>
                <el-button
                  type="danger"
                  link
                  icon="Close"
                  size="small"
                  @click="stopSpecificListener(listener.listen_id)"
                >
                  停止
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 运行日志区域 -->
    <el-card class="log-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="module-title">📋 运行日志</span>
          <div class="log-actions">
            <el-button type="primary" size="small" icon="Delete" @click="clearLogs">
              清空日志
            </el-button>
          </div>
        </div>
      </template>

      <el-collapse v-model="activeLogPanel">
        <el-collapse-item title="查看详细日志" name="logs">
          <div class="log-container">
            <div class="log-content" ref="logContentRef">
              <div v-for="(log, index) in logs" :key="index" class="log-entry" :class="log.type">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-type">[{{ log.type.toUpperCase() }}]</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
              <div v-if="logs.length === 0" class="no-logs">暂无日志记录</div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api/api.js'

export default {
  name: 'WebshellNatTraversal',
  props: {
    currentWebshell: {
      type: Object,
      required: true,
    },
    visible: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    // 判断 webshell 类型
    const isPhpWebshell = computed(() => {
      return props.currentWebshell?.webshellType?.toLowerCase() === 'php'
    })

    // 根据 webshell 类型选择对应的 API
    const shellApi = computed(() => {
      return isPhpWebshell.value ? api.phpShell : api.javaShell
    })
    // 日志相关
    const logs = ref([])
    const activeLogPanel = ref([])
    const logContentRef = ref(null)

    // 端口映射相关
    const portMappingForm = reactive({
      localPort: 8080,
      targetIp: '192.168.1.1',
      targetPort: 80,
    })

    const portMappingStatus = reactive({
      isActive: false,
      starting: false,
      stopping: false,
      refreshing: false,
      mappings: [],
    })

    const portMappingRules = {
      localPort: [
        { required: true, message: '请输入本地端口', trigger: 'blur' },
        { type: 'number', min: 1024, max: 65535, message: '端口范围：1024-65535', trigger: 'blur' },
      ],
      targetIp: [
        { required: true, message: '请输入目标IP地址', trigger: 'blur' },
        {
          pattern:
            /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
          message: 'IP地址格式不正确',
          trigger: 'blur',
        },
      ],
      targetPort: [
        { required: true, message: '请输入目标端口', trigger: 'blur' },
        { type: 'number', min: 1, max: 65535, message: '端口范围：1-65535', trigger: 'blur' },
      ],
    }

    // Socks隧道相关
    const socksTunnelForm = reactive({
      localPort: 1080,
      socksVersion: '5',
      enableWhitelist: false,
      ipWhitelist: '',
    })

    const socksTunnelStatus = reactive({
      isActive: false,
      starting: false,
      stopping: false,
      refreshing: false,
      updatingWhitelist: false,
      activeConnections: 0,
    })

    const socksTunnelRules = {
      localPort: [
        { required: true, message: '请输入本地端口', trigger: 'blur' },
        { type: 'number', min: 1024, max: 65535, message: '端口范围：1024-65535', trigger: 'blur' },
      ],
      socksVersion: [{ required: true, message: '请选择SOCKS版本', trigger: 'change' }],
    }

    // 反连端口相关
    const reverseConnectForm = reactive({
      listenPort: 4444,
      localIp: '127.0.0.1',
      localPort: 5555,
    })

    const reverseConnectStatus = reactive({
      starting: false,
      stopping: false,
      refreshing: false,
      listeners: [],
    })

    const reverseConnectRules = {
      listenPort: [
        { required: true, message: '请输入监听端口', trigger: 'blur' },
        { type: 'number', min: 1024, max: 65535, message: '端口范围：1024-65535', trigger: 'blur' },
      ],
      localIp: [
        { required: true, message: '请输入本地转发IP地址', trigger: 'blur' },
        {
          pattern:
            /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
          message: 'IP地址格式不正确',
          trigger: 'blur',
        },
      ],
      localPort: [
        { required: true, message: '请输入本地转发端口', trigger: 'blur' },
        { type: 'number', min: 1024, max: 65535, message: '端口范围：1024-65535', trigger: 'blur' },
      ],
    }

    // 引用
    const portMappingFormRef = ref(null)
    const socksTunnelFormRef = ref(null)
    const reverseConnectFormRef = ref(null)

    // 日志方法
    const addLog = (message, type = 'info') => {
      const now = new Date()
      const time = now.toLocaleTimeString()
      logs.value.push({
        time,
        type,
        message,
      })

      // 自动滚动到底部
      nextTick(() => {
        if (logContentRef.value) {
          logContentRef.value.scrollTop = logContentRef.value.scrollHeight
        }
      })
    }

    const clearLogs = () => {
      logs.value = []
      ElMessage.success('日志已清空')
    }

    // 端口映射计算属性（已移除，启动按钮现在始终可用）

    // 端口映射方法
    const startPortMapping = async () => {
      if (!portMappingFormRef.value) return

      const valid = await portMappingFormRef.value.validate().catch(() => false)
      if (!valid) return

      portMappingStatus.starting = true
      addLog(
        `正在启动端口映射: ${portMappingForm.localPort} -> ${portMappingForm.targetIp}:${portMappingForm.targetPort}`,
        'info',
      )

      try {
        const response = await shellApi.value.startPortMapping({
          webshell_id: props.currentWebshell.id,
          localPort: portMappingForm.localPort,
          targetIp: portMappingForm.targetIp,
          targetPort: portMappingForm.targetPort,
        })

        if (response.data.status === 'success') {
          addLog(`端口映射启动成功: ${response.data.data.mapping}`, 'success')
          ElMessage.success(response.data.message)
          await getPortMappingStatus()
        } else {
          addLog(`端口映射启动失败: ${response.data.message}`, 'error')
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        addLog(`端口映射启动异常: ${error.message}`, 'error')
        ElMessage.error('端口映射启动失败')
      } finally {
        portMappingStatus.starting = false
      }
    }

    const stopAllPortMappings = async () => {
      portMappingStatus.stopping = true
      addLog(`正在停止所有端口映射`, 'info')

      try {
        const response = await shellApi.value.stopAllPortMappings({
          webshell_id: props.currentWebshell.id,
        })

        if (response.data.status === 'success') {
          addLog(`所有端口映射已停止`, 'success')
          ElMessage.success(response.data.message)
          await getPortMappingStatus()
        } else {
          addLog(`停止所有端口映射失败: ${response.data.message}`, 'error')
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        addLog(`停止所有端口映射异常: ${error.message}`, 'error')
        ElMessage.error('停止所有端口映射失败')
      } finally {
        portMappingStatus.stopping = false
      }
    }

    const stopSpecificMapping = async (localPort) => {
      addLog(`正在停止端口映射: ${localPort}`, 'info')

      try {
        const response = await shellApi.value.stopPortMapping({
          webshell_id: props.currentWebshell.id,
          localPort: localPort,
        })

        if (response.data.status === 'success') {
          addLog(`端口映射停止成功: ${localPort}`, 'success')
          ElMessage.success(`端口 ${localPort} 映射已停止`)
          await getPortMappingStatus()
        } else {
          addLog(`端口映射停止失败: ${response.data.message}`, 'error')
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        addLog(`端口映射停止异常: ${error.message}`, 'error')
        ElMessage.error('端口映射停止失败')
      }
    }

    const getPortMappingStatus = async () => {
      portMappingStatus.refreshing = true

      try {
        const response = await shellApi.value.getPortMappingStatus({
          webshell_id: props.currentWebshell.id,
        })

        if (response.data.status === 'success') {
          const data = response.data.data
          portMappingStatus.mappings = data.mappings || []
          portMappingStatus.isActive = data.total_mappings > 0
          addLog(`端口映射状态已更新: ${data.total_mappings} 个映射`, 'info')
        }
      } catch (error) {
        addLog(`获取端口映射状态失败: ${error.message}`, 'error')
      } finally {
        portMappingStatus.refreshing = false
      }
    }

    // 解析白名单输入
    const parseWhitelist = (whitelistText) => {
      if (!whitelistText || !whitelistText.trim()) return []

      return whitelistText
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
    }

    // Socks隧道方法
    const startSocksTunnel = async () => {
      if (!socksTunnelFormRef.value) return

      const valid = await socksTunnelFormRef.value.validate().catch(() => false)
      if (!valid) return

      // 处理IP白名单
      let ipWhitelist = []
      if (socksTunnelForm.enableWhitelist) {
        ipWhitelist = parseWhitelist(socksTunnelForm.ipWhitelist)
        if (ipWhitelist.length === 0) {
          ElMessage.warning('启用白名单时必须至少添加一个IP地址')
          return
        }
        addLog(`IP白名单已启用: ${ipWhitelist.join(', ')}`, 'info')
      } else {
        addLog('IP白名单未启用，允许所有IP访问', 'info')
      }

      socksTunnelStatus.starting = true
      addLog(`正在启动SOCKS隧道: 0.0.0.0:${socksTunnelForm.localPort}`, 'info')

      try {
        const response = await shellApi.value.startSocksTunnel({
          webshell_id: props.currentWebshell.id,
          listenPort: socksTunnelForm.localPort,
          listenIp: '0.0.0.0',
          ipWhitelist: ipWhitelist,
        })

        if (response.data.status === 'success') {
          socksTunnelStatus.isActive = true
          addLog(`SOCKS隧道启动成功: ${response.data.data.proxy}`, 'success')
          if (ipWhitelist.length > 0) {
            addLog(`白名单规则已生效，共 ${ipWhitelist.length} 条`, 'info')
          }
          ElMessage.success(response.data.message)
          await getSocksTunnelStatus()
        } else {
          addLog(`SOCKS隧道启动失败: ${response.data.message}`, 'error')
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        addLog(`SOCKS隧道启动异常: ${error.message}`, 'error')
        ElMessage.error('SOCKS隧道启动失败')
      } finally {
        socksTunnelStatus.starting = false
      }
    }

    const stopSocksTunnel = async () => {
      socksTunnelStatus.stopping = true
      addLog(`正在停止SOCKS隧道: ${socksTunnelForm.localPort}`, 'info')

      try {
        const response = await shellApi.value.stopSocksTunnel({
          webshell_id: props.currentWebshell.id,
        })

        if (response.data.status === 'success') {
          socksTunnelStatus.isActive = false
          socksTunnelStatus.activeConnections = 0
          addLog(`SOCKS隧道停止成功: ${socksTunnelForm.localPort}`, 'success')
          ElMessage.success(response.data.message)
        } else {
          addLog(`SOCKS隧道停止失败: ${response.data.message}`, 'error')
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        addLog(`SOCKS隧道停止异常: ${error.message}`, 'error')
        ElMessage.error('SOCKS隧道停止失败')
      } finally {
        socksTunnelStatus.stopping = false
      }
    }

    const getSocksTunnelStatus = async () => {
      socksTunnelStatus.refreshing = true
      addLog('正在刷新SOCKS隧道状态...', 'info')

      try {
        const response = await shellApi.value.getSocksTunnelStatus({
          webshell_id: props.currentWebshell.id,
        })

        if (response.data.status === 'success') {
          const data = response.data.data
          socksTunnelStatus.isActive = data.isRunning
          socksTunnelStatus.activeConnections = data.activeConnections || 0

          if (data.isRunning) {
            addLog(`SOCKS隧道状态: 运行中 (${data.listenIp}:${data.listenPort})`, 'success')
          } else {
            addLog('SOCKS隧道状态: 未运行', 'info')
          }
        } else {
          addLog(`获取SOCKS隧道状态失败: ${response.data.message}`, 'error')
        }
      } catch (error) {
        addLog(`获取SOCKS隧道状态异常: ${error.message}`, 'error')
      } finally {
        socksTunnelStatus.refreshing = false
      }
    }

    const updateWhitelist = async () => {
      if (!socksTunnelStatus.isActive) {
        ElMessage.warning('请先启动SOCKS隧道')
        return
      }

      // 处理IP白名单
      let ipWhitelist = []
      if (socksTunnelForm.enableWhitelist) {
        ipWhitelist = parseWhitelist(socksTunnelForm.ipWhitelist)
        if (ipWhitelist.length === 0) {
          ElMessage.warning('启用白名单时必须至少添加一个IP地址')
          return
        }
      }

      socksTunnelStatus.updatingWhitelist = true
      addLog('正在更新SOCKS隧道IP白名单...', 'info')

      try {
        const response = await shellApi.value.updateSocksWhitelist({
          webshell_id: props.currentWebshell.id,
          ipWhitelist: ipWhitelist,
        })

        if (response.data.status === 'success') {
          if (ipWhitelist.length > 0) {
            addLog(`白名单更新成功: ${ipWhitelist.join(', ')}`, 'success')
          } else {
            addLog('白名单已清空，允许所有IP访问', 'success')
          }
          ElMessage.success('IP白名单更新成功')
        } else {
          addLog(`白名单更新失败: ${response.data.message}`, 'error')
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        addLog(`白名单更新异常: ${error.message}`, 'error')
        ElMessage.error('IP白名单更新失败')
      } finally {
        socksTunnelStatus.updatingWhitelist = false
      }
    }

    // 反连端口方法
    const startReverseConnect = async () => {
      if (!reverseConnectFormRef.value) return

      const valid = await reverseConnectFormRef.value.validate().catch(() => false)
      if (!valid) return

      reverseConnectStatus.starting = true
      addLog(
        `正在启动反连监听: ${reverseConnectForm.listenPort} → ${reverseConnectForm.localIp}:${reverseConnectForm.localPort}`,
        'info',
      )

      try {
        const listenId = `reverse_${Date.now()}`
        const response = await api.javaShell.startReverseConnect({
          webshell_id: props.currentWebshell.id,
          listenId: listenId,
          webshellPort: reverseConnectForm.listenPort,
          localIp: reverseConnectForm.localIp,
          localPort: reverseConnectForm.localPort,
        })

        if (response.data.status === 'success') {
          const instructions = response.data.data.instructions || []
          addLog(`反连监听启动成功`, 'success')
          instructions.forEach((instruction) => {
            addLog(instruction, 'info')
          })

          // 获取最新状态
          await getReverseConnectStatus()
          ElMessage.success(response.data.message)
        } else {
          addLog(`反连监听启动失败: ${response.data.message}`, 'error')
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        addLog(`反连监听启动异常: ${error.message}`, 'error')
        ElMessage.error('反连监听启动失败')
      } finally {
        reverseConnectStatus.starting = false
      }
    }

    const stopAllReverseConnects = async () => {
      reverseConnectStatus.stopping = true
      addLog(`正在停止所有反连监听...`, 'info')

      try {
        const response = await api.javaShell.stopAllReverseConnects({
          webshell_id: props.currentWebshell.id,
        })

        if (response.data.status === 'success') {
          reverseConnectStatus.listeners = []
          addLog(`所有反连监听已停止`, 'success')
          ElMessage.success(response.data.message)
        } else {
          addLog(`停止所有反连监听失败: ${response.data.message}`, 'error')
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        addLog(`停止所有反连监听异常: ${error.message}`, 'error')
        ElMessage.error('停止所有反连监听失败')
      } finally {
        reverseConnectStatus.stopping = false
      }
    }

    const stopSpecificListener = async (listenId) => {
      addLog(`正在停止反连监听: ${listenId}`, 'info')

      try {
        const response = await api.webshell.stopReverseConnect({
          webshell_id: props.currentWebshell.id,
          listenId: listenId,
        })

        if (response.data.status === 'success') {
          addLog(`反连监听停止成功: ${listenId}`, 'success')
          await getReverseConnectStatus() // 刷新状态
          ElMessage.success(response.data.message)
        } else {
          addLog(`停止反连监听失败: ${response.data.message}`, 'error')
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        addLog(`停止反连监听异常: ${error.message}`, 'error')
        ElMessage.error('停止反连监听失败')
      }
    }

    const getReverseConnectStatus = async () => {
      reverseConnectStatus.refreshing = true
      addLog('正在刷新反连端口状态...', 'info')

      try {
        const response = await api.javaShell.getReverseConnectStatus({
          webshell_id: props.currentWebshell.id,
        })

        if (response.data.status === 'success') {
          const data = response.data.data
          reverseConnectStatus.listeners = data.listeners || []

          if (reverseConnectStatus.listeners.length > 0) {
            addLog(`反连端口状态: ${reverseConnectStatus.listeners.length} 个监听器活跃`, 'success')
          } else {
            addLog('反连端口状态: 未运行', 'info')
          }
        } else {
          addLog(`获取反连端口状态失败: ${response.data.message}`, 'error')
        }
      } catch (error) {
        addLog(`获取反连端口状态异常: ${error.message}`, 'error')
      } finally {
        reverseConnectStatus.refreshing = false
      }
    }

    return {
      // webshell 类型判定
      isPhpWebshell,
      shellApi,

      // 日志相关
      logs,
      activeLogPanel,
      logContentRef,
      addLog,
      clearLogs,

      // 端口映射相关
      portMappingForm,
      portMappingStatus,
      portMappingRules,
      portMappingFormRef,
      startPortMapping,
      stopAllPortMappings,
      stopSpecificMapping,
      getPortMappingStatus,

      // Socks隧道相关
      socksTunnelForm,
      socksTunnelStatus,
      socksTunnelRules,
      socksTunnelFormRef,
      parseWhitelist,
      startSocksTunnel,
      stopSocksTunnel,
      getSocksTunnelStatus,
      updateWhitelist,

      // 反连端口相关
      reverseConnectForm,
      reverseConnectStatus,
      reverseConnectRules,
      reverseConnectFormRef,
      startReverseConnect,
      stopAllReverseConnects,
      stopSpecificListener,
      getReverseConnectStatus,
    }
  },
}
</script>

<style scoped>
.nat-traversal-container {
  padding: 20px;
  max-height: 70vh;
  overflow-y: auto;
}

.module-card {
  margin-bottom: 20px;
}

.log-card {
  margin-bottom: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.module-title {
  font-weight: bold;
  font-size: 16px;
  color: #303133;
}

.status-indicator {
  display: flex;
  align-items: center;
}

.module-content {
  padding: 10px 0;
}

.button-group {
  display: flex;
  gap: 10px;
  margin-top: 15px;
  flex-wrap: wrap;
}

.status-display {
  margin-top: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #409eff;
}

.mapping-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mapping-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: white;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
}

.mapping-info {
  font-family: 'Courier New', monospace;
  color: #606266;
}

.mapping-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.listener-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: white;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
}

.listener-info {
  font-family: 'Courier New', monospace;
  color: #606266;
}

.listener-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.whitelist-control {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.whitelist-help-text {
  color: #909399;
  font-size: 12px;
}

.proxy-config,
.reverse-status {
  color: #606266;
}

.proxy-config p,
.reverse-status p {
  margin: 8px 0;
}

.proxy-config .el-tag {
  margin-right: 4px;
  margin-bottom: 4px;
}

.log-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.log-container {
  max-height: 300px;
  overflow-y: auto;
  background-color: #1e1e1e;
  border-radius: 4px;
  padding: 10px;
}

.log-content {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-entry {
  display: flex;
  margin-bottom: 4px;
  word-wrap: break-word;
}

.log-entry.info {
  color: #909399;
}

.log-entry.success {
  color: #67c23a;
}

.log-entry.error {
  color: #f56c6c;
}

.log-entry.warning {
  color: #e6a23c;
}

.log-time {
  color: #909399;
  min-width: 90px;
  margin-right: 8px;
}

.log-type {
  min-width: 70px;
  margin-right: 8px;
  font-weight: bold;
}

.log-message {
  flex: 1;
  word-break: break-all;
}

.no-logs {
  color: #909399;
  text-align: center;
  padding: 20px;
  font-style: italic;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .button-group {
    flex-direction: column;
  }

  .mapping-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }
}
</style>
