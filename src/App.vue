<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-container">
    <header>
      <div class="nav-container">
        <img alt="Vue logo" class="logo" src="@/assets/1.ico" width="50" height="50" />
        <h2>欧耶！我见过马</h2>
        <nav>
          <RouterLink to="/">首页</RouterLink>
          <RouterLink to="/webshellManager">Webshell管理</RouterLink>
        </nav>
      </div>
    </header>

    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background-color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
  padding: 0.6rem 1.2rem;
}

.nav-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1180px;
  margin: 0 auto;
  width: 100%;
}

.logo {
  display: block;
}

nav {
  display: flex;
  align-items: center;
  font-size: 1rem;
}

nav a {
  display: inline-block;
  padding: 0.5rem 1rem;
  margin: 0 0.5rem;
  border-left: 1px solid var(--color-border);
  text-decoration: none;
  color: var(--color-text);
  transition: all 0.3s ease;
}

nav a:first-of-type {
  border: 0;
}

nav a.router-link-exact-active {
  color: var(--color-primary);
  font-weight: bold;
}

nav a.router-link-exact-active:hover {
  background-color: transparent;
}

main {
  flex: 1;
  padding: 5rem 1rem 1.5rem; /* 预留顶部固定导航的高度 */
}

/* 响应式设计 - 保持导航栏在顶部 */
@media (max-width: 768px) {
  .nav-container {
    flex-direction: column;
    padding: 0.5rem 0;
  }

  .logo {
    margin-bottom: 0.5rem;
  }

  nav {
    width: 100%;
    justify-content: center;
  }
}
</style>
