'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { 
  ShieldAlert, 
  CheckCircle, 
  XCircle, 
  Loader2, 
  Clock, 
  User, 
  FileText,
  AlertTriangle,
  Play
} from 'lucide-react';

type ToastType = { message: string; type: 'success' | 'error' };

export default function ApprovalsQueuePage() {
  const { businessId } = useWorkflowStore();
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApproval, setSelectedApproval] = useState<any | null>(null);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<ToastType | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (message: string, type: 'success' | 'error') => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ message, type });
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  };

  const fetchApprovals = async () => {
    if (!businessId) return;
    setLoading(true);
    try {
      const res = await api.listApprovals(businessId);
      if (res.success && res.data) {
        setApprovals(res.data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, [businessId]);

  const handleAction = async (approvalId: string, action: 'APPROVE' | 'REJECT' | 'MODIFY' | 'ESCALATE') => {
    setIsSubmitting(true);
    try {
      const res = await api.takeApprovalAction(approvalId, action, notes, "Owner");
      if (res.success) {
        showToast(`✅ Approval request resolved: ${action}`, 'success');
        setNotes('');
        setSelectedApproval(null);
        await fetchApprovals();
      } else {
        showToast(`❌ Action failed: ${res.error?.message || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      showToast(`❌ ${err.message}`, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      PENDING: 'bg-amber-100 text-amber-800 border-amber-200',
      APPROVED: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      REJECTED: 'bg-rose-100 text-rose-800 border-rose-200',
      ESCALATED: 'bg-indigo-100 text-indigo-800 border-indigo-200',
      MODIFIED: 'bg-blue-100 text-blue-800 border-blue-200',
    };
    return map[status.toUpperCase()] || 'bg-slate-100 text-slate-700';
  };

  const displayApprovals = approvals;

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
      <div>
        <h2 className="font-outfit font-bold text-xl text-slate-900">Approval Queue</h2>
        <p className="text-xs text-slate-500 mt-1">Review, approve, reject, or escalate sessions currently paused at Human Approval Nodes.</p>
      </div>

      {loading && approvals.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
          <Loader2 className="w-6 h-6 text-emerald-600 animate-spin mb-2" />
          <span className="text-xs font-semibold">Loading approval queue...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main List */}
          <div className="lg:col-span-2 flex flex-col gap-3">
            {displayApprovals.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-400 text-xs font-semibold">
                No human approvals currently in queue.
              </div>
            ) : (
              displayApprovals.map((a) => {
                const isPending = a.status === 'PENDING';
              return (
                <div
                  key={a.id}
                  onClick={() => setSelectedApproval(a)}
                  className={`bg-white border rounded-xl p-4 flex justify-between items-center cursor-pointer transition-all ${
                    selectedApproval?.id === a.id
                      ? 'border-emerald-500 ring-2 ring-emerald-500/10'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-xl border flex items-center justify-center shrink-0 ${
                      isPending ? 'bg-amber-50 border-amber-200 text-amber-600' : 'bg-slate-50 border-slate-200 text-slate-400'
                    }`}>
                      <ShieldAlert className="w-5 h-5" />
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-800 text-sm capitalize">{a.request_type.replace('_', ' ')}</span>
                        <span className={`px-2 py-0.5 border rounded text-[9px] font-bold ${getStatusBadge(a.status)}`}>
                          {a.status}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-medium">Session ID: <strong className="text-slate-700 font-mono">{a.session_id}</strong></span>
                      <span className="text-[10px] text-slate-400">Trigger Node: <span className="font-mono">{a.node_id}</span></span>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1.5 ml-4">
                    <span className="text-[10px] text-slate-400 font-semibold font-mono">
                      {new Date(a.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <button 
                      onClick={(e) => { e.stopPropagation(); setSelectedApproval(a); }}
                      className="text-[10px] font-bold text-emerald-600 hover:text-emerald-700"
                    >
                      Configure Decision
                    </button>
                  </div>
                </div>
              );
            }))}
          </div>

          {/* Details Drawer */}
          <div className="lg:col-span-1">
            {selectedApproval ? (
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm sticky top-6 flex flex-col gap-5">
                <div className="border-b border-slate-100 pb-3 flex justify-between items-start">
                  <div>
                    <h3 className="font-bold text-sm text-slate-800 capitalize">{selectedApproval.request_type.replace('_', ' ')} Details</h3>
                    <span className="text-[9px] text-slate-400 font-mono mt-0.5 break-all">ID: {selectedApproval.id}</span>
                  </div>
                  <span className={`px-2 py-0.5 border rounded text-[9px] font-bold ${getStatusBadge(selectedApproval.status)}`}>
                    {selectedApproval.status}
                  </span>
                </div>

                <div className="flex flex-col gap-4 text-xs">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Payload Details</span>
                    <pre className="mt-2 p-3 bg-slate-900 text-slate-200 rounded-lg text-[10px] font-mono overflow-x-auto max-h-40">
                      {JSON.stringify(selectedApproval.details, null, 2)}
                    </pre>
                  </div>

                  {selectedApproval.status === 'PENDING' ? (
                    <div className="flex flex-col gap-3">
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Resolution Notes</label>
                        <textarea
                          value={notes}
                          onChange={e => setNotes(e.target.value)}
                          placeholder="Provide decision context/reasoning..."
                          rows={2}
                          className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors resize-none"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-2 mt-1">
                        <button
                          disabled={isSubmitting}
                          onClick={() => handleAction(selectedApproval.id, 'APPROVE')}
                          className="py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-sm cursor-pointer disabled:opacity-50"
                        >
                          Approve
                        </button>
                        <button
                          disabled={isSubmitting}
                          onClick={() => handleAction(selectedApproval.id, 'REJECT')}
                          className="py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-sm cursor-pointer disabled:opacity-50"
                        >
                          Reject
                        </button>
                        <button
                          disabled={isSubmitting}
                          onClick={() => handleAction(selectedApproval.id, 'MODIFY')}
                          className="py-2 rounded-lg bg-white border border-blue-200 text-blue-700 hover:bg-blue-50 font-bold text-xs shadow-sm cursor-pointer disabled:opacity-50"
                        >
                          Modify
                        </button>
                        <button
                          disabled={isSubmitting}
                          onClick={() => handleAction(selectedApproval.id, 'ESCALATE')}
                          className="py-2 rounded-lg bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-50 font-bold text-xs shadow-sm cursor-pointer disabled:opacity-50"
                        >
                          Escalate
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 flex flex-col gap-1.5 text-[11px] text-slate-600">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Decision Metadata</span>
                      <span>Action taken: <strong className="text-slate-800 font-bold uppercase">{selectedApproval.action_taken}</strong></span>
                      <span>Resolved by: <strong className="text-slate-800 font-semibold">{selectedApproval.resolved_by}</strong></span>
                      <span>Resolved at: <strong className="text-slate-800 font-semibold">{new Date(selectedApproval.resolved_at).toLocaleString()}</strong></span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white border border-slate-200 rounded-xl p-6 text-center text-xs text-slate-400 font-semibold flex flex-col items-center justify-center gap-2 h-48 shadow-sm">
                <ShieldAlert className="w-8 h-8 text-slate-300" />
                Select any approval card to configure resolution decisions.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
