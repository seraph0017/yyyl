/**
 * 登录授权工具
 * - 微信登录（wx.login获取code → 后端换token）
 * - 手机号授权
 * - Token管理
 */

import { post } from './request';

/**
 * 微信静默登录
 * 使用wx.login获取code，发送给后端换取token
 */
export async function wxLogin(): Promise<ILoginResult> {
  // 获取微信登录code
  const { code } = await new Promise<WechatMiniprogram.LoginSuccessCallbackResult>(
    (resolve, reject) => {
      wx.login({
        success: resolve,
        fail: reject,
      });
    }
  );

  // 用code换取token
  const result = await post<ILoginResult>('/auth/login', { code }, { needAuth: false });

  // 保存登录信息
  saveLoginInfo(result);

  return result;
}

/**
 * 手机号授权登录
 * @param e 手机号按钮回调事件
 */
export async function phoneLogin(e: WechatMiniprogram.ButtonGetPhoneNumber): Promise<ILoginResult | null> {
  if (e.detail.errMsg !== 'getPhoneNumber:ok') {
    return null;
  }

  const { code: loginCode } = await new Promise<WechatMiniprogram.LoginSuccessCallbackResult>(
    (resolve, reject) => {
      wx.login({ success: resolve, fail: reject });
    }
  );

  const result = await post<ILoginResult>('/auth/phone-login', {
    code: loginCode,
    phone_code: e.detail.code,
  }, { needAuth: false });

  saveLoginInfo(result);

  return result;
}

/**
 * 保存登录信息
 */
export function saveLoginInfo(result: ILoginResult): void {
  wx.setStorageSync('access_token', result.access_token);
  wx.setStorageSync('refresh_token', result.refresh_token);
  wx.setStorageSync('user_info', JSON.stringify(result.user));

  const app = getApp<IAppOption>();
  if (app && app.globalData) {
    app.globalData.token = result.access_token;
    app.globalData.refreshToken = result.refresh_token;
    app.globalData.userInfo = result.user;
    app.globalData.isLoggedIn = true;
    app.globalData.isStaff = result.user.is_staff || false;
  }
}

/**
 * 检查登录状态
 */
export function checkLoginStatus(): boolean {
  const token = wx.getStorageSync('access_token');
  return !!token;
}

/**
 * 获取已登录的用户信息
 */
export function getUserInfo(): IUserInfo | null {
  try {
    const str = wx.getStorageSync('user_info');
    return str ? JSON.parse(str) : null;
  } catch {
    return null;
  }
}

/**
 * 退出登录
 */
export function logout(): void {
  wx.removeStorageSync('access_token');
  wx.removeStorageSync('refresh_token');
  wx.removeStorageSync('user_info');

  const app = getApp<IAppOption>();
  if (app && app.globalData) {
    app.globalData.token = '';
    app.globalData.refreshToken = '';
    app.globalData.userInfo = null;
    app.globalData.isLoggedIn = false;
    app.globalData.isStaff = false;
  }
}

/**
 * 确保已登录，未登录则尝试静默登录
 */
export async function ensureLogin(): Promise<boolean> {
  if (checkLoginStatus()) {
    return true;
  }

  try {
    await wxLogin();
    return true;
  } catch {
    return false;
  }
}

/**
 * 需要登录时调用，未登录跳转引导
 */
export function requireLogin(callback?: () => void): void {
  if (checkLoginStatus()) {
    callback?.();
    return;
  }

  wx.showModal({
    title: '提示',
    content: '请先登录后再操作',
    confirmText: '去登录',
    success(res) {
      if (res.confirm) {
        wx.navigateTo({ url: '/pages/mine/index' });
      }
    },
  });
}
