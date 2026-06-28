'use client';

import React, { useEffect, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { Radio, RefreshCw, Zap, TrendingUp, BarChart2 } from 'lucide-react';

export default function ConversionsPage() {
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

  const metrics = data?.success_metrics || { executions: 0, success_rate: 100.0, failures: 0 };

  return (
    <div className="flex-1 p-8 flex flex-col gap-8 bg-slate-50/50">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Conversion Funnel</h2>
          <p className="text-xs text-slate-500 mt-1">Audit user transition completion rates through each operational FSM stage.</p>
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
          {/* Funnel KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-card p-6 rounded-xl flex flex-col gap-2 bg-white">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Completed traversals</span>
              <h3 className="text-3xl font-extrabold text-slate-900">
                {Math.round(metrics.executions * (metrics.success_rate / 100))}
              </h3>
              <p className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1 mt-1">
                <Zap className="w-3.5 h-3.5" /> Reached FSM terminal state
              </p>
            </div>

            <div className="glass-card p-6 rounded-xl flex flex-col gap-2 bg-white">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total Sessions Started</span>
              <h3 className="text-3xl font-extrabold text-slate-900">{metrics.executions}</h3>
              <p className="text-[10px] text-slate-400 font-medium mt-1">Initiated customer chat traces</p>
            </div>

            <div className="glass-card p-6 rounded-xl flex flex-col gap-2 bg-white">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Overall Conversion Rate</span>
              <h3 className="text-3xl font-extrabold text-emerald-650">{metrics.success_rate}%</h3>
              <p className="text-[10px] text-slate-400 font-medium mt-1">FSM path validation success rate</p>
            </div>
          </div>

          {/* conversion funnel visual diagram */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-6">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
              <BarChart2 className="w-4 h-4 text-emerald-600" /> Operational Conversion Funnel (START → terminal)
            </span>

            <div className="flex flex-col gap-4 max-w-2xl mx-auto w-full py-4">
              {/* Funnel Stage 1 */}
              <div className="flex items-center gap-4">
                <span className="w-32 text-xs font-bold text-slate-500 uppercase">1. Session Start</span>
                <div className="flex-1 bg-slate-100 h-8 rounded-lg overflow-hidden relative">
                  <div className="bg-emerald-500 h-full rounded-lg" style={{ width: '100%' }}></div>
                  <span className="absolute inset-y-0 right-4 flex items-center text-xs font-extrabold text-emerald-950">100%</span>
                </div>
              </div>

              {/* Funnel Stage 2 */}
              <div className="flex items-center gap-4">
                <span className="w-32 text-xs font-bold text-slate-500 uppercase">2. View Catalog</span>
                <div className="flex-1 bg-slate-100 h-8 rounded-lg overflow-hidden relative">
                  <div className="bg-emerald-500/90 h-full rounded-lg" style={{ width: '85%' }}></div>
                  <span className="absolute inset-y-0 right-4 flex items-center text-xs font-extrabold text-emerald-950">85%</span>
                </div>
              </div>

              {/* Funnel Stage 3 */}
              <div className="flex items-center gap-4">
                <span className="w-32 text-xs font-bold text-slate-500 uppercase">3. Create Cart</span>
                <div className="flex-1 bg-slate-100 h-8 rounded-lg overflow-hidden relative">
                  <div className="bg-emerald-500/80 h-full rounded-lg" style={{ width: '70%' }}></div>
                  <span className="absolute inset-y-0 right-4 flex items-center text-xs font-extrabold text-emerald-950">70%</span>
                </div>
              </div>

              {/* Funnel Stage 4 */}
              <div className="flex items-center gap-4">
                <span className="w-32 text-xs font-bold text-slate-500 uppercase">4. checkout link</span>
                <div className="flex-1 bg-slate-100 h-8 rounded-lg overflow-hidden relative">
                  <div className="bg-emerald-500/70 h-full rounded-lg" style={{ width: '55%' }}></div>
                  <span className="absolute inset-y-0 right-4 flex items-center text-xs font-extrabold text-emerald-950">55%</span>
                </div>
              </div>

              {/* Funnel Stage 5 */}
              <div className="flex items-center gap-4">
                <span className="w-32 text-xs font-bold text-slate-500 uppercase">5. Confirmed Payment</span>
                <div className="flex-1 bg-slate-100 h-8 rounded-lg overflow-hidden relative">
                  <div className="bg-emerald-500/60 h-full rounded-lg" style={{ width: `${metrics.success_rate}%` }}></div>
                  <span className="absolute inset-y-0 right-4 flex items-center text-xs font-extrabold text-emerald-950">
                    {metrics.success_rate}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
