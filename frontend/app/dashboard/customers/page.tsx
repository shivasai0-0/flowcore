'use client';

import React, { useEffect, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { Users, RefreshCw, Search, Award, ShoppingCart, Calendar, AlertTriangle } from 'lucide-react';

export default function CustomersPage() {
  const { businessId } = useWorkflowStore();
  const [customers, setCustomers] = useState<any[]>([]);
  const [filteredCustomers, setFilteredCustomers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

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

  useEffect(() => {
    if (search.trim()) {
      const term = search.toLowerCase();
      setFilteredCustomers(
        customers.filter(c => 
          c.customer_id.includes(term) || 
          (c.business_data?.name && c.business_data.name.toLowerCase().includes(term))
        )
      );
    } else {
      setFilteredCustomers(customers);
    }
  }, [customers, search]);

  return (
    <div className="flex-1 p-8 flex flex-col gap-6 bg-slate-50/50">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Customer Directory</h2>
          <p className="text-xs text-slate-500 mt-1">View and manage shared consumer contexts, loyalty points, and cross-channel profiles.</p>
        </div>
        <button 
          onClick={fetchCustomers}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      <div className="flex gap-4 justify-between items-center bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by Phone or Name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
          />
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
          <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin mb-2" />
          <span className="text-xs font-semibold">Fetching customer contexts...</span>
        </div>
      ) : filteredCustomers.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredCustomers.map((c) => (
            <div key={c.customer_id} className="glass-card p-6 rounded-xl flex flex-col gap-4 bg-white border border-slate-200">
              {/* Card Header */}
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center font-bold text-emerald-600 border border-emerald-100 shrink-0 text-sm">
                    {c.business_data?.name ? c.business_data.name[0].toUpperCase() : 'C'}
                  </div>
                  <div>
                    <h4 className="text-sm font-extrabold text-slate-900">{c.business_data?.name || 'Anonymous Customer'}</h4>
                    <span className="text-xs text-slate-500 font-mono">{c.customer_id}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 bg-amber-50 border border-amber-100 px-2 py-0.5 rounded text-[10px] font-bold text-amber-700">
                  <Award className="w-3.5 h-3.5 text-amber-500" />
                  {c.loyalty_points || 0} Pts
                </div>
              </div>

              {/* Context Lists */}
              <div className="flex flex-col gap-2.5">
                {/* Active Orders */}
                <div className="flex items-start gap-2 text-xs">
                  <ShoppingCart className="w-4 h-4 text-purple-500 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <span className="font-semibold text-slate-700">Orders: </span>
                    {c.active_orders && c.active_orders.length > 0 ? (
                      <span className="text-purple-600 font-bold">
                        {c.active_orders.length} active (Total: ${c.active_orders.reduce((sum: number, o: any) => sum + parseFloat(o.total || 0), 0).toFixed(2)})
                      </span>
                    ) : (
                      <span className="text-slate-400">No active orders</span>
                    )}
                  </div>
                </div>

                {/* Active Bookings */}
                <div className="flex items-start gap-2 text-xs">
                  <Calendar className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <span className="font-semibold text-slate-700">Bookings: </span>
                    {c.active_bookings && c.active_bookings.length > 0 ? (
                      <span className="text-blue-600 font-bold">
                        {c.active_bookings.length} reservation(s) scheduled
                      </span>
                    ) : (
                      <span className="text-slate-400">No active bookings</span>
                    )}
                  </div>
                </div>

                {/* Active Support Tickets */}
                <div className="flex items-start gap-2 text-xs">
                  <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <span className="font-semibold text-slate-700">Support Tickets: </span>
                    {c.support_tickets && c.support_tickets.length > 0 ? (
                      <span className="text-rose-600 font-bold">
                        {c.support_tickets.length} ticket(s) open
                      </span>
                    ) : (
                      <span className="text-slate-400">Zero active issues</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Card Footer */}
              <div className="flex justify-between items-center border-t border-slate-100 pt-3 text-[10px] text-slate-400 font-medium mt-1">
                <span>Last updated: {new Date(c.updated_at).toLocaleString()}</span>
                <span className="font-mono text-[9px]">ID: {c.customer_id.replace('+', '')}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-12 text-center text-xs text-slate-400 font-semibold border border-dashed border-slate-200 rounded-xl bg-white shadow-sm flex flex-col items-center gap-2">
          <Users className="w-8 h-8 text-slate-300" />
          No customers found matching the search criteria.
        </div>
      )}
    </div>
  );
}
