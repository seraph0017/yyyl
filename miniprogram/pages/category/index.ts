// pages/category/index.ts
import { get, resolveImageUrl } from '../../utils/request';

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

/** 后端商品类型到前端 category 映射 */
const TYPE_MAP: Record<string, string> = {
  'rental': 'equipment_rental',
  'shop': 'camp_shop',
};

/** 将后端列表项映射为 IProduct */
function mapProductItem(item: Record<string, any>): IProduct {
  const images = item.images || [];
  const coverImage = images.length > 0 ? resolveImageUrl(images[0].url || '') : '';
  const tags: string[] = [];
  if (item.is_seckill) tags.push('秒杀');
  let category: ProductCategory = (item.category || item.type || 'daily_camping') as ProductCategory;
  if (TYPE_MAP[category as string]) category = TYPE_MAP[category as string] as ProductCategory;

  return {
    id: item.id,
    name: item.name,
    category,
    description: item.description || '',
    cover_image: coverImage,
    images: images.map((img: any) => resolveImageUrl(img.url || '')),
    base_price: parseFloat(item.base_price) || 0,
    current_price: parseFloat(item.base_price) || 0,
    original_price: parseFloat(item.base_price) || 0,
    status: item.status || 'on_sale',
    tags,
    attributes: [],
    stock: 0,
    sales_count: 0,
    ticket_start_time: item.sale_start_at || null,
    is_seckill: item.is_seckill || false,
    has_disclaimer: true,
    identity_mode: 'optional',
    deposit_amount: 0,
  };
}

/** 前端 category 到后端 type 的反向映射 */
const CATEGORY_TO_TYPE: Record<string, string> = {
  'equipment_rental': 'rental',
  'camp_shop': 'shop',
};

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

    const currentTab = this.data.tabs[this.data.activeTab];
    const pageSize = 10;

    // 构建查询参数
    const params: Record<string, string | number | boolean | undefined> = {
      page: this.data.page,
      page_size: pageSize,
      status: 'on_sale',
    };

    // 类型筛选：前端 category → 后端 type
    const backendType = CATEGORY_TO_TYPE[currentTab.key] || currentTab.key;
    params.type = backendType;

    // 搜索关键词
    if (this.data.searchKeyword) {
      params.keyword = this.data.searchKeyword;
    }

    try {
      const data = await get<{ list: any[]; total: number }>(
        '/products', params, { needAuth: false },
      );

      const newProducts = (data.list || []).map(mapProductItem);
      const allProducts = this.data.page === 1
        ? newProducts
        : [...this.data.products, ...newProducts];

      this.setData({
        products: allProducts,
        loading: false,
        hasMore: allProducts.length < (data.total || 0),
      });
    } catch (err) {
      console.error('加载商品列表失败:', err);
      this.setData({ loading: false });
    }
  },

  /** 加载更多 */
  async loadMore() {
    this.setData({ page: this.data.page + 1 });
    await this.loadProducts();
  },
});
