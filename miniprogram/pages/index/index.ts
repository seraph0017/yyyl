// pages/index/index.ts
import { get, resolveImageUrl } from '../../utils/request';
import { brandConfig } from '../../config/brand';

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

/** 将后端商品列表项转为前端 IProduct */
function mapProduct(item: Record<string, any>): IProduct {
  const images = item.images || [];
  const coverImage = images.length > 0 ? resolveImageUrl(images[0].url || '') : '';
  const tags: string[] = [];
  if (item.is_seckill) tags.push('秒杀');
  const attributes: IProductAttribute[] = [];
  if (item.ext_camping) {
    if (item.ext_camping.has_electricity) attributes.push({ key: 'power', label: '电源', value: '有电', icon: '⚡' });
    if (item.ext_camping.has_platform) attributes.push({ key: 'platform', label: '平台', value: '木平台', icon: '🪵' });
    if (item.ext_camping.sun_exposure === 'shaded') attributes.push({ key: 'shade', label: '遮阳', value: '阴凉', icon: '🌳' });
    if (item.ext_camping.area) attributes.push({ key: 'area', label: '区域', value: item.ext_camping.area, icon: '📍' });
  }
  // category 映射: 后端 type 字段
  let category: ProductCategory = (item.category || item.type || 'daily_camping') as ProductCategory;
  // 后端 type=rental → 前端 category=equipment_rental
  if (category === 'rental' as any) category = 'equipment_rental';
  if (category === 'shop' as any) category = 'camp_shop';

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
    attributes,
    stock: 0,
    sales_count: 0,
    ticket_start_time: item.sale_start_at || null,
    is_seckill: item.is_seckill || false,
    has_disclaimer: item.require_disclaimer !== false,
    identity_mode: 'optional',
    deposit_amount: item.ext_rental?.deposit_amount || 0,
  };
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
      title: brandConfig.shareTitle,
      path: '/pages/index/index',
    };
  },

  async loadData() {
    this.setData({ loading: true });

    try {
      // 并行加载 Banner 和商品列表
      const [bannerData, productData] = await Promise.all([
        get<{ banners: IBanner[] }>('/pages/home_banner', undefined, { needAuth: false, showError: false })
          .catch(() => ({ banners: [] as IBanner[] })),
        get<{ list: any[]; total: number }>('/products', { page_size: 18, status: 'on_sale' }, { needAuth: false })
          .catch(() => ({ list: [], total: 0 })),
      ]);

      const banners = (bannerData?.banners || []).map((b: IBanner) => ({
        ...b,
        image: resolveImageUrl(b.image),
      }));
      const products = (productData?.list || []).map(mapProduct);

      // 推荐商品：全部
      const recommendProducts = products;

      // 热门商品：取前 4 个（营位优先）
      const campingFirst = products
        .filter(p => p.category === 'daily_camping' || p.category === 'event_camping')
        .slice(0, 4);
      const hotProducts = campingFirst.length >= 4
        ? campingFirst
        : products.slice(0, 4);

      this.setData({
        banners: banners.length > 0 ? banners : [
          // 兜底 Banner（无图时的文字版）
          { id: 1, image: '', title: '🌲 春日露营季 · 限时特惠', link: '', color: '#2E7D32' },
          { id: 2, image: '', title: '🎶 仲夏夜星空音乐节', link: '', color: '#FF6B35' },
          { id: 3, image: '', title: '⛺ 新品装备上线 · 全场9折', link: '', color: '#2196F3' },
        ],
        recommendProducts,
        hotProducts,
        loading: false,
      });
    } catch (err) {
      console.error('首页加载失败:', err);
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败，下拉刷新重试', icon: 'none' });
    }
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
