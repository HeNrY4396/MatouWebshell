import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/webshellManager',
      name: 'webshellManager',
      component: () => import('../views/WebshellManagerView.vue'),
      meta: {
        title: 'Webshell管理',
      },
    },
  ],
})

export default router
