Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  properties: {
    /** 图标emoji */
    icon: {
      type: String,
      value: '📦',
    },
    /** 标题文字 */
    title: {
      type: String,
      value: '暂无数据',
    },
    /** 描述文字 */
    description: {
      type: String,
      value: '',
    },
    /** 按钮文字（不传则不显示按钮） */
    buttonText: {
      type: String,
      value: '',
    },
  },

  methods: {
    onButtonTap() {
      this.triggerEvent('action');
    },
  },
});
