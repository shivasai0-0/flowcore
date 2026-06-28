'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { Calendar, RefreshCw, Search, CheckCircle, Clock, AlertCircle } from 'lucide-react';

export default function BookingsPage() {
  const { businessId } = useWorkflowStore();
  const [bookings, setBookings] = useState<any[]>([]);
  const [filteredBookings, setFilteredBookings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const parentRef = useRef<HTMLDivElement>(null);

  const fetchBookings = async () => {
    if (!businessId) return;
    try {
      const res = await api.getOperations(businessId);
      if (res.success && res.data) {
        setBookings(res.data.bookings || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBookings();
  }, [businessId]);

  useEffect(() => {
    let result = bookings;
    if (search.trim()) {
      const term = search.toLowerCase();
      result = result.filter(b => 
        b.id.toLowerCase().includes(term) || 
        b.customer_phone.includes(term) ||
        b.service.toLowerCase().includes(term)
      );
    }
    if (statusFilter !== 'ALL') {
      result = result.filter(b => b.status === statusFilter);
    }
    setFilteredBookings(result);
  }, [bookings, search, statusFilter]);

  const rowVirtualizer = useVirtualizer({
    count: filteredBookings.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 52,
    overscan: 10,
  });

  return (
    <div className="flex-1 p-8 flex flex-col gap-6 bg-slate-50/50">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Appointment Bookings</h2>
          <p className="text-xs text-slate-500 mt-1">Manage scheduled calendar sessions, slots, and salon or medical services.</p>
        </div>
        <button 
          onClick={fetchBookings}
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
            placeholder="Search by Booking ID or Service..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
          />
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          {['ALL', 'PENDING', 'CONFIRMED'].map((status) => (
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
          <span className="text-xs font-semibold">Fetching bookings...</span>
        </div>
      ) : filteredBookings.length > 0 ? (
        <div 
          ref={parentRef}
          className="bg-white border border-slate-200 rounded-xl overflow-auto shadow-sm"
          style={{ height: 'calc(100vh - 250px)' }}
        >
          <div className="w-full min-w-[800px] text-left border-collapse">
            <div className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider sticky top-0 z-10 flex w-full">
              <div className="p-4 w-[15%] shrink-0">Booking ID</div>
              <div className="p-4 w-[15%] shrink-0">Customer Phone</div>
              <div className="p-4 w-[20%] shrink-0">Service</div>
              <div className="p-4 w-[15%] shrink-0">Date</div>
              <div className="p-4 w-[10%] shrink-0">Slot</div>
              <div className="p-4 w-[12%] shrink-0">Status</div>
              <div className="p-4 w-[13%] shrink-0">Updated At</div>
            </div>
            <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }}>
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const booking = filteredBookings[virtualRow.index];
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
                    <div className="p-4 font-mono font-bold text-slate-800 w-[15%] shrink-0 truncate">{booking.id}</div>
                    <div className="p-4 w-[15%] shrink-0 truncate">{booking.customer_phone}</div>
                    <div className="p-4 font-semibold text-slate-800 w-[20%] shrink-0 truncate">{booking.service}</div>
                    <div className="p-4 font-medium text-slate-600 w-[15%] shrink-0 truncate">{booking.date}</div>
                    <div className="p-4 font-medium text-slate-600 w-[10%] shrink-0 truncate">{booking.slot}</div>
                    <div className="p-4 w-[12%] shrink-0">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                        booking.status === 'CONFIRMED' 
                          ? 'bg-emerald-100 text-emerald-800' 
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {booking.status === 'CONFIRMED' ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : (
                          <Clock className="w-3 h-3" />
                        )}
                        {booking.status}
                      </span>
                    </div>
                    <div className="p-4 text-slate-500 w-[13%] shrink-0 truncate">
                      {new Date(booking.updated_at).toLocaleString()}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="p-12 text-center text-xs text-slate-400 font-semibold border border-dashed border-slate-200 rounded-xl bg-white shadow-sm flex flex-col items-center gap-2">
          <Calendar className="w-8 h-8 text-slate-300" />
          No bookings found matching the filter criteria.
        </div>
      )}
    </div>
  );
}
