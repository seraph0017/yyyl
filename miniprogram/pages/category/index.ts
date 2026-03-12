// pages/category/index.ts

interface CategoryPageData {
  tabs: ICategoryTab[];
  activeTab: number;
  filters: IFilter[];
  activeFilters: string[];
  products: IProduct[];
  loading: boolean;
  searchMode: boolean;
  searchKeyword: string;
  page: number;
  hasMore: boolean;
}

interface ICategoryTab {
  key: ProductCategory;
  name: string;
  icon: string;
}

interface IFilter {
  key: string;
  label: string;
  icon: string;
}

Page<CategoryPageData, WechatMiniprogram.IAnyObject>({
  data: {
    tabs: [
      { key: 'daily_camping', name: '日常露营', icon: '🏕️' },
      { key: 'event_camping', name: '活动露营', icon: '🎃' },
      { key: 'equipment_rental', name: '装备租赁', icon: '⛺' },
      { key: 'daily_activity', name: '日常活动', icon: '🛶' },
      { key: 'special_activity', name: '特定活动', icon: '🎪' },
      { key: 'camp_shop', name: '小商店', icon: '🛒' },
      { key: 'merchandise', name: '周边商品', icon: '👕' },
    ],
    activeTab: 0,
    filters: [
      { key: 'has_power', label: '有电', icon: '⚡' },
      { key: 'no_power', label: '无电', icon: '🔋' },
      { key: 'has_platform', label: '有木平台', icon: '🪵' },
      { key: 'sunshine', label: '阳光', icon: '☀️' },
      { key: 'shade', label: '阴凉', icon: '🌳' },
    ],
    activeFilters: [],
    products: [],
    loading: true,
    searchMode: false,
    searchKeyword: '',
    page: 1,
    hasMore: true,
  },

  onLoad(options) {
    if (options.search === '1') {
      this.setData({ searchMode: true });
    }
    if (options.category) {
      const tabIndex = this.data.tabs.findIndex(t => t.key === options.category);
      if (tabIndex >= 0) {
        this.setData({ activeTab: tabIndex });
      }
    }
    this.loadProducts();
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadMore();
    }
  },

  onPullDownRefresh() {
    this.setData({ page: 1, hasMore: true });
    this.loadProducts().then(() => wx.stopPullDownRefresh());
  },

  /** 切换Tab */
  onTabChange(e: WechatMiniprogram.TouchEvent) {
    const index = e.currentTarget.dataset.index as number;
    this.setData({
      activeTab: index,
      page: 1,
      hasMore: true,
      products: [],
      activeFilters: [],
    });
    this.loadProducts();
  },

  /** 切换筛选 */
  onFilterToggle(e: WechatMiniprogram.TouchEvent) {
    const key = e.currentTarget.dataset.key as string;
    const { activeFilters } = this.data;
    const index = activeFilters.indexOf(key);
    if (index >= 0) {
      activeFilters.splice(index, 1);
    } else {
      activeFilters.push(key);
    }
    this.setData({ activeFilters: [...activeFilters], page: 1, products: [] });
    this.loadProducts();
  },

  /** 搜索输入 */
  onSearchInput(e: WechatMiniprogram.Input) {
    this.setData({ searchKeyword: e.detail.value });
  },

  /** 搜索确认 */
  onSearchConfirm() {
    this.setData({ page: 1, products: [] });
    this.loadProducts();
  },

  /** 取消搜索 */
  onSearchCancel() {
    this.setData({ searchMode: false, searchKeyword: '' });
    this.loadProducts();
  },

  /** 加载商品列表 */
  async loadProducts() {
    this.setData({ loading: true });

    // Mock数据
    const currentTab = this.data.tabs[this.data.activeTab];
    const mockProducts: IProduct[] = Array.from({ length: 6 }, (_, i) => ({
      id: i + 1 + this.data.activeTab * 10,
      name: `${currentTab.icon} ${currentTab.name}商品${i + 1}`,
      category: currentTab.key,
      description: `这是${currentTab.name}分类下的精选商品，品质保证`,
      cover_image: '',
      images: [],
      base_price: 100 + i * 30,
      current_price: 80 + i * 25,
      original_price: 100 + i * 30,
      status: 'on_sale' as const,
      tags: i === 0 ? ['热卖'] : i === 2 ? ['秒杀'] : [],
      attributes: currentTab.key === 'daily_camping' ? [
        { key: 'power', label: '电源', value: i % 2 === 0 ? '有电' : '无电', icon: i % 2 === 0 ? '⚡' : '🔋' },
        { key: 'platform', label: '平台', value: i % 3 === 0 ? '木平台' : '无平台', icon: '🪵' },
      ] : [],
      stock: 10 - i,
      sales_count: 100 + i * 50,
      ticket_start_time: null,
      is_seckill: i === 2,
      has_disclaimer: true,
      identity_mode: 'required' as const,
      deposit_amount: 0,
    }));

    setTimeout(() => {
      this.setData({
        products: this.data.page === 1 ? mockProducts : [...this.data.products, ...mockProducts],
        loading: false,
        hasMore: this.data.page < 3,
      });
    }, 300);
  },

  /** 加载更多 */
  async loadMore() {
    this.setData({ page: this.data.page + 1 });
    await this.loadProducts();
  },
});
