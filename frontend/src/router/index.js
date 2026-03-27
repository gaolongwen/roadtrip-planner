import { createRouter, createWebHashHistory } from 'vue-router'
import MapView from '@/views/MapView.vue'
import TripView from '@/views/TripView.vue'
import LoginView from '@/views/LoginView.vue'
import TripsListView from '@/views/TripsListView.vue'

const routes = [
  {
    path: '/',
    name: 'login',
    component: LoginView,
  },
  {
    path: '/trips',
    name: 'trips',
    component: TripsListView,
    meta: { requiresAuth: true },
  },
  {
    path: '/trip/:tripId?',
    name: 'trip',
    component: TripView,
    meta: { requiresAuth: true },
  },
  {
    path: '/map',
    name: 'map',
    component: MapView,
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const isLoggedIn = !!token
  
  if (to.meta.requiresAuth && !isLoggedIn) {
    // 需要登录但未登录，跳转到登录页
    next({
      name: 'login',
      query: { redirect: to.fullPath }
    })
  } else if (to.name === 'login' && isLoggedIn) {
    // 已登录访问登录页，跳转到行程列表
    next({ name: 'trips' })
  } else {
    next()
  }
})

export default router
