/**
 * 通用工具函数
 */

/**
 * 格式化价格（分→元，保留两位小数）
 */
export function formatPrice(price: number): string {
  return (price / 100).toFixed(2);
}

/**
 * 格式化价格（已是元的数值）
 */
export function formatPriceYuan(price: number): string {
  return price.toFixed(2);
}

/**
 * 格式化日期
 * @param dateStr 日期字符串或时间戳
 * @param format 格式（支持 YYYY-MM-DD HH:mm:ss）
 */
export function formatDate(dateStr: string | number | Date, format: string = 'YYYY-MM-DD'): string {
  const date = new Date(dateStr);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');

  return format
    .replace('YYYY', String(year))
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
}

/**
 * 获取相对时间描述
 */
export function getRelativeTime(dateStr: string): string {
  const now = Date.now();
  const target = new Date(dateStr).getTime();
  const diff = now - target;

  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  if (diff < 2592000000) return `${Math.floor(diff / 86400000)}天前`;
  return formatDate(dateStr, 'MM-DD HH:mm');
}

/**
 * 获取星期几
 */
export function getWeekDay(dateStr: string): string {
  const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  return weekDays[new Date(dateStr).getDay()];
}

/**
 * 获取日期类型标签
 */
export function getDateTypeLabel(type: string): string {
  const map: Record<string, string> = {
    workday: '工作日',
    weekend: '周末',
    holiday: '节假日',
  };
  return map[type] || type;
}

/**
 * 获取订单状态文本
 */
export function getOrderStatusText(status: OrderStatus): string {
  const map: Record<OrderStatus, string> = {
    pending_payment: '待支付',
    paid: '待使用',
    verified: '使用中',
    completed: '已完成',
    cancelled: '已取消',
    refunding: '退款中',
    refunded: '已退款',
  };
  return map[status] || status;
}

/**
 * 获取订单状态颜色
 */
export function getOrderStatusColor(status: OrderStatus): string {
  const map: Record<OrderStatus, string> = {
    pending_payment: '#FF6B35',
    paid: '#2E7D32',
    verified: '#2196F3',
    completed: '#999999',
    cancelled: '#999999',
    refunding: '#FFC107',
    refunded: '#E53935',
  };
  return map[status] || '#999999';
}

/**
 * 品类名称映射
 */
export function getCategoryName(category: ProductCategory): string {
  const map: Record<ProductCategory, string> = {
    daily_camping: '日常露营',
    event_camping: '活动露营',
    equipment_rental: '装备租赁',
    daily_activity: '日常活动',
    special_activity: '特定活动',
    camp_shop: '小商店',
    merchandise: '周边商品',
  };
  return map[category] || category;
}

/**
 * 品类图标映射
 */
export function getCategoryIcon(category: ProductCategory): string {
  const map: Record<ProductCategory, string> = {
    daily_camping: '🏕️',
    event_camping: '🎃',
    equipment_rental: '⛺',
    daily_activity: '🛶',
    special_activity: '🎪',
    camp_shop: '🛒',
    merchandise: '👕',
  };
  return map[category] || '📦';
}

/**
 * 防抖
 */
export function debounce<T extends (...args: unknown[]) => void>(fn: T, delay: number = 300): T {
  let timer: number | null = null;
  return function (this: unknown, ...args: unknown[]) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
      timer = null;
    }, delay) as unknown as number;
  } as T;
}

/**
 * 节流
 */
export function throttle<T extends (...args: unknown[]) => void>(fn: T, interval: number = 300): T {
  let lastTime = 0;
  return function (this: unknown, ...args: unknown[]) {
    const now = Date.now();
    if (now - lastTime >= interval) {
      lastTime = now;
      fn.apply(this, args);
    }
  } as T;
}

/**
 * 校验手机号
 */
export function isValidPhone(phone: string): boolean {
  return /^1[3-9]\d{9}$/.test(phone);
}

/**
 * 校验身份证号
 */
export function isValidIdCard(idCard: string): boolean {
  return /^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[012])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/.test(idCard);
}

/**
 * 脱敏手机号
 */
export function maskPhone(phone: string): string {
  if (!phone || phone.length < 11) return phone;
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
}

/**
 * 脱敏身份证
 */
export function maskIdCard(idCard: string): string {
  if (!idCard || idCard.length < 15) return idCard;
  return idCard.replace(/(\d{4})\d+(\d{4})/, '$1**********$2');
}

/**
 * 生成rpx单位的系统信息
 */
export function getSystemInfoSync(): WechatMiniprogram.SystemInfo {
  return wx.getSystemInfoSync();
}
