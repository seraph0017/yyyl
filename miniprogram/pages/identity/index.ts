import { isValidPhone, isValidIdCard, maskPhone, maskIdCard } from '../../utils/util';

Page({
  data: {
    identities: [] as IIdentity[],
    showForm: false,
    editingId: 0,
    formData: { name: '', id_card: '', phone: '' },
    maskPhone,
    maskIdCard,
  },

  onLoad() {
    this.loadIdentities();
  },

  loadIdentities() {
    this.setData({
      identities: [
        { id: 1, name: '张三', id_card: '310101199001011234', phone: '13812341234', custom_fields: {}, is_default: true },
        { id: 2, name: '李四', id_card: '320101199002025678', phone: '13912345678', custom_fields: {}, is_default: false },
      ],
    });
  },

  onAddIdentity() {
    this.setData({ showForm: true, editingId: 0, formData: { name: '', id_card: '', phone: '' } });
  },

  onEditIdentity(e: WechatMiniprogram.TouchEvent) {
    const id = e.currentTarget.dataset.id as number;
    const identity = this.data.identities.find(i => i.id === id);
    if (identity) {
      this.setData({ showForm: true, editingId: id, formData: { name: identity.name, id_card: identity.id_card, phone: identity.phone } });
    }
  },

  onDeleteIdentity(e: WechatMiniprogram.TouchEvent) {
    const id = e.currentTarget.dataset.id as number;
    wx.showModal({
      title: '提示', content: '确定删除该出行人信息吗？',
      success: (res) => {
        if (res.confirm) {
          this.setData({ identities: this.data.identities.filter(i => i.id !== id) });
          wx.showToast({ title: '已删除', icon: 'success' });
        }
      },
    });
  },

  onFormInput(e: WechatMiniprogram.Input) {
    const field = e.currentTarget.dataset.field as string;
    this.setData({ [`formData.${field}`]: e.detail.value });
  },

  onSaveIdentity() {
    const { formData } = this.data;
    if (!formData.name.trim()) { wx.showToast({ title: '请输入姓名', icon: 'none' }); return; }
    if (!isValidIdCard(formData.id_card)) { wx.showToast({ title: '请输入正确的身份证号', icon: 'none' }); return; }
    if (!isValidPhone(formData.phone)) { wx.showToast({ title: '请输入正确的手机号', icon: 'none' }); return; }

    wx.showToast({ title: '保存成功', icon: 'success' });
    this.setData({ showForm: false });
    this.loadIdentities();
  },

  onCancelForm() {
    this.setData({ showForm: false });
  },
});
