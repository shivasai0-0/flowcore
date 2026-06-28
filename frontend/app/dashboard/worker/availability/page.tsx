'use client';

import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { 
  Calendar as CalendarIcon, 
  Clock, 
  User, 
  Sliders, 
  Award,
  CheckCircle,
  Briefcase,
  Loader2,
  XCircle,
  Users,
  Save
} from 'lucide-react';

const WEEKDAYS = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday'
];

const workerSchema = z.object({
  specialization: z.string().min(2, 'Specialization must be at least 2 characters.'),
  capacity: z.number({ invalid_type_error: 'Capacity must be a number.' }).min(1, 'Capacity must be at least 1.').max(100, 'Capacity cannot exceed 100.'),
  activeDays: z.record(z.boolean()),
  shiftStartTimes: z.record(z.string()),
  shiftEndTimes: z.record(z.string())
}).refine((data) => {
  for (const day of WEEKDAYS) {
    if (data.activeDays[day]) {
      const start = data.shiftStartTimes[day];
      const end = data.shiftEndTimes[day];
      
      const getMinutes = (t: string) => {
        const [h, m] = t.split(':').map(Number);
        return h * 60 + m;
      };
      
      let startMins = getMinutes(start);
      let endMins = getMinutes(end);
      if (endMins <= startMins) {
        endMins += 24 * 60; // assume next day wrap
      }
      if (startMins >= endMins) {
        return false;
      }
    }
  }
  return true;
}, {
  message: 'Shift end time must be after start time on all active days.',
  path: ['shiftEndTimes']
});

type WorkerFormData = z.infer<typeof workerSchema>;

export default function WorkerAvailabilityPage() {
  const { businessId: storeBusinessId } = useWorkflowStore();
  const [businessId, setBusinessId] = useState<string | null>(null);

  // States
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [workers, setWorkers] = useState<any[]>([]);
  const [selectedWorkerId, setSelectedWorkerId] = useState<string>('');

  const [savedMessage, setSavedMessage] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors }, watch, setValue, reset } = useForm<WorkerFormData>({
    resolver: zodResolver(workerSchema),
    defaultValues: {
      specialization: 'General',
      capacity: 15,
      activeDays: {
        Monday: true, Tuesday: true, Wednesday: true, Thursday: true, Friday: true, Saturday: false, Sunday: false
      },
      shiftStartTimes: {
        Monday: '09:00', Tuesday: '09:00', Wednesday: '09:00', Thursday: '09:00', Friday: '09:00', Saturday: '09:00', Sunday: '09:00'
      },
      shiftEndTimes: {
        Monday: '17:00', Tuesday: '17:00', Wednesday: '17:00', Thursday: '17:00', Friday: '17:00', Saturday: '17:00', Sunday: '17:00'
      }
    }
  });

  const formValues = watch();
  const activeDays = formValues.activeDays || {};
  const shiftStartTimes = formValues.shiftStartTimes || {};
  const shiftEndTimes = formValues.shiftEndTimes || {};

  useEffect(() => {
    const id = storeBusinessId || localStorage.getItem('flowcore_active_business_id');
    setBusinessId(id);
  }, [storeBusinessId]);

  // Fetch all workers
  const fetchAllWorkers = async (targetBizId: string) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await api.listWorkers(targetBizId);
      if (res.success && res.data) {
        setWorkers(res.data);
        if (res.data.length > 0) {
          setSelectedWorkerId(res.data[0].id);
        }
      }
    } catch (e) {
      console.error(e);
      setErrorMessage('Failed to fetch worker registry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (businessId) {
      fetchAllWorkers(businessId);
    }
  }, [businessId]);

  // Sync state when selected worker changes
  useEffect(() => {
    if (!selectedWorkerId) return;
    const worker = workers.find(w => w.id === selectedWorkerId);
    if (worker) {
      const newActiveDays: Record<string, boolean> = {};
      const newStartTimes: Record<string, string> = {};
      const newEndTimes: Record<string, string> = {};
      
      WEEKDAYS.forEach(day => {
        const times = worker.availability?.[day];
        if (times && times.length >= 2) {
          newActiveDays[day] = true;
          newStartTimes[day] = times[0];
          newEndTimes[day] = times[1];
        } else {
          newActiveDays[day] = false;
          newStartTimes[day] = '09:00';
          newEndTimes[day] = '17:00';
        }
      });
      
      reset({
        specialization: worker.specialization || 'General',
        capacity: worker.capacity || 15,
        activeDays: newActiveDays,
        shiftStartTimes: newStartTimes,
        shiftEndTimes: newEndTimes
      });
    }
  }, [selectedWorkerId, workers, reset]);

  const handleSave = async (data: WorkerFormData) => {
    if (!selectedWorkerId) return;

    setSaving(true);
    setErrorMessage(null);
    setSavedMessage(false);

    try {
      // Build availability payload
      const availabilityPayload: Record<string, string[]> = {};
      WEEKDAYS.forEach(day => {
        if (data.activeDays[day]) {
          availabilityPayload[day] = [data.shiftStartTimes[day], data.shiftEndTimes[day]];
        }
      });

      const res = await api.updateWorker(selectedWorkerId, {
        specialization: data.specialization,
        capacity: data.capacity,
        availability: availabilityPayload
      });

      if (res.success) {
        setSavedMessage(true);
        // Refresh local workers array
        const updatedWorkers = workers.map(w => {
          if (w.id === selectedWorkerId) {
            return {
              ...w,
              specialization: data.specialization,
              capacity: data.capacity,
              availability: availabilityPayload
            };
          }
          return w;
        });
        setWorkers(updatedWorkers);
        setTimeout(() => setSavedMessage(false), 3000);
      } else {
        setErrorMessage(res.error?.message || 'Failed to update availability.');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Network error updating scheduling details.');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleDay = (day: string) => {
    setValue(`activeDays.${day}`, !activeDays[day], { shouldValidate: true });
  };

  const handleTimeChange = (day: string, type: 'start' | 'end', val: string) => {
    setValue(type === 'start' ? `shiftStartTimes.${day}` : `shiftEndTimes.${day}`, val, { shouldValidate: true });
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
        <Loader2 className="w-8 h-8 text-emerald-600 animate-spin mb-3" />
        <span className="text-xs font-semibold">Synchronizing shift roster data...</span>
      </div>
    );
  }

  const selectedWorker = workers.find(w => w.id === selectedWorkerId);

  return (
    <div className="flex-1 p-8 flex flex-col gap-8 bg-slate-50/50">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Availability & Scheduling</h2>
          <p className="text-xs text-slate-500 mt-1">Configure active shift calendars, role specializations, and daily task capacity load.</p>
        </div>
        <div className="flex flex-col gap-2 items-end">
          {savedMessage && (
            <div className="p-2.5 bg-emerald-50 border border-emerald-250 text-emerald-800 rounded-lg text-xs font-bold flex items-center gap-2 shadow-sm animate-pulse">
              <CheckCircle className="w-4 h-4 text-emerald-600" /> Availability saved!
            </div>
          )}
          {errorMessage && (
            <div className="p-2.5 bg-rose-50 border border-rose-250 text-rose-800 rounded-lg text-xs font-bold flex items-center gap-2 shadow-sm">
              <XCircle className="w-4 h-4 text-rose-600" /> {errorMessage}
            </div>
          )}
        </div>
      </div>

      {/* Select Employee Selector */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row items-center gap-4">
        <div className="flex items-center gap-2 text-slate-700">
          <Users className="w-4 h-4 text-emerald-600" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Select Employee</span>
        </div>
        
        {workers.length === 0 ? (
          <span className="text-xs font-semibold text-rose-600">No employees registered in this workspace yet.</span>
        ) : (
          <select
            value={selectedWorkerId}
            onChange={e => setSelectedWorkerId(e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-bold text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors cursor-pointer min-w-[200px]"
          >
            {workers.map(w => (
              <option key={w.id} value={w.id}>
                {w.name} ({w.role.replace('_', ' ')})
              </option>
            ))}
          </select>
        )}
      </div>

      {workers.length > 0 && selectedWorker && (
        <form onSubmit={handleSubmit(handleSave)} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Columns: Shift Calendar */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider border-b border-slate-100 pb-3">
                <CalendarIcon className="w-4 h-4 text-emerald-600" /> Weekly Shift Patterns
              </h3>
              
              {errors.shiftEndTimes && (errors.shiftEndTimes as any).message && (
                <div className="p-2.5 bg-rose-55 border border-rose-200 text-rose-800 rounded-lg text-xs font-semibold flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-rose-600" /> {(errors.shiftEndTimes as any).message}
                </div>
              )}

              <div className="flex flex-col gap-3">
                {WEEKDAYS.map((day) => {
                  const isActive = activeDays[day];
                  return (
                    <div key={day} className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg border border-slate-100 bg-slate-50/20 hover:bg-slate-50/50 transition-colors gap-3">
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => handleToggleDay(day)}
                          className={`w-4 h-4 rounded border flex items-center justify-center transition-all cursor-pointer ${
                            isActive ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-slate-350 bg-white'
                          }`}
                        >
                          {isActive && <span className="text-[10px]">✓</span>}
                        </button>
                        <span className={`font-bold text-xs w-24 ${isActive ? 'text-slate-800' : 'text-slate-400'}`}>{day}</span>
                      </div>
                      
                      {isActive ? (
                        <div className="flex items-center gap-2 text-xs">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          <select 
                            value={shiftStartTimes[day]}
                            onChange={e => handleTimeChange(day, 'start', e.target.value)}
                            className="bg-white border border-slate-200 rounded px-2 py-1 text-slate-700 focus:outline-none"
                          >
                            <option value="08:00">08:00 AM</option>
                            <option value="09:00">09:00 AM</option>
                            <option value="10:00">10:00 AM</option>
                            <option value="12:00">12:00 PM</option>
                            <option value="20:00">08:00 PM</option>
                          </select>
                          <span className="text-slate-400 font-bold">to</span>
                          <select 
                            value={shiftEndTimes[day]}
                            onChange={e => handleTimeChange(day, 'end', e.target.value)}
                            className="bg-white border border-slate-200 rounded px-2 py-1 text-slate-700 focus:outline-none"
                          >
                            <option value="16:00">04:00 PM</option>
                            <option value="17:00">05:00 PM</option>
                            <option value="18:00">06:00 PM</option>
                            <option value="20:00">08:00 PM</option>
                            <option value="04:00">04:00 AM (Next Day)</option>
                          </select>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400 font-medium italic">Off Duty</span>
                      )}

                      <span className={`self-start sm:self-auto text-[9px] font-extrabold px-2 py-0.5 rounded-full ${
                        isActive ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-slate-100 text-slate-500'
                      }`}>
                        {isActive ? 'ACTIVE' : 'OFF'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column: Settings Form */}
          <div className="lg:col-span-1">
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-5 sticky top-6">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider border-b border-slate-100 pb-3">
                <Sliders className="w-4 h-4 text-emerald-600" /> Configure Scheduling
              </h3>

              <div className="flex flex-col gap-4 text-xs">
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <Award className="w-3 h-3 text-slate-400" /> Specialization
                  </label>
                  <input 
                    type="text"
                    {...register('specialization')}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                  />
                  {errors.specialization && (
                    <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{errors.specialization.message}</span>
                  )}
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <Briefcase className="w-3 h-3 text-slate-400" /> Max Daily Capacity
                  </label>
                  <input 
                    type="number"
                    {...register('capacity', { valueAsNumber: true })}
                    min={1}
                    max={100}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                  />
                  {errors.capacity && (
                    <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{errors.capacity.message}</span>
                  )}
                </div>

                <button 
                  type="submit"
                  disabled={saving}
                  className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md transition-all cursor-pointer mt-2 disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />} Save Work Details
                </button>
              </div>
            </div>
          </div>
        </form>
      )}
    </div>
  );
}

