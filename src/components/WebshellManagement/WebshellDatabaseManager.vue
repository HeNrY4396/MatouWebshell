<template>
  <div class="database-manager">
    <!-- 没有webshell连接时的提示 -->
    <div v-if="!currentWebshell" class="no-webshell">
      <el-empty description="请先选择一个webshell连接">
        <el-icon size="64" color="#409eff"><Files /></el-icon>
      </el-empty>
    </div>

    <!-- 有webshell连接时显示正常界面 -->
    <el-row v-else :gutter="20" style="height: 100%">
      <!-- 左侧数据库树 -->
      <el-col :span="8" class="left-panel">
        <el-card shadow="never" style="height: 100%">
          <template #header>
            <div class="card-header">
              <span>数据库结构</span>
              <el-button
                size="small"
                type="primary"
                :icon="Refresh"
                @click="refreshDatabases"
                :loading="loading"
                :disabled="!connected"
              >
                刷新
              </el-button>
            </div>
          </template>

          <div v-if="!connected" class="empty-state">
            <el-empty description="请先连接数据库">
              <el-icon size="64" color="#409eff"><Files /></el-icon>
            </el-empty>
          </div>

          <el-tree
            v-else
            ref="treeRef"
            :data="treeData"
            :props="treeProps"
            :load="loadTreeNode"
            lazy
            :expand-on-click-node="false"
            node-key="id"
            @node-click="handleTreeNodeClick"
          >
            <template #default="{ node, data }">
              <span class="tree-node">
                <el-icon v-if="data.type === 'database'"><Files /></el-icon>
                <el-icon v-else-if="data.type === 'table'"><Grid /></el-icon>
                <span class="node-label">{{ node.label }}</span>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- 右侧操作区域 -->
      <el-col :span="16" class="right-panel">
        <!-- 数据库配置 -->
        <el-card shadow="never" class="config-card">
          <template #header>
            <span>数据库配置</span>
          </template>

          <el-form :model="dbConfig" :rules="dbRules" ref="dbFormRef" label-width="100px">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="数据库类型" prop="dbType">
                  <el-select
                    v-model="dbConfig.dbType"
                    placeholder="选择数据库类型"
                    @change="handleDbTypeChange"
                  >
                    <el-option
                      v-for="opt in dbTypeOptions"
                      :key="opt.value"
                      :label="opt.label"
                      :value="opt.value"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item :label="hostLabel" prop="host">
                  <el-input v-model="dbConfig.host" :placeholder="hostPlaceholder" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item v-if="showPortField" label="端口" prop="port">
                  <el-input-number
                    v-model="dbConfig.port"
                    :min="1"
                    :max="65535"
                    placeholder="端口"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item v-if="showUsernameField" label="用户名" prop="username">
                  <el-input v-model="dbConfig.username" placeholder="数据库用户名" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item v-if="showPasswordField" label="密码" prop="password">
                  <el-input
                    v-model="dbConfig.password"
                    type="password"
                    placeholder="数据库密码"
                    show-password
                  />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item>
                  <el-button type="primary" @click="connectDatabase" :loading="connecting">
                    {{ connected ? '重新连接' : '连接数据库' }}
                  </el-button>
                  <el-button v-if="connected" type="success" :icon="CircleCheck" disabled>
                    已连接
                  </el-button>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>

        <!-- SQL查询区域 -->
        <el-card shadow="never" class="sql-card">
          <template #header>
            <div class="card-header">
              <span>SQL查询</span>
              <div class="header-buttons">
                <el-button size="small" @click="clearSql" :icon="Delete"> 清空 </el-button>
                <el-button
                  size="small"
                  type="primary"
                  @click="executeSql"
                  :loading="executing"
                  :disabled="!connected || !sqlQuery.trim()"
                  :icon="CaretRight"
                >
                  执行
                </el-button>
              </div>
            </div>
          </template>

          <el-input
            v-model="sqlQuery"
            type="textarea"
            :rows="6"
            placeholder="请输入SQL语句..."
            :disabled="!connected"
            @keydown.ctrl.enter="executeSql"
          />

          <div class="sql-tips">
            <el-alert type="info" :closable="false" show-icon>
              <template #title>
                <span>快捷键：Ctrl+Enter 执行SQL | 支持多条SQL语句（用分号分隔）</span>
              </template>
            </el-alert>
          </div>
        </el-card>

        <!-- 查询结果 -->
        <el-card shadow="never" class="result-card">
          <template #header>
            <div class="card-header">
              <span>查询结果</span>
              <el-button
                v-if="queryResult.data && queryResult.data.length > 0"
                size="small"
                @click="exportResults"
                :icon="Download"
              >
                导出
              </el-button>
            </div>
          </template>

          <!-- 无结果状态 -->
          <div v-if="!queryResult.data" class="empty-result">
            <el-empty description="暂无查询结果">
              <el-icon size="48" color="#909399"><Search /></el-icon>
            </el-empty>
          </div>

          <!-- 查询结果表格 -->
          <div v-else class="result-container">
            <!-- 结果信息 -->
            <div class="result-info">
              <el-tag type="success"> 查询成功，共 {{ queryResult.data.length }} 行结果 </el-tag>
              <el-tag type="info" v-if="queryResult.executionTime">
                执行时间：{{ queryResult.executionTime }}ms
              </el-tag>
              <!-- 调试信息 -->
              <el-tag type="warning" v-if="queryResult.columns">
                列数：{{ queryResult.columns.length }}
              </el-tag>
            </div>

            <!-- 结果表格 -->
            <div class="table-container">
              <el-table :data="paginatedData" style="width: 100%" stripe border max-height="400">
                <el-table-column
                  v-for="column in queryResult.columns"
                  :key="column"
                  :prop="column"
                  :label="column"
                  show-overflow-tooltip
                  min-width="120"
                />
              </el-table>
            </div>

            <!-- 分页组件 -->
            <div
              class="pagination-container"
              v-if="queryResult.data && queryResult.data.length > 0"
            >
              <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="pageSizeOptions"
                :total="queryResult.data.length"
                layout="total, sizes, prev, pager, next, jumper"
                @current-change="handleCurrentPageChange"
                @size-change="handlePageSizeChange"
                background
              />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Files,
  Grid,
  Refresh,
  CircleCheck,
  Delete,
  CaretRight,
  Download,
  Search,
} from '@element-plus/icons-vue'
import api from '@/api/api.js'

// Props
const props = defineProps({
  currentWebshell: {
    type: Object,
    required: false,
    default: null,
  },
  visible: {
    type: Boolean,
    default: true,
  },
})

// 不同webshell类型支持的数据库类型映射（前端约束/展示）
const DB_TYPES_BY_WEBSHELL = {
  csharp: ['sqlserver', 'sqlite', 'access'],
  asp: ['sqlserver'],
  jsp: ['mysql', 'oracle', 'sqlserver', 'postgresql'],
  php: ['mysql'],
}

const DB_TYPE_LABEL = {
  mysql: 'MySQL',
  oracle: 'Oracle',
  sqlserver: 'SQL Server',
  postgresql: 'PostgreSQL',
  sqlite: 'SQLite',
  access: 'Access',
}

const FILE_BASED_DB_TYPES = new Set(['sqlite', 'access'])

// 根据 webshell 类型选择对应的 API
const shellApi = computed(() => {
  if (!props.currentWebshell) return api.javaShell

  const webshellType = props.currentWebshell.webshellType?.toLowerCase() || 'jsp'

  if (webshellType === 'php') {
    return api.phpShell
  } else if (webshellType === 'csharp') {
    return api.csharpShell
  } else if (webshellType === 'asp') {
    return api.aspShell
  } else {
    return api.javaShell
  }
})

// 响应式数据
const connected = ref(false)
const connecting = ref(false)
const loading = ref(false)
const executing = ref(false)

const currentWebshellType = computed(
  () => props.currentWebshell?.webshellType?.toLowerCase() || 'jsp',
)

const supportedDbTypes = computed(() => {
  return DB_TYPES_BY_WEBSHELL[currentWebshellType.value] || DB_TYPES_BY_WEBSHELL.jsp
})

const dbTypeOptions = computed(() => {
  return supportedDbTypes.value.map((t) => ({
    value: t,
    label: DB_TYPE_LABEL[t] || t,
  }))
})

// 数据库配置
const dbConfig = reactive({
  dbType: 'mysql',
  host: 'localhost',
  port: 3306,
  username: 'root',
  password: '',
})

const isFileBasedDbType = computed(() => FILE_BASED_DB_TYPES.has(dbConfig.dbType))

// Access 虽然是文件型，但可能存在密码/用户；SQLite 不需要
const showPortField = computed(() => !isFileBasedDbType.value)
const showUsernameField = computed(() => !isFileBasedDbType.value || dbConfig.dbType === 'access')
const showPasswordField = computed(() => !isFileBasedDbType.value || dbConfig.dbType === 'access')

const hostLabel = computed(() => (isFileBasedDbType.value ? '数据库文件' : '主机'))
const hostPlaceholder = computed(() => {
  if (dbConfig.dbType === 'sqlite') {
    return 'SQLite数据库文件路径，例如 C:\\\\data\\\\db.sqlite'
  }
  if (dbConfig.dbType === 'access') {
    return 'Access数据库文件路径，例如 C:\\\\data\\\\db.mdb 或 C:\\\\data\\\\db.accdb'
  }
  return '数据库主机地址'
})

// 表单验证规则（按dbType动态调整）
const dbRules = computed(() => {
  const rules = {
    dbType: [{ required: true, message: '请选择数据库类型', trigger: 'change' }],
    host: [
      {
        required: true,
        message: isFileBasedDbType.value ? '请输入数据库文件路径' : '请输入主机地址',
        trigger: 'blur',
      },
    ],
  }
  if (!isFileBasedDbType.value) {
    rules.port = [{ required: true, message: '请输入端口号', trigger: 'blur' }]
    rules.username = [{ required: true, message: '请输入用户名', trigger: 'blur' }]
    rules.password = [{ required: true, message: '请输入密码', trigger: 'blur' }]
  }
  return rules
})

// 树形数据
const treeData = ref([])
const treeProps = {
  label: 'name',
  children: 'children',
  isLeaf: 'isLeaf',
}

// SQL查询
const sqlQuery = ref('')
const queryResult = ref({
  data: null,
  columns: [],
  executionTime: null,
})

// 分页相关
const currentPage = ref(1)
const pageSize = ref(50)
const pageSizeOptions = [10, 20, 50, 100, 200, 500]

// 计算分页数据
const paginatedData = computed(() => {
  if (!queryResult.value.data || !Array.isArray(queryResult.value.data)) {
    return []
  }
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return queryResult.value.data.slice(start, end)
})

// 处理页码变化
const handleCurrentPageChange = (page) => {
  currentPage.value = page
}

// 处理每页条数变化
const handlePageSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1 // 重置到第一页
}

// 引用
const dbFormRef = ref()
const treeRef = ref()

// 数据库端口默认值
const defaultPorts = {
  mysql: 3306,
  oracle: 1521,
  sqlserver: 1433,
  postgresql: 5432,
  // file-based DB: 仅用于满足后端必填字段（策略A），实际连接通常不使用端口
  sqlite: 0,
  access: 0,
}

// 针对某些dbType自动填充字段（策略A）
const applyDbTypeDefaults = () => {
  if (!isFileBasedDbType.value) return

  // 后端/载荷要求字段存在，这里用“可忽略的默认值”填充
  dbConfig.port = 0

  // file-based DB：host 字段用于填写数据库文件路径，默认把 localhost 清掉避免误导
  if (dbConfig.host === 'localhost') {
    dbConfig.host = ''
  }

  if (dbConfig.dbType === 'sqlite') {
    // SQLite 不需要用户名/密码
    dbConfig.username = ''
    dbConfig.password = ''
    return
  }

  if (dbConfig.dbType === 'access') {
    // Access 常见场景下 username 为空；若用户手动填写则保留
    if (!dbConfig.username || dbConfig.username === 'root') {
      dbConfig.username = ''
    }
    if (dbConfig.password === null || dbConfig.password === undefined) {
      dbConfig.password = ''
    }
  }
}

// 监听数据库类型变化，自动设置默认端口
const handleDbTypeChange = (value) => {
  if (Object.prototype.hasOwnProperty.call(defaultPorts, value)) {
    dbConfig.port = defaultPorts[value]
  }
  // file-based DB 自动填充非关键字段，避免后端缺参
  applyDbTypeDefaults()
}

// 切换webshell类型时，纠正dbType到支持范围内
watch(
  () => supportedDbTypes.value,
  (types) => {
    if (!types || types.length === 0) return
    if (!types.includes(dbConfig.dbType)) {
      dbConfig.dbType = types[0]
      handleDbTypeChange(dbConfig.dbType)
    }
  },
  { immediate: true },
)

// 连接数据库
const connectDatabase = async () => {
  try {
    if (!props.currentWebshell) {
      ElMessage.error('请先选择一个webshell连接')
      return
    }

    // 策略A：先填充，再校验/提交
    applyDbTypeDefaults()
    await dbFormRef.value.validate()

    connecting.value = true

    // 测试连接
    const response = await shellApi.value.testDatabaseConnection({
      webshell_id: props.currentWebshell.id,
      dbType: dbConfig.dbType,
      host: dbConfig.host,
      port: dbConfig.port,
      username: dbConfig.username,
      dbPassword: dbConfig.password,
    })

    if (response.data.status === 'success') {
      connected.value = true
      ElMessage.success('数据库连接成功')

      // 自动加载数据库列表
      await loadDatabases()
    } else {
      throw new Error(response.data.message || '数据库连接失败')
    }
  } catch (error) {
    console.error('连接数据库失败:', error)
    ElMessage.error(error.message || '数据库连接失败')
    connected.value = false
  } finally {
    connecting.value = false
  }
}

// 加载数据库列表
const loadDatabases = async () => {
  try {
    if (!props.currentWebshell) {
      ElMessage.error('webshell连接已断开')
      return
    }

    loading.value = true

    // Access/SQLite 没有“数据库列表”概念：以当前文件作为单一库
    if (dbConfig.dbType === 'access' || dbConfig.dbType === 'sqlite') {
      const dbNameFromPath = (dbConfig.host || '').split(/[\\/]/).filter(Boolean).slice(-1)[0]
      const displayName = dbNameFromPath || (dbConfig.dbType === 'access' ? 'Access数据库' : 'SQLite数据库')
      treeData.value = [
        {
          id: 'db_0',
          name: displayName,
          type: 'database',
          children: [],
          isLeaf: false,
        },
      ]
      ElMessage.success('已加载数据库')
      return
    }

    let sql = ''
    switch (dbConfig.dbType) {
      case 'mysql':
        sql = 'SHOW DATABASES'
        break
      case 'oracle':
        sql = 'SELECT USERNAME AS database_name FROM ALL_USERS ORDER BY USERNAME'
        break
      case 'sqlserver':
        sql = 'SELECT name AS database_name FROM sys.databases WHERE database_id > 4'
        break
      case 'postgresql':
        sql = 'SELECT datname AS database_name FROM pg_database WHERE datistemplate = false'
        break
      default:
        sql = 'SHOW DATABASES'
    }

    const response = await shellApi.value.executeSql({
      webshell_id: props.currentWebshell.id,
      dbType: dbConfig.dbType,
      host: dbConfig.host,
      port: dbConfig.port,
      username: dbConfig.username,
      dbPassword: dbConfig.password,
      sql: sql,
    })

    if (response.data.status === 'success' && response.data.data) {
      const databases = response.data.data.map((row, index) => {
        const dbName = row[Object.keys(row)[0]] // 取第一列的值
        return {
          id: `db_${index}`,
          name: dbName,
          type: 'database',
          children: [],
          isLeaf: false,
        }
      })

      treeData.value = databases
      ElMessage.success(`成功加载 ${databases.length} 个数据库`)
    } else {
      throw new Error(response.data.message || '加载数据库列表失败')
    }
  } catch (error) {
    console.error('加载数据库失败:', error)
    ElMessage.error(error.message || '加载数据库列表失败')
  } finally {
    loading.value = false
  }
}

// 懒加载树节点（加载表）
const loadTreeNode = async (node, resolve) => {
  if (node.level === 0) {
    return resolve([])
  }

  if (node.data.type === 'database') {
    try {
      if (!props.currentWebshell) {
        resolve([])
        return
      }

      const dbName = node.data.name
      let sql = ''

      switch (dbConfig.dbType) {
        case 'mysql':
          sql = `SHOW TABLES FROM \`${dbName}\``
          break
        case 'oracle':
          sql = `SELECT table_name FROM all_tables WHERE owner = '${dbName}' ORDER BY table_name`
          break
        case 'sqlserver':
          sql = `USE [${dbName}]; SELECT name AS table_name FROM sys.tables ORDER BY name`
          break
        case 'postgresql':
          sql = `SELECT tablename AS table_name FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename`
          break
        case 'sqlite':
          sql =
            "SELECT name AS table_name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
          break
        case 'access':
          // MSysObjects 可能因权限不可读；该SQL用于常见场景下列出用户表
          sql =
            "SELECT [Name] AS table_name FROM MSysObjects WHERE [Type]=1 AND Left([Name],4)<>'MSys' AND Left([Name],1)<>'~' ORDER BY [Name]"
          break
        default:
          sql = `SHOW TABLES FROM \`${dbName}\``
      }

      const response = await shellApi.value.executeSql({
        webshell_id: props.currentWebshell.id,
        dbType: dbConfig.dbType,
        host: dbConfig.host,
        port: dbConfig.port,
        username: dbConfig.username,
        dbPassword: dbConfig.password,
        sql: sql,
      })

      if (response.data.status === 'success' && response.data.data) {
        const tables = response.data.data.map((row, index) => {
          const tableName = row[Object.keys(row)[0]] // 取第一列的值
          return {
            id: `table_${dbName}_${index}`,
            name: tableName,
            type: 'table',
            database: dbName,
            isLeaf: true,
          }
        })

        resolve(tables)
      } else {
        resolve([])
      }
    } catch (error) {
      console.error('加载表失败:', error)
      resolve([])
    }
  } else {
    resolve([])
  }
}

// 树节点点击事件
const handleTreeNodeClick = (data) => {
  if (data.type === 'table') {
    // 点击表时，生成SELECT语句
    const dbName = data.database
    const tableName = data.name
    let selectSql = ''

    if (dbConfig.dbType === 'mysql') {
      selectSql = `SELECT * FROM \`${dbName}\`.\`${tableName}\` LIMIT 100;`
    } else if (dbConfig.dbType === 'oracle') {
      selectSql = `SELECT * FROM ${dbName}.${tableName} WHERE ROWNUM <= 100;`
    } else if (dbConfig.dbType === 'sqlserver') {
      selectSql = `USE [${dbName}]; SELECT TOP 100 * FROM [${tableName}];`
    } else if (dbConfig.dbType === 'postgresql') {
      selectSql = `SELECT * FROM ${tableName} LIMIT 100;`
    } else if (dbConfig.dbType === 'sqlite') {
      selectSql = `SELECT * FROM "${tableName}" LIMIT 100;`
    } else if (dbConfig.dbType === 'access') {
      selectSql = `SELECT TOP 100 * FROM [${tableName}];`
    }

    sqlQuery.value = selectSql
  }
}

// 刷新数据库列表
const refreshDatabases = async () => {
  if (connected.value) {
    await loadDatabases()
  }
}

// 清空SQL
const clearSql = () => {
  sqlQuery.value = ''
}

// 执行SQL
const executeSql = async () => {
  if (!props.currentWebshell) {
    ElMessage.error('请先选择一个webshell连接')
    return
  }

  if (!sqlQuery.value.trim()) {
    ElMessage.warning('请输入SQL语句')
    return
  }

  try {
    executing.value = true
    const startTime = Date.now()

    const response = await shellApi.value.executeSql({
      webshell_id: props.currentWebshell.id,
      dbType: dbConfig.dbType,
      host: dbConfig.host,
      port: dbConfig.port,
      username: dbConfig.username,
      dbPassword: dbConfig.password,
      sql: sqlQuery.value,
    })

    const executionTime = Date.now() - startTime

    if (response.data.status === 'success') {
      // 重置分页到第一页
      currentPage.value = 1

      if (
        response.data.data &&
        Array.isArray(response.data.data) &&
        response.data.data.length > 0
      ) {
        // 查询结果
        const columns = Object.keys(response.data.data[0])
        queryResult.value = {
          data: response.data.data,
          columns: columns,
          executionTime: executionTime,
        }
        ElMessage.success(`查询成功，返回 ${response.data.data.length} 行数据`)
      } else if (response.data.message && response.data.message.includes('Query OK')) {
        // 更新操作结果
        queryResult.value = {
          data: [
            {
              操作结果: response.data.message,
            },
          ],
          columns: ['操作结果'],
          executionTime: executionTime,
        }
        ElMessage.success('SQL执行成功')
      } else {
        queryResult.value = {
          data: [
            {
              结果: '执行成功，无返回数据',
            },
          ],
          columns: ['结果'],
          executionTime: executionTime,
        }
        ElMessage.success('SQL执行成功')
      }
    } else {
      throw new Error(response.data.message || 'SQL执行失败')
    }
  } catch (error) {
    console.error('执行SQL失败:', error)
    ElMessage.error(error.message || 'SQL执行失败')

    // 显示错误信息
    queryResult.value = {
      data: [
        {
          错误信息: error.message || 'SQL执行失败',
        },
      ],
      columns: ['错误信息'],
      executionTime: null,
    }
  } finally {
    executing.value = false
  }
}

// 导出结果
const exportResults = () => {
  try {
    if (!queryResult.value.data || queryResult.value.data.length === 0) {
      ElMessage.warning('没有可导出的数据')
      return
    }

    // 生成CSV内容
    const columns = queryResult.value.columns
    const csvContent = [
      columns.join(','), // 表头
      ...queryResult.value.data.map((row) =>
        columns
          .map((col) => {
            const value = row[col] || ''
            // 处理包含逗号或引号的值
            return value.toString().includes(',') || value.toString().includes('"')
              ? `"${value.toString().replace(/"/g, '""')}"`
              : value
          })
          .join(','),
      ),
    ].join('\n')

    // 创建下载链接
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `query_result_${new Date().getTime()}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// 组件挂载时的初始化
onMounted(() => {
  // 可以在这里进行一些初始化操作
})
</script>

<style scoped>
.database-manager {
  padding: 20px;
  max-height: 70vh;
  overflow-y: auto;
}

.no-webshell {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
}

.left-panel,
.right-panel {
  height: 100%;
}

.left-panel .el-card {
  height: 100%;
}

.left-panel .el-card .el-card__body {
  height: calc(100% - 57px);
  padding: 0;
  overflow: auto;
}

/* 右侧面板设置 */
.right-panel {
  display: flex;
  flex-direction: column;
}

.right-panel > .el-card:not(:last-child) {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: 8px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tree-node .node-label {
  font-size: 14px;
}

.config-card {
  margin-bottom: 16px;
}

.sql-card {
  margin-bottom: 16px;
}

.sql-tips {
  margin-top: 12px;
}

/* 移除原有的 result-card 样式，现在由右侧面板统一控制 */

.empty-result {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.result-info {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-shrink: 0; /* 结果信息不缩小 */
}

/* 结果容器样式 */
.result-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 分页容器样式 */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding: 16px 0;
}

/* 优化表格显示 */
:deep(.el-table) {
  border-radius: 6px;
}

/* 自定义滚动条样式 */
.database-manager::-webkit-scrollbar {
  width: 8px;
}

.database-manager::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.database-manager::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.database-manager::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.el-input-number {
  width: 100%;
}

.el-select {
  width: 100%;
}

:deep(.el-tree-node__content) {
  height: 32px;
}

:deep(.el-tree-node__label) {
  font-size: 14px;
}

:deep(.el-card__body) {
  padding: 16px;
}
</style>
