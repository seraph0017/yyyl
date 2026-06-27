function isPlainObject(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

export function extractErrorMessage(payload, fallback = '操作失败') {
  if (typeof payload === 'string') {
    const text = payload.trim()
    return text || fallback
  }

  if (Array.isArray(payload)) {
    const messages = payload
      .map((item) => extractErrorMessage(item, ''))
      .filter(Boolean)
    return messages.join('；') || fallback
  }

  if (isPlainObject(payload)) {
    const record = payload
    const directFields = ['message', 'msg', 'error']

    for (const field of directFields) {
      const value = record[field]
      const text = extractErrorMessage(value, '')
      if (text) return text
    }

    if ('detail' in record) {
      const detailText = extractErrorMessage(record.detail, '')
      if (detailText) return detailText
    }

    if ('errors' in record) {
      const errorText = extractErrorMessage(record.errors, '')
      if (errorText) return errorText
    }
  }

  return fallback
}

export function isAuthEndpoint(url) {
  const path = String(url || '')
  return (
    path.includes('/auth/admin-login')
    || path.includes('/auth/login')
    || path.includes('/auth/phone-login')
    || path.includes('/auth/wechat-login')
    || path.includes('/auth/refresh')
  )
}
