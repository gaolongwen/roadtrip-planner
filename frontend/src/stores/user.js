import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/index'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const nickname = computed(() => user.value?.nickname || user.value?.username || '')

  // 从 localStorage 恢复用户信息
  const savedUser = localStorage.getItem('user')
  if (savedUser) {
    try {
      user.value = JSON.parse(savedUser)
    } catch (e) {
      console.error('Failed to parse saved user:', e)
    }
  }

  // 登录
  async function login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    
    const response = await fetch(`${api.defaults.baseURL}/api/auth/login`, {
      method: 'POST',
      body: formData,
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '登录失败')
    }
    
    const data = await response.json()
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    
    // 获取用户信息
    await fetchUserInfo()
    
    return data
  }

  // 注册
  async function register(username, password, nickname) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    if (nickname) {
      formData.append('nickname', nickname)
    }
    
    const response = await fetch(`${api.defaults.baseURL}/api/auth/register`, {
      method: 'POST',
      body: formData,
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '注册失败')
    }
    
    const data = await response.json()
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    
    // 获取用户信息
    await fetchUserInfo()
    
    return data
  }

  // 获取用户信息
  async function fetchUserInfo() {
    if (!token.value) return null
    
    try {
      const response = await fetch(`${api.defaults.baseURL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token.value}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        user.value = data
        localStorage.setItem('user', JSON.stringify(data))
        return data
      }
    } catch (e) {
      console.error('Failed to fetch user info:', e)
    }
    
    return null
  }

  // 退出登录
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return {
    token,
    user,
    isLoggedIn,
    nickname,
    login,
    register,
    fetchUserInfo,
    logout,
  }
})
