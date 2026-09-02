export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const APP_CONFIG = {
  appName: 'FinSight AI',
  tagline: 'Intelligent Financial Document Analysis & Visual Insights',
  maxFileSizeMB: 25,
  allowedMimeTypes: ['application/pdf'],
};

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  REPORT_ANALYSIS: '/reports/:reportId',
};
