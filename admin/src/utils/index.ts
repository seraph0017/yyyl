// 某露营地 — 通用工具函数
import dayjs from 'dayjs'

// 格式化价格（分→元）
export function formatPrice(price: number): string {
  return (price / 100).toFixed(2)
}

// 格式化日期
export function formatDate(date: string | Date, format = 'YYYY-MM-DD'): string {
  return dayjs(date).format(format)
}

// 格式化日期时间
export function formatDateTime(date: string | Date): string {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

// 相对时间
export function formatRelativeTime(date: string | Date): string {
  const d = dayjs(date)
  const now = dayjs()
  const diff = now.diff(d, 'minute')
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff}分钟前`
  if (diff < 1440) return `${Math.floor(diff / 60)}小时前`
  if (diff < 43200) return `${Math.floor(diff / 1440)}天前`
  return d.format('YYYY-MM-DD')
}

// 商品品类映射
export const categoryMap: Record<string, string> = {
  campsite: '营位',
  activity: '活动',
  meal: '餐饮',
  equipment_rental: '装备租赁',
  addon: '加人票',
  shop_item: '小商店',
  peripheral: '周边商品',
}

export function getCategoryName(category: string): string {
  return categoryMap[category] || category
}

// 订单状态映射
export const orderStatusMap: Record<string, { label: string; type: string }> = {
  pending_payment: { label: '待支付', type: 'warning' },
  paid: { label: '已支付', type: 'primary' },
  confirmed: { label: '已确认', type: 'success' },
  in_use: { label: '使用中', type: 'primary' },
  completed: { label: '已完成', type: 'info' },
  cancelled: { label: '已取消', type: 'info' },
  refunding: { label: '退款中', type: 'warning' },
  refunded: { label: '已退款', type: 'danger' },
}

// 支付状态映射
export const paymentStatusMap: Record<string, { label: string; type: string }> = {
  unpaid: { label: '未支付', type: 'info' },
  paid: { label: '已支付', type: 'success' },
  refunding: { label: '退款中', type: 'warning' },
  refunded: { label: '已退款', type: 'danger' },
  partial_refunded: { label: '部分退款', type: 'warning' },
}

// 生成随机确认码
export function generateConfirmCode(): string {
  return Math.random().toString(36).substring(2, 8).toUpperCase()
}

// 防抖
export function debounce<T extends (...args: any[]) => any>(fn: T, delay = 300): T {
  let timer: ReturnType<typeof setTimeout>
  return ((...args: any[]) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }) as T
}

// 文件大小格式化
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

// 下载文件
export function downloadFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
