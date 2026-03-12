// pages/cart/index.ts

interface CartPageData {
  cartItems: ICartItem[];
  allSelected: boolean;
  totalPrice: number;
  totalCount: number;
  loading: boolean;
  editing: boolean;
}

Page<CartPageData, WechatMiniprogram.IAnyObject>({
  data: {
    cartItems: [],
    allSelected: false,
    totalPrice: 0,
    totalCount: 0,
    loading: true,
    editing: false,
  },

  onShow() {
    this.loadCartData();
  },

  async loadCartData() {
    this.setData({ loading: true });

    // Mock数据
    const mockItems: ICartItem[] = [
      {
        id: 1, product_id: 6, product_name: '营地柴火 · 一捆',
        cover_image: '', price: 25, quantity: 2, selected: true, stock: 50,
        category: 'camp_shop',
      },
      {
        id: 2, product_id: 7, product_name: '冰镇可乐 330ml',
        cover_image: '', price: 5, quantity: 3, selected: true, stock: 100,
        category: 'camp_shop',
      },
      {
        id: 3, product_id: 8, product_name: '某露营地品牌T恤 · 绿色',
        cover_image: '', price: 128, quantity: 1, selected: false, stock: 20,
        category: 'merchandise',
      },
    ];

    this.setData({ cartItems: mockItems, loading: false });
    this.calcTotal();
  },

  /** 计算合计 */
  calcTotal() {
    const { cartItems } = this.data;
    let totalPrice = 0;
    let totalCount = 0;
    let allSelected = cartItems.length > 0;

    cartItems.forEach(item => {
      if (item.selected) {
        totalPrice += item.price * item.quantity;
        totalCount += item.quantity;
      } else {
        allSelected = false;
      }
    });

    this.setData({ totalPrice, totalCount, allSelected });
  },

  /** 全选/取消全选 */
  onToggleAll() {
    const { allSelected, cartItems } = this.data;
    const newSelected = !allSelected;
    cartItems.forEach(item => { item.selected = newSelected; });
    this.setData({ cartItems: [...cartItems] });
    this.calcTotal();
  },

  /** 单个选择 */
  onToggleItem(e: WechatMiniprogram.TouchEvent) {
    const index = e.currentTarget.dataset.index as number;
    const { cartItems } = this.data;
    cartItems[index].selected = !cartItems[index].selected;
    this.setData({ cartItems: [...cartItems] });
    this.calcTotal();
  },

  /** 增加数量 */
  onAdd(e: WechatMiniprogram.TouchEvent) {
    const index = e.currentTarget.dataset.index as number;
    const { cartItems } = this.data;
    if (cartItems[index].quantity < cartItems[index].stock) {
      cartItems[index].quantity++;
      this.setData({ cartItems: [...cartItems] });
      this.calcTotal();
    } else {
      wx.showToast({ title: '已达库存上限', icon: 'none' });
    }
  },

  /** 减少数量 */
  onMinus(e: WechatMiniprogram.TouchEvent) {
    const index = e.currentTarget.dataset.index as number;
    const { cartItems } = this.data;
    if (cartItems[index].quantity > 1) {
      cartItems[index].quantity--;
      this.setData({ cartItems: [...cartItems] });
      this.calcTotal();
    }
  },

  /** 删除商品 */
  onDelete(e: WechatMiniprogram.TouchEvent) {
    const index = e.currentTarget.dataset.index as number;
    wx.showModal({
      title: '提示',
      content: '确定删除该商品吗？',
      success: (res) => {
        if (res.confirm) {
          const { cartItems } = this.data;
          cartItems.splice(index, 1);
          this.setData({ cartItems: [...cartItems] });
          this.calcTotal();
        }
      },
    });
  },

  /** 切换编辑模式 */
  onToggleEdit() {
    this.setData({ editing: !this.data.editing });
  },

  /** 批量删除 */
  onBatchDelete() {
    const selectedItems = this.data.cartItems.filter(item => item.selected);
    if (selectedItems.length === 0) {
      wx.showToast({ title: '请选择要删除的商品', icon: 'none' });
      return;
    }
    wx.showModal({
      title: '提示',
      content: `确定删除选中的${selectedItems.length}件商品吗？`,
      success: (res) => {
        if (res.confirm) {
          const remaining = this.data.cartItems.filter(item => !item.selected);
          this.setData({ cartItems: remaining });
          this.calcTotal();
        }
      },
    });
  },

  /** 去结算 */
  onCheckout() {
    const selectedItems = this.data.cartItems.filter(item => item.selected);
    if (selectedItems.length === 0) {
      wx.showToast({ title: '请选择要结算的商品', icon: 'none' });
      return;
    }
    // 跳转订单确认页
    wx.navigateTo({
      url: `/pages/order-confirm/index?from=cart`,
    });
  },

  /** 去逛逛 */
  onGoShopping() {
    wx.switchTab({ url: '/pages/category/index' });
  },
});
