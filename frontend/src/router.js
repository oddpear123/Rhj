import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', component: () => import('./views/Home.vue') },
  { path: '/gallery', component: () => import('./views/Gallery.vue') },
  { path: '/pricing', component: () => import('./views/Pricing.vue') },
  { path: '/login', component: () => import('./views/Login.vue') },
  { path: '/register', component: () => import('./views/Register.vue') },
  { path: '/dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/admin', component: () => import('./views/AdminPanel.vue') },
  { path: '/admin/upload', component: () => import('./views/Upload.vue') },
  { path: '/photo/:id', component: () => import('./views/PhotoDetail.vue') },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
