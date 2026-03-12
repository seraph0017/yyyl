// 某露营地 — 用户状态管理
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AdminUserInfo } from '@/types'
import { login as loginApi, logout as logoutApi, getMe } from '@/api/auth'
import { setToken, clearToken, getToken } from '@/utils/request'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref<AdminUserInfo | null>(null)
  const isLoggedIn = computed(() => !!getToken())
  const roleName = computed(() => userInfo.value?.role?.role_name || '')
  const roleCode = computed(() => userInfo.value?.role?.role_code || '')
  const isAdmin = computed(() => ['admin', 'super_admin'].includes(roleCode.value))
  const isSuperAdmin = computed(() => roleCode.value === 'super_admin')

  // 初始化用户信息（从localStorage恢复）
  function initUser() {
    const cached = localStorage.getItem('user_info')
    if (cached) {
      try {
        userInfo.value = JSON.parse(cached)
      } catch {
        localStorage.removeItem('user_info')
      }
    }
  }

  // 登录
  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    const data = res.data
    setToken(data.access_token, data.refresh_token)
    userInfo.value = data.user
    localStorage.setItem('user_info', JSON.stringify(data.user))
    return data
  }

  // 获取最新用户信息
  async function fetchUserInfo() {
    try {
      const res = await getMe()
      userInfo.value = res.data
      localStorage.setItem('user_info', JSON.stringify(res.data))
    } catch {
      // Token无效则清除
      logout()
    }
  }

  // 登出
  async function logout() {
    try {
      await logoutApi()
    } catch {
      // 忽略登出接口失败
    } finally {
      userInfo.value = null
      clearToken()
      router.push('/login')
    }
  }

  return {
    userInfo,
    isLoggedIn,
    roleName,
    roleCode,
    isAdmin,
    isSuperAdmin,
    initUser,
    login,
    fetchUserInfo,
    logout,
  }
})
