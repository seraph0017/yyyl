// pages/order/index.ts
import { getOrderStatusText, getOrderStatusColor } from '../../utils/util';

interface OrderPageData {
  tabs: IOrderTab[];
  activeTab: number;
  orders: IOrder[];
  loading: boolean;
  page: number;
  hasMore: boolean;
  statusTextMap: Record<string, string>;
  statusColorMap: Record<string, string>;
}

interface IOrderTab {
  key: string;
  name: string;
  status: OrderStatus | '';
}

Page<OrderPageData, WechatMiniprogram.IAnyObject>({
  data: {
    tabs: [
      { key: 'all', name: '全部', status: '' },
      { key: 'pending', name: '待支付', status: 'pending_payment' },
      { key: 'paid', name: '待使用', status: 'paid' },
      { key: 'completed', name: '已完成', status: 'completed' },
      { key: 'refund', name: '退款', status: 'refunding' },
    ],
    activeTab: 0,
    orders: [],
    loading: true,
    page: 1,
    hasMore: true,
    statusTextMap: {
      pending_payment: '待支付',
      paid: '待使用',
      verified: '使用中',
      completed: '已完成',
      cancelled: '已取消',
      refunding: '退款中',
      refunded: '已退款',
    },
    statusColorMap: {
      pending_payment: '#FF6B35',
      paid: '#2E7D32',
      verified: '#2196F3',
      completed: '#999999',
      cancelled: '#999999',
      refunding: '#FFC107',
      refunded: '#E53935',
    },
  },

  onLoad(options) {
    if (options.tab) {
      const tabIndex = this.data.tabs.findIndex(t => t.key === options.tab);
      if (tabIndex >= 0) {
        this.setData({ activeTab: tabIndex });
      }
    }
    this.loadOrders();
  },

  onShow() {
    // 每次显示刷新
    this.loadOrders();
  },

  onPullDownRefresh() {
    this.setData({ page: 1, hasMore: true });
    this.loadOrders().then(() => wx.stopPullDownRefresh());
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 });
      this.loadOrders();
    }
  },

  /** 切换Tab */
  onTabChange(e: WechatMiniprogram.TouchEvent) {
    const index = e.currentTarget.dataset.index as number;
    this.setData({ activeTab: index, page: 1, hasMore: true, orders: [] });
    this.loadOrders();
  },

  /** 加载订单 */
  async loadOrders() {
    this.setData({ loading: true });

    // Mock订单数据
    const mockOrders: IOrder[] = [
      {
        id: 1, order_no: 'YY20260310001',
        status: 'paid',
        total_amount: 296, actual_amount: 256, discount_amount: 40,
        items: [
          { id: 1, product_id: 1, product_name: 'A区阳光营位 · 有电有木平台', cover_image: '', date: '2026-03-15', quantity: 1, unit_price: 168, actual_price: 128, identity_id: 1 },
          { id: 2, product_id: 1, product_name: 'A区阳光营位 · 有电有木平台', cover_image: '', date: '2026-03-16', quantity: 1, unit_price: 168, actual_price: 128, identity_id: 1 },
        ],
        created_at: '2026-03-10T10:30:00', paid_at: '2026-03-10T10:31:00', expired_at: '',
        refund_reason: '', payment_method: 'wechat', shipping_address: null,
      },
      {
        id: 2, order_no: 'YY20260309002',
        status: 'pending_payment',
        total_amount: 78, actual_amount: 78, discount_amount: 0,
        items: [
          { id: 3, product_id: 5, product_name: '皮划艇体验 · 单人艇', cover_image: '', date: '2026-03-20', quantity: 1, unit_price: 78, actual_price: 78, identity_id: null },
        ],
        created_at: '2026-03-09T18:00:00', paid_at: null, expired_at: '2026-03-09T18:30:00',
        refund_reason: '', payment_method: '', shipping_address: null,
      },
      {
        id: 3, order_no: 'YY20260305003',
        status: 'completed',
        total_amount: 50, actual_amount: 50, discount_amount: 0,
        items: [
          { id: 4, product_id: 6, product_name: '营地柴火 · 一捆', cover_image: '', date: '', quantity: 2, unit_price: 25, actual_price: 25, identity_id: null },
        ],
        created_at: '2026-03-05T14:20:00', paid_at: '2026-03-05T14:21:00', expired_at: '',
        refund_reason: '', payment_method: 'wechat', shipping_address: null,
      },
    ];

    setTimeout(() => {
      this.setData({
        orders: this.data.page === 1 ? mockOrders : [...this.data.orders, ...mockOrders],
        loading: false,
        hasMore: false,
      });
    }, 300);
  },

  /** 点击订单 */
  onOrderTap(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/order-detail/index?id=${id}` });
  },

  /** 去支付 */
  onPay(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/payment/index?order_id=${id}` });
  },

  /** 取消订单 */
  onCancel(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset;
    wx.showModal({
      title: '提示',
      content: '确定取消该订单吗？',
      success: (res) => {
        if (res.confirm) {
          wx.showToast({ title: '订单已取消', icon: 'success' });
          this.loadOrders();
        }
      },
    });
  },

  /** 查看电子票 */
  onViewTicket(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/ticket/index?order_id=${id}` });
  },

  /** 申请退款 */
  onRefund(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset;
    wx.showModal({
      title: '申请退款',
      content: '确定要申请退款吗？退款将原路返回',
      success: (res) => {
        if (res.confirm) {
          wx.showToast({ title: '退款申请已提交', icon: 'success' });
        }
      },
    });
  },

  getStatusText(status: OrderStatus): string {
    return getOrderStatusText(status);
  },

  getStatusColor(status: OrderStatus): string {
    return getOrderStatusColor(status);
  },
});
