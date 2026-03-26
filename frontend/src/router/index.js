import { createRouter, createWebHistory } from 'vue-router'
import MapView from '@/views/MapView.vue'
import TripView from '@/views/TripView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: MapView,
  },
  {
    path: '/trip/:tripId?',
    name: 'trip',
    component: TripView,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
