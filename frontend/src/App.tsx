import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { ReportProvider } from './context/ReportContext';
import { MainLayout } from './layouts/MainLayout';
import { AuthLayout } from './layouts/AuthLayout';
import { ProtectedRoute, PublicRoute } from './components/auth';
import { PageLoadingState } from './components/PageLoadingState';

// Route-level code splitting for instant initial page render & fast load times
const HomePage = lazy(() => import('./pages/HomePage').then((m) => ({ default: m.HomePage })));
const LoginPage = lazy(() => import('./pages/LoginPage').then((m) => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import('./pages/RegisterPage').then((m) => ({ default: m.RegisterPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })));
const ReportsPage = lazy(() => import('./pages/ReportsPage').then((m) => ({ default: m.ReportsPage })));
const UploadPage = lazy(() => import('./pages/UploadPage').then((m) => ({ default: m.UploadPage })));
const AnalystPage = lazy(() => import('./pages/AnalystPage').then((m) => ({ default: m.AnalystPage })));
const ComparePage = lazy(() => import('./pages/ComparePage').then((m) => ({ default: m.ComparePage })));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage })));
const ChatHistoryPage = lazy(() => import('./pages/ChatHistoryPage').then((m) => ({ default: m.ChatHistoryPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })));
const ReportAnalysisPage = lazy(() => import('./pages/ReportAnalysisPage').then((m) => ({ default: m.ReportAnalysisPage })));
const ReportSummaryPage = lazy(() => import('./pages/ReportSummaryPage').then((m) => ({ default: m.ReportSummaryPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })));

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ReportProvider>
          <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Suspense fallback={<PageLoadingState />}>
              <Routes>
                {/* Public Layout / Landing */}
                <Route element={<MainLayout />}>
                  <Route path="/" element={<HomePage />} />

                  {/* Protected Dashboard & App Routes */}
                  <Route
                    path="/dashboard"
                    element={
                      <ProtectedRoute>
                        <DashboardPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/reports"
                    element={
                      <ProtectedRoute>
                        <ReportsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/upload"
                    element={
                      <ProtectedRoute>
                        <UploadPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/analyst"
                    element={
                      <ProtectedRoute>
                        <AnalystPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/compare"
                    element={
                      <ProtectedRoute>
                        <ComparePage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/summary"
                    element={
                      <ProtectedRoute>
                        <ReportSummaryPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/analytics"
                    element={
                      <ProtectedRoute>
                        <AnalyticsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/history"
                    element={
                      <ProtectedRoute>
                        <ChatHistoryPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/settings"
                    element={
                      <ProtectedRoute>
                        <SettingsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/reports/:id/summary"
                    element={
                      <ProtectedRoute>
                        <ReportSummaryPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/reports/:reportId"
                    element={
                      <ProtectedRoute>
                        <ReportAnalysisPage />
                      </ProtectedRoute>
                    }
                  />
                </Route>

                {/* Auth Layout: Guest-only routes */}
                <Route element={<AuthLayout />}>
                  <Route
                    path="/login"
                    element={
                      <PublicRoute>
                        <LoginPage />
                      </PublicRoute>
                    }
                  />
                  <Route
                    path="/register"
                    element={
                      <PublicRoute>
                        <RegisterPage />
                      </PublicRoute>
                    }
                  />
                </Route>

                {/* 404 Catch-All Route */}
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </Suspense>
          </Router>
        </ReportProvider>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;

