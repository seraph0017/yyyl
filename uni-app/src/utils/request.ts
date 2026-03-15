/**
 * 网络请求封装
 * - 自动携带token + X-Site-Id
 * - 统一响应处理（code=0成功）
 * - token过期自动刷新（并发排队）
 * - 错误提示
 */

import { currentSite } from '@/config/sites'
import type { IApiResponse } from '@/types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const SERVER_BASE = import.meta.env.VITE_SERVER_BASE || 'http://localhost:8000'

/**
 * 将后端返回的图片路径转换为完整 URL
 * 微信小程序要求图片必须使用 HTTPS 协议
 */
export function resolveImageUrl(path: string): string {
  if (!path) return ''
  if (path.startsWith('https://')) return path
  if (path.startsWith('http://')) {
    // 微信小程序不支持 HTTP 图片，自动升级为 HTTPS
    return path.replace('http://', 'https://')
  }
  const fullUrl = `${SERVER_BASE}${path.startsWith('/') ? '' : '/'}${path}`
  // 开发环境 localhost 用 HTTP，小程序中图片无法加载，返回空让 placeholder 生效
  // #ifdef MP-WEIXIN
  if (fullUrl.startsWith('http://localhost') || fullUrl.startsWith('http://127.0.0.1')) {
    return ''
  }
  // #endif
  return fullUrl
}

export interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: Record<string, unknown> | unknown[]
  params?: Record<string, string | number | boolean | undefined>
  header?: Record<string, string>
  showLoading?: boolean
  loadingText?: string
  showError?: boolean
  needAuth?: boolean
}

/** 是否正在刷新token */
let isRefreshing = false
/** 等待刷新的请求队列 */
let waitingQueue: Array<() => void> = []

/**
 * 构建URL查询参数
 */
function buildQueryString(params: Record<string, string | number | boolean | undefined>): string {
  const parts: string[] = []
  for (const key of Object.keys(params)) {
    const value = params[key]
    if (value !== undefined && value !== null) {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    }
  }
  return parts.length > 0 ? `?${parts.join('&')}` : ''
}

/**
 * 获取Token
 */
function getToken(): string {
  try {
    return uni.getStorageSync('access_token') || ''
  } catch {
    return ''
  }
}

/**
 * 刷新Token
 */
async function refreshToken(): Promise<string> {
  const refreshTokenStr = uni.getStorageSync('refresh_token') || ''
  if (!refreshTokenStr) {
    throw new Error('No refresh token')
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}/auth/refresh`,
      method: 'POST',
      data: { refresh_token: refreshTokenStr },
      header: { 'X-Site-Id': String(currentSite.id) },
      success(res) {
        const data = res.data as IApiResponse<{ access_token: string; refresh_token: string }>
        if (data.code === 0 && data.data) {
          uni.setStorageSync('access_token', data.data.access_token)
          uni.setStorageSync('refresh_token', data.data.refresh_token)
          resolve(data.data.access_token)
        } else {
          reject(new Error('Refresh token failed'))
        }
      },
      fail(err) {
        reject(err)
      },
    })
  })
}

/**
 * 处理Token过期
 */
async function handleTokenExpired<T>(options: RequestOptions): Promise<T> {
  if (isRefreshing) {
    return new Promise<T>((resolve) => {
      waitingQueue.push(() => {
        resolve(request<T>(options))
      })
    })
  }

  isRefreshing = true

  try {
    await refreshToken()
    isRefreshing = false

    waitingQueue.forEach((callback) => callback())
    waitingQueue = []

    return request<T>(options)
  } catch {
    isRefreshing = false
    waitingQueue = []

    uni.removeStorageSync('access_token')
    uni.removeStorageSync('refresh_token')
    uni.removeStorageSync('user_info')

    uni.showToast({
      title: '登录已过期，请重新登录',
      icon: 'none',
      duration: 2000,
    })

    throw new Error('Token expired')
  }
}

/**
 * 核心请求方法
 */
export function request<T = unknown>(options: RequestOptions): Promise<T> {
  const {
    url,
    method = 'GET',
    data,
    params,
    header = {},
    showLoading = false,
    loadingText = '加载中...',
    showError = true,
    needAuth = true,
  } = options

  let fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`
  if (params) {
    fullUrl += buildQueryString(params)
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Site-Id': String(currentSite.id),
    ...header,
  }

  if (needAuth) {
    const token = getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
  }

  if (showLoading) {
    uni.showLoading({ title: loadingText, mask: true })
  }

  return new Promise<T>((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method,
      data: data as Record<string, unknown>,
      header: headers,
      success(res) {
        if (showLoading) uni.hideLoading()

        const statusCode = res.statusCode
        const responseData = res.data as IApiResponse<T>

        if (statusCode === 401) {
          handleTokenExpired<T>(options).then(resolve).catch(reject)
          return
        }

        if (statusCode >= 400) {
          const errMsg = responseData?.message || `请求失败(${statusCode})`
          if (showError) {
            uni.showToast({ title: errMsg, icon: 'none', duration: 2500 })
          }
          reject(new Error(errMsg))
          return
        }

        if (responseData.code === 0) {
          resolve(responseData.data)
        } else {
          const errMsg = responseData.message || '请求异常'
          if (showError) {
            uni.showToast({ title: errMsg, icon: 'none', duration: 2500 })
          }
          reject(new Error(errMsg))
        }
      },
      fail(err) {
        if (showLoading) uni.hideLoading()

        const errMsg = '网络连接失败，请检查网络设置'
        if (showError) {
          uni.showToast({ title: errMsg, icon: 'none', duration: 2500 })
        }
        reject(new Error(err.errMsg || errMsg))
      },
    })
  })
}

/** GET请求 */
export function get<T = unknown>(
  url: string,
  params?: Record<string, string | number | boolean | undefined>,
  options?: Partial<RequestOptions>,
): Promise<T> {
  return request<T>({ url, method: 'GET', params, ...options })
}

/** POST请求 */
export function post<T = unknown>(
  url: string,
  data?: Record<string, unknown> | unknown[],
  options?: Partial<RequestOptions>,
): Promise<T> {
  return request<T>({ url, method: 'POST', data, ...options })
}

/** PUT请求 */
export function put<T = unknown>(
  url: string,
  data?: Record<string, unknown> | unknown[],
  options?: Partial<RequestOptions>,
): Promise<T> {
  return request<T>({ url, method: 'PUT', data, ...options })
}

/** DELETE请求 */
export function del<T = unknown>(
  url: string,
  options?: Partial<RequestOptions>,
): Promise<T> {
  return request<T>({ url, method: 'DELETE', ...options })
}
