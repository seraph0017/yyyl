// 一月一露 — Web管理后台 TypeScript 类型定义

// ==================== 通用类型 ====================

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PaginationParams {
  page?: number
  page_size?: number
}

export interface SortParams {
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

// ==================== 认证 ====================

export interface AdminLoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: AdminUserInfo
}

export interface AdminUserInfo {
  id: number
  username: string
  real_name: string
  phone: string
  role: RoleInfo
  status: 'active' | 'disabled'
  last_login_at: string | null
  avatar?: string
}

export interface RoleInfo {
  id: number
  role_name: string
  role_code: 'super_admin' | 'admin' | 'staff'
  description: string
}

export interface TokenPayload {
  sub: string
  role: string
  exp: number
  jti: string
}

// ==================== 商品 ====================

export type ProductCategory = 'campsite' | 'activity' | 'meal' | 'equipment_rental' | 'addon' | 'shop_item' | 'peripheral'

export type ProductStatus = 'active' | 'inactive' | 'draft'

export interface Product {
  id: number
  name: string
  category: ProductCategory
  sub_category: string
  status: ProductStatus
  cover_image: string
  images: string[]
  description: string
  base_price: number
  market_price: number | null
  unit: string
  sort_order: number
  tags: string[]
  require_identity: boolean
  require_disclaimer: boolean
  created_at: string
  updated_at: string
  // 扩展信息
  extension?: ProductExtension
  skus?: ProductSKU[]
  pricing_rules?: PricingRule[]
  discount_rules?: DiscountRule[]
}

export interface ProductExtension {
  capacity?: number
  area?: number
  facilities?: string[]
  check_in_time?: string
  check_out_time?: string
  min_participants?: number
  max_participants?: number
  duration?: string
  deposit_amount?: number
  // ... 更多扩展字段
}

export interface ProductSKU {
  id: number
  product_id: number
  sku_name: string
  sku_code: string
  price: number
  stock: number
  attributes: Record<string, string>
  status: ProductStatus
}

export interface PricingRule {
  id: number
  product_id: number
  date_type: string
  price: number
  start_date: string | null
  end_date: string | null
  specific_dates: string[]
  priority: number
}

export interface DiscountRule {
  id: number
  product_id: number
  name: string
  rule_type: 'consecutive_days' | 'early_bird' | 'group' | 'member'
  conditions: Record<string, any>
  discount_value: number
  discount_type: 'percentage' | 'fixed'
  start_date: string | null
  end_date: string | null
  status: 'active' | 'inactive'
}

export interface ProductCreateRequest {
  name: string
  category: ProductCategory
  sub_category?: string
  status?: ProductStatus
  cover_image: string
  images?: string[]
  description?: string
  base_price: number
  market_price?: number
  unit?: string
  sort_order?: number
  tags?: string[]
  require_identity?: boolean
  require_disclaimer?: boolean
  extension?: Record<string, any>
}

export interface ProductSearchParams extends PaginationParams, SortParams {
  keyword?: string
  category?: ProductCategory
  status?: ProductStatus
}

// ==================== 库存 ====================

export interface Inventory {
  id: number
  product_id: number
  product_name: string
  date: string
  total_stock: number
  locked_stock: number
  sold_stock: number
  available_stock: number
  status: 'open' | 'closed' | 'sold_out'
  date_type: string
  price: number
}

export interface InventoryUpdateRequest {
  total_stock?: number
  status?: 'open' | 'closed'
}

export interface InventoryBatchRequest {
  product_id: number
  start_date: string
  end_date: string
  total_stock: number
}

// ==================== 订单 ====================

export type OrderStatus = 'pending_payment' | 'paid' | 'confirmed' | 'in_use' | 'completed' | 'cancelled' | 'refunding' | 'refunded'
export type PaymentStatus = 'unpaid' | 'paid' | 'refunding' | 'refunded' | 'partial_refunded'

export interface Order {
  id: number
  order_no: string
  user_id: number
  user_nickname: string
  user_phone: string
  status: OrderStatus
  payment_status: PaymentStatus
  payment_method: string
  total_amount: number
  paid_amount: number
  refund_amount: number
  item_count: number
  remark: string | null
  expire_at: string
  paid_at: string | null
  created_at: string
  updated_at: string
  items: OrderItem[]
}

export interface OrderItem {
  id: number
  product_id: number
  product_name: string
  product_category: ProductCategory
  sku_name: string
  quantity: number
  unit_price: number
  actual_price: number
  date: string
  refund_status: 'none' | 'refunding' | 'refunded'
  ticket_code: string | null
  ticket_status: 'unused' | 'used' | 'expired' | 'refunded'
}

export interface OrderSearchParams extends PaginationParams {
  keyword?: string
  status?: OrderStatus
  payment_status?: PaymentStatus
  category?: ProductCategory
  start_date?: string
  end_date?: string
  order_no?: string
}

// ==================== 会员 ====================

export interface MemberInfo {
  id: number
  user_id: number
  nickname: string
  phone: string
  avatar: string
  member_level: 'normal' | 'annual' | 'vip'
  total_spent: number
  order_count: number
  points_balance: number
  registered_at: string
  last_active_at: string | null
  annual_card: AnnualCardInfo | null
  times_cards: TimesCardInfo[]
}

export interface AnnualCardInfo {
  id: number
  config_name: string
  status: 'active' | 'expired' | 'frozen'
  start_date: string
  end_date: string
  total_used_days: number
  daily_limit: number
}

export interface TimesCardInfo {
  id: number
  config_name: string
  status: 'active' | 'expired' | 'exhausted'
  total_times: number
  used_times: number
  remaining_times: number
  expire_date: string
}

export interface AnnualCardConfig {
  id: number
  name: string
  price: number
  duration_days: number
  daily_limit: number
  max_consecutive_days: number
  gap_days: number
  applicable_products: number[]
  status: 'active' | 'inactive'
  description: string
}

export interface TimesCardConfig {
  id: number
  name: string
  total_times: number
  price: number
  validity_days: number
  applicable_products: number[]
  status: 'active' | 'inactive'
  description: string
  consumption_rules?: TimesConsumptionRule[]
}

export interface TimesConsumptionRule {
  id: number
  config_id: number
  product_id: number
  product_name: string
  consume_times: number
}

export interface ActivationCode {
  id: number
  code: string
  batch_no: string
  config_id: number
  config_name: string
  status: 'unused' | 'used' | 'disabled'
  used_by: number | null
  used_at: string | null
  created_at: string
}

export interface PointsExchangeConfig {
  id: number
  name: string
  exchange_type: 'product' | 'coupon' | 'gift'
  required_points: number
  product_id: number | null
  product_name: string | null
  stock: number
  exchanged_count: number
  status: 'active' | 'inactive'
  start_date: string | null
  end_date: string | null
}

export interface MemberSearchParams extends PaginationParams {
  keyword?: string
  member_level?: string
  has_annual_card?: boolean
}

// ==================== 财务 ====================

export interface FinanceOverview {
  pending_amount: number
  withdrawable_amount: number
  deposit_amount: number
  today_income: number
  month_income: number
  month_income_rate: number
  last_month_income: number
}

export interface FinanceTransaction {
  id: number
  transaction_no: string
  type: 'income' | 'refund' | 'withdraw' | 'deposit_refund'
  amount: number
  balance_after: number
  related_order_no: string | null
  description: string
  status: 'pending' | 'confirmed' | 'completed' | 'failed'
  created_at: string
}

export interface TransactionSearchParams extends PaginationParams {
  type?: string
  status?: string
  start_date?: string
  end_date?: string
}

// ==================== Dashboard ====================

export interface RealtimeData {
  today_orders: number
  today_income: number
  current_visitors: number
  stock_alerts: number
  yesterday_orders: number
  yesterday_income: number
  orders_trend: 'up' | 'down' | 'flat'
  income_trend: 'up' | 'down' | 'flat'
}

export interface TrendData {
  dates: string[]
  orders: number[]
  income: number[]
}

export interface SalesRankingItem {
  product_id: number
  product_name: string
  category: ProductCategory
  sales_count: number
  sales_amount: number
  cover_image: string
}

export interface MemberStats {
  total_members: number
  annual_members: number
  times_card_holders: number
  active_members: number
  new_today: number
  new_this_week: number
  new_this_month: number
}

export interface HeatmapItem {
  product_id: number
  product_name: string
  report_date: string
  booking_rate: number
  booked: number
  total: number
}

export interface FinanceSummary {
  pending_amount: number
  withdrawable_amount: number
  deposit_amount: number
  month_income: number
  last_month_income: number
  mom_rate: number
  yoy_rate: number
}

export interface CategoryRevenue {
  category: ProductCategory
  category_name: string
  revenue: number
  percentage: number
  order_count: number
}

// ==================== 系统管理 ====================

export interface StaffMember {
  id: number
  username: string
  real_name: string
  phone: string
  role: RoleInfo
  status: 'active' | 'disabled'
  last_login_at: string | null
  created_at: string
}

export interface Permission {
  id: number
  name: string
  code: string
  module: string
  children?: Permission[]
}

export interface OperationLog {
  id: number
  admin_id: number
  admin_name: string
  action: string
  module: string
  target_type: string
  target_id: number | null
  before_data: Record<string, any> | null
  after_data: Record<string, any> | null
  ip: string
  created_at: string
}

export interface OperationLogSearchParams extends PaginationParams {
  admin_id?: number
  module?: string
  action?: string
  start_date?: string
  end_date?: string
}

// ==================== FAQ ====================

export interface FaqCategory {
  id: number
  name: string
  sort_order: number
  item_count: number
  status: 'active' | 'inactive'
}

export interface FaqItem {
  id: number
  category_id: number
  category_name: string
  question: string
  answer: string
  keywords: string[]
  sort_order: number
  view_count: number
  status: 'active' | 'inactive'
}

// ==================== 页面配置 ====================

export interface PageConfig {
  page_key: string
  page_name: string
  config: Record<string, any>
  updated_at: string
}

// ==================== 通知 ====================

export interface NotificationTemplate {
  id: number
  template_key: string
  name: string
  description: string
  channel: 'wechat' | 'sms' | 'site'
  enabled: boolean
  template_id: string | null
}

export interface NotificationRecord {
  id: number
  user_id: number
  user_nickname: string
  template_key: string
  template_name: string
  channel: string
  status: 'pending' | 'sent' | 'failed'
  send_at: string | null
  created_at: string
}

export interface NotificationStats {
  total_sent: number
  success_rate: number
  template_stats: Array<{
    template_key: string
    template_name: string
    sent_count: number
    success_count: number
    subscriber_count: number
  }>
  send_trends: Array<{
    date: string
    sent: number
    success: number
  }>
}

// ==================== 报表 ====================

export interface SalesReportParams {
  granularity: 'day' | 'week' | 'month'
  start_date: string
  end_date: string
  category?: ProductCategory
}

export interface SalesReportData {
  summary: {
    total_orders: number
    total_income: number
    avg_order_amount: number
    refund_amount: number
    mom_rate: number
    yoy_rate: number
  }
  details: Array<{
    date: string
    orders: number
    income: number
    refund: number
    avg_amount: number
  }>
}

// ==================== 营地日历 ====================

export interface CalendarQuery {
  date_start: string
  date_end: string
  product_ids?: number[]
}

export interface CalendarItem {
  product_id: number
  product_name: string
  date: string
  date_type: string
  price: number
  total_stock: number
  available_stock: number
  booked_stock: number
  status: 'open' | 'closed' | 'sold_out'
}

// ==================== 二次确认 ====================

export interface ConfirmAction {
  action: string
  description: string
  confirm_type: 'code' | 'password'
  code?: string
}
