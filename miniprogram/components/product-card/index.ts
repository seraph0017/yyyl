Component({
  options: {
    multipleSlots: true,
    styleIsolation: 'apply-shared',
  },

  properties: {
    product: {
      type: Object,
      value: {} as IProduct,
    },
    /** 展示模式：grid=双列网格，list=单列列表 */
    mode: {
      type: String,
      value: 'grid',
    },
    /** 是否显示标签 */
    showTag: {
      type: Boolean,
      value: true,
    },
  },

  data: {
    imageLoaded: false,
  },

  methods: {
    onTap() {
      const product = this.data.product as IProduct;
      if (product && product.id) {
        wx.navigateTo({
          url: `/pages/product-detail/index?id=${product.id}`,
        });
      }
    },

    onImageLoad() {
      this.setData({ imageLoaded: true });
    },

    onImageError() {
      this.setData({ imageLoaded: true });
    },
  },
});
