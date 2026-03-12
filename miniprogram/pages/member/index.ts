// pages/member/index.ts
Page({
  data: {
    tabs: [
      { key: 'annual', name: '年卡' },
      { key: 'times', name: '次数卡' },
      { key: 'points', name: '积分' },
    ],
    activeTab: 0,
    annualCard: null as IAnnualCard | null,
    timesCards: [] as ITimesCard[],
    points: 1280,
    activateCode: '',
  },

  onLoad(options) {
    if (options.tab) {
      const idx = this.data.tabs.findIndex(t => t.key === options.tab);
      if (idx >= 0) this.setData({ activeTab: idx });
    }
    this.loadData();
  },

  loadData() {
    // Mock
    this.setData({
      annualCard: {
        id: 1, status: 'active', start_date: '2026-01-01', end_date: '2027-01-01',
        remaining_days: 295,
        benefits: [
          { product_name: 'A区营位', total_times: null, used_times: 12 },
          { product_name: 'B区营位', total_times: 6, used_times: 2 },
        ],
      },
      timesCards: [
        { id: 1, name: '体验次数卡', total_times: 10, remaining_times: 7, start_date: '2026-01-01', end_date: '2026-12-31', status: 'active', applicable_products: [1, 2] },
      ],
    });
  },

  onTabChange(e: WechatMiniprogram.TouchEvent) {
    this.setData({ activeTab: e.currentTarget.dataset.index as number });
  },

  onActivateInput(e: WechatMiniprogram.Input) {
    this.setData({ activateCode: e.detail.value });
  },

  onActivateCard() {
    if (!this.data.activateCode.trim()) {
      wx.showToast({ title: '请输入激活码', icon: 'none' });
      return;
    }
    wx.showToast({ title: '激活成功！', icon: 'success' });
    this.setData({ activateCode: '' });
  },
});
