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
  role?: 'user' | 'staff' | 'admin' | 'super_admin' | string
  is_member?: boolean
  member_level?: string
  points_balance?: number
  status?: string
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
  user?: IUserInfo
  user_info?: IUserInfo
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

/** 商品 SKU */
export interface IProductSku {
  id: number
  product_id: number
  sku_code: string
  spec_values: Record<string, string>
  price: number
  stock: number
  status: string
  image_url?: string | null
  inventory_mode?: 'independent' | 'shared_product' | string
  inventory_pool_id?: number | null
  inventory_pool_available?: number | null
}

/** 露营商品扩展 */
export interface IProductCampingExt {
  max_persons?: number | null
  free_child_age?: number | null
  has_electricity?: boolean | null
  has_platform?: boolean | null
  sun_exposure?: string | null
  area?: string | null
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
  ext_camping?: IProductCampingExt | null
  is_seckill: boolean
  has_disclaimer: boolean
  identity_mode: 'required' | 'optional' | 'none'
  deposit_amount: number
  ext_shop?: {
    shipping_required?: boolean
    has_sku?: boolean
    spec_definitions?: Array<Record<string, unknown>> | null
    shop_type?: string
  }
  ext_activity?: {
    booking_unit?: 'person' | 'group' | string
    time_slots?: Array<Record<string, unknown>>
    event_date?: string | null
    meeting_point?: string | null
  }
  skus?: IProductSku[]
}

/** 商品价格/库存日历项 */
export interface IPriceCalendarItem {
  date: string
  date_type: 'weekday' | 'weekend' | 'holiday' | 'custom' | string
  price: number
  available: number
  status: 'open' | 'closed' | string
  inventory_source?: 'inventory' | 'inventory_pool' | 'none' | string
  inventory_pool_id?: number | null
}

/** 购物车项 */
export interface ICartItem {
  id: number
  product_id: number
  sku_id?: number | null
  product_name: string
  cover_image: string
  sku_spec_values?: Record<string, unknown> | null
  price: number
  quantity: number
  selected: boolean
  stock: number
  category: ProductCategory
  shipping_required?: boolean
}

/** 订单状态 */
export type OrderStatus =
  | 'pending_payment'
  | 'paid'
  | 'verified'
  | 'completed'
  | 'cancelled'
  | 'refund_pending'
  | 'refunded'
  | 'partial_refunded'

/** 订单 */
export interface IOrder {
  id: number
  order_no: string
  status: OrderStatus
  order_type?: string
  user_id?: number
  user_nickname?: string | null
  user_phone?: string | null
  user_phone_masked?: string | null
  total_amount: number
  actual_amount: number
  discount_amount: number
  items: IOrderItem[]
  created_at: string
  payment_time?: string | null
  expire_at?: string | null
  refund_reason?: string | null
  payment_method?: string
  remark?: string | null
  shipping_address?: IAddress | null
}

/** 订单项 */
export interface IOrderItem {
  id: number
  product_id: number
  product_name: string
  cover_image?: string | null
  product_category?: ProductCategory | string
  sku_id?: number | null
  sku_name?: string | null
  sku_spec_values?: Record<string, unknown> | null
  date?: string | null
  time_slot?: string | null
  quantity: number
  unit_price: number
  actual_price: number
  identity_id: number | null
  inventory_pool_id?: number | null
  product_image?: string | null
  remark?: string | null
}

/** 订单报价项 */
export interface IOrderQuoteItem {
  product_id: number
  sku_id?: number | null
  product_name: string
  date?: string | null
  quantity: number
  unit_price: number
  actual_price: number
  inventory_source: 'inventory' | 'inventory_pool' | 'none' | string
  inventory_pool_id?: number | null
  available?: number | null
}

/** 订单报价响应 */
export interface IOrderQuoteResponse {
  items: IOrderQuoteItem[]
  total_amount: number
  discount_amount: number
  actual_amount: number
  deposit_amount: number
  discount_type?: string | null
  discount_detail?: Record<string, unknown> | null
  has_shared_inventory: boolean
}

/** 智能客服回答来源 */
export interface ICustomerServiceSource {
  id: number
  title: string
  source_type: 'manual' | 'faq' | 'txt' | 'md' | 'pdf' | 'docx' | string
  source_name?: string | null
}

/** 智能客服问答响应 */
export interface ICustomerServiceAskResult {
  answer: string
  sources: ICustomerServiceSource[]
  matched_article_ids: number[]
  confidence: number
  needs_human: boolean
  log_id: number
  feedback_token: string
}

/** 地址 */
export interface IAddress {
  id: number
  contact_name: string
  contact_phone: string
  province: string
  city: string
  district: string
  detail: string
  is_default: boolean
}

export interface IAddressFormPayload {
  address_id?: number
  contact_name?: string
  contact_phone?: string
  province?: string
  city?: string
  district?: string
  detail?: string
  is_default?: boolean
}

/** 身份信息 */
export interface IIdentity {
  id: number
  name: string
  /** 新增/编辑时为完整身份证；列表接口通常只返回脱敏值 */
  id_card?: string | null
  /** 后端列表接口返回的脱敏身份证号 */
  id_card_masked?: string | null
  /** 后端列表接口返回的手机号可能已脱敏 */
  phone?: string | null
  custom_fields?: Record<string, string>
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
  qr_token?: string
  qrcode_token: string
  qr_token_expires_at?: string | null
  qr_matrix?: boolean[][]
  verified_at: string | null
}

/** 员工端待核销票券 */
export interface IStaffPendingTicket {
  ticket_id: number
  ticket_no: string
  ticket_type: string
  order_id: number
  order_no: string
  order_item_id?: number | null
  user_id: number
  user_nickname?: string | null
  user_phone_masked?: string | null
  product_name?: string | null
  quantity: number
  date?: string | null
  time_slot?: string | null
  verify_date?: string | null
  verify_status: string
  current_verify_count: number
  total_verify_count: number
  can_verify: boolean
  actual_amount: number
  remark?: string | null
}

/** 员工端今日订单行 */
export interface IStaffTodayOrder {
  order_id: number
  order_no: string
  status: string
  payment_status: string
  payment_time?: string | null
  actual_amount: number
  user_id: number
  user_nickname?: string | null
  user_phone_masked?: string | null
  order_item_id: number
  product_id: number
  product_name?: string | null
  quantity: number
  date?: string | null
  time_slot?: string | null
  verify_status: string
  ticket_id?: number | null
  ticket_no?: string | null
  can_verify: boolean
  remark?: string | null
}

/** 员工端核销历史 */
export interface IStaffTicketLog {
  id: number
  ticket_id?: number | null
  ticket_no?: string | null
  order_id?: number | null
  order_no?: string | null
  order_item_id?: number | null
  product_name?: string | null
  verify_date?: string | null
  quantity?: number | null
  time_slot?: string | null
  user_nickname?: string | null
  user_phone_masked?: string | null
  staff_id: number
  verify_result: 'success' | 'failed' | 'duplicate' | string
  failure_reason?: string | null
  device_info?: string | null
  remark?: string | null
  created_at: string
}

export interface IStaffTicketSummary {
  ticket_id: number
  ticket_no: string
  ticket_type: string
  verify_status: string
  verify_date?: string | null
  verified_at?: string | null
  verified_by?: number | null
  current_verify_count: number
  total_verify_count: number
  can_verify: boolean
}

export interface IStaffOrderItem {
  order_item_id: number
  product_id: number
  sku_id?: number | null
  product_name?: string | null
  product_image?: string | null
  quantity: number
  date?: string | null
  time_slot?: string | null
  unit_price: number
  actual_price: number
  tickets: IStaffTicketSummary[]
}

/** 员工端订单详情 */
export interface IStaffOrderDetail {
  order_id: number
  order_no: string
  user_id: number
  user_nickname?: string | null
  user_phone_masked?: string | null
  status: string
  payment_status: string
  payment_method: string
  payment_time?: string | null
  total_amount: number
  actual_amount: number
  discount_amount: number
  remark?: string | null
  created_at: string
  items: IStaffOrderItem[]
}

/** 员工扫码核销响应 */
export interface IStaffScanResponse {
  session_id: string
  ticket_id: number
  ticket_no: string
  ticket_type: string
  product_name?: string | null
  verify_date?: string | null
  needs_verification_code: boolean
  verification_code?: string | null
}

export interface ITemporaryOrderCreatePayload {
  payment_flow: 'customer_scan_qr' | 'merchant_scan_code'
  mode?: 'custom_amount' | 'product'
  product_id?: number
  sku_id?: number
  quantity: number
  booking_date?: string
  time_slot?: string
  item_name?: string
  amount?: number
  remark?: string
  auth_code?: string
  device_id?: string
}

export interface ITemporaryOrderSession {
  id: number
  session_no: string
  token?: string | null
  status: string
  payment_flow: 'customer_scan_qr' | 'merchant_scan_code'
  mode: 'custom_amount' | 'product'
  product_id?: number | null
  sku_id?: number | null
  quantity: number
  booking_date?: string | null
  time_slot?: string | null
  item_name?: string | null
  amount?: number | string | null
  remark?: string | null
  order_id?: number | null
  expire_at: string
  miniapp_path?: string | null
  qrcode_image_url?: string | null
}

export interface ITemporaryOrderCodePayResult {
  session: ITemporaryOrderSession
  order: IOrder
  trade_state?: string | null
  transaction_id?: string | null
  requires_query?: boolean
}

export type ITemporaryOrderCreateResult = ITemporaryOrderSession | ITemporaryOrderCodePayResult

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

/** 统一会员卡 */
export interface IMembershipCard {
  card_type: 'annual' | 'times'
  card_type_label: string
  usage_mode: 'unlimited' | 'limited'
  usage_mode_label: string
  status: 'active' | 'expired' | 'cancelled' | 'inactive'
  status_label: string
  start_date: string
  end_date: string
  valid_range_label: string
  remaining_days: number | null
  remaining_days_label: string
  remaining_times: number | null
  remaining_times_label: string
  applicable_products: Array<string | number>
  applicable_products_label: string
  activation_mode: 'code' | 'auto'
}

/** 旧会员接口聚合响应 */
export interface IMembershipCardLegacyResponse {
  current_card: IAnnualCard | null
  times_cards?: ITimesCard[]
}

/** 统一会员卡接口响应 */
export type IMembershipCardApiResponse = IMembershipCard | IMembershipCardLegacyResponse

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
  location_name?: string
  temperature: number
  weather: string
  wind: string
  humidity: number
  sunrise: string
  sunset: string
  icon: string
  description: string
  hourly_forecasts?: IWeatherHourlyForecast[]
  updated_at?: number
}

export interface IWeatherHourlyForecast {
  datetime: string
  time: string
  temperature: number
  weather: string
  icon: string
  precipitation: number
  precipitation_probability: number
}

export interface IWeatherForecast {
  date: string
  temperature_min: number
  temperature_max: number
  weather: string
  icon: string
  precipitation_probability?: number
}

export interface IWeatherForecastResponse {
  location_name?: string
  forecasts: IWeatherForecast[]
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
  sort_order?: number
  link_type?: 'product' | 'cms' | 'h5' | null
  link_target?: string | null
  link_label?: string | null
  click_count?: number
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
