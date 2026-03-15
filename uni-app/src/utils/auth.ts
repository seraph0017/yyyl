/**
 * 登录授权工具
 * - 微信登录（uni.login获取code → 后端换token）
 * - 手机号授权
 * - Token管理
 */

import { post } from './request'
import { useUserStore } from '@/store/user'
import { currentSite } from '@/config/sites'
import type { ILoginResult, IUserInfo } from '@/types'

/**
 * 微信静默登录
 */
export async function wxLogin(): Promise<ILoginResult> {
  let code: string
  try {
    // uni-app Vue 3 中 uni.login 返回 Promise<LoginRes>
    const res = await uni.login({})
    // 兼容两种返回格式：直接对象 { code } 或旧版数组 [err, res]
    if (Array.isArray(res)) {
      const [err, loginRes] = res as unknown as [unknown, { code: string } | undefined]
      if (err || !loginRes?.code) throw new Error('微信登录失败')
      code = loginRes.code
    } else {
      code = (res as { code: string }).code
    }
  } catch {
    throw new Error('微信登录失败')
  }

  if (!code) {
    throw new Error('微信登录失败：未获取到 code')
  }

  const result = await post<ILoginResult>(
    '/auth/login',
    { code, site_id: currentSite.id },
    { needAuth: false },
  )

  saveLoginInfo(result)
  return result
}

/**
 * 手机号授权登录
 */
export async function phoneLogin(e: { detail: { code?: string; errMsg: string } }): Promise<ILoginResult | null> {
  if (!e.detail.code) {
    return null
  }

  let wxCode: string
  try {
    const res = await uni.login({})
    if (Array.isArray(res)) {
      const [err, loginRes] = res as unknown as [unknown, { code: string } | undefined]
      if (err || !loginRes?.code) throw new Error('微信登录失败')
      wxCode = loginRes.code
    } else {
      wxCode = (res as { code: string }).code
    }
  } catch {
    throw new Error('微信登录失败')
  }

  const result = await post<ILoginResult>(
    '/auth/phone-login',
    { code: wxCode, phone_code: e.detail.code, site_id: currentSite.id },
    { needAuth: false },
  )

  saveLoginInfo(result)
  return result
}

/**
 * 保存登录信息
 */
export function saveLoginInfo(result: ILoginResult): void {
  uni.setStorageSync('access_token', result.access_token)
  uni.setStorageSync('refresh_token', result.refresh_token)
  uni.setStorageSync('user_info', JSON.stringify(result.user))

  const userStore = useUserStore()
  userStore.setUser(result.user)
  userStore.setToken(result.access_token, result.refresh_token)
}

/**
 * 检查登录状态
 */
export function checkLoginStatus(): boolean {
  const token = uni.getStorageSync('access_token')
  return !!token
}

/**
 * 获取已登录的用户信息
 */
export function getUserInfo(): IUserInfo | null {
  try {
    const str = uni.getStorageSync('user_info')
    return str ? JSON.parse(str) : null
  } catch {
    return null
  }
}

/**
 * 退出登录
 */
export function logout(): void {
  uni.removeStorageSync('access_token')
  uni.removeStorageSync('refresh_token')
  uni.removeStorageSync('user_info')

  const userStore = useUserStore()
  userStore.clearUser()
}

/**
 * 确保已登录，未登录则尝试静默登录
 */
export async function ensureLogin(): Promise<boolean> {
  if (checkLoginStatus()) {
    return true
  }

  try {
    await wxLogin()
    return true
  } catch {
    return false
  }
}

/**
 * 需要登录时调用，未登录跳转引导
 */
export function requireLogin(callback?: () => void): void {
  if (checkLoginStatus()) {
    callback?.()
    return
  }

  uni.showModal({
    title: '提示',
    content: '请先登录后再操作',
    confirmText: '去登录',
    success(res) {
      if (res.confirm) {
        uni.navigateTo({ url: '/pages/mine/index' })
      }
    },
  })
}
