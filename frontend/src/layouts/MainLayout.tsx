import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from '../components/Header';
import { Sidebar } from '../components/Sidebar';

export const MainLayout: React.FC = () => {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('finsight_sidebar_collapsed');
    return saved === 'true';
  });

  const toggleSidebarCollapse = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('finsight_sidebar_collapsed', String(next));
      return next;
    });
  };

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200 overflow-x-hidden">
      {/* Sidebar (Desktop and Mobile) */}
      <Sidebar
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
        collapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebarCollapse}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 w-full">
        <Header
          onToggleMobileSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)}
          onToggleDesktopSidebar={toggleSidebarCollapse}
          sidebarCollapsed={sidebarCollapsed}
        />
        <main className="flex-1 p-3 sm:p-5 lg:p-7 max-w-[1600px] w-full mx-auto animate-fade-in min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
