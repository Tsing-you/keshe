import axios from 'axios';
import { showToast } from './utils/toast';

const api = axios.create({
  baseURL: '/api',
  timeout: 5000
});

api.interceptors.request.use(config => {
  // Attach JWT token if available
  try {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers = config.headers || {};
      config.headers['Authorization'] = `Bearer ${token}`;
    } else {
      // fallback: if legacy credentials are stored, and it's a mutating request, attach them
      const credsStr = localStorage.getItem('credentials');
      if (credsStr) {
        const creds = JSON.parse(credsStr);
        if (['post', 'put', 'patch'].includes(config.method?.toLowerCase())) {
          if (!config.data) config.data = {};
          if (config.data instanceof FormData) {
            if (!config.data.has('account')) config.data.append('account', creds.account);
            if (!config.data.has('password')) config.data.append('password', creds.password);
          } else {
            config.data = { ...creds, ...config.data };
          }
        }
      }
    }
  } catch (e) {}
  return config;
}, error => {
  return Promise.reject(error);
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || error.message || '请求失败';
    const status = error.response?.status;
    const url = error.config?.url || '';

    // Debug log to help trace intermittent logout
    console.debug('[api] response error', { status, url, message });

    // Only treat 401 as session expired. Avoid auto-logout for generic "账号或密码错误"
    // because that can legitimately occur during a login attempt.
    if (status === 401) {
      console.debug('[api] auth expired -> clearing session');
      localStorage.removeItem('user');
      localStorage.removeItem('credentials');
      if (window.location.pathname !== '/login') {
        showToast('登录状态已过期，请重新登录', 'error');
        window.location.href = '/login';
      }
    } else if (status >= 500) {
      showToast('服务器繁忙，请稍后再试', 'error');
    }

    return Promise.reject(error);
  }
);

export default api;
