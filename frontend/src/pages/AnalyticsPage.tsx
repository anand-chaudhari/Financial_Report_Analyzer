import React, { useState } from 'react';
import { useTheme } from '../hooks/useTheme';
import { MOCK_REPORTS } from '../utils/mockData';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
} from 'recharts';
import { BarChart3, TrendingUp, DollarSign, PieChart, Sparkles } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const { theme } = useTheme();
  const [selectedTicker, setSelectedTicker] = useState('AAPL');

  const chartTheme = {
    grid: theme === 'dark' ? '#334155' : '#e2e8f0',
    axis: theme === 'dark' ? '#94a3b8' : '#64748b',
    tooltipBg: theme === 'dark' ? '#0f172a' : '#ffffff',
    tooltipBorder: theme === 'dark' ? '#334155' : '#cbd5e1',
    tooltipText: theme === 'dark' ? '#f8fafc' : '#0f172a',
  };

  const revenueData = [
    { period: '2021', value: 365.8 },
    { period: '2022', value: 394.3 },
    { period: '2023', value: 383.3 },
    { period: '2024', value: 391.0 },
  ];

  const netIncomeData = [
    { period: '2021', value: 94.7 },
    { period: '2022', value: 99.8 },
    { period: '2023', value: 96.9 },
    { period: '2024', value: 93.7 },
  ];

  return (
    <div className="space-y-6 animate-fade-in w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Financial Visual Analytics
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Automated statement extraction & time-series trajectory modeling
          </p>
        </div>

        {/* Company Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Company:</span>
          <select
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value)}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-emerald-500"
          >
            <option value="AAPL">Apple Inc. (AAPL)</option>
            <option value="MSFT">Microsoft Corp (MSFT)</option>
            <option value="NVDA">NVIDIA Corp (NVDA)</option>
            <option value="TSLA">Tesla Inc. (TSLA)</option>
          </select>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Chart */}
        <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>Annual Revenue Trend ($B)</span>
            </h3>
            <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">+2.0% YoY</span>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={revenueData}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.4} />
                <XAxis dataKey="period" stroke={chartTheme.axis} fontSize={12} />
                <YAxis stroke={chartTheme.axis} fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: chartTheme.tooltipBg,
                    borderColor: chartTheme.tooltipBorder,
                    borderRadius: '12px',
                    color: chartTheme.tooltipText,
                  }}
                />
                <Bar dataKey="value" fill="#10b981" radius={[6, 6, 0, 0]} name="Revenue ($B)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Net Income Trend */}
        <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              <span>Net Income Trajectory ($B)</span>
            </h3>
            <span className="text-xs font-bold text-cyan-600 dark:text-cyan-400">24.0% Margin</span>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={netIncomeData}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} opacity={0.4} />
                <XAxis dataKey="period" stroke={chartTheme.axis} fontSize={12} />
                <YAxis stroke={chartTheme.axis} fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: chartTheme.tooltipBg,
                    borderColor: chartTheme.tooltipBorder,
                    borderRadius: '12px',
                    color: chartTheme.tooltipText,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#06b6d4"
                  strokeWidth={3}
                  dot={{ r: 4, fill: '#06b6d4' }}
                  name="Net Income ($B)"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Key Financial Ratios Cards */}
      <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
          Extracted Key Ratios & Operating Metrics
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400 block font-medium">Gross Margin</span>
            <span className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1 block">46.2%</span>
            <span className="text-[10px] text-slate-400 mt-1 block">Products 37.1% • Services 74.0%</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400 block font-medium">Operating Margin</span>
            <span className="text-2xl font-extrabold text-cyan-600 dark:text-cyan-400 mt-1 block">31.2%</span>
            <span className="text-[10px] text-slate-400 mt-1 block">Operating Income $123.2B</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400 block font-medium">Free Cash Flow</span>
            <span className="text-2xl font-extrabold text-indigo-600 dark:text-indigo-400 mt-1 block">$108.8B</span>
            <span className="text-[10px] text-slate-400 mt-1 block">Operating Cash $118.3B</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400 block font-medium">Diluted EPS</span>
            <span className="text-2xl font-extrabold text-amber-600 dark:text-amber-400 mt-1 block">$6.08</span>
            <span className="text-[10px] text-slate-400 mt-1 block">+10% YoY growth</span>
          </div>
        </div>
      </div>
    </div>
  );
};
