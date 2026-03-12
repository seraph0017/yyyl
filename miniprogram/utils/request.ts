/**
 * 网络请求封装
 * - baseURL配置
 * - 自动携带token
 * - 统一响应处理（code=0成功）
 * - token过期自动刷新
 * - 错误提示
 */

const BASE_URL = 'http://localhost:8000/api/v1';

interface RequestOptions {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  data?: Record<string, unknown> | unknown[];
  params?: Record<string, string | number | boolean | undefined>;
  header?: Record<string, string>;
  showLoading?: boolean;
  loadingText?: string;
  showError?: boolean;
  needAuth?: boolean;
}

/** 是否正在刷新token */
let isRefreshing = false;
/** 等待刷新的请求队列 */
let waitingQueue: Array<() => void> = [];

/**
 * 构建URL查询参数
 */
function buildQueryString(params: Record<string, string | number | boolean | undefined>): string {
  const parts: string[] = [];
  for (const key of Object.keys(params)) {
    const value = params[key];
    if (value !== undefined && value !== null) {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
    }
  }
  return parts.length > 0 ? `?${parts.join('&')}` : '';
}

/**
 * 获取Token
 */
function getToken(): string {
  try {
    return wx.getStorageSync('access_token') || '';
  } catch {
    return '';
  }
}

/**
 * 刷新Token
 */
async function refreshToken(): Promise<string> {
  const refreshTokenStr = wx.getStorageSync('refresh_token') || '';
  if (!refreshTokenStr) {
    throw new Error('No refresh token');
  }

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}/auth/refresh`,
      method: 'POST',
      data: { refresh_token: refreshTokenStr },
      success(res) {
        const data = res.data as IApiResponse<{ access_token: string; refresh_token: string }>;
        if (data.code === 0 && data.data) {
          wx.setStorageSync('access_token', data.data.access_token);
          wx.setStorageSync('refresh_token', data.data.refresh_token);
          resolve(data.data.access_token);
        } else {
          reject(new Error('Refresh token failed'));
        }
      },
      fail(err) {
        reject(err);
      }
    });
  });
}

/**
 * 处理Token过期
 */
async function handleTokenExpired<T>(options: RequestOptions): Promise<T> {
  if (isRefreshing) {
    // 等待刷新完成后重试
    return new Promise<T>((resolve) => {
      waitingQueue.push(() => {
        resolve(request<T>(options));
      });
    });
  }

  isRefreshing = true;

  try {
    await refreshToken();
    isRefreshing = false;

    // 执行等待队列中的请求
    waitingQueue.forEach((callback) => callback());
    waitingQueue = [];

    // 重试当前请求
    return request<T>(options);
  } catch {
    isRefreshing = false;
    waitingQueue = [];

    // 刷新失败，清除登录状态，跳转登录
    wx.removeStorageSync('access_token');
    wx.removeStorageSync('refresh_token');
    wx.removeStorageSync('user_info');

    const app = getApp<IAppOption>();
    if (app && app.globalData) {
      app.globalData.isLoggedIn = false;
      app.globalData.token = '';
      app.globalData.userInfo = null;
    }

    wx.showToast({
      title: '登录已过期，请重新登录',
      icon: 'none',
      duration: 2000,
    });

    throw new Error('Token expired');
  }
}

/**
 * 核心请求方法
 */
export function request<T = unknown>(options: RequestOptions): Promise<T> {
  const {
    url,
    method = 'GET',
    data,
    params,
    header = {},
    showLoading = false,
    loadingText = '加载中...',
    showError = true,
    needAuth = true,
  } = options;

  // 构建完整URL
  let fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`;
  if (params) {
    fullUrl += buildQueryString(params);
  }

  // 设置请求头
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...header,
  };

  // 自动携带token
  if (needAuth) {
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  // 显示loading
  if (showLoading) {
    wx.showLoading({ title: loadingText, mask: true });
  }

  return new Promise<T>((resolve, reject) => {
    wx.request({
      url: fullUrl,
      method,
      data: data as WechatMiniprogram.IAnyObject,
      header: headers,
      success(res) {
        if (showLoading) wx.hideLoading();

        const statusCode = res.statusCode;
        const responseData = res.data as IApiResponse<T>;

        // HTTP状态码检查
        if (statusCode === 401) {
          // Token过期，尝试刷新
          handleTokenExpired<T>(options).then(resolve).catch(reject);
          return;
        }

        if (statusCode >= 400) {
          const errMsg = responseData?.message || `请求失败(${statusCode})`;
          if (showError) {
            wx.showToast({ title: errMsg, icon: 'none', duration: 2500 });
          }
          reject(new Error(errMsg));
          return;
        }

        // 业务状态码检查
        if (responseData.code === 0) {
          resolve(responseData.data);
        } else {
          const errMsg = responseData.message || '请求异常';
          if (showError) {
            wx.showToast({ title: errMsg, icon: 'none', duration: 2500 });
          }
          reject(new Error(errMsg));
        }
      },
      fail(err) {
        if (showLoading) wx.hideLoading();

        const errMsg = '网络连接失败，请检查网络设置';
        if (showError) {
          wx.showToast({ title: errMsg, icon: 'none', duration: 2500 });
        }
        reject(new Error(err.errMsg || errMsg));
      },
    });
  });
}

/** GET请求 */
export function get<T = unknown>(url: string, params?: Record<string, string | number | boolean | undefined>, options?: Partial<RequestOptions>): Promise<T> {
  return request<T>({ url, method: 'GET', params, ...options });
}

/** POST请求 */
export function post<T = unknown>(url: string, data?: Record<string, unknown> | unknown[], options?: Partial<RequestOptions>): Promise<T> {
  return request<T>({ url, method: 'POST', data, ...options });
}

/** PUT请求 */
export function put<T = unknown>(url: string, data?: Record<string, unknown> | unknown[], options?: Partial<RequestOptions>): Promise<T> {
  return request<T>({ url, method: 'PUT', data, ...options });
}

/** DELETE请求 */
export function del<T = unknown>(url: string, options?: Partial<RequestOptions>): Promise<T> {
  return request<T>({ url, method: 'DELETE', ...options });
}
