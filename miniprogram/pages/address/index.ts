Page({
  data: {
    addresses: [] as IAddress[],
    selectMode: false,
  },
  onLoad(options) {
    this.setData({ selectMode: options.action === 'select' });
    this.loadAddresses();
  },
  loadAddresses() {
    this.setData({
      addresses: [
        { id: 1, name: '张三', phone: '13812341234', province: '上海市', city: '上海市', district: '浦东新区', detail: '世纪大道100号', is_default: true },
      ],
    });
  },
  onSelectAddress(e: WechatMiniprogram.TouchEvent) {
    if (this.data.selectMode) {
      const id = e.currentTarget.dataset.id as number;
      const address = this.data.addresses.find(a => a.id === id);
      if (address) {
        const pages = getCurrentPages();
        const prevPage = pages[pages.length - 2];
        if (prevPage) { prevPage.setData({ address }); }
        wx.navigateBack();
      }
    }
  },
  onAddAddress() {
    wx.showToast({ title: '添加地址功能开发中', icon: 'none' });
  },
  onDeleteAddress(e: WechatMiniprogram.TouchEvent) {
    const id = e.currentTarget.dataset.id as number;
    wx.showModal({
      title: '提示', content: '确定删除该地址吗？',
      success: (res) => {
        if (res.confirm) this.setData({ addresses: this.data.addresses.filter(a => a.id !== id) });
      },
    });
  },
});
