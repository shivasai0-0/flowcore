'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { 
  Briefcase, 
  UserCheck, 
  Trash2, 
  Plus, 
  CheckCircle, 
  XCircle, 
  Loader2, 
  Clock, 
  Search,
  UserPlus
} from 'lucide-react';

type ToastType = { message: string; type: 'success' | 'error' };

export default function WorkerRegistryPage() {
  const { businessId } = useWorkflowStore();
  const [workers, setWorkers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<ToastType | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // New Worker Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [name, setName] = useState('');
  const [role, setRole] = useState('doctor');
  const [specialization, setSpecialization] = useState('');
  const [capacity, setCapacity] = useState(20);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const showToast = (message: string, type: 'success' | 'error') => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ message, type });
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  };

  const fetchWorkers = async () => {
    if (!businessId) return;
    setLoading(true);
    try {
      const res = await api.listWorkers(businessId);
      if (res.success && res.data) {
        setWorkers(res.data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
  }, [businessId]);

  const handleCreateWorker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !name.trim() || !role.trim()) return;

    setIsSubmitting(true);
    try {
      const res = await api.createWorker({
        business_id: businessId,
        name,
        role,
        specialization: specialization || 'General',
        capacity,
        availability: { days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], hours: "09:00 - 17:00" }
      });

      if (res.success) {
        showToast('✅ Worker successfully registered to registry!', 'success');
        setName('');
        setSpecialization('');
        setShowAddForm(false);
        await fetchWorkers();
      } else {
        showToast(`❌ Registration failed: ${res.error?.message || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      showToast(`❌ ${err.message}`, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteWorker = async (workerId: string) => {
    if (!confirm('Are you sure you want to remove this worker from the registry?')) return;
    try {
      const res = await api.deleteWorker(workerId);
      if (res.success) {
        showToast('🗑️ Worker successfully removed.', 'success');
        await fetchWorkers();
      } else {
        showToast(`❌ Delete failed: ${res.error?.message || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      showToast(`❌ ${err.message}`, 'error');
    }
  };

  const displayWorkers = workers;

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
          <h2 className="font-outfit font-bold text-xl text-slate-900">Worker Registry</h2>
          <p className="text-xs text-slate-500 mt-1">Manage staff schedules, specialization domains, active workloads, and distribute appointments intelligently.</p>
        </div>
        <button
          onClick={() => setShowAddForm(p => !p)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-sm transition-all cursor-pointer"
        >
          <UserPlus className="w-3.5 h-3.5" />
          Register Worker
        </button>
      </div>

      {/* Add Worker Form */}
      {showAddForm && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm max-w-xl">
          <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2 mb-4">
            <Plus className="w-4 h-4 text-emerald-600" /> Register New Business Worker
          </h3>
          <form onSubmit={handleCreateWorker} className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="flex flex-col gap-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Full Name</label>
              <input 
                type="text" 
                value={name} 
                onChange={e => setName(e.target.value)} 
                placeholder="e.g. Dr. John Smith"
                required
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Role Type</label>
              <select
                value={role}
                onChange={e => setRole(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors cursor-pointer"
              >
                <option value="doctor">Doctor (Hospital/Clinic)</option>
                <option value="delivery_agent">Delivery Agent (Restaurant/Store)</option>
                <option value="stylist">Stylist (Salon)</option>
                <option value="receptionist">Receptionist</option>
                <option value="teacher">Teacher (Education)</option>
                <option value="support_staff">Support Agent</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Specialization</label>
              <input 
                type="text" 
                value={specialization} 
                onChange={e => setSpecialization(e.target.value)} 
                placeholder="e.g. Cardiology, Fast Courier, Hair styling"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Daily Capacity limit</label>
              <input 
                type="number" 
                value={capacity} 
                onChange={e => setCapacity(Number(e.target.value))} 
                min={1}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
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
                disabled={isSubmitting || !name.trim()}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-sm transition-all cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UserCheck className="w-3.5 h-3.5" />}
                Add to Registry
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Workers Grid */}
      {loading && workers.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
          <Loader2 className="w-6 h-6 text-emerald-600 animate-spin mb-2" />
          <span className="text-xs font-semibold">Loading registry...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayWorkers.length === 0 ? (
            <div className="col-span-full bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-400 text-xs font-semibold">
              No workers registered. Add one using the form above!
            </div>
          ) : (
            displayWorkers.map((w) => {
              const isMock = w.id.startsWith('w_mock');
            return (
              <div key={w.id} className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col gap-4 shadow-sm relative overflow-hidden group hover:border-slate-300 transition-all">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0">
                      <Briefcase className="w-5 h-5 text-slate-500" />
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <h4 className="font-extrabold text-sm text-slate-800 leading-tight">{w.name}</h4>
                      <span className="text-[10px] text-emerald-600 font-bold uppercase tracking-wider">{w.role.replace('_', ' ')}</span>
                    </div>
                  </div>
                  {!isMock && (
                    <button
                      onClick={() => handleDeleteWorker(w.id)}
                      className="text-slate-400 hover:text-rose-600 transition-colors p-1"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs border-t border-slate-50 pt-3">
                  <div>
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Specialization</span>
                    <span className="font-semibold text-slate-700">{w.specialization}</span>
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Daily Capacity</span>
                    <span className="font-semibold text-slate-700">{w.capacity} tasks</span>
                  </div>
                </div>

                <div className="bg-slate-50/50 rounded-lg p-3 border border-slate-100 flex flex-col gap-1.5 text-[10px]">
                  <div className="flex items-center gap-1.5 text-slate-500">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span className="font-bold text-slate-600">Hours: {w.availability?.hours || '09:00 - 17:00'}</span>
                  </div>
                  <div className="flex gap-1 flex-wrap">
                    {(w.availability?.days || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']).map((day: string) => (
                      <span key={day} className="px-1.5 py-0.5 bg-white border border-slate-200 rounded font-semibold text-[8px] text-slate-500 uppercase">
                        {day.substring(0, 3)}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            );
          }))}
        </div>
      )}
    </div>
  );
}
