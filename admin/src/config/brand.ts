/**
 * 品牌配置
 * 所有 UI 展示用的品牌名集中在此管理
 * 修改品牌名只需改此文件
 */

export const brandConfig = {
  /** 品牌名称 */
  name: '一月一露',
  /** 管理后台标题后缀 */
  adminTitle: '露营地管理后台',
  /** 浏览器标签页完整标题 */
  get fullTitle() {
    return `${this.name} - ${this.adminTitle}`
  },
}

export default brandConfig
