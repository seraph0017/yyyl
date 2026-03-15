// H5 游戏管理 API
import { get, post, put, del } from '@/utils/request'
import type { MiniGame, MiniGameCreate } from '@/types'

/** 游戏列表（分页） */
export function getGames(params: object) {
  return get<{ code: number; data: { list: MiniGame[]; pagination: { total: number } } }>('/admin/games', params)
}

/** 创建游戏 */
export function createGame(data: MiniGameCreate) {
  return post<{ code: number; data: MiniGame }>('/admin/games', data)
}

/** 更新游戏 */
export function updateGame(id: number, data: Partial<MiniGameCreate>) {
  return put<{ code: number; data: MiniGame }>(`/admin/games/${id}`, data)
}

/** 删除游戏 */
export function deleteGame(id: number) {
  return del(`/admin/games/${id}`)
}
