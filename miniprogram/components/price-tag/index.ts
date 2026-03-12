Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  properties: {
    /** 当前价格 */
    price: {
      type: Number,
      value: 0,
    },
    /** 原价（显示划线价） */
    originalPrice: {
      type: Number,
      value: 0,
    },
    /** 尺寸 small | medium | large */
    size: {
      type: String,
      value: 'medium',
    },
    /** 是否显示会员价标记 */
    memberPrice: {
      type: Boolean,
      value: false,
    },
    /** 价格单位（如 /天, /晚, /次） */
    unit: {
      type: String,
      value: '',
    },
  },

  observers: {
    'price, originalPrice'(price: number, originalPrice: number) {
      this.setData({
        showOriginal: originalPrice > 0 && originalPrice > price,
        priceInt: Math.floor(price),
        priceDecimal: (price % 1).toFixed(2).slice(1),
      });
    },
  },

  data: {
    showOriginal: false,
    priceInt: 0,
    priceDecimal: '.00',
  },
});
