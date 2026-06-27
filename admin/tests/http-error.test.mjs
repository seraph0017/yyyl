import test from 'node:test'
import assert from 'node:assert/strict'

import { extractErrorMessage, isAuthEndpoint } from '../src/utils/http-error.js'

test('extractErrorMessage reads FastAPI detail.message for login failures', () => {
  const payload = {
    detail: {
      code: 40101,
      message: '用户名或密码错误',
    },
  }

  assert.equal(extractErrorMessage(payload, '请求失败 (401)'), '用户名或密码错误')
})

test('extractErrorMessage keeps network fallback for empty payloads', () => {
  assert.equal(extractErrorMessage(null, '请求失败 (500)'), '请求失败 (500)')
})

test('isAuthEndpoint skips token refresh for login and refresh requests', () => {
  assert.equal(isAuthEndpoint('/auth/admin-login'), true)
  assert.equal(isAuthEndpoint('/api/v1/auth/refresh'), true)
  assert.equal(isAuthEndpoint('/orders'), false)
})
