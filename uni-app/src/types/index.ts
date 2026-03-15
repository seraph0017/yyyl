/**
 * 全局类型定义
 * 从微信原生 typings/index.d.ts 迁移而来
 */

/** 用户信息 */
export interface IUserInfo {
  id: number
  nickname: string
  avatar_url: string
  phone: string
  is_annual_member: boolean
  annual_card_expire_date: string
  points: number
  is_staff: boolean
  staff_role: string
}

/** 登录结果 */
export interface ILoginResult {
  access_token: string
  refresh_token: string
  user: IUserInfo
}

/** API通用响应 */
export interface IApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

/** 分页请求 */
export interface IPaginationParams {
  page: number
  page_size: number
}

/** 分页响应 */
export interface IPaginationResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/** 商品品类枚举 */
export type ProductCategory =
  | 'daily_camping'
  | 'event_camping'
  | 'equipment_rental'
  | 'daily_activity'
  | 'special_activity'
  | 'camp_shop'
  | 'merchandise'

/** 商品属性 */
export interface IProductAttribute {
  key: string
  label: string
  value: string
  icon: string
}

/** 商品 */
export interface IProduct {
  id: number
  name: string
  category: ProductCategory
  description: string
  cover_image: string
  images: string[]
  base_price: number
  current_price: number
  original_price: number
  status: 'on_sale' | 'off_sale'
  tags: string[]
  attributes: IProductAttribute[]
  stock: number
  sales_count: number
  ticket_start_time: string | null
  is_seckill: boolean
  has_disclaimer: boolean
  identity_mode: 'required' | 'optional' | 'none'
  deposit_amount: number
}

/** 购物车项 */
export interface ICartItem {
  id: number
  product_id: number
  product_name: string
  cover_image: string
  price: number
  quantity: number
  selected: boolean
  stock: number
  category: ProductCategory
}

/** 订单状态 */
export type OrderStatus =
  | 'pending_payment'
  | 'paid'
  | 'verified'
  | 'completed'
  | 'cancelled'
  | 'refunding'
  | 'refunded'

/** 订单 */
export interface IOrder {
  id: number
  order_no: string
  status: OrderStatus
  total_amount: number
  actual_amount: number
  discount_amount: number
  items: IOrderItem[]
  created_at: string
  paid_at: string | null
  expired_at: string
  refund_reason: string
  payment_method: string
  shipping_address: IAddress | null
}

/** 订单项 */
export interface IOrderItem {
  id: number
  product_id: number
  product_name: string
  cover_image: string
  date: string
  quantity: number
  unit_price: number
  actual_price: number
  identity_id: number | null
}

/** 地址 */
export interface IAddress {
  id: number
  name: string
  phone: string
  province: string
  city: string
  district: string
  detail: string
  is_default: boolean
}

/** 身份信息 */
export interface IIdentity {
  id: number
  name: string
  id_card: string
  phone: string
  custom_fields: Record<string, string>
  is_default: boolean
}

/** 电子票 */
export interface ITicket {
  id: number
  ticket_no: string
  order_id: number
  product_name: string
  date: string
  status: 'unused' | 'used' | 'expired' | 'refunded'
  qrcode_token: string
  verified_at: string | null
}

/** 年卡 */
export interface IAnnualCard {
  id: number
  status: 'active' | 'expired' | 'cancelled'
  start_date: string
  end_date: string
  remaining_days: number
  benefits: IAnnualCardBenefit[]
}

export interface IAnnualCardBenefit {
  product_name: string
  total_times: number | null
  used_times: number
}

/** 次数卡 */
export interface ITimesCard {
  id: number
  name: string
  total_times: number
  remaining_times: number
  start_date: string
  end_date: string
  status: 'active' | 'expired'
  applicable_products: number[]
}

/** 通知 */
export interface INotification {
  id: number
  title: string
  content: string
  type: string
  is_read: boolean
  created_at: string
}

/** FAQ */
export interface IFaqCategory {
  id: number
  name: string
  icon: string
  items: IFaqItem[]
}

export interface IFaqItem {
  id: number
  question: string
  answer: string
  view_count: number
}

/** 日历日期价格 */
export interface IDatePrice {
  date: string
  price: number
  date_type: 'workday' | 'weekend' | 'holiday'
  stock: number
  is_available: boolean
}

/** Banner */
export interface IBanner {
  id: number
  image: string
  title: string
  link: string
  color: string
}

/** ===== v1.5 新增类型 ===== */

/** 天气信息 */
export interface IWeatherCurrent {
  temperature: number
  weather: string
  wind: string
  humidity: number
  sunrise: string
  sunset: string
  icon: string
  description: string
}

export interface IWeatherForecast {
  date: string
  temperature_min: number
  temperature_max: number
  weather: string
  icon: string
}

/** 搭配售卖 */
export interface IBundleItem {
  product_id: number
  product_name: string
  product_image: string
  original_price: number
  bundle_price: number
  max_quantity: number
  is_default_checked: boolean
}

export interface IBundleConfig {
  id: number
  main_product_id: number
  name: string
  items: IBundleItem[]
}

/** 秒杀预填 */
export interface ISeckillPrefill {
  product_id: number
  identity_ids: number[]
  phone: string
  disclaimer_signed: boolean
  bundle_items: { product_id: number; quantity: number }[]
  saved_at: string
}

export interface ISeckillStatus {
  product_id: number
  remaining_stock: number
  online_count: number
  status: 'warmup' | 'active' | 'ended' | 'sold_out'
}

/** 营地地图 */
export interface ICampMap {
  id: number
  name: string
  map_image: string
  map_type: string
  zones: ICampMapZone[]
}

export interface ICampMapZone {
  id: number
  zone_name: string
  zone_code: string
  coordinates: { x: number; y: number; width: number; height: number }
  product_ids: number[]
  description: string
  available_count?: number
  total_count?: number
}

/** H5小游戏 */
export interface IMiniGame {
  id: number
  name: string
  cover_image: string
  game_url: string
  description: string
  points_reward: number
}

/** 订单项扩展（搭配字段） */
export interface IOrderItemBundle {
  bundle_group_id: string | null
  bundle_config_id: number | null
  is_bundle_item: boolean
}
