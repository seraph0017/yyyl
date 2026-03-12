// pages/customer-service/index.ts
Page({
  data: {
    searchKeyword: '',
    categories: [
      { id: 1, name: '预定问题', icon: '🏕️' },
      { id: 2, name: '退票退款', icon: '↩️' },
      { id: 3, name: '营位介绍', icon: '⛺' },
      { id: 4, name: '交通路线', icon: '🚗' },
      { id: 5, name: '装备租赁', icon: '🎒' },
      { id: 6, name: '活动咨询', icon: '🎪' },
      { id: 7, name: '会员与次数卡', icon: '💳' },
      { id: 8, name: '其他问题', icon: '❓' },
    ],
    hotQuestions: [
      { id: 1, question: '如何预定营位？', answer: '打开首页 → 选择日常露营 → 选择营位 → 选择日期 → 提交订单 → 完成支付即可。' },
      { id: 2, question: '退票规则是什么？', answer: '入营日前2天可申请全额退款。超过退票时间无法退款，特殊情况请联系客服处理。' },
      { id: 3, question: '营地有电源吗？', answer: '部分营位配备220V电源，在选择营位时可通过"有电"标签筛选。' },
      { id: 4, question: '年卡会员有什么权益？', answer: '年卡会员可享受指定营位免费预定、专属活动参与等权益，具体权益请在"我的→年卡"中查看。' },
      { id: 5, question: '如何使用次数卡？', answer: '在"我的→次数卡"中输入激活码领取次数卡，预定营位时可选择使用次数卡抵扣。' },
    ],
    selectedFaq: null as { question: string; answer: string } | null,
    servicePhone: '400-888-1234',
    serviceWechat: 'yyyl_service',
    serviceHours: '09:00 - 21:00',
  },

  onSearchInput(e: WechatMiniprogram.Input) {
    this.setData({ searchKeyword: e.detail.value });
  },

  onSearchConfirm() {
    const { searchKeyword, hotQuestions } = this.data;
    if (!searchKeyword.trim()) return;
    const found = hotQuestions.find(q => q.question.includes(searchKeyword) || q.answer.includes(searchKeyword));
    if (found) {
      this.setData({ selectedFaq: found });
    } else {
      wx.showToast({ title: '未找到相关问题，请联系人工客服', icon: 'none' });
    }
  },

  onFaqTap(e: WechatMiniprogram.TouchEvent) {
    const id = e.currentTarget.dataset.id as number;
    const faq = this.data.hotQuestions.find(q => q.id === id);
    if (faq) this.setData({ selectedFaq: faq });
  },

  onCategoryTap(e: WechatMiniprogram.TouchEvent) {
    const { name } = e.currentTarget.dataset;
    wx.showToast({ title: `${name}分类开发中`, icon: 'none' });
  },

  onCloseFaq() {
    this.setData({ selectedFaq: null });
  },

  onCallPhone() {
    wx.makePhoneCall({ phoneNumber: this.data.servicePhone });
  },

  onCopyWechat() {
    wx.setClipboardData({
      data: this.data.serviceWechat,
      success: () => wx.showToast({ title: '微信号已复制', icon: 'success' }),
    });
  },
});
