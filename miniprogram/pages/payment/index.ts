// pages/payment/index.ts

interface PaymentPageData {
  orderId: string;
  amount: number;
  orderNo: string;
  expiredAt: string;
  paying: boolean;
}

Page<PaymentPageData, WechatMiniprogram.IAnyObject>({
  data: {
    orderId: '',
    amount: 0,
    orderNo: '',
    expiredAt: '',
    paying: false,
  },

  onLoad(options) {
    this.setData({
      orderId: options.order_id || '',
      amount: Number(options.amount || 0),
      orderNo: options.order_no || 'YY20260310001',
      expiredAt: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
    });
  },

  /** 模拟支付成功 */
  onPaySuccess() {
    if (this.data.paying) return;
    this.setData({ paying: true });

    wx.showLoading({ title: '支付处理中...' });

    setTimeout(() => {
      wx.hideLoading();
      this.setData({ paying: false });
      wx.redirectTo({
        url: `/pages/payment-result/index?status=success&order_id=${this.data.orderId}`,
      });
    }, 1500);
  },

  /** 模拟支付失败 */
  onPayFail() {
    if (this.data.paying) return;
    this.setData({ paying: true });

    wx.showLoading({ title: '支付处理中...' });

    setTimeout(() => {
      wx.hideLoading();
      this.setData({ paying: false });
      wx.redirectTo({
        url: `/pages/payment-result/index?status=fail&order_id=${this.data.orderId}`,
      });
    }, 1000);
  },

  /** 取消支付 */
  onCancel() {
    wx.showModal({
      title: '提示',
      content: '确定放弃支付吗？订单将在30分钟后自动取消',
      success: (res) => {
        if (res.confirm) {
          wx.navigateBack();
        }
      },
    });
  },

  /** 倒计时结束 */
  onCountdownFinish() {
    wx.showModal({
      title: '提示',
      content: '支付超时，订单已取消',
      showCancel: false,
      success() {
        wx.navigateBack({ delta: 2 });
      },
    });
  },
});
