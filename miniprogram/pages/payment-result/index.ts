Page({
  data: {
    status: 'success' as 'success' | 'fail',
    orderId: '',
  },

  onLoad(options) {
    this.setData({
      status: (options.status as 'success' | 'fail') || 'success',
      orderId: options.order_id || '',
    });
  },

  onViewOrder() {
    wx.redirectTo({ url: `/pages/order-detail/index?id=${this.data.orderId}` });
  },

  onViewTicket() {
    wx.redirectTo({ url: `/pages/ticket/index?order_id=${this.data.orderId}` });
  },

  onRetryPay() {
    wx.navigateBack();
  },

  onGoHome() {
    wx.switchTab({ url: '/pages/index/index' });
  },
});
