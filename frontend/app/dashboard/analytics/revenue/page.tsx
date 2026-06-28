'use client';

import React, { useEffect, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { DollarSign, RefreshCw, BarChart3, TrendingUp, CreditCard } from 'lucide-react';

export default function RevenueAnalyticsPage() {
  const { businessId } = useWorkflowStore();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchOverview = async () => {
    if (!businessId) return;
    try {
      const res = await api.getDashboardOverview(businessId);
      if (res.success && res.data) {
        setData(res.data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, [businessId]);

  const kpis = data?.kpis || { orders: 0, revenue: 0.0 };
  const avgOrderValue = kpis.orders > 0 ? (kpis.revenue / kpis.orders) : 0.0;

  return (
    <div className="flex-1 p-8 flex flex-col gap-8 bg-slate-50/50">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Revenue Analytics</h2>
          <p className="text-xs text-slate-500 mt-1">Detailed performance audit of transactions processed via the automated checkout system.</p>
        </div>
        <button 
          onClick={fetchOverview}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
          <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin" />
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          {/* Row 1: KPI Blocks */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-card p-6 rounded-xl flex flex-col gap-2 bg-white">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Gross Revenue</span>
              <h3 className="text-3xl font-extrabold text-slate-900">${kpis.revenue.toFixed(2)}</h3>
              <p className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1 mt-1">
                <TrendingUp className="w-3.5 h-3.5" /> 100% automated traversal sales
              </p>
            </div>

            <div className="glass-card p-6 rounded-xl flex flex-col gap-2 bg-white">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Checkout Orders</span>
              <h3 className="text-3xl font-extrabold text-slate-900">{kpis.orders}</h3>
              <p className="text-[10px] text-slate-400 font-medium mt-1">Cart checkout states reached</p>
            </div>

            <div className="glass-card p-6 rounded-xl flex flex-col gap-2 bg-white">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Average Order Value (AOV)</span>
              <h3 className="text-3xl font-extrabold text-slate-900">${avgOrderValue.toFixed(2)}</h3>
              <p className="text-[10px] text-slate-400 font-medium mt-1">Average cart ticket size value</p>
            </div>
          </div>

          {/* Row 2: Premium Interactive SVG Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                <BarChart3 className="w-4 h-4 text-emerald-600" /> Hourly Transaction Velocity
              </span>
              
              <div className="h-64 flex items-end justify-between gap-4 pt-8 pb-2 px-2 border-b border-slate-100">
                {/* SVG Mocking a sleek area/bar chart */}
                {[30, 45, 25, 60, 80, 55, 95, 70, 85, 100].map((h, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center gap-2 group h-full justify-end">
                    <div 
                      style={{ height: `${h}%` }}
                      className="w-full bg-gradient-to-t from-emerald-500 to-emerald-400 rounded-t hover:from-emerald-600 hover:to-emerald-500 transition-all cursor-pointer relative"
                    >
                      <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[9px] px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity font-bold">
                        ${(h * 3.4).toFixed(0)}
                      </div>
                    </div>
                    <span className="text-[9px] font-semibold text-slate-400">0{i}:00</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="lg:col-span-1 bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                <CreditCard className="w-4 h-4 text-emerald-600" /> Gateway Breakdown
              </span>
              
              <div className="flex flex-col gap-4 mt-4">
                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>Stripe Link Checkout</span>
                    <span>70%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '70%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>Razorpay Invoice</span>
                    <span>20%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-blue-500 h-full rounded-full" style={{ width: '20%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>Cash on Delivery</span>
                    <span>10%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-purple-500 h-full rounded-full" style={{ width: '10%' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
