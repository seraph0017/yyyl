// pages/product-detail/index.ts

interface DetailPageData {
  product: IProduct | null;
  swiperCurrent: number;
  selectedDates: string[];
  calendarDays: ICalendarDay[];
  currentMonth: string;
  calendarYear: number;
  calendarMonth: number;
  totalPrice: number;
  quantity: number;
  showCalendar: boolean;
  showDisclaimer: boolean;
  disclaimerText: string;
  disclaimerAgreed: boolean;
  loading: boolean;
  isFavorite: boolean;
  notStarted: boolean;
}

interface ICalendarDay {
  date: string;
  day: number;
  price: number;
  dateType: string;
  stock: number;
  isAvailable: boolean;
  isSelected: boolean;
  isToday: boolean;
  isPast: boolean;
  isCurrentMonth: boolean;
}

Page<DetailPageData, WechatMiniprogram.IAnyObject>({
  data: {
    product: null,
    swiperCurrent: 0,
    selectedDates: [],
    calendarDays: [],
    currentMonth: '',
    calendarYear: 2026,
    calendarMonth: 3,
    totalPrice: 0,
    quantity: 1,
    showCalendar: false,
    showDisclaimer: false,
    disclaimerText: '',
    disclaimerAgreed: false,
    loading: true,
    isFavorite: false,
    notStarted: false,
  },

  onLoad(options) {
    const id = options.id || '1';
    this.loadProduct(Number(id));
  },

  onShareAppMessage() {
    const product = this.data.product;
    return {
      title: product ? product.name : '一月一露露营',
      path: `/pages/product-detail/index?id=${product?.id || 1}`,
    };
  },

  /** 加载商品详情 */
  async loadProduct(id: number) {
    this.setData({ loading: true });

    // Mock数据
    const mockProduct: IProduct = {
      id,
      name: 'A区阳光营位 · 有电有木平台',
      category: 'daily_camping',
      description: '位于营地A区的独立营位，配备220V电源插座和实木平台。视野开阔，阳光充足，适合家庭露营。\n\n📍 营位面积：约80㎡\n⚡ 电源：220V交流电，限流10A\n🪵 平台：3m×4m实木平台\n🚗 停车：营位旁可停1辆车\n🚿 距离卫生间：约100m',
      cover_image: '',
      images: ['', '', ''],
      base_price: 168,
      current_price: 128,
      original_price: 168,
      status: 'on_sale',
      tags: ['热卖'],
      attributes: [
        { key: 'power', label: '电源', value: '有电 ⚡', icon: '⚡' },
        { key: 'platform', label: '平台', value: '木平台 🪵', icon: '🪵' },
        { key: 'shade', label: '光照', value: '阳光 ☀️', icon: '☀️' },
        { key: 'size', label: '面积', value: '约80㎡', icon: '📐' },
      ],
      stock: 5,
      sales_count: 326,
      ticket_start_time: null,
      is_seckill: false,
      has_disclaimer: true,
      identity_mode: 'required',
      deposit_amount: 0,
    };

    const disclaimerText = '免责声明\n\n1. 参与者确认已充分了解户外露营活动的风险性，自愿参加本次露营活动。\n2. 参与者应遵守营地管理规定，爱护公共设施，保持环境整洁。\n3. 参与者对自身及随行人员的安全负有责任。\n4. 如遇极端天气或不可抗力因素，营地有权调整或取消活动。\n5. 参与者应妥善管理个人财物，营地对个人财物遗失不承担赔偿责任。\n6. 未成年人须在监护人陪同下参加露营活动。\n7. 禁止在非指定区域使用明火，违规产生的一切后果由参与者自行承担。';

    this.setData({
      product: mockProduct,
      disclaimerText,
      notStarted: !!mockProduct.ticket_start_time && new Date(mockProduct.ticket_start_time).getTime() > Date.now(),
      loading: false,
    });

    this.generateCalendar();
  },

  /** 生成日历 */
  generateCalendar() {
    const { calendarYear, calendarMonth, selectedDates } = this.data;
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    const firstDay = new Date(calendarYear, calendarMonth - 1, 1);
    const lastDay = new Date(calendarYear, calendarMonth, 0);
    const startWeekDay = firstDay.getDay();

    const days: ICalendarDay[] = [];

    // 上月补位
    const prevMonthLastDay = new Date(calendarYear, calendarMonth - 1, 0).getDate();
    for (let i = startWeekDay - 1; i >= 0; i--) {
      const d = prevMonthLastDay - i;
      const m = calendarMonth === 1 ? 12 : calendarMonth - 1;
      const y = calendarMonth === 1 ? calendarYear - 1 : calendarYear;
      const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({
        date: dateStr, day: d, price: 0, dateType: '', stock: 0,
        isAvailable: false, isSelected: false, isToday: false, isPast: true, isCurrentMonth: false,
      });
    }

    // 当月日期
    for (let d = 1; d <= lastDay.getDate(); d++) {
      const dateStr = `${calendarYear}-${String(calendarMonth).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const dayOfWeek = new Date(calendarYear, calendarMonth - 1, d).getDay();
      const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
      const isPast = dateStr < todayStr;

      days.push({
        date: dateStr,
        day: d,
        price: isWeekend ? 168 : 128,
        dateType: isWeekend ? '周末' : '工作日',
        stock: isPast ? 0 : Math.floor(Math.random() * 8) + 1,
        isAvailable: !isPast,
        isSelected: selectedDates.includes(dateStr),
        isToday: dateStr === todayStr,
        isPast,
        isCurrentMonth: true,
      });
    }

    // 下月补位
    const remaining = 42 - days.length;
    for (let d = 1; d <= remaining; d++) {
      const m = calendarMonth === 12 ? 1 : calendarMonth + 1;
      const y = calendarMonth === 12 ? calendarYear + 1 : calendarYear;
      const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({
        date: dateStr, day: d, price: 0, dateType: '', stock: 0,
        isAvailable: false, isSelected: false, isToday: false, isPast: false, isCurrentMonth: false,
      });
    }

    const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];

    this.setData({
      calendarDays: days,
      currentMonth: `${calendarYear}年${monthNames[calendarMonth - 1]}`,
    });
  },

  /** 轮播切换 */
  onSwiperChange(e: WechatMiniprogram.SwiperChange) {
    this.setData({ swiperCurrent: e.detail.current });
  },

  /** 打开日历 */
  onOpenCalendar() {
    this.setData({ showCalendar: true });
  },

  /** 关闭日历 */
  onCloseCalendar() {
    this.setData({ showCalendar: false });
  },

  /** 上个月 */
  onPrevMonth() {
    let { calendarYear, calendarMonth } = this.data;
    if (calendarMonth === 1) {
      calendarYear--;
      calendarMonth = 12;
    } else {
      calendarMonth--;
    }
    this.setData({ calendarYear, calendarMonth });
    this.generateCalendar();
  },

  /** 下个月 */
  onNextMonth() {
    let { calendarYear, calendarMonth } = this.data;
    if (calendarMonth === 12) {
      calendarYear++;
      calendarMonth = 1;
    } else {
      calendarMonth++;
    }
    this.setData({ calendarYear, calendarMonth });
    this.generateCalendar();
  },

  /** 选择日期 */
  onSelectDate(e: WechatMiniprogram.TouchEvent) {
    const { date, available } = e.currentTarget.dataset;
    if (!available) return;

    let { selectedDates } = this.data;
    const index = selectedDates.indexOf(date);
    if (index >= 0) {
      selectedDates.splice(index, 1);
    } else {
      selectedDates.push(date);
      selectedDates.sort();
    }

    this.setData({ selectedDates: [...selectedDates] });
    this.generateCalendar();
    this.calcPrice();
  },

  /** 计算价格 */
  calcPrice() {
    const { selectedDates, calendarDays, quantity } = this.data;
    let total = 0;
    selectedDates.forEach(date => {
      const day = calendarDays.find(d => d.date === date);
      if (day) {
        total += day.price;
      }
    });
    this.setData({ totalPrice: total * quantity });
  },

  /** 数量加减 */
  onQuantityAdd() {
    const { quantity, product } = this.data;
    if (product && quantity < product.stock) {
      this.setData({ quantity: quantity + 1 });
      this.calcPrice();
    }
  },

  onQuantityMinus() {
    if (this.data.quantity > 1) {
      this.setData({ quantity: this.data.quantity - 1 });
      this.calcPrice();
    }
  },

  /** 打开免责声明 */
  onShowDisclaimer() {
    this.setData({ showDisclaimer: true });
  },

  onCloseDisclaimer() {
    this.setData({ showDisclaimer: false });
  },

  onAgreeDisclaimer() {
    this.setData({ disclaimerAgreed: true, showDisclaimer: false });
  },

  /** 加入购物车 */
  onAddToCart() {
    const { product } = this.data;
    if (!product) return;

    // 仅小商店和周边商品可加入购物车
    if (product.category !== 'camp_shop' && product.category !== 'merchandise') {
      wx.showToast({ title: '该商品不支持加入购物车，请直接预定', icon: 'none' });
      return;
    }

    wx.showToast({ title: '已加入购物车', icon: 'success' });
  },

  /** 立即预定 */
  onBook() {
    const { product, selectedDates, disclaimerAgreed, notStarted } = this.data;
    if (!product) return;

    if (notStarted) {
      wx.showToast({ title: '尚未开票，请等待', icon: 'none' });
      return;
    }

    // 需要选日期的品类
    const needDate = ['daily_camping', 'event_camping', 'equipment_rental', 'daily_activity', 'special_activity'];
    if (needDate.includes(product.category) && selectedDates.length === 0) {
      wx.showToast({ title: '请先选择日期', icon: 'none' });
      return;
    }

    if (product.has_disclaimer && !disclaimerAgreed) {
      this.onShowDisclaimer();
      return;
    }

    // 跳转订单确认页
    wx.navigateTo({
      url: `/pages/order-confirm/index?product_id=${product.id}&dates=${selectedDates.join(',')}&quantity=${this.data.quantity}`,
    });
  },

  /** 联系客服 */
  onContactService() {
    wx.navigateTo({ url: '/pages/customer-service/index' });
  },

  /** 收藏 */
  onToggleFavorite() {
    this.setData({ isFavorite: !this.data.isFavorite });
    wx.showToast({
      title: this.data.isFavorite ? '已收藏' : '已取消收藏',
      icon: 'success',
    });
  },

  /** 阻止冒泡 */
  preventBubble() {},
});
