import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { getIdToken } from 'firebase/auth';
import { auth } from '../firebase/config';
import { API_BASE_URL } from '../utils/constants';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 180000, // 3 min timeout for RAG processing & vector embeddings
});

// Request Interceptor: Attach fresh Firebase Bearer Token
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      const user = auth.currentUser;
      if (user) {
        // Force-refresh ensures we never send an expired 1-hour-old token
        const token = await getIdToken(user, true);
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
    } catch (err) {
      console.warn('Could not attach auth token to request:', err);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Global Error Logging & Format
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.warn('Unauthorized request. User session may have expired.');
    }
    return Promise.reject(error);
  }
);

export default apiClient;
