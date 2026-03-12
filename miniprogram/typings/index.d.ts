/// <reference path="./wx/index.d.ts" />

/** 全局App实例接口 */
interface IAppOption {
  globalData: {
    userInfo: IUserInfo | null;
    token: string;
    refreshToken: string;
    isLoggedIn: boolean;
    systemInfo: WechatMiniprogram.SystemInfo | null;
    statusBarHeight: number;
    navBarHeight: number;
    isStaff: boolean;
  };
  checkLogin(): Promise<boolean>;
  login(): Promise<ILoginResult>;
  logout(): void;
}

/** 用户信息 */
interface IUserInfo {
  id: number;
  nickname: string;
  avatar_url: string;
  phone: string;
  is_annual_member: boolean;
  annual_card_expire_date: string;
  points: number;
  is_staff: boolean;
  staff_role: string;
}

/** 登录结果 */
interface ILoginResult {
  access_token: string;
  refresh_token: string;
  user: IUserInfo;
}

/** API通用响应 */
interface IApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

/** 分页请求 */
interface IPaginationParams {
  page: number;
  page_size: number;
}

/** 分页响应 */
interface IPaginationResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** 商品接口 */
interface IProduct {
  id: number;
  name: string;
  category: ProductCategory;
  description: string;
  cover_image: string;
  images: string[];
  base_price: number;
  current_price: number;
  original_price: number;
  status: 'on_sale' | 'off_sale';
  tags: string[];
  attributes: IProductAttribute[];
  stock: number;
  sales_count: number;
  ticket_start_time: string | null;
  is_seckill: boolean;
  has_disclaimer: boolean;
  identity_mode: 'required' | 'optional' | 'none';
  deposit_amount: number;
}

/** 商品属性 */
interface IProductAttribute {
  key: string;
  label: string;
  value: string;
  icon: string;
}

/** 商品品类枚举 */
type ProductCategory =
  | 'daily_camping'    // 日常露营
  | 'event_camping'    // 活动露营
  | 'equipment_rental' // 装备租赁
  | 'daily_activity'   // 日常活动
  | 'special_activity' // 特定活动
  | 'camp_shop'        // 营地小商店
  | 'merchandise';     // 周边商品

/** 购物车项 */
interface ICartItem {
  id: number;
  product_id: number;
  product_name: string;
  cover_image: string;
  price: number;
  quantity: number;
  selected: boolean;
  stock: number;
  category: ProductCategory;
}

/** 订单 */
interface IOrder {
  id: number;
  order_no: string;
  status: OrderStatus;
  total_amount: number;
  actual_amount: number;
  discount_amount: number;
  items: IOrderItem[];
  created_at: string;
  paid_at: string | null;
  expired_at: string;
  refund_reason: string;
  payment_method: string;
  shipping_address: IAddress | null;
}

/** 订单项 */
interface IOrderItem {
  id: number;
  product_id: number;
  product_name: string;
  cover_image: string;
  date: string;
  quantity: number;
  unit_price: number;
  actual_price: number;
  identity_id: number | null;
}

/** 订单状态 */
type OrderStatus =
  | 'pending_payment'  // 待支付
  | 'paid'             // 已支付/待使用
  | 'verified'         // 已验票/使用中
  | 'completed'        // 已完成
  | 'cancelled'        // 已取消
  | 'refunding'        // 退款中
  | 'refunded';        // 已退款

/** 地址 */
interface IAddress {
  id: number;
  name: string;
  phone: string;
  province: string;
  city: string;
  district: string;
  detail: string;
  is_default: boolean;
}

/** 身份信息 */
interface IIdentity {
  id: number;
  name: string;
  id_card: string;
  phone: string;
  custom_fields: Record<string, string>;
  is_default: boolean;
}

/** 电子票 */
interface ITicket {
  id: number;
  ticket_no: string;
  order_id: number;
  product_name: string;
  date: string;
  status: 'unused' | 'used' | 'expired' | 'refunded';
  qrcode_token: string;
  verified_at: string | null;
}

/** 年卡 */
interface IAnnualCard {
  id: number;
  status: 'active' | 'expired' | 'cancelled';
  start_date: string;
  end_date: string;
  remaining_days: number;
  benefits: IAnnualCardBenefit[];
}

interface IAnnualCardBenefit {
  product_name: string;
  total_times: number | null;
  used_times: number;
}

/** 次数卡 */
interface ITimesCard {
  id: number;
  name: string;
  total_times: number;
  remaining_times: number;
  start_date: string;
  end_date: string;
  status: 'active' | 'expired';
  applicable_products: number[];
}

/** 通知 */
interface INotification {
  id: number;
  title: string;
  content: string;
  type: string;
  is_read: boolean;
  created_at: string;
}

/** FAQ */
interface IFaqCategory {
  id: number;
  name: string;
  icon: string;
  items: IFaqItem[];
}

interface IFaqItem {
  id: number;
  question: string;
  answer: string;
  view_count: number;
}

/** 日历日期价格 */
interface IDatePrice {
  date: string;
  price: number;
  date_type: 'workday' | 'weekend' | 'holiday';
  stock: number;
  is_available: boolean;
}
