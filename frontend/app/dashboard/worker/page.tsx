'use client';

import React, { useEffect, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { 
  ClipboardList, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  User, 
  Play, 
  ArrowRight,
  TrendingUp,
  RefreshCw,
  Zap
} from 'lucide-react';

export default function WorkerDashboardPage() {
  const { businessId, businessName } = useWorkflowStore();
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchTasks = async () => {
    if (!businessId) return;
    try {
      const res = await api.listTasks(businessId);
      if (res.success && res.data) {
        setTasks(res.data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 10000);
    return () => clearInterval(interval);
  }, [businessId]);

  const handleUpdateStatus = async (taskId: string, newStatus: string) => {
    setUpdatingId(taskId);
    try {
      const res = await api.updateTask(taskId, { status: newStatus });
      if (res.success) {
        await fetchTasks();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setUpdatingId(null);
    }
  };

  const getPriorityBadge = (priority: string) => {
    const map: Record<string, string> = {
      CRITICAL: 'bg-rose-100 text-rose-800 border-rose-200',
      HIGH: 'bg-orange-100 text-orange-800 border-orange-200',
      MEDIUM: 'bg-blue-100 text-blue-800 border-blue-200',
      LOW: 'bg-slate-100 text-slate-700 border-slate-200',
    };
    return map[priority.toUpperCase()] || 'bg-slate-100 text-slate-700';
  };

  const getStatusIcon = (status: string) => {
    const map: Record<string, any> = {
      PENDING: <Clock className="w-3.5 h-3.5 text-slate-400" />,
      ACCEPTED: <AlertCircle className="w-3.5 h-3.5 text-blue-500" />,
      IN_PROGRESS: <Play className="w-3.5 h-3.5 text-amber-500 animate-pulse" />,
      COMPLETED: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />,
      CANCELLED: <XCircle className="w-3.5 h-3.5 text-rose-500" />,
    };
    return map[status.toUpperCase()] || <Clock className="w-3.5 h-3.5 text-slate-400" />;
  };

  const displayedTasks = tasks;

  return (
    <div className="flex-1 p-8 flex flex-col gap-8 bg-slate-50/50">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Task Dashboard</h2>
          <p className="text-xs text-slate-500 mt-1">Universal agent workspace. View and process workflows assigned to you.</p>
        </div>
        <button 
          onClick={fetchTasks}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Tasks
        </button>
      </div>

      {/* Task Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 p-5 rounded-xl flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center border border-amber-100 shrink-0">
            <Clock className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Assigned Tasks</span>
            <h4 className="text-xl font-extrabold text-slate-900 mt-0.5">
              {displayedTasks.filter(t => t.status !== 'COMPLETED' && t.status !== 'CANCELLED').length}
            </h4>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-5 rounded-xl flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center border border-emerald-100 shrink-0">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Completed Today</span>
            <h4 className="text-xl font-extrabold text-emerald-600 mt-0.5">
              {displayedTasks.filter(t => t.status === 'COMPLETED').length}
            </h4>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-5 rounded-xl flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-rose-50 flex items-center justify-center border border-rose-100 shrink-0">
            <TrendingUp className="w-5 h-5 text-rose-600" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Critical Priority</span>
            <h4 className="text-xl font-extrabold text-rose-600 mt-0.5">
              {displayedTasks.filter(t => t.priority === 'CRITICAL' && t.status !== 'COMPLETED').length}
            </h4>
          </div>
        </div>
      </div>

      {/* Task List Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex-1 flex flex-col">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <ClipboardList className="w-4 h-4 text-emerald-600" /> Current Tasks Queue
          </h3>
          <span className="text-[10px] bg-slate-100 text-slate-500 font-bold px-2 py-0.5 rounded-full">
            {displayedTasks.length} Active Tasks
          </span>
        </div>

        <div className="flex-1 overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-4">Task Details</th>
                <th className="p-4">Customer</th>
                <th className="p-4">Priority</th>
                <th className="p-4">Due Time</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {displayedTasks.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-400">
                    No active tasks assigned to you. Enjoy your break!
                  </td>
                </tr>
              ) : (
                displayedTasks.map((t) => {
                  const isUpdating = updatingId === t.id;
                return (
                  <tr key={t.id} className="hover:bg-slate-50/40 transition-colors">
                    <td className="p-4">
                      <div className="flex flex-col gap-0.5">
                        <span className="font-bold text-slate-800 text-sm">{t.title}</span>
                        <span className="text-[10px] text-slate-500 break-words max-w-md">{t.description}</span>
                        <span className="text-[9px] text-slate-400 font-mono mt-0.5">ID: {t.id}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-1.5 text-slate-700">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-semibold">{t.customer_phone}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 border rounded text-[9px] font-bold ${getPriorityBadge(t.priority)}`}>
                        {t.priority}
                      </span>
                    </td>
                    <td className="p-4 text-slate-500 font-medium">
                      {t.due_time ? new Date(t.due_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'No due time'}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[10px]">
                        {getStatusIcon(t.status)}
                        <span>{t.status}</span>
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {t.status === 'PENDING' && (
                          <button
                            disabled={isUpdating}
                            onClick={() => handleUpdateStatus(t.id, 'ACCEPTED')}
                            className="px-2.5 py-1 rounded bg-blue-600 text-white font-bold text-[10px] hover:bg-blue-500 shadow-sm cursor-pointer disabled:opacity-50"
                          >
                            Accept
                          </button>
                        )}
                        {t.status === 'ACCEPTED' && (
                          <button
                            disabled={isUpdating}
                            onClick={() => handleUpdateStatus(t.id, 'IN_PROGRESS')}
                            className="px-2.5 py-1 rounded bg-amber-500 text-white font-bold text-[10px] hover:bg-amber-400 shadow-sm cursor-pointer disabled:opacity-50"
                          >
                            Start
                          </button>
                        )}
                        {(t.status === 'ACCEPTED' || t.status === 'IN_PROGRESS') && (
                          <>
                            <button
                              disabled={isUpdating}
                              onClick={() => handleUpdateStatus(t.id, 'COMPLETED')}
                              className="px-2.5 py-1 rounded bg-emerald-600 text-white font-bold text-[10px] hover:bg-emerald-500 shadow-sm cursor-pointer disabled:opacity-50"
                            >
                              Complete
                            </button>
                            <button
                              disabled={isUpdating}
                              onClick={() => handleUpdateStatus(t.id, 'CANCELLED')}
                              className="px-2 py-1 rounded bg-white border border-rose-200 text-rose-600 font-bold text-[10px] hover:bg-rose-50 cursor-pointer disabled:opacity-50"
                            >
                              Cancel
                            </button>
                          </>
                        )}
                        {(t.status === 'COMPLETED' || t.status === 'CANCELLED') && (
                          <span className="text-[10px] text-slate-400 font-semibold italic">Archived</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              }))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
