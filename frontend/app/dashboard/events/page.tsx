'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import {
  RefreshCw,
  Search,
  Filter,
  Clock,
  Layers,
  Terminal,
  Play,
  Pause,
  ChevronRight,
  Eye,
  CheckCircle,
  XCircle,
  Activity,
  Zap,
  Lock,
  UserPlus,
  FileText,
  MessageSquare
} from 'lucide-react';

type ToastType = { message: string; type: 'success' | 'error' };

export default function EventMonitorPage() {
  const { businessId } = useWorkflowStore();
  const [events, setEvents] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [liveStreaming, setLiveStreaming] = useState(true);
  
  // Filters state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedWorkflow, setSelectedWorkflow] = useState('all');
  const [selectedEventType, setSelectedEventType] = useState('all');
  const [customerFilter, setCustomerFilter] = useState('');

  // Selected event for detail drawer
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null);

  // Toast
  const [toast, setToast] = useState<ToastType | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (message: string, type: 'success' | 'error') => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ message, type });
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  };

  const fetchWorkflows = async () => {
    if (!businessId) return;
    try {
      const res = await api.listAllWorkflows(businessId);
      if (res.success && res.data) {
        setWorkflows(res.data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchEvents = async (silent = false) => {
    if (!businessId) return;
    if (!silent) setLoading(true);
    try {
      const res = liveStreaming 
        ? await api.listLiveEvents(businessId)
        : await api.listEvents(businessId, 50, 0);

      if (res.success && res.data) {
        setEvents(res.data || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  // Fetch initial data
  useEffect(() => {
    fetchWorkflows();
    fetchEvents();
  }, [businessId]);

  // Set up streaming interval
  useEffect(() => {
    let interval: any = null;
    if (liveStreaming && businessId) {
      interval = setInterval(() => {
        fetchEvents(true);
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [liveStreaming, businessId]);

  // Filter events client-side
  const filteredEvents = events.filter(evt => {
    // Workflow Filter
    if (selectedWorkflow !== 'all' && evt.workflow_version_id !== selectedWorkflow) {
      return false;
    }
    // Event Type Filter
    if (selectedEventType !== 'all' && evt.event_type !== selectedEventType) {
      return false;
    }
    // Customer phone filter
    if (customerFilter.trim() && !evt.customer_id?.includes(customerFilter.trim())) {
      return false;
    }
    // Global search query (checks payload or session ID)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const stringifiedPayload = JSON.stringify(evt.payload || {}).toLowerCase();
      if (!evt.session_id?.toLowerCase().includes(q) && 
          !evt.event_type?.toLowerCase().includes(q) && 
          !stringifiedPayload.includes(q)) {
        return false;
      }
    }
    return true;
  });

  // Extract unique event types
  const uniqueEventTypes = Array.from(new Set(events.map(e => e.event_type))).filter(Boolean);

  const getEventBadgeColor = (type: string) => {
    if (type.includes('ERROR') || type.includes('FAIL')) return 'bg-rose-50 border-rose-200 text-rose-800';
    if (type.includes('SUCCESS') || type.includes('GRANTED') || type.includes('COMPLETED')) return 'bg-emerald-50 border-emerald-200 text-emerald-800';
    if (type.includes('APPROVAL') || type.includes('PAUSE')) return 'bg-amber-50 border-amber-200 text-amber-800';
    if (type.includes('ASSIGN')) return 'bg-sky-50 border-sky-200 text-sky-800';
    if (type.includes('MESSAGE')) return 'bg-blue-50 border-blue-200 text-blue-800';
    if (type.includes('REPORT')) return 'bg-purple-50 border-purple-200 text-purple-800';
    return 'bg-slate-50 border-slate-200 text-slate-700';
  };

  const getEventIcon = (type: string) => {
    if (type.includes('APPROVAL')) return <Lock className="w-3.5 h-3.5 text-amber-600" />;
    if (type.includes('ASSIGN')) return <UserPlus className="w-3.5 h-3.5 text-sky-600" />;
    if (type.includes('REPORT')) return <FileText className="w-3.5 h-3.5 text-purple-600" />;
    if (type.includes('MESSAGE') || type.includes('WHATSAPP')) return <MessageSquare className="w-3.5 h-3.5 text-blue-600" />;
    if (type.includes('SUCCESS') || type.includes('COMPLETED')) return <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />;
    if (type.includes('ERROR') || type.includes('FAIL')) return <XCircle className="w-3.5 h-3.5 text-rose-600" />;
    return <Zap className="w-3.5 h-3.5 text-slate-500" />;
  };

  return (
    <div className="flex-1 p-8 flex flex-col gap-6 bg-slate-50/50 relative">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-xl shadow-lg text-xs font-bold flex items-center gap-2 transition-all ${
          toast.type === 'success'
            ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
            : 'bg-rose-50 border border-rose-200 text-rose-800'
        }`}>
          {toast.type === 'success' ? <CheckCircle className="w-4 h-4 text-emerald-600" /> : <XCircle className="w-4 h-4 text-rose-600" />}
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Event Monitor</h2>
          <p className="text-xs text-slate-500 mt-1">Audit, trace, and inspect the real-time flow of event signals through the FSM traverser.</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Live Streaming toggle */}
          <button
            onClick={() => {
              setLiveStreaming(p => !p);
              showToast(liveStreaming ? '⏸️ Streaming paused' : '▶️ Live streaming activated', 'success');
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold shadow-sm transition-all cursor-pointer border ${
              liveStreaming
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : 'bg-slate-100 border-slate-200 text-slate-500 hover:bg-slate-200'
            }`}
          >
            {liveStreaming ? (
              <>
                <Pause className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
                Live Stream ON
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                Live Stream OFF
              </>
            )}
          </button>
          
          <button
            onClick={() => fetchEvents(false)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-3 shadow-sm">
        <div className="flex items-center gap-1.5 text-xs font-bold text-slate-400 uppercase tracking-wider">
          <Filter className="w-3.5 h-3.5 text-slate-400" /> Filter Logs
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
          {/* Search Query */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Search Payload / Session</label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="e.g. Stripe, items..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
            </div>
          </div>

          {/* Workflow Version Selector */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Workflow Version</label>
            <select
              value={selectedWorkflow}
              onChange={e => setSelectedWorkflow(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors cursor-pointer"
            >
              <option value="all">All Workflows</option>
              {workflows.map(wf => (
                <option key={wf.id} value={wf.id}>Version #{wf.version_number} ({wf.workflow_type})</option>
              ))}
            </select>
          </div>

          {/* Event Type Selector */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Event Type</label>
            <select
              value={selectedEventType}
              onChange={e => setSelectedEventType(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors cursor-pointer"
            >
              <option value="all">All Event Types</option>
              {uniqueEventTypes.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
              {/* Fallback standard categories if empty */}
              {uniqueEventTypes.length === 0 && (
                <>
                  <option value="USER_MESSAGE">USER_MESSAGE</option>
                  <option value="ORDER_CREATED">ORDER_CREATED</option>
                  <option value="PAYMENT_COMPLETED">PAYMENT_COMPLETED</option>
                  <option value="APPROVAL_PAUSE">APPROVAL_PAUSE</option>
                  <option value="TASK_ASSIGNED">TASK_ASSIGNED</option>
                </>
              )}
            </select>
          </div>

          {/* Customer Phone Filter */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Customer Phone</label>
            <input
              type="text"
              placeholder="e.g. +1555"
              value={customerFilter}
              onChange={e => setCustomerFilter(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
            />
          </div>
        </div>
      </div>

      {/* Main Logs Table and Detail Drawer Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Logs Table */}
        <div className={`flex flex-col gap-3 ${selectedEvent ? 'lg:col-span-7' : 'lg:col-span-12'}`}>
          <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm">
            <div className="p-3 bg-slate-50 border-b border-slate-200 flex justify-between items-center text-xs font-semibold text-slate-700">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-slate-500" />
                <span>Logs Feed ({filteredEvents.length} entry/entries)</span>
              </div>
              {liveStreaming && (
                <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                  Streaming
                </span>
              )}
            </div>

            {loading && events.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin mb-2" />
                <span className="text-xs font-semibold">Loading events logs...</span>
              </div>
            ) : filteredEvents.length > 0 ? (
              <div className="overflow-x-auto max-h-[600px]">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-extrabold text-slate-500 uppercase">
                      <th className="p-3">Time</th>
                      <th className="p-3">Session ID</th>
                      <th className="p-3">Event Type</th>
                      <th className="p-3">Customer Phone</th>
                      <th className="p-3">Quick Specs</th>
                      <th className="p-3 text-right">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs font-medium text-slate-700">
                    {filteredEvents.map(evt => (
                      <tr 
                        key={evt.id} 
                        onClick={() => setSelectedEvent(evt)}
                        className={`hover:bg-slate-50/70 transition-colors cursor-pointer ${
                          selectedEvent?.id === evt.id ? 'bg-emerald-50/30' : ''
                        }`}
                      >
                        <td className="p-3 text-slate-400 font-mono text-[10px] whitespace-nowrap">
                          {new Date(evt.emitted_at).toLocaleTimeString()}
                        </td>
                        <td className="p-3 font-mono font-bold text-[10px] text-slate-800">
                          {evt.session_id}
                        </td>
                        <td className="p-3">
                          <span className={`flex items-center gap-1.5 px-2 py-0.5 border rounded-full text-[9px] font-bold w-fit ${getEventBadgeColor(evt.event_type)}`}>
                            {getEventIcon(evt.event_type)}
                            {evt.event_type}
                          </span>
                        </td>
                        <td className="p-3 text-slate-500 font-bold">
                          {evt.customer_id}
                        </td>
                        <td className="p-3 text-slate-500 max-w-xs truncate font-mono text-[10px]">
                          {JSON.stringify(evt.payload)}
                        </td>
                        <td className="p-3 text-right">
                          <button
                            onClick={e => {
                              e.stopPropagation();
                              setSelectedEvent(evt);
                            }}
                            className="text-slate-400 hover:text-emerald-600 transition-colors inline-flex items-center gap-0.5"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-12 text-center text-xs text-slate-400 font-semibold border-t border-slate-100 flex flex-col items-center justify-center gap-2 bg-slate-50/20">
                <Activity className="w-8 h-8 text-slate-300" />
                No events match the selected filters.
              </div>
            )}
          </div>
        </div>

        {/* Selected Event Details Panel / Sidebar */}
        {selectedEvent && (
          <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-5 flex flex-col gap-4 shadow-sm sticky top-6">
            <div className="border-b border-slate-100 pb-3 flex justify-between items-start">
              <div>
                <h3 className="font-extrabold text-sm text-slate-800 flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-emerald-600" /> Event Details
                </h3>
                <p className="text-[10px] text-slate-400 mt-0.5 font-mono">{selectedEvent.id}</p>
              </div>
              <button 
                onClick={() => setSelectedEvent(null)}
                className="text-slate-400 hover:text-slate-600 text-xs font-bold"
              >
                Close
              </button>
            </div>

            <div className="flex flex-col gap-3 text-xs">
              <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-100 font-medium">
                <div>
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Session ID</span>
                  <span className="font-mono text-slate-800 text-[10px] font-bold">{selectedEvent.session_id}</span>
                </div>
                <div>
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Customer</span>
                  <span className="text-slate-800 font-bold">{selectedEvent.customer_id}</span>
                </div>
                <div>
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Workflow Ver ID</span>
                  <span className="font-mono text-slate-500 text-[10px] break-all">{selectedEvent.workflow_version_id || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Emitted At</span>
                  <span className="text-slate-500 text-[10px] font-semibold">{new Date(selectedEvent.emitted_at).toLocaleString()}</span>
                </div>
              </div>

              <div>
                <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px]">Event Type Badge</span>
                <div className="mt-1 flex items-center gap-1.5">
                  <span className={`flex items-center gap-1.5 px-3 py-1 border rounded-full text-[10px] font-bold ${getEventBadgeColor(selectedEvent.event_type)}`}>
                    {getEventIcon(selectedEvent.event_type)}
                    {selectedEvent.event_type}
                  </span>
                </div>
              </div>

              <div>
                <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px] block mb-1">Payload JSON</span>
                <pre className="p-3 bg-slate-900 text-slate-200 rounded-lg text-[10px] font-mono overflow-x-auto max-h-[300px]">
                  {JSON.stringify(selectedEvent.payload, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
