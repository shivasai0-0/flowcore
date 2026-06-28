'use client';

import React, { useEffect, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { Users, RefreshCw, Award, Activity, Heart } from 'lucide-react';

export default function CustomerAnalyticsPage() {
  const { businessId } = useWorkflowStore();
  const [customers, setCustomers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCustomers = async () => {
    if (!businessId) return;
    try {
      const res = await api.listCustomers(businessId);
      if (res.success && res.data) {
        setCustomers(res.data || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, [businessId]);

  const totalPoints = customers.reduce((sum, c) => sum + (c.loyalty_points || 0), 0);
  const avgPoints = customers.length > 0 ? (totalPoints / customers.length).toFixed(0) : '0';

  return (
    <div className="flex-1 p-8 flex flex-col gap-8 bg-slate-50/50">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Customer Analytics</h2>
          <p className="text-xs text-slate-500 mt-1">Review user engagement logs, loyalty metrics, and retention stats.</p>
        </div>
        <button 
          onClick={fetchCustomers}
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
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total Active Customers</span>
              <h3 className="text-3xl font-extrabold text-slate-900">{customers.length}</h3>
              <p className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1 mt-1">
                <Users className="w-3.5 h-3.5" /> Unique phone number contexts
              </p>
            </div>

            <div className="glass-card p-6 rounded-xl flex flex-col gap-2 bg-white">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total Loyalty Points Distributed</span>
              <h3 className="text-3xl font-extrabold text-slate-900">{totalPoints}</h3>
              <p className="text-[10px] text-slate-400 font-medium mt-1">Points accumulated from purchases</p>
            </div>

            <div className="glass-card p-6 rounded-xl flex flex-col gap-2 bg-white">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Average Points Per Customer</span>
              <h3 className="text-3xl font-extrabold text-slate-900">{avgPoints}</h3>
              <p className="text-[10px] text-slate-400 font-medium mt-1">Reflects frequency of repeat cart orders</p>
            </div>
          </div>

          {/* Row 2: Top Loyalty Leaderboard & Segment */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                <Award className="w-4 h-4 text-emerald-600" /> Top Customer Leaderboard
              </span>
              <div className="divide-y divide-slate-100 text-xs">
                {customers.slice(0, 5).map((c, i) => (
                  <div key={c.customer_id} className="flex justify-between items-center py-3">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-slate-400">#{i + 1}</span>
                      <div className="flex flex-col">
                        <span className="font-extrabold text-slate-800">{c.business_data?.name || 'Anonymous User'}</span>
                        <span className="text-[10px] text-slate-500 font-mono">{c.customer_id}</span>
                      </div>
                    </div>
                    <span className="font-bold text-emerald-600">{c.loyalty_points} points</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1">
                <Heart className="w-4 h-4 text-emerald-600" /> Retention Segments
              </span>
              
              <div className="flex flex-col gap-4 mt-2">
                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>Active Buyers (2+ orders)</span>
                    <span>65%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '65%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>One-Time Checkouts</span>
                    <span>25%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-blue-500 h-full rounded-full" style={{ width: '25%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>Idle/Incomplete Cart Conversions</span>
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
