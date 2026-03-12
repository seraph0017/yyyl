// pages/ticket/index.ts
Page({
  data: {
    tickets: [] as ITicket[],
    loading: true,
    refreshTimer: null as number | null,
  },

  onLoad(options) {
    this.loadTickets(options.order_id || '1');
  },

  onUnload() {
    if (this.data.refreshTimer) clearInterval(this.data.refreshTimer);
  },

  async loadTickets(orderId: string) {
    // Mock
    const tickets: ITicket[] = [
      { id: 1, ticket_no: 'TK20260315001', order_id: Number(orderId), product_name: 'A区阳光营位', date: '2026-03-15', status: 'unused', qrcode_token: 'mock_token_001', verified_at: null },
      { id: 2, ticket_no: 'TK20260316001', order_id: Number(orderId), product_name: 'A区阳光营位', date: '2026-03-16', status: 'unused', qrcode_token: 'mock_token_002', verified_at: null },
    ];
    this.setData({ tickets, loading: false });
    this.startQrRefresh();
  },

  startQrRefresh() {
    // 每30秒刷新二维码token
    const timer = setInterval(() => {
      const { tickets } = this.data;
      tickets.forEach(t => {
        t.qrcode_token = `token_${Date.now()}_${t.id}`;
      });
      this.setData({ tickets: [...tickets] });
    }, 30000) as unknown as number;
    this.setData({ refreshTimer: timer });
  },

  onPreviewQr(e: WechatMiniprogram.TouchEvent) {
    const { token } = e.currentTarget.dataset;
    wx.showToast({ title: `票码：${token.substring(0, 10)}...`, icon: 'none' });
  },
});
