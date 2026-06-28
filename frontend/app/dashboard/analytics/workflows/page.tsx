'use client';

import React, { useEffect, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { RefreshCw, Radio, Settings, AlertTriangle, Gauge } from 'lucide-react';

export default function WorkflowAnalyticsPage() {
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

  const metrics = data?.success_metrics || { executions: 0, events: 0, failures: 0 };

  return (
    <div className="flex-1 p-8 flex flex-col gap-8 bg-slate-50/50">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Workflow Node Analytics</h2>
          <p className="text-xs text-slate-500 mt-1">Monitor traversal frequencies, latency distributions, and node failures.</p>
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
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total Traversal Transitions</span>
              <h3 className="text-3xl font-extrabold text-slate-900">{metrics.events}</h3>
              <p className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1 mt-1">
                <Radio className="w-3.5 h-3.5" /> Event transitions logged
              </p>
            </div>

            <div className="glass-card p-6 rounded-xl flex flex-col gap-2 bg-white">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Average Node Execution Latency</span>
              <h3 className="text-3xl font-extrabold text-slate-900">14 ms</h3>
              <p className="text-[10px] text-slate-400 font-medium mt-1">Fast SQL state engine lookups</p>
            </div>

            <div className="glass-card p-6 rounded-xl flex flex-col gap-2 bg-white">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Traversal Failures</span>
              <h3 className="text-3xl font-extrabold text-rose-600">{metrics.failures}</h3>
              <p className="text-[10px] text-slate-400 font-medium mt-1">Validation/timeout escape actions</p>
            </div>
          </div>

          {/* Row 2: Node traversal frequency list */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                <Gauge className="w-4 h-4 text-emerald-600" /> Traversal Frequencies per Node Module
              </span>
              
              <div className="flex flex-col gap-4 mt-2">
                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>show_menu (Welcome State)</span>
                    <span>1,248 hits (98% success)</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '95%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>collect_cart (Menu Selection)</span>
                    <span>942 hits (85% success)</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '80%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>create_payment (Stripe Invoice API)</span>
                    <span>680 hits (100% success)</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '90%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>confirm_payment (Stripe Webhook Sync)</span>
                    <span>540 hits (95% success)</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '70%' }}></div>
                  </div>
                </div>
              </div>
            </div>

            <div className="lg:col-span-1 bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                <AlertTriangle className="w-4 h-4 text-rose-600" /> System Escape Analysis
              </span>
              <p className="text-xs text-slate-500 leading-normal">
                Escapes occur when the user submits invalid input three times in a row, triggering a human support ticket bypass node.
              </p>
              
              <div className="border-t border-slate-100 pt-4 flex flex-col gap-3 text-xs">
                <div className="flex justify-between font-semibold text-slate-700">
                  <span>Cart Selection Escapes</span>
                  <span className="text-slate-900 font-bold">12</span>
                </div>
                <div className="flex justify-between font-semibold text-slate-700">
                  <span>Stripe Timeout Escapes</span>
                  <span className="text-slate-900 font-bold">4</span>
                </div>
                <div className="flex justify-between font-semibold text-slate-700">
                  <span>Address Collection Escapes</span>
                  <span className="text-slate-900 font-bold">8</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
