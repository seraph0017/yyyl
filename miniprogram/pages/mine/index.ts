// pages/mine/index.ts
import { checkLoginStatus, getUserInfo, requireLogin } from '../../utils/auth';

interface MinePageData {
  isLoggedIn: boolean;
  userInfo: IUserInfo | null;
  orderMenus: IOrderMenu[];
  funcMenus: IFuncMenu[];
  isStaff: boolean;
}

interface IOrderMenu {
  key: string;
  name: string;
  icon: string;
  badge: number;
}

interface IFuncMenu {
  key: string;
  name: string;
  icon: string;
  url: string;
}

Page<MinePageData, WechatMiniprogram.IAnyObject>({
  data: {
    isLoggedIn: false,
    userInfo: null,
    orderMenus: [
      { key: 'pending', name: '待支付', icon: '💰', badge: 1 },
      { key: 'paid', name: '待使用', icon: '🎫', badge: 2 },
      { key: 'completed', name: '已完成', icon: '✅', badge: 0 },
      { key: 'refund', name: '退款', icon: '↩️', badge: 0 },
    ],
    funcMenus: [
      { key: 'order', name: '我的订单', icon: '📋', url: '/pages/order/index' },
      { key: 'identity', name: '身份信息', icon: '👤', url: '/pages/identity/index' },
      { key: 'address', name: '收货地址', icon: '📍', url: '/pages/address/index' },
      { key: 'annual', name: '我的年卡', icon: '💳', url: '/pages/member/index?tab=annual' },
      { key: 'times', name: '次数卡', icon: '🎟️', url: '/pages/member/index?tab=times' },
      { key: 'points', name: '积分明细', icon: '⭐', url: '/pages/member/index?tab=points' },
      { key: 'service', name: '联系客服', icon: '💬', url: '/pages/customer-service/index' },
    ],
    isStaff: false,
  },

  onShow() {
    this.refreshUserState();
  },

  refreshUserState() {
    const isLoggedIn = checkLoginStatus();
    const userInfo = getUserInfo();
    const app = getApp<IAppOption>();

    this.setData({
      isLoggedIn,
      userInfo,
      isStaff: app.globalData.isStaff || false,
    });
  },

  /** 头像昵称登录 */
  onGetPhoneNumber(e: WechatMiniprogram.ButtonGetPhoneNumber) {
    if (e.detail.errMsg === 'getPhoneNumber:ok') {
      // 调用手机号授权登录
      const auth = require('../../utils/auth');
      auth.phoneLogin(e).then(() => {
        this.refreshUserState();
        wx.showToast({ title: '登录成功', icon: 'success' });
      });
    }
  },

  /** 订单入口点击 */
  onOrderMenuTap(e: WechatMiniprogram.TouchEvent) {
    const { key } = e.currentTarget.dataset;
    requireLogin(() => {
      wx.navigateTo({ url: `/pages/order/index?tab=${key}` });
    });
  },

  /** 功能入口点击 */
  onFuncMenuTap(e: WechatMiniprogram.TouchEvent) {
    const { url } = e.currentTarget.dataset;
    requireLogin(() => {
      wx.navigateTo({ url });
    });
  },

  /** 查看全部订单 */
  onViewAllOrders() {
    requireLogin(() => {
      wx.switchTab({ url: '/pages/order/index' });
    });
  },

  /** 员工入口 */
  onStaffEntry() {
    wx.navigateTo({ url: '/pages/staff/index' });
  },

  /** 设置 */
  onSettings() {
    wx.showActionSheet({
      itemList: ['个人信息', '关于我们', '退出登录'],
      success: (res) => {
        if (res.tapIndex === 0) {
          wx.navigateTo({ url: '/pages/profile/index' });
        } else if (res.tapIndex === 2) {
          this.onLogout();
        }
      },
    });
  },

  /** 退出登录 */
  onLogout() {
    wx.showModal({
      title: '提示',
      content: '确定退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          const app = getApp<IAppOption>();
          app.logout();
          this.refreshUserState();
          wx.showToast({ title: '已退出登录', icon: 'success' });
        }
      },
    });
  },
});
