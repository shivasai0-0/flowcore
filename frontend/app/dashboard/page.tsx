'use client';

import React, { useEffect, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { 
  Users, 
  DollarSign, 
  ShoppingBag, 
  Activity, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  Play,
  Database,
  Radio,
  FileText,
  Briefcase,
  ShieldAlert,
  ClipboardList,
  Calendar,
  Heart,
  UserCheck,
  Send,
  XCircle,
  ThumbsUp,
  AlertCircle
} from 'lucide-react';

export default function OperationsCenterHub() {
  const { businessId, businessName } = useWorkflowStore();
  const [loading, setLoading] = useState(true);
  const [kpis, setKpis] = useState<any>({
    appointments_count: 0,
    tasks_pending: 0,
    tasks_completed: 0,
    active_employees: 0,
    revenue: 0.0,
    csat_score: 5.0
  });
  const [timeline, setTimeline] = useState<any[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [slaAlerts, setSlaAlerts] = useState<any[]>([]);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchHubData = async () => {
    if (!businessId) return;
    try {
      // 1. Fetch widgets/KPIs
      const widgetsRes = await api.getDashboardWidgets(businessId);
      if (widgetsRes.success && widgetsRes.data) {
        setKpis(widgetsRes.data);
      }

      // 2. Fetch Operations Timeline
      const timelineRes = await api.getDashboardTimeline(businessId, 25);
      if (timelineRes.success && timelineRes.data) {
        setTimeline(timelineRes.data);
      }

      // 3. Fetch Pending Approvals
      const approvalsRes = await api.listApprovals(businessId, 'PENDING');
      if (approvalsRes.success && approvalsRes.data) {
        setApprovals(approvalsRes.data);
      }

      // 4. Fetch Tasks
      const tasksRes = await api.listTasks(businessId);
      if (tasksRes.success && tasksRes.data) {
        setTasks(tasksRes.data.slice(0, 10)); // limit to top 10
      }

      // Mock SLA Alerts derived from pending tasks/approvals
      const alerts = [];
      if (approvalsRes.data && approvalsRes.data.length > 0) {
        alerts.push({
          id: 'sla_app_1',
          type: 'WARNING',
          entity: 'Approval Request',
          message: `${approvalsRes.data.length} approval tasks are awaiting manager review.`,
          time: '15m remaining'
        });
      }
      const overdueTasks = tasksRes.data ? tasksRes.data.filter((t: any) => t.status !== 'COMPLETED' && t.due_time && new Date(t.due_time) < new Date()) : [];
      if (overdueTasks.length > 0) {
        alerts.push({
          id: 'sla_tsk_1',
          type: 'BREACHED',
          entity: 'Task Deadline',
          message: `${overdueTasks.length} assigned task(s) have breached their due time threshold.`,
          time: 'OVERDUE'
        });
      }
      setSlaAlerts(alerts);

    } catch (e) {
      console.error('Error fetching dashboard telemetry:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleApprovalAction = async (approvalId: string, action: 'APPROVE' | 'REJECT') => {
    setActionLoading(approvalId);
    try {
      const res = await api.takeApprovalAction(approvalId, action, 'Dashboard quick action', 'System Owner');
      if (res.success) {
        await fetchHubData();
      } else {
        alert('Action failed: ' + (res.error?.message || 'Unknown error'));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(null);
    }
  };

  useEffect(() => {
    fetchHubData();
    const interval = setInterval(fetchHubData, 6000); // refresh every 6s
    return () => clearInterval(interval);
  }, [businessId]);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
        <Activity className="w-8 h-8 text-emerald-600 animate-spin mb-3" />
        <span className="text-xs font-semibold">Initializing Operations Hub Telemetry...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 flex flex-col gap-8 bg-slate-50/50">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Operations Center Hub</h2>
          <p className="text-xs text-slate-500 mt-1">Live, event-driven monitoring of {businessName || 'your business'} WhatsApp workforce actions.</p>
        </div>
        <button 
          onClick={fetchHubData}
          className="px-4 py-2 rounded-lg bg-white border border-slate-200 text-xs font-bold text-slate-700 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
        >
          Refresh Feed
        </button>
      </div>

      {/* Row 1: Unified Metrics Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Metric 1: Revenue */}
        <div className="glass-card p-5 rounded-xl flex flex-col gap-3">
          <div className="flex justify-between items-center">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Revenue Today</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
              <DollarSign className="w-4 h-4 text-emerald-600" />
            </div>
          </div>
          <div>
            <span className="text-2xl font-bold text-slate-900 tracking-tight">${kpis.revenue.toFixed(2)}</span>
            <p className="text-[10px] text-emerald-600 mt-1 font-semibold">Total checkout proceeds</p>
          </div>
        </div>

        {/* Metric 2: Appointments */}
        <div className="glass-card p-5 rounded-xl flex flex-col gap-3">
          <div className="flex justify-between items-center">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Bookings Today</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
              <Calendar className="w-4 h-4 text-indigo-600" />
            </div>
          </div>
          <div>
            <span className="text-2xl font-bold text-slate-900 tracking-tight">{kpis.appointments_count}</span>
            <p className="text-[10px] text-indigo-600 mt-1 font-semibold">Appointments registered</p>
          </div>
        </div>

        {/* Metric 3: Active Tasks */}
        <div className="glass-card p-5 rounded-xl flex flex-col gap-3">
          <div className="flex justify-between items-center">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Staff Tasks</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
              <ClipboardList className="w-4 h-4 text-amber-600" />
            </div>
          </div>
          <div>
            <span className="text-2xl font-bold text-slate-900 tracking-tight">{kpis.tasks_pending}</span>
            <p className="text-[10px] text-amber-600 mt-1 font-semibold">Pending / In-progress tasks</p>
          </div>
        </div>

        {/* Metric 4: CSAT Rating */}
        <div className="glass-card p-5 rounded-xl flex flex-col gap-3">
          <div className="flex justify-between items-center">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Customer CSAT</span>
            <div className="w-8 h-8 rounded-lg bg-pink-50 flex items-center justify-center">
              <Heart className="w-4 h-4 text-pink-600" />
            </div>
          </div>
          <div>
            <span className="text-2xl font-bold text-slate-900 tracking-tight">{kpis.csat_score.toFixed(1)} / 5.0</span>
            <p className="text-[10px] text-pink-600 mt-1 font-semibold">Feedback satisfaction rating</p>
          </div>
        </div>
      </div>

      {/* Row 2: Secondary Quick KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 p-4 rounded-xl flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
            <Briefcase className="w-4 h-4 text-slate-600" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Staff Size</span>
            <h4 className="text-lg font-extrabold text-slate-900 mt-0.5">{kpis.active_employees} Active Employee(s)</h4>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-xl flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center shrink-0">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Tasks Completed</span>
            <h4 className="text-lg font-extrabold text-emerald-600 mt-0.5">{kpis.tasks_completed} Today</h4>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-xl flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-rose-50 flex items-center justify-center shrink-0">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Awaiting Approvals</span>
            <h4 className="text-lg font-extrabold text-rose-600 mt-0.5">{approvals.length} Pending Approval(s)</h4>
          </div>
        </div>
      </div>

      {/* Main Grid: Left Timeline and Alerts, Right Approvals and Task list */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        
        {/* Left Column: Timeline (span 2) */}
        <div className="xl:col-span-2 flex flex-col gap-8">
          
          {/* Timeline Widget */}
          <div className="glass-card p-6 rounded-xl flex flex-col gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 uppercase tracking-wider">
                <Activity className="w-4 h-4 text-emerald-600" /> Live Operations Timeline
              </h3>
              <p className="text-[10px] text-slate-500 mt-0.5">Real-time chronicle of business events and audit logs.</p>
            </div>

            <div className="flex flex-col gap-3 max-h-[500px] overflow-y-auto pr-1">
              {timeline.length > 0 ? (
                timeline.map((item: any) => {
                  const isAudit = item.type === 'AUDIT_EVENT';
                  const isCustomerMessage = item.event_type === 'CUSTOMER_MESSAGE';
                  const isSlaWarning = item.event_type?.includes('SLA');
                  
                  let badgeColor = 'bg-indigo-100 text-indigo-800';
                  if (isAudit) badgeColor = 'bg-blue-100 text-blue-800';
                  else if (isCustomerMessage) badgeColor = 'bg-emerald-100 text-emerald-800';
                  else if (isSlaWarning) badgeColor = 'bg-rose-100 text-rose-800';

                  return (
                    <div key={item.id} className="flex justify-between items-start gap-4 text-xs p-3.5 rounded-lg bg-slate-50 border border-slate-200/60 hover:bg-slate-100/30 transition-all">
                      <div className="flex items-start gap-3">
                        <span className={`px-2 py-0.5 rounded text-[9px] font-bold tracking-wide shrink-0 ${badgeColor}`}>
                          {item.event_type}
                        </span>
                        <div className="flex flex-col gap-0.5">
                          <span className="font-semibold text-slate-800">
                            {item.description}
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono mt-0.5">
                            ID: {item.entity_id} | Entity: {item.entity_type}
                          </span>
                          {item.payload && Object.keys(item.payload).length > 0 && (
                            <pre className="text-[9px] bg-slate-100 p-1.5 rounded border border-slate-200 mt-1 font-mono text-slate-500 overflow-x-auto max-w-lg">
                              {JSON.stringify(item.payload, null, 2)}
                            </pre>
                          )}
                        </div>
                      </div>
                      <span className="text-[10px] text-slate-400 font-medium shrink-0">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="p-8 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
                  No operational timeline records found.
                </div>
              )}
            </div>
          </div>

          {/* SLA Alerts Panel */}
          <div className="bg-white border border-slate-200 p-6 rounded-xl flex flex-col gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 uppercase tracking-wider">
                <AlertTriangle className="w-4 h-4 text-rose-600" /> Active SLA Alerts
              </h3>
              <p className="text-[10px] text-slate-500 mt-0.5">Workforce response and action timelines currently under threat.</p>
            </div>

            <div className="flex flex-col gap-2">
              {slaAlerts.length > 0 ? (
                slaAlerts.map((alert: any) => (
                  <div key={alert.id} className="flex justify-between items-center p-3 rounded-lg border border-rose-100 bg-rose-50/30 text-xs">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                      <div>
                        <span className="font-bold text-rose-900 block">{alert.entity}</span>
                        <span className="text-[10px] text-rose-700">{alert.message}</span>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-bold text-[9px]">
                      {alert.time}
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-4 text-center text-xs text-slate-400 bg-slate-50 rounded-lg border border-slate-100">
                  All systems operating within defined SLA parameters.
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Right Column: Approvals and Active Tasks (span 1) */}
        <div className="flex flex-col gap-8">
          
          {/* Approvals Widget */}
          <div className="bg-white border border-slate-200 p-6 rounded-xl flex flex-col gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 uppercase tracking-wider">
                <ShieldAlert className="w-4 h-4 text-rose-600" /> Pending Approvals Queue
              </h3>
              <p className="text-[10px] text-slate-500 mt-0.5">High-risk actions requiring manager override.</p>
            </div>

            <div className="flex flex-col gap-3 max-h-96 overflow-y-auto">
              {approvals.length > 0 ? (
                approvals.map((app: any) => {
                  const details = JSON.parse(app.details_json || '{}');
                  return (
                    <div key={app.id} className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-3">
                      <div>
                        <div className="flex justify-between items-center">
                          <span className="font-bold text-xs text-slate-800 uppercase tracking-wide">
                            {app.request_type}
                          </span>
                          <span className="text-[9px] text-slate-400 font-mono">
                            ID: {app.id.substring(0, 8)}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 mt-1">
                          Employee <b>{details.employee_name || 'Staff'}</b> requested completion of <b>{details.task_title || 'Critical Task'}</b>.
                        </p>
                      </div>

                      <div className="flex gap-2">
                        <button
                          disabled={actionLoading !== null}
                          onClick={() => handleApprovalAction(app.id, 'APPROVE')}
                          className="flex-1 py-1.5 rounded bg-emerald-600 text-white text-[10px] font-bold hover:bg-emerald-700 cursor-pointer disabled:opacity-50 transition-all flex items-center justify-center gap-1"
                        >
                          <ThumbsUp className="w-3 h-3" /> Approve
                        </button>
                        <button
                          disabled={actionLoading !== null}
                          onClick={() => handleApprovalAction(app.id, 'REJECT')}
                          className="flex-1 py-1.5 rounded bg-rose-600 text-white text-[10px] font-bold hover:bg-rose-700 cursor-pointer disabled:opacity-50 transition-all flex items-center justify-center gap-1"
                        >
                          <XCircle className="w-3 h-3" /> Reject
                        </button>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
                  No pending approvals.
                </div>
              )}
            </div>
          </div>

          {/* Active Tasks Widget */}
          <div className="bg-white border border-slate-200 p-6 rounded-xl flex flex-col gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 uppercase tracking-wider">
                <ClipboardList className="w-4 h-4 text-indigo-600" /> Recent Assigned Tasks
              </h3>
              <p className="text-[10px] text-slate-500 mt-0.5">Workforce tasks current queue status.</p>
            </div>

            <div className="flex flex-col gap-2.5 max-h-96 overflow-y-auto">
              {tasks.length > 0 ? (
                tasks.map((task: any) => (
                  <div key={task.id} className="p-3 rounded-lg bg-slate-50 border border-slate-150 flex justify-between items-center text-xs">
                    <div className="flex flex-col gap-0.5">
                      <span className="font-semibold text-slate-800">{task.title}</span>
                      <span className="text-[9px] text-slate-400">Assigned: {task.assigned_worker_name || 'Unassigned'}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[8px] font-bold tracking-wide uppercase shrink-0 ${
                      task.status === 'COMPLETED' ? 'bg-emerald-100 text-emerald-800' :
                      task.status === 'IN_PROGRESS' ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-700'
                    }`}>
                      {task.status}
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg">
                  No tasks currently scheduled.
                </div>
              )}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
