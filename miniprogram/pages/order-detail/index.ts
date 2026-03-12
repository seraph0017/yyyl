// pages/order-detail/index.ts
import { getOrderStatusText } from '../../utils/util';

Page({
  data: {
    order: null as IOrder | null,
    loading: true,
    statusText: '',
    statusSteps: [] as Array<{ label: string; time: string; active: boolean }>,
  },

  onLoad(options) {
    this.loadOrder(options.id || '1');
  },

  async loadOrder(id: string) {
    // Mock
    const order: IOrder = {
      id: Number(id), order_no: 'YY20260310001', status: 'paid',
      total_amount: 256, actual_amount: 256, discount_amount: 40,
      items: [
        { id: 1, product_id: 1, product_name: 'A区阳光营位 · 有电有木平台', cover_image: '', date: '2026-03-15', quantity: 1, unit_price: 168, actual_price: 128, identity_id: 1 },
        { id: 2, product_id: 1, product_name: 'A区阳光营位 · 有电有木平台', cover_image: '', date: '2026-03-16', quantity: 1, unit_price: 168, actual_price: 128, identity_id: 1 },
      ],
      created_at: '2026-03-10T10:30:00', paid_at: '2026-03-10T10:31:00', expired_at: '',
      refund_reason: '', payment_method: 'wechat', shipping_address: null,
    };

    this.setData({
      order,
      statusText: getOrderStatusText(order.status),
      loading: false,
      statusSteps: [
        { label: '提交订单', time: '03-10 10:30', active: true },
        { label: '支付成功', time: '03-10 10:31', active: true },
        { label: '验票入营', time: '', active: false },
        { label: '已完成', time: '', active: false },
      ],
    });
  },

  onViewTicket() {
    wx.navigateTo({ url: `/pages/ticket/index?order_id=${this.data.order?.id}` });
  },

  onRefund() {
    wx.showModal({
      title: '申请退款', content: '确定要申请退款吗？',
      success: (res) => { if (res.confirm) wx.showToast({ title: '退款申请已提交', icon: 'success' }); },
    });
  },

  onContactService() {
    wx.navigateTo({ url: '/pages/customer-service/index' });
  },

  onCopyOrderNo() {
    wx.setClipboardData({ data: this.data.order?.order_no || '' });
  },
});
