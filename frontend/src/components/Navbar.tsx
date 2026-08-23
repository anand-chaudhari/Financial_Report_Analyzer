import React, { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';
import { TrendingUp, User as UserIcon, LogOut, Menu, X, Sparkles, LayoutDashboard, Sun, Moon } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-950/95 backdrop-blur-xl transition-colors duration-200">
      <div className="max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-3 group focus:outline-none">
          <div className="relative w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 via-emerald-500 to-teal-400 flex items-center justify-center shadow-md shadow-emerald-950/20 dark:shadow-emerald-950/80 group-hover:scale-105 group-hover:shadow-glow-emerald transition-all duration-300">
            <TrendingUp className="w-5 h-5 text-white transform group-hover:-translate-y-0.5 transition-transform" />
            <div className="absolute inset-0 rounded-xl bg-emerald-400 opacity-0 group-hover:opacity-20 blur-sm transition-opacity" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-lg font-extrabold text-slate-900 dark:text-white tracking-tight">
                FinSight <span className="text-emerald-600 dark:text-emerald-400">AI</span>
              </span>
              <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30">
                <Sparkles className="w-2.5 h-2.5" />
                Intelligence
              </span>
            </div>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium tracking-wide hidden sm:block">
              Financial Document Insights & Analytics
            </span>
          </div>
        </Link>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-2">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `px-3.5 py-2 text-sm font-medium rounded-xl transition-all duration-200 ${
                isActive
                  ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-900/80'
              }`
            }
          >
            Home
          </NavLink>

          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-xl transition-all duration-200 ${
                isActive
                  ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-900/80'
              }`
            }
          >
            <LayoutDashboard className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Dashboard</span>
          </NavLink>

          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle Theme"
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-900 border border-slate-200 dark:border-slate-800 transition-all ml-1 cursor-pointer"
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-400 transition-transform hover:rotate-45" />
            ) : (
              <Moon className="w-4 h-4 text-slate-700 transition-transform hover:-rotate-12" />
            )}
          </button>

          {/* User Profile / Auth Action */}
          {user ? (
            <div className="flex items-center gap-3 pl-3 ml-2 border-l border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
                {/* Profile Picture (Google Avatar or Initial) */}
                <div className="relative w-8 h-8 rounded-full overflow-hidden flex items-center justify-center bg-gradient-to-tr from-emerald-700 to-teal-500 text-xs font-bold text-white shadow-inner flex-shrink-0">
                  {user.photoURL ? (
                    <img
                      src={user.photoURL}
                      alt={user.displayName || 'User Avatar'}
                      className="w-full h-full object-cover"
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <span>{user.displayName ? user.displayName[0].toUpperCase() : 'U'}</span>
                  )}
                  <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-white dark:border-slate-950" />
                </div>

                <div className="flex flex-col text-left">
                  <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 line-clamp-1 max-w-[130px]">
                    {user.displayName || 'Analyst'}
                  </span>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400 truncate max-w-[130px]" title={user.email || ''}>
                    {user.email}
                  </span>
                </div>
              </div>

              <button
                onClick={handleLogout}
                title="Sign Out"
                className="p-2 rounded-xl text-slate-500 dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 border border-transparent hover:border-rose-200 dark:hover:border-rose-500/20 transition-all duration-200 focus:outline-none cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 pl-2">
              <Link
                to="/login"
                className="px-4 py-2 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-900 rounded-xl transition-all"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 rounded-xl shadow-lg shadow-emerald-950/20 dark:shadow-emerald-950/60 hover:shadow-glow-emerald transition-all"
              >
                <UserIcon className="w-4 h-4" />
                <span>Get Started</span>
              </Link>
            </div>
          )}
        </nav>

        {/* Mobile Actions: Theme + Hamburger */}
        <div className="flex md:hidden items-center gap-2">
          <button
            onClick={toggleTheme}
            aria-label="Toggle Theme"
            className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900 border border-slate-200 dark:border-slate-800"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
          </button>

          {user && (
            <div className="w-8 h-8 rounded-full overflow-hidden bg-emerald-600 flex items-center justify-center text-xs font-bold text-white">
              {user.photoURL ? (
                <img src={user.photoURL} alt={user.displayName || 'Avatar'} className="w-full h-full object-cover" referrerPolicy="no-referrer" />
              ) : (
                <span>{user.displayName ? user.displayName[0].toUpperCase() : 'U'}</span>
              )}
            </div>
          )}

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-900 border border-slate-200 dark:border-slate-800 transition-colors"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-950/95 backdrop-blur-2xl px-4 pt-3 pb-5 space-y-3 animate-fade-in-down">
          <NavLink
            to="/"
            onClick={() => setMobileMenuOpen(false)}
            className={({ isActive }) =>
              `block px-4 py-2.5 rounded-xl text-sm font-medium ${
                isActive
                  ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                  : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900'
              }`
            }
          >
            Home
          </NavLink>
          <NavLink
            to="/dashboard"
            onClick={() => setMobileMenuOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium ${
                isActive
                  ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                  : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900'
              }`
            }
          >
            <LayoutDashboard className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Dashboard</span>
          </NavLink>

          {user ? (
            <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-3">
              <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-slate-100 dark:bg-slate-900 text-xs">
                <div className="w-8 h-8 rounded-full overflow-hidden bg-emerald-600 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
                  {user.photoURL ? (
                    <img src={user.photoURL} alt={user.displayName || 'Avatar'} className="w-full h-full object-cover" referrerPolicy="no-referrer" />
                  ) : (
                    <span>{user.displayName ? user.displayName[0].toUpperCase() : 'U'}</span>
                  )}
                </div>
                <div className="overflow-hidden">
                  <div className="font-semibold text-slate-800 dark:text-slate-200 truncate">{user.displayName}</div>
                  <div className="text-slate-500 dark:text-slate-400 truncate">{user.email}</div>
                </div>
              </div>
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign Out</span>
              </button>
            </div>
          ) : (
            <div className="pt-3 border-t border-slate-200 dark:border-slate-800 grid grid-cols-2 gap-2">
              <Link
                to="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="text-center py-2.5 rounded-xl text-sm font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                onClick={() => setMobileMenuOpen(false)}
                className="text-center py-2.5 rounded-xl text-sm font-semibold text-white bg-emerald-600"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
};
