'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { ShoppingBag, RefreshCw, Search, CheckCircle, Clock, AlertCircle } from 'lucide-react';

export default function OrdersPage() {
  const { businessId } = useWorkflowStore();
  const [orders, setOrders] = useState<any[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const parentRef = useRef<HTMLDivElement>(null);

  const fetchOrders = async () => {
    if (!businessId) return;
    try {
      const res = await api.getOperations(businessId);
      if (res.success && res.data) {
        setOrders(res.data.orders || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [businessId]);

  useEffect(() => {
    let result = orders;
    if (search.trim()) {
      const term = search.toLowerCase();
      result = result.filter(o => 
        o.id.toLowerCase().includes(term) || 
        o.customer_phone.includes(term) ||
        (o.items && o.items.some((i: any) => i.name.toLowerCase().includes(term)))
      );
    }
    if (statusFilter !== 'ALL') {
      result = result.filter(o => o.status === statusFilter);
    }
    setFilteredOrders(result);
  }, [orders, search, statusFilter]);

  const rowVirtualizer = useVirtualizer({
    count: filteredOrders.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
    overscan: 10,
  });

  return (
    <div className="flex-1 p-8 flex flex-col gap-6 bg-slate-50/50">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Order Management</h2>
          <p className="text-xs text-slate-500 mt-1">Track active and completed consumer shopping carts across sessions.</p>
        </div>
        <button 
          onClick={fetchOrders}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by Order ID or Phone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
          />
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          {['ALL', 'PENDING', 'COMPLETED'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${
                statusFilter === status 
                  ? 'bg-emerald-600 text-white shadow-sm' 
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
          <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin mb-2" />
          <span className="text-xs font-semibold">Fetching orders...</span>
        </div>
      ) : filteredOrders.length > 0 ? (
        <div 
          ref={parentRef}
          className="bg-white border border-slate-200 rounded-xl overflow-auto shadow-sm"
          style={{ height: 'calc(100vh - 250px)' }}
        >
          <div className="w-full min-w-[800px] text-left border-collapse">
            <div className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider sticky top-0 z-10 flex w-full">
              <div className="p-4 w-[15%] shrink-0">Order ID</div>
              <div className="p-4 w-[15%] shrink-0">Customer Phone</div>
              <div className="p-4 w-[35%] shrink-0">Items</div>
              <div className="p-4 w-[10%] shrink-0">Total</div>
              <div className="p-4 w-[12%] shrink-0">Status</div>
              <div className="p-4 w-[13%] shrink-0">Updated At</div>
            </div>
            <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }}>
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const order = filteredOrders[virtualRow.index];
                return (
                  <div
                    key={virtualRow.key}
                    data-index={virtualRow.index}
                    ref={rowVirtualizer.measureElement}
                    className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 flex w-full items-center text-xs text-slate-700"
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      transform: `translateY(${virtualRow.start}px)`
                    }}
                  >
                    <div className="p-4 font-mono font-bold text-slate-800 w-[15%] shrink-0 truncate">{order.id}</div>
                    <div className="p-4 w-[15%] shrink-0 truncate">{order.customer_phone}</div>
                    <div className="p-4 w-[35%] shrink-0 truncate">
                      <div className="flex flex-col gap-0.5 max-w-full">
                        {order.items && order.items.length > 0 ? (
                          order.items.map((item: any, idx: number) => (
                            <span key={idx} className="truncate">
                              {item.quantity}x {item.name} (${(item.price * item.quantity).toFixed(2)})
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-400 italic">No items recorded</span>
                        )}
                      </div>
                    </div>
                    <div className="p-4 font-semibold text-slate-900 w-[10%] shrink-0">${parseFloat(order.total || 0).toFixed(2)}</div>
                    <div className="p-4 w-[12%] shrink-0">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                        order.status === 'COMPLETED' 
                          ? 'bg-emerald-100 text-emerald-800' 
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {order.status === 'COMPLETED' ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : (
                          <Clock className="w-3 h-3" />
                        )}
                        {order.status}
                      </span>
                    </div>
                    <div className="p-4 text-slate-500 w-[13%] shrink-0 truncate">
                      {new Date(order.updated_at).toLocaleString()}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="p-12 text-center text-xs text-slate-400 font-semibold border border-dashed border-slate-200 rounded-xl bg-white shadow-sm flex flex-col items-center gap-2">
          <ShoppingBag className="w-8 h-8 text-slate-300" />
          No orders found matching the filter criteria.
        </div>
      )}
    </div>
  );
}
