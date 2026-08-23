export * from './auth';
export * from './report';
export * from './chat';
export * from './financial';

export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data: T;
  error?: string;
}
