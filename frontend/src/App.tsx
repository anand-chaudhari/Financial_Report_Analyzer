import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { ReportProvider } from './context/ReportContext';
import { MainLayout } from './layouts/MainLayout';
import { AuthLayout } from './layouts/AuthLayout';
import { ProtectedRoute, PublicRoute } from './components/auth';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { ReportsPage } from './pages/ReportsPage';
import { UploadPage } from './pages/UploadPage';
import { AnalystPage } from './pages/AnalystPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { ChatHistoryPage } from './pages/ChatHistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import { ReportAnalysisPage } from './pages/ReportAnalysisPage';
import { ReportSummaryPage } from './pages/ReportSummaryPage';
import { NotFoundPage } from './pages/NotFoundPage';

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ReportProvider>
          <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
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
          </Router>
        </ReportProvider>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
