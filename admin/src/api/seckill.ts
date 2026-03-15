// 秒杀监控 API
import { get } from '@/utils/request'
import type { SeckillMonitorData } from '@/types'

export function getSeckillMonitor(productId: number) {
  return get<{ code: number; data: SeckillMonitorData }>(`/admin/seckill/monitor/${productId}`)
}

export function getSeckillReport(productId: number) {
  return get<{ code: number; data: object }>(`/admin/seckill/report/${productId}`)
}
