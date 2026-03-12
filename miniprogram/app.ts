import { checkLoginStatus, getUserInfo, wxLogin } from './utils/auth';
import { brandConfig } from './config/brand';

App<IAppOption>({
  globalData: {
    userInfo: null,
    token: '',
    refreshToken: '',
    isLoggedIn: false,
    systemInfo: null,
    statusBarHeight: 44,
    navBarHeight: 44,
    isStaff: false,
    brandConfig,
  },

  onLaunch() {
    // 获取系统信息
    try {
      const sysInfo = wx.getSystemInfoSync();
      this.globalData.systemInfo = sysInfo;
      this.globalData.statusBarHeight = sysInfo.statusBarHeight || 44;
      // 胶囊按钮位置信息计算导航栏高度
      const menuButton = wx.getMenuButtonBoundingClientRect();
      this.globalData.navBarHeight =
        (menuButton.top - (sysInfo.statusBarHeight || 0)) * 2 + menuButton.height;
    } catch (e) {
      console.error('获取系统信息失败:', e);
    }

    // 恢复登录状态
    this.checkLogin();
  },

  onError(err: string) {
    console.error('App Error:', err);
  },

  /**
   * 检查登录状态
   */
  async checkLogin(): Promise<boolean> {
    // 从本地存储恢复
    if (checkLoginStatus()) {
      const token = wx.getStorageSync('access_token') || '';
      const refreshToken = wx.getStorageSync('refresh_token') || '';
      const userInfo = getUserInfo();

      this.globalData.token = token;
      this.globalData.refreshToken = refreshToken;
      this.globalData.userInfo = userInfo;
      this.globalData.isLoggedIn = true;
      this.globalData.isStaff = userInfo?.is_staff || false;

      return true;
    }

    // 尝试静默登录
    try {
      await this.login();
      return true;
    } catch {
      return false;
    }
  },

  /**
   * 执行登录
   */
  async login(): Promise<ILoginResult> {
    const result = await wxLogin();
    return result;
  },

  /**
   * 退出登录
   */
  logout() {
    wx.removeStorageSync('access_token');
    wx.removeStorageSync('refresh_token');
    wx.removeStorageSync('user_info');

    this.globalData.token = '';
    this.globalData.refreshToken = '';
    this.globalData.userInfo = null;
    this.globalData.isLoggedIn = false;
    this.globalData.isStaff = false;
  },
});
