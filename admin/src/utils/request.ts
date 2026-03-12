// 某露营地 — HTTP 请求封装
import axios, { type AxiosRequestConfig, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import router from '@/router'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const service = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token管理
const getToken = () => localStorage.getItem('access_token')
const getRefreshToken = () => localStorage.getItem('refresh_token')
const setToken = (access: string, refresh: string) => {
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}
const clearToken = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user_info')
}

// Token刷新控制
let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

function onTokenRefreshed(newToken: string) {
  refreshSubscribers.forEach(cb => cb(newToken))
  refreshSubscribers = []
}

// 请求拦截器
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // CSRF Token
    const csrfToken = localStorage.getItem('csrf_token')
    if (csrfToken && config.method !== 'get') {
      config.headers['X-Request-Token'] = csrfToken
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
service.interceptors.response.use(
  (response: AxiosResponse) => {
    const { data } = response

    // 如果直接返回数据（比如文件下载）
    if (response.config.responseType === 'blob') {
      return response
    }

    // 业务code检查
    if (data.code !== undefined && data.code !== 0 && data.code !== 200) {
      ElMessage.error(data.message || '操作失败')
      return Promise.reject(new Error(data.message || '操作失败'))
    }

    return data
  },
  async (error) => {
    const { response, config } = error

    if (!response) {
      ElMessage.error('网络异常，请检查网络连接')
      return Promise.reject(error)
    }

    // 401: Token过期，尝试刷新
    if (response.status === 401 && !config._isRetry) {
      if (!isRefreshing) {
        isRefreshing = true
        try {
          const refreshToken = getRefreshToken()
          if (!refreshToken) throw new Error('no refresh token')

          const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const newToken = data.data?.access_token || data.access_token
          const newRefresh = data.data?.refresh_token || data.refresh_token
          setToken(newToken, newRefresh)
          onTokenRefreshed(newToken)
          isRefreshing = false

          // 重试原请求
          config._isRetry = true
          config.headers.Authorization = `Bearer ${newToken}`
          return service(config)
        } catch {
          isRefreshing = false
          refreshSubscribers = []
          clearToken()
          ElMessageBox.confirm('登录已过期，请重新登录', '提示', {
            confirmButtonText: '重新登录',
            cancelButtonText: '取消',
            type: 'warning',
          }).then(() => {
            router.push('/login')
          })
          return Promise.reject(error)
        }
      } else {
        // 等待Token刷新
        return new Promise((resolve) => {
          subscribeTokenRefresh((newToken: string) => {
            config._isRetry = true
            config.headers.Authorization = `Bearer ${newToken}`
            resolve(service(config))
          })
        })
      }
    }

    // 403: 权限不足
    if (response.status === 403) {
      ElMessage.error('权限不足，无法执行此操作')
      return Promise.reject(error)
    }

    // 其他错误
    const message = response.data?.message || response.data?.detail || `请求失败 (${response.status})`
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// 导出请求方法
export function get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
  return service.get(url, { params, ...config }) as Promise<T>
}

export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return service.post(url, data, config) as Promise<T>
}

export function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return service.put(url, data, config) as Promise<T>
}

export function del<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return service.delete(url, config) as Promise<T>
}

export { setToken, clearToken, getToken }
export default service
