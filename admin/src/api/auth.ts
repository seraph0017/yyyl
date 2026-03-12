import { post, get } from '@/utils/request'
import type { AdminLoginRequest, LoginResponse, AdminUserInfo } from '@/types'

export function login(data: AdminLoginRequest) {
  return post<{ data: LoginResponse }>('/auth/admin-login', data)
}

export function refreshToken(refresh_token: string) {
  return post<{ data: LoginResponse }>('/auth/refresh', { refresh_token })
}

export function logout() {
  return post('/auth/logout')
}

export function getMe() {
  return get<{ data: AdminUserInfo }>('/auth/me')
}
