import axios from 'axios';
import { useAuthStore } from '../stores/auth';
import router from '../router';

// URLs relativas (/api/...) em todos os ambientes:
// - Local: o proxy do Vite (vite.config.ts) encaminha /api para o backend em :8000.
// - Vercel: o rewrite do vercel.json encaminha /api para o backend no Render.
// Assim, o endereço do Render fica definido em um único lugar (vercel.json).
const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  }
});

api.interceptors.request.use(config => {
  const authStore = useAuthStore();
  const token = authStore.accessToken;
  
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    const authStore = useAuthStore();

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise(function(resolve, reject) {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await api.post('/api/token/refresh');
        authStore.setToken(data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        processQueue(null, data.access_token);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        authStore.logout(router);
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;