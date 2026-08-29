import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { useReportContext } from '../context/ReportContext';
import {
  LayoutDashboard,
  FileText,
  UploadCloud,
  Bot,
  BarChart3,
  MessageSquare,
  Settings,
  Sparkles,
  TrendingUp,
  Scale,
  X,
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  mobileOpen,
  onCloseMobile,
  collapsed = false,
  onToggleCollapse,
}) => {
  const { reports } = useReportContext();
  const reportsCount = reports.length;

  const mainNav = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    {
      to: '/reports',
      label: 'My Reports',
      icon: FileText,
      badge: reportsCount > 0 ? String(reportsCount) : undefined,
    },
    { to: '/upload', label: 'Upload Report', icon: UploadCloud },
    { to: '/analyst', label: 'AI Analyst', icon: Bot, isNew: true },
    { to: '/compare', label: 'Compare Filings', icon: Scale },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/history', label: 'Chat History', icon: MessageSquare },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  const sidebarContent = (isMobileView = false) => (
    <div className={`flex flex-col justify-between h-full select-none transition-all duration-300 ${collapsed && !isMobileView ? 'p-2.5' : 'p-4'}`}>
      <div className="space-y-6">
        {/* Brand Logo in Sidebar */}
        <div className={`flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/80 ${collapsed && !isMobileView ? 'px-1 justify-center' : 'px-2'}`}>
          <Link
            to="/dashboard"
            onClick={onCloseMobile}
            className="flex items-center gap-3 group"
            title="FinSight AI Dashboard"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 via-emerald-500 to-teal-400 flex items-center justify-center shadow-md shadow-emerald-950/20 dark:shadow-emerald-950/80 group-hover:scale-105 transition-all flex-shrink-0">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            {(!collapsed || isMobileView) && (
              <div className="flex flex-col overflow-hidden">
                <div className="flex items-center gap-1.5">
                  <span className="text-base font-extrabold text-slate-900 dark:text-white tracking-tight truncate">
                    FinSight <span className="text-emerald-600 dark:text-emerald-400">AI</span>
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 dark:text-slate-500 font-medium truncate">
                  Financial Report Intelligence
                </span>
              </div>
            )}
          </Link>

          {/* Close button on mobile */}
          {isMobileView && onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 md:hidden cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Navigation links */}
        <div>
          {(!collapsed || isMobileView) && (
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 px-3 mb-2">
              Main Menu
            </div>
          )}
          <nav className="space-y-1">
            {mainNav.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onCloseMobile}
                  title={collapsed && !isMobileView ? item.label : undefined}
                  className={({ isActive }) =>
                    `group flex items-center rounded-xl font-semibold transition-all duration-200 ${
                      collapsed && !isMobileView
                        ? 'justify-center p-2.5 my-1 text-sm'
                        : 'justify-between px-3 py-2.5 text-xs sm:text-sm'
                    } ${
                      isActive
                        ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 shadow-xs'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-900'
                    }`
                  }
                >
                  <div className={`flex items-center ${collapsed && !isMobileView ? 'justify-center' : 'gap-3'}`}>
                    <Icon className="w-4 h-4 text-slate-500 dark:text-slate-400 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors flex-shrink-0" />
                    {(!collapsed || isMobileView) && <span>{item.label}</span>}
                  </div>

                  {(!collapsed || isMobileView) && (
                    <div className="flex items-center gap-1.5">
                      {item.badge && (
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 group-hover:bg-emerald-500/20 group-hover:text-emerald-700 dark:group-hover:text-emerald-400 transition-colors">
                          {item.badge}
                        </span>
                      )}

                      {item.isNew && (
                        <span className="px-1.5 py-0.2 rounded-md text-[9px] font-bold uppercase bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                          AI
                        </span>
                      )}
                    </div>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Footer System Status & Collapse Toggle */}
      <div className="space-y-3 pt-4 border-t border-slate-100 dark:border-slate-800/80">
        {(!collapsed || isMobileView) ? (
          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-900 dark:text-slate-200 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
                FinSight Core
              </span>
              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Active
              </span>
            </div>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Financial Intelligence Engine
            </p>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" title="FinSight Core Active" />
          </div>
        )}

        {/* Desktop Collapse / Expand Button */}
        {!isMobileView && onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="w-full flex items-center justify-center gap-2 py-2 px-2.5 rounded-xl text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors text-xs font-semibold cursor-pointer border border-transparent hover:border-slate-200 dark:hover:border-slate-800"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <PanelLeftOpen className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <>
                <PanelLeftClose className="w-4 h-4 text-slate-500" />
                <span>Collapse Sidebar</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside
        className={`border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 hidden md:block min-h-screen sticky top-0 transition-all duration-300 flex-shrink-0 z-30 ${
          collapsed ? 'w-20' : 'w-64'
        }`}
      >
        {sidebarContent(false)}
      </aside>

      {/* Mobile Drawer with Backdrop */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex animate-fade-in">
          {/* Overlay */}
          <div
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
          />
          {/* Drawer panel */}
          <div className="relative w-72 max-w-[85vw] bg-white dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 h-full shadow-2xl z-10 animate-fade-in-right">
            {sidebarContent(true)}
          </div>
        </div>
      )}
    </>
  );
};

export default Sidebar;
