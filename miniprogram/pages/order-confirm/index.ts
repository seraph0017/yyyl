// pages/order-confirm/index.ts

interface ConfirmPageData {
  from: string;
  productId: number;
  dates: string[];
  quantity: number;
  product: IProduct | null;
  identities: IIdentity[];
  selectedIdentity: IIdentity | null;
  address: IAddress | null;
  needAddress: boolean;
  totalPrice: number;
  discountAmount: number;
  actualPrice: number;
  disclaimerAgreed: boolean;
  submitting: boolean;
  useAnnualCard: boolean;
  useTimesCard: boolean;
}

Page<ConfirmPageData, WechatMiniprogram.IAnyObject>({
  data: {
    from: 'direct',
    productId: 0,
    dates: [],
    quantity: 1,
    product: null,
    identities: [],
    selectedIdentity: null,
    address: null,
    needAddress: false,
    totalPrice: 0,
    discountAmount: 0,
    actualPrice: 0,
    disclaimerAgreed: true,
    submitting: false,
    useAnnualCard: false,
    useTimesCard: false,
  },

  onLoad(options) {
    const productId = Number(options.product_id || 0);
    const dates = options.dates ? options.dates.split(',') : [];
    const quantity = Number(options.quantity || 1);
    const from = options.from || 'direct';

    this.setData({ productId, dates, quantity, from });
    this.loadData();
  },

  async loadData() {
    // Mock商品
    const product: IProduct = {
      id: this.data.productId || 1,
      name: 'A区阳光营位 · 有电有木平台',
      category: 'daily_camping',
      description: '',
      cover_image: '',
      images: [],
      base_price: 168,
      current_price: 128,
      original_price: 168,
      status: 'on_sale',
      tags: [],
      attributes: [],
      stock: 5,
      sales_count: 326,
      ticket_start_time: null,
      is_seckill: false,
      has_disclaimer: true,
      identity_mode: 'required',
      deposit_amount: 0,
    };

    const identities: IIdentity[] = [
      { id: 1, name: '张三', id_card: '310***********1234', phone: '138****1234', custom_fields: {}, is_default: true },
      { id: 2, name: '李四', id_card: '320***********5678', phone: '139****5678', custom_fields: {}, is_default: false },
    ];

    const totalPrice = product.current_price * this.data.dates.length * this.data.quantity;
    const discountAmount = this.data.dates.length >= 2 ? Math.floor(totalPrice * 0.2) : 0;

    this.setData({
      product,
      identities,
      selectedIdentity: identities[0],
      needAddress: product.category === 'merchandise',
      totalPrice,
      discountAmount,
      actualPrice: totalPrice - discountAmount,
    });
  },

  /** 选择身份 */
  onSelectIdentity(e: WechatMiniprogram.TouchEvent) {
    const id = e.currentTarget.dataset.id as number;
    const identity = this.data.identities.find(i => i.id === id) || null;
    this.setData({ selectedIdentity: identity });
  },

  /** 添加身份 */
  onAddIdentity() {
    wx.navigateTo({ url: '/pages/identity/index?action=add' });
  },

  /** 选择地址 */
  onSelectAddress() {
    wx.navigateTo({ url: '/pages/address/index?action=select' });
  },

  /** 提交订单 */
  async onSubmitOrder() {
    const { product, selectedIdentity, submitting, actualPrice } = this.data;

    if (submitting) return;
    if (!product) return;

    // 验证身份
    if (product.identity_mode === 'required' && !selectedIdentity) {
      wx.showToast({ title: '请选择出行人信息', icon: 'none' });
      return;
    }

    // 验证地址
    if (this.data.needAddress && !this.data.address) {
      wx.showToast({ title: '请选择收货地址', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });

    // Mock提交
    setTimeout(() => {
      this.setData({ submitting: false });
      wx.navigateTo({
        url: `/pages/payment/index?order_id=mock_001&amount=${actualPrice}`,
      });
    }, 800);
  },
});
