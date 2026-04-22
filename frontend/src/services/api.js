import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
});

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401 — try to refresh, then retry the original request once
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem('refresh');

      if (refresh) {
        try {
          const { data } = await axios.post(
            'http://localhost:8000/api/auth/refresh/',
            { refresh }
          );
          localStorage.setItem('access', data.access);
          if (data.refresh) localStorage.setItem('refresh', data.refresh);
          original.headers.Authorization = `Bearer ${data.access}`;
          return api(original);
        } catch {
          localStorage.removeItem('access');
          localStorage.removeItem('refresh');
          window.location.href = '/login';
        }
      } else {
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default api;