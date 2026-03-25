<script setup>
import { useRouter } from 'vue-router'
import { Monitor, Connection, Link, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()

const features = [
  {
    icon: Monitor,
    title: 'Webshell 管理',
    desc: '统一管理 JSP/PHP Webshell，支持状态监控、文件管理与命令执行。',
  },
  {
    icon: Connection,
    title: '持续扩展',
    desc: '后续将引入与webshell有关的工具，例如内存马定制、漏洞攻击链利用等',
  },
]

const openLink = (url) => {
  window.open(url, '_blank')
}
</script>

<template>
  <div class="welcome-container">
    <div class="hero-section">
      <div class="logo-area">
        <div class="logo-box">MT</div>
      </div>
      <h1 class="project-title">MatouWebshell</h1>
      <p class="project-desc">MatouWebshell 主要用于集成 Webshell相关的工具<br /></p>

      <div class="action-buttons">
        <el-button type="primary" size="large" round @click="router.push('/webshellManager')">
          开始使用
          <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
        <el-button
          size="large"
          round
          @click="openLink('https://github.com/HeNrY4396/MatouWebshell')"
        >
          <el-icon class="el-icon--left"><Link /></el-icon>
          GitHub
        </el-button>
      </div>
    </div>

    <div class="features-grid">
      <div v-for="(feature, index) in features" :key="index" class="feature-card">
        <div class="icon-wrapper">
          <el-icon :size="24"><component :is="feature.icon" /></el-icon>
        </div>
        <h3>{{ feature.title }}</h3>
        <p>{{ feature.desc }}</p>
      </div>
    </div>

    <footer class="welcome-footer">
      <p>Designed for Security Research & Penetration Testing</p>
    </footer>
  </div>
</template>

<style scoped>
.welcome-container {
  min-height: 80vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  background: radial-gradient(circle at 50% -20%, #f0f4ff, #ffffff 60%);
  color: #2c3e50;
}

.hero-section {
  text-align: center;
  max-width: 800px;
  margin-bottom: 60px;
  animation: fadeInDown 0.8s ease-out;
}

.logo-area {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

.logo-box {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  border-radius: 20px;
  color: white;
  font-size: 32px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 20px rgba(64, 158, 255, 0.3);
}

.project-title {
  font-size: 48px;
  font-weight: 800;
  margin: 0 0 20px;
  background: -webkit-linear-gradient(315deg, #1d1e21 25%, #409eff);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -1px;
}

.project-desc {
  font-size: 18px;
  line-height: 1.8;
  color: #5c6b7f;
  margin-bottom: 40px;
}

.project-desc span {
  color: #409eff;
  font-weight: 600;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 24px;
  width: 100%;
  max-width: 1200px;
  padding: 0 20px;
  animation: fadeInUp 1s ease-out;
}

.feature-card {
  background: white;
  padding: 30px;
  border-radius: 16px;
  box-shadow:
    0 4px 6px rgba(0, 0, 0, 0.02),
    0 10px 15px rgba(0, 0, 0, 0.03);
  transition:
    transform 0.3s,
    box-shadow 0.3s;
  border: 1px solid #f0f2f5;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow:
    0 20px 25px rgba(0, 0, 0, 0.05),
    0 10px 10px rgba(0, 0, 0, 0.02);
}

.icon-wrapper {
  width: 48px;
  height: 48px;
  background: #ecf5ff;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  margin-bottom: 20px;
}

.feature-card h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 12px;
  color: #1a1a1a;
}

.feature-card p {
  font-size: 14px;
  line-height: 1.6;
  color: #6b7785;
  margin: 0;
}

.welcome-footer {
  margin-top: 60px;
  color: #909399;
  font-size: 13px;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式调整 */
@media (max-width: 768px) {
  .project-title {
    font-size: 36px;
  }
  .action-buttons {
    flex-direction: column;
    padding: 0 40px;
  }
  .action-buttons .el-button {
    width: 100%;
    margin-left: 0 !important;
  }
}
</style>
