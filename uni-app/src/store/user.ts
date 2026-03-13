/**
 * 用户状态管理
 * 替代微信原生 App.globalData
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { IUserInfo } from '@/types'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref<IUserInfo | null>(null)
  const token = ref('')
  const refreshToken = ref('')

  const isLoggedIn = computed(() => !!token.value)
  const isStaff = computed(() => userInfo.value?.is_staff || false)
  const isMember = computed(() => userInfo.value?.is_annual_member || false)

  function setUser(user: IUserInfo) {
    userInfo.value = user
  }

  function setToken(accessToken: string, refresh: string) {
    token.value = accessToken
    refreshToken.value = refresh
  }

  function clearUser() {
    userInfo.value = null
    token.value = ''
    refreshToken.value = ''
  }

  /**
   * 从本地存储恢复登录状态
   */
  function restoreFromStorage() {
    try {
      const storedToken = uni.getStorageSync('access_token') || ''
      const storedRefresh = uni.getStorageSync('refresh_token') || ''
      const storedUser = uni.getStorageSync('user_info')

      if (storedToken) {
        token.value = storedToken
        refreshToken.value = storedRefresh
        if (storedUser) {
          userInfo.value = JSON.parse(storedUser)
        }
      }
    } catch (e) {
      console.error('恢复登录状态失败:', e)
    }
  }

  return {
    userInfo,
    token,
    refreshToken,
    isLoggedIn,
    isStaff,
    isMember,
    setUser,
    setToken,
    clearUser,
    restoreFromStorage,
  }
})
