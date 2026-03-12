Page({
  data: {
    todayStats: { orders: 12, revenue: 3680, visitors: 8, alerts: 1 },
    menus: [
      { key: 'scan', name: '扫码验票', icon: '📷', desc: '扫描用户电子票二维码' },
      { key: 'orders', name: '查看订单', icon: '📋', desc: '查看今日订单列表' },
      { key: 'stock', name: '库存查看', icon: '📦', desc: '查看当前库存状态' },
    ],
    verifyCode: '',
    showVerifyResult: false,
    verifyResult: null as Record<string, string> | null,
  },

  onScanVerify() {
    wx.scanCode({
      onlyFromCamera: true,
      success: (res) => {
        console.log('扫码结果:', res.result);
        // Mock验票结果
        this.setData({
          showVerifyResult: true,
          verifyResult: {
            status: 'success',
            name: '张三',
            product: 'A区阳光营位',
            date: '2026-03-15',
            isMember: 'true',
          },
          verifyCode: String(Math.floor(100000 + Math.random() * 900000)),
        });
      },
      fail: () => {
        wx.showToast({ title: '扫码取消', icon: 'none' });
      },
    });
  },

  onMenuTap(e: WechatMiniprogram.TouchEvent) {
    const key = e.currentTarget.dataset.key as string;
    if (key === 'scan') {
      this.onScanVerify();
    } else {
      wx.showToast({ title: '功能开发中', icon: 'none' });
    }
  },

  onCloseResult() {
    this.setData({ showVerifyResult: false, verifyResult: null, verifyCode: '' });
  },
});
