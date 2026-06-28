'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { 
  ClipboardList, 
  Trash2, 
  Plus, 
  CheckCircle, 
  XCircle, 
  Loader2, 
  Clock, 
  Search,
  User,
  AlertCircle,
  Play
} from 'lucide-react';

type ToastType = { message: string; type: 'success' | 'error' };

export default function TasksRegistryPage() {
  const { businessId } = useWorkflowStore();
  const [tasks, setTasks] = useState<any[]>([]);
  const [workers, setWorkers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<ToastType | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // New Task Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('MEDIUM');
  const [assignedWorkerId, setAssignedWorkerId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const showToast = (message: string, type: 'success' | 'error') => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ message, type });
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  };

  const fetchData = async () => {
    if (!businessId) return;
    setLoading(true);
    try {
      const tasksRes = await api.listTasks(businessId);
      if (tasksRes.success && tasksRes.data) {
        setTasks(tasksRes.data);
      }
      const workersRes = await api.listWorkers(businessId);
      if (workersRes.success && workersRes.data) {
        setWorkers(workersRes.data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [businessId]);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !title.trim()) return;

    setIsSubmitting(true);
    try {
      const res = await api.createTask({
        business_id: businessId,
        title,
        description,
        priority,
        assigned_worker_id: assignedWorkerId || undefined
      });

      if (res.success) {
        showToast('✅ Task successfully added to registry!', 'success');
        setTitle('');
        setDescription('');
        setAssignedWorkerId('');
        setShowAddForm(false);
        await fetchData();
      } else {
        showToast(`❌ Task addition failed: ${res.error?.message || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      showToast(`❌ ${err.message}`, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm('Are you sure you want to remove this task?')) return;
    try {
      const res = await api.deleteTask(taskId);
      if (res.success) {
        showToast('🗑️ Task removed successfully.', 'success');
        await fetchData();
      } else {
        showToast(`❌ Delete failed: ${res.error?.message || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      showToast(`❌ ${err.message}`, 'error');
    }
  };

  const getPriorityColor = (p: string) => {
    const map: Record<string, string> = {
      CRITICAL: 'bg-rose-100 text-rose-800 border-rose-200',
      HIGH: 'bg-orange-100 text-orange-800 border-orange-200',
      MEDIUM: 'bg-blue-100 text-blue-800 border-blue-200',
      LOW: 'bg-slate-100 text-slate-700 border-slate-200',
    };
    return map[p.toUpperCase()] || 'bg-slate-100 text-slate-700';
  };

  const displayTasks = tasks;

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
          <h2 className="font-outfit font-bold text-xl text-slate-900">Tasks Registry</h2>
          <p className="text-xs text-slate-500 mt-1">Audit, assign, create, and remove task execution records for your workers.</p>
        </div>
        <button
          onClick={() => setShowAddForm(p => !p)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-sm transition-all cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          Create Task
        </button>
      </div>

      {/* Add Task Form */}
      {showAddForm && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm max-w-xl">
          <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2 mb-4">
            <Plus className="w-4 h-4 text-emerald-600" /> Create New Business Task
          </h3>
          <form onSubmit={handleCreateTask} className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="flex flex-col gap-1 md:col-span-2">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Task Title</label>
              <input 
                type="text" 
                value={title} 
                onChange={e => setTitle(e.target.value)} 
                placeholder="e.g. Prepare Order, Consult Patient"
                required
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
            </div>

            <div className="flex flex-col gap-1 md:col-span-2">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Description</label>
              <textarea
                value={description} 
                onChange={e => setDescription(e.target.value)} 
                placeholder="Add details regarding this assignment..."
                rows={2}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors resize-none"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Priority</label>
              <select
                value={priority}
                onChange={e => setPriority(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors cursor-pointer"
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Assign Worker</label>
              <select
                value={assignedWorkerId}
                onChange={e => setAssignedWorkerId(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors cursor-pointer"
              >
                <option value="">Unassigned</option>
                {workers.map(w => (
                  <option key={w.id} value={w.id}>{w.name} ({w.role})</option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2 flex justify-end gap-2 mt-2">
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !title.trim()}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-sm transition-all cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ClipboardList className="w-3.5 h-3.5" />}
                Add Task
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Task List Table */}
      {loading && tasks.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
          <Loader2 className="w-6 h-6 text-emerald-600 animate-spin mb-2" />
          <span className="text-xs font-semibold">Loading tasks...</span>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-4">Task Details</th>
                <th className="p-4">Assigned To</th>
                <th className="p-4">Priority</th>
                <th className="p-4">Status</th>
                <th className="p-4">Created At</th>
                <th className="p-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {displayTasks.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-400">
                    No tasks found in registry. Add one using the form above!
                  </td>
                </tr>
              ) : (
                displayTasks.map((t) => {
                  const isMock = t.id.startsWith('t_mock');
                return (
                  <tr key={t.id} className="hover:bg-slate-50/20 transition-colors">
                    <td className="p-4">
                      <div className="flex flex-col gap-0.5">
                        <span className="font-extrabold text-slate-800 text-sm">{t.title}</span>
                        <span className="text-[10px] text-slate-500 max-w-sm">{t.description || 'No description provided.'}</span>
                        <span className="text-[9px] text-slate-400 font-mono mt-0.5">ID: {t.id}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-1 text-slate-800 font-medium">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        <span>{t.assigned_worker_name || 'Unassigned'}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 border rounded text-[9px] font-bold ${getPriorityColor(t.priority)}`}>
                        {t.priority}
                      </span>
                    </td>
                    <td className="p-4 uppercase font-bold text-[10px] tracking-wider">
                      <div className="flex items-center gap-1.5">
                        {t.status === 'COMPLETED' ? (
                          <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                        ) : t.status === 'CANCELLED' ? (
                          <XCircle className="w-3.5 h-3.5 text-rose-500" />
                        ) : t.status === 'IN_PROGRESS' ? (
                          <Play className="w-3.5 h-3.5 text-amber-500 animate-pulse" />
                        ) : (
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                        )}
                        <span>{t.status}</span>
                      </div>
                    </td>
                    <td className="p-4 text-slate-400 font-semibold font-mono text-[10px]">
                      {new Date(t.created_at).toLocaleString()}
                    </td>
                    <td className="p-4 text-right">
                      {!isMock ? (
                        <button
                          onClick={() => handleDeleteTask(t.id)}
                          className="text-slate-400 hover:text-rose-600 transition-colors p-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-300 font-bold uppercase">Locked</span>
                      )}
                    </td>
                  </tr>
                );
              }))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
