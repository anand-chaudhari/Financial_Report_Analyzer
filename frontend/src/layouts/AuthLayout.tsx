import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { TrendingUp, Shield, Sun, Moon } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';

export const AuthLayout: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="relative min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col justify-center items-center p-4 sm:p-6 overflow-hidden bg-grid-pattern transition-colors duration-200">
      {/* Theme Toggle Top-Right */}
      <div className="absolute top-4 right-4 z-20">
        <button
          onClick={toggleTheme}
          aria-label="Toggle Theme"
          className="p-2.5 rounded-xl bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 shadow-sm hover:scale-105 transition-all"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
        </button>
      </div>

      {/* Ambient background glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] bg-emerald-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[350px] h-[350px] bg-cyan-500/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Header Brand */}
      <div className="relative mb-6 text-center space-y-2 animate-fade-in-down">
        <Link to="/" className="inline-flex items-center gap-3 group focus:outline-none">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-600 via-emerald-500 to-teal-400 flex items-center justify-center shadow-xl shadow-emerald-950/20 dark:shadow-emerald-950/80 group-hover:scale-105 group-hover:shadow-glow-emerald transition-all duration-300">
            <TrendingUp className="w-6 h-6 text-white" />
          </div>
          <div className="text-left">
            <span className="text-2xl font-extrabold bg-gradient-to-r from-slate-900 via-slate-700 to-emerald-600 dark:from-white dark:via-slate-100 dark:to-emerald-400 bg-clip-text text-transparent">
              FinSight AI
            </span>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
              Intelligent Financial Document Platform
            </p>
          </div>
        </Link>
      </div>

      {/* Auth Card */}
      <div className="relative w-full max-w-md bg-white/90 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800/90 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-2xl animate-fade-in-up">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-[1.5px] bg-gradient-to-r from-transparent via-emerald-500 to-transparent opacity-80" />
        <Outlet />
      </div>

      {/* Security Note */}
      <div className="relative mt-6 text-center flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500 animate-fade-in">
        <Shield className="w-3.5 h-3.5 text-emerald-500" />
        <span>Secure Encrypted Cloud Authentication</span>
      </div>
    </div>
  );
};
