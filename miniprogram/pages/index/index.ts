// pages/index/index.ts

interface IndexPageData {
  banners: IBanner[];
  categories: ICategoryNav[];
  recommendProducts: IProduct[];
  hotProducts: IProduct[];
  swiperCurrent: number;
  loading: boolean;
  refreshing: boolean;
}

interface IBanner {
  id: number;
  image: string;
  title: string;
  link: string;
  color: string;
}

interface ICategoryNav {
  key: ProductCategory;
  name: string;
  icon: string;
}

Page<IndexPageData, WechatMiniprogram.IAnyObject>({
  data: {
    banners: [],
    categories: [
      { key: 'daily_camping', name: '日常露营', icon: '🏕️' },
      { key: 'event_camping', name: '活动露营', icon: '🎃' },
      { key: 'equipment_rental', name: '装备租赁', icon: '⛺' },
      { key: 'daily_activity', name: '日常活动', icon: '🛶' },
      { key: 'special_activity', name: '特定活动', icon: '🎪' },
      { key: 'camp_shop', name: '小商店', icon: '🛒' },
      { key: 'merchandise', name: '周边商品', icon: '👕' },
    ],
    recommendProducts: [],
    hotProducts: [],
    swiperCurrent: 0,
    loading: true,
    refreshing: false,
  },

  onLoad() {
    this.loadData();
  },

  onShow() {
    // 如果需要每次显示都刷新
  },

  onPullDownRefresh() {
    this.setData({ refreshing: true });
    this.loadData().then(() => {
      wx.stopPullDownRefresh();
      this.setData({ refreshing: false });
    });
  },

  onShareAppMessage() {
    return {
      title: '一月一露 · 享受户外生活',
      path: '/pages/index/index',
    };
  },

  async loadData() {
    this.setData({ loading: true });

    // Mock数据 - 后续替换为API调用
    const banners: IBanner[] = [
      { id: 1, image: '', title: '🌲 春日露营季 · 限时特惠', link: '', color: '#2E7D32' },
      { id: 2, image: '', title: '🎃 万圣节帐友会 · 火热报名中', link: '', color: '#FF6B35' },
      { id: 3, image: '', title: '⛺ 新品装备上线 · 全场9折', link: '', color: '#2196F3' },
    ];

    const mockProducts: IProduct[] = [
      {
        id: 1, name: 'A区阳光营位 · 有电有木平台', category: 'daily_camping',
        description: '独立营位，配备电源插座和实木平台，视野开阔',
        cover_image: '', images: [], base_price: 168, current_price: 128, original_price: 168,
        status: 'on_sale', tags: ['热卖'], attributes: [
          { key: 'power', label: '电源', value: '有电', icon: '⚡' },
          { key: 'platform', label: '平台', value: '木平台', icon: '🪵' },
        ],
        stock: 5, sales_count: 326, ticket_start_time: null, is_seckill: false,
        has_disclaimer: true, identity_mode: 'required', deposit_amount: 0,
      },
      {
        id: 2, name: 'B区林间营位 · 自然风', category: 'daily_camping',
        description: '林间遮阴营位，夏日清凉之选',
        cover_image: '', images: [], base_price: 128, current_price: 98, original_price: 128,
        status: 'on_sale', tags: [], attributes: [
          { key: 'shade', label: '遮阳', value: '阴凉', icon: '🌳' },
        ],
        stock: 8, sales_count: 215, ticket_start_time: null, is_seckill: false,
        has_disclaimer: true, identity_mode: 'required', deposit_amount: 0,
      },
      {
        id: 3, name: '万圣节帐友会 · 夜间营位', category: 'event_camping',
        description: '万圣节限定活动，含篝火晚会+手作活动',
        cover_image: '', images: [], base_price: 298, current_price: 258, original_price: 298,
        status: 'on_sale', tags: ['秒杀', '热卖'], attributes: [],
        stock: 20, sales_count: 89, ticket_start_time: '2026-04-01T20:00:00', is_seckill: true,
        has_disclaimer: true, identity_mode: 'required', deposit_amount: 0,
      },
      {
        id: 4, name: '帐篷租赁 · 4人家庭帐', category: 'equipment_rental',
        description: '4-6人大帐篷，含地垫+防潮垫',
        cover_image: '', images: [], base_price: 150, current_price: 120, original_price: 150,
        status: 'on_sale', tags: [], attributes: [],
        stock: 10, sales_count: 156, ticket_start_time: null, is_seckill: false,
        has_disclaimer: true, identity_mode: 'optional', deposit_amount: 200,
      },
      {
        id: 5, name: '皮划艇体验 · 单人艇', category: 'daily_activity',
        description: '专业教练带队，含救生衣，时长60分钟',
        cover_image: '', images: [], base_price: 98, current_price: 78, original_price: 98,
        status: 'on_sale', tags: ['热卖'], attributes: [],
        stock: 6, sales_count: 432, ticket_start_time: null, is_seckill: false,
        has_disclaimer: true, identity_mode: 'required', deposit_amount: 0,
      },
      {
        id: 6, name: '营地柴火 · 一捆', category: 'camp_shop',
        description: '天然松木柴火，约5kg一捆',
        cover_image: '', images: [], base_price: 30, current_price: 25, original_price: 30,
        status: 'on_sale', tags: [], attributes: [],
        stock: 50, sales_count: 1024, ticket_start_time: null, is_seckill: false,
        has_disclaimer: false, identity_mode: 'none', deposit_amount: 0,
      },
    ];

    this.setData({
      banners,
      recommendProducts: mockProducts,
      hotProducts: mockProducts.slice(0, 4),
      loading: false,
    });
  },

  /** 轮播切换 */
  onSwiperChange(e: WechatMiniprogram.SwiperChange) {
    this.setData({ swiperCurrent: e.detail.current });
  },

  /** 搜索 */
  onSearchTap() {
    wx.navigateTo({ url: '/pages/category/index?search=1' });
  },

  /** 分类点击 */
  onCategoryTap(e: WechatMiniprogram.TouchEvent) {
    const { key } = e.currentTarget.dataset;
    wx.switchTab({ url: '/pages/category/index' });
    // 通过事件通道传递品类信息
    const eventChannel = this.getOpenerEventChannel?.();
    if (eventChannel) {
      eventChannel.emit('selectCategory', { category: key });
    }
  },

  /** 轮播卡片点击 */
  onBannerTap(e: WechatMiniprogram.TouchEvent) {
    const { id } = e.currentTarget.dataset;
    console.log('Banner tapped:', id);
  },

  /** 查看更多推荐 */
  onViewMore() {
    wx.switchTab({ url: '/pages/category/index' });
  },
});
