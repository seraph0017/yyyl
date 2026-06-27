/**
 * 页面浏览埋点工具
 */

import { post } from '@/utils/request'

export async function recordPageView(pageKey: string, pageTitle?: string): Promise<void> {
  try {
    await post(
      '/analytics/page-view',
      { page_key: pageKey, page_title: pageTitle },
      { needAuth: false, showError: false },
    )
  } catch {
    // 埋点失败不影响页面主流程。
  }
}
