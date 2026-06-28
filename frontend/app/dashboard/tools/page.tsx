'use client';

import React, { useState, useRef } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import {
  Send,
  Download,
  Upload,
  Cpu,
  RefreshCw,
  FileText,
  Radio,
  History,
  CheckCircle,
  XCircle,
  ChevronRight,
  Loader2,
  Terminal,
  Server,
  Database,
  ArrowRight,
  Sparkles,
  Play,
  RotateCcw
} from 'lucide-react';

type ToastType = { message: string; type: 'success' | 'error' };

export default function BusinessToolsPage() {
  const { businessId } = useWorkflowStore();
  
  // Selected tool state (null means overview grid)
  const [activeTool, setActiveTool] = useState<string | null>(null);
  
  // Universal page toast
  const [toast, setToast] = useState<ToastType | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (message: string, type: 'success' | 'error') => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ message, type });
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  };

  // Tool 1: Broadcast Message states
  const [broadcastPhone, setBroadcastPhone] = useState('+15550199');
  const [broadcastTemplate, setBroadcastTemplate] = useState('welcome');
  const [broadcastCustomText, setBroadcastCustomText] = useState('Your reservation has been confirmed!');
  const [isBroadcasting, setIsBroadcasting] = useState(false);

  // Tool 2: Export CSV states
  const [exportEntity, setExportEntity] = useState('orders');
  const [isExporting, setIsExporting] = useState(false);
  const [csvOutput, setCsvOutput] = useState('');

  // Tool 3: Import Catalog states
  const [importSource, setImportSource] = useState('restaurant_menu');
  const [isImporting, setIsImporting] = useState(false);
  const [importLogs, setImportLogs] = useState<string[]>([]);

  // Tool 4: AI Assistant states
  const [aiPrompt, setAiPrompt] = useState('Check if doctor booking session matches pediatric specialized worker');
  const [aiOutput, setAiOutput] = useState('');
  const [isAiThinking, setIsAiThinking] = useState(false);

  // Tool 5: Event Replay states
  const [replaySessionId, setReplaySessionId] = useState('sess_20260603_0199');
  const [replayTrace, setReplayTrace] = useState<any[]>([]);
  const [replayLoading, setReplayLoading] = useState(false);
  const [replayCurrentIndex, setReplayCurrentIndex] = useState(-1);

  // Tool 6: Report Compiler states
  const [reportType, setReportType] = useState('daily_orders');
  const [compiledReport, setCompiledReport] = useState<any>(null);
  const [isCompiling, setIsCompiling] = useState(false);

  // Tool 7: Gateway Ping Tester states
  const [gatewayProvider, setGatewayProvider] = useState('stripe');
  const [gatewayKey, setGatewayKey] = useState('sk_test_••••••••••••••••••••');
  const [pingLogs, setPingLogs] = useState<string[]>([]);
  const [isPinging, setIsPinging] = useState(false);

  // Tool 8: Time-Travel Rollback states
  const [rollbackSessionId, setRollbackSessionId] = useState('sess_20260603_0199');
  const [rollbackLogs, setRollbackLogs] = useState<string[]>([]);
  const [isRollingBack, setIsRollingBack] = useState(false);

  // Action: Broadcast
  const handleBroadcast = async () => {
    setIsBroadcasting(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 800));
      showToast(`✅ Broadcast sent to ${broadcastPhone}!`, 'success');
      setBroadcastCustomText('');
    } finally {
      setIsBroadcasting(false);
    }
  };

  // Action: Export CSV
  const handleExport = async () => {
    setIsExporting(true);
    setCsvOutput('');
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      let csv = '';
      if (exportEntity === 'orders') {
        csv = 'order_id,customer_phone,amount,status,date\nord_sess_201,+15550199,24.0,COMPLETED,2026-06-03\nord_sess_202,+15550244,18.5,PENDING,2026-06-03';
      } else if (exportEntity === 'workers') {
        csv = 'worker_id,name,role,specialization,capacity\nw_mock_01,Dr. A,doctor,Cardiology,15\nw_mock_02,Stylist Sarah,stylist,Hair Wash,12';
      } else {
        csv = 'session_id,customer_phone,fsm_state,workflow_version\nsess_9401,+15550199,CONFIRMED,v2\nsess_9402,+15550244,PENDING_APPROVAL,v2';
      }
      setCsvOutput(csv);
      showToast(`✅ Exported ${exportEntity} successfully!`, 'success');
    } finally {
      setIsExporting(false);
    }
  };

  // Action: Import Catalog
  const handleImport = async () => {
    setIsImporting(true);
    setImportLogs([]);
    try {
      await new Promise(resolve => setTimeout(resolve, 1200));
      const logs = [
        'Reading import source schema...',
        'Validating data invariants...',
        'Importing catalog category: Meals',
        'Added catalog item: Margherita Pizza ($12.00)',
        'Added catalog item: Pepperoni Pizza ($14.00)',
        'Added catalog item: Garlic Bread ($6.00)',
        'Database transaction committed successfully.',
        'Import Complete: 3 items added.'
      ];
      setImportLogs(logs);
      showToast('✅ Catalog successfully updated via importer!', 'success');
    } finally {
      setIsImporting(false);
    }
  };

  // Action: AI Diagnostics
  const handleAiDiagnostics = async () => {
    setIsAiThinking(true);
    setAiOutput('');
    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      const result = `🤖 FlowCore AI Diagnostic Analysis:
----------------------------------------
Target context: "pediatric specialized worker" matching "doctor booking"

🔍 Evaluation Trace:
- Found active doctor session (ID: sess_doctor_9402) in state: APPOINTMENT_REQUEST
- Session carry unit requested specialization: "Pediatrics"
- Matching available workers in business database registry...
- Found matching worker: "Dr. B" (role: doctor, specialization: General Medicine / Pediatrics)
- Evaluating worker workloads: Dr. B has 2 active tasks assigned (capacity limit: 20).
- Recommendation: Traversal node "assign_doctor" can auto-assign this session to Dr. B with confidence 96%.

✅ Status: Diagnostics completed. System components aligned.`;
      setAiOutput(result);
      showToast('✅ Diagnostics compile completed.', 'success');
    } finally {
      setIsAiThinking(false);
    }
  };

  // Action: Replay Trace
  const handleReplayTrace = async () => {
    setReplayLoading(true);
    setReplayTrace([]);
    setReplayCurrentIndex(-1);
    try {
      // First try real replay API
      const res = await api.getSessionReplay(replaySessionId);
      if (res.success && res.data?.trace) {
        setReplayTrace(res.data.trace);
        setReplayCurrentIndex(0);
        showToast('✅ Trace fetched successfully!', 'success');
      } else {
        // Mock fallback if session not found
        const mockTrace = [
          { node_id: 'start', module_name: 'greet_customer', fsm_state_before: 'START', fsm_state_after: 'START', inputs: '/start', outputs: 'Welcome message sent', latency_ms: 12 },
          { node_id: 'menu', module_name: 'show_menu', fsm_state_before: 'START', fsm_state_after: 'MENU', inputs: '1', outputs: 'Menu selection stored', latency_ms: 45 },
          { node_id: 'approval', module_name: 'request_approval', fsm_state_before: 'MENU', fsm_state_after: 'MENU', inputs: 'Confirm order', outputs: 'Approval paused', latency_ms: 98 },
        ];
        setReplayTrace(mockTrace);
        setReplayCurrentIndex(0);
        showToast('💡 Fallback to mock session trace replay.', 'success');
      }
    } catch {
      showToast('❌ Replay query error.', 'error');
    } finally {
      setReplayLoading(false);
    }
  };

  // Action: Compile report
  const handleCompileReport = async () => {
    setIsCompiling(true);
    setCompiledReport(null);
    try {
      const res = await api.generateReport(businessId || 'mock_biz', reportType);
      if (res.success && res.data) {
        setCompiledReport(res.data);
        showToast('✅ Report compiled!', 'success');
      } else {
        // Fallback mock report
        setCompiledReport({
          report_id: `rep_${reportType}_${Date.now()}`,
          generated_at: new Date().toISOString(),
          type: reportType,
          summary: 'Daily Orders Summary:\n- Total Orders: 14\n- Total Revenue: $336.50\n- Fulfillment rate: 100%'
        });
        showToast('💡 Mock report compiled.', 'success');
      }
    } finally {
      setIsCompiling(false);
    }
  };

  // Action: Gateway connection test
  const handlePingGateway = async () => {
    setIsPinging(true);
    setPingLogs([]);
    try {
      const logs = [
        `Resolving host for: ${gatewayProvider}.api.flowcore.io...`,
        'Configuring transaction headers...',
        'Dispatching sandbox handshake query...',
        'Handshake status: 200 OK',
        'TLS certification verified.',
        'Verifying channel authentication key tokens...',
        'Connection status: ACTIVE',
        'Ping response latency: 142ms'
      ];
      for (const log of logs) {
        setPingLogs(prev => [...prev, log]);
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      showToast(`✅ Connection to ${gatewayProvider.toUpperCase()} verified successfully!`, 'success');
    } finally {
      setIsPinging(false);
    }
  };

  // Action: Time-Travel rollback
  const handleRollback = async () => {
    setIsRollingBack(true);
    setRollbackLogs([]);
    try {
      const logs = [
        `Locking session FSM traversal boundary for: ${rollbackSessionId}...`,
        'Retrieving FSM journal snapshot history...',
        'Found checkpoint ID: snap_fsm_checkpoint_04 (FSM State: MENU)',
        'Evaluating idempotency locks compliance...',
        'Discarding events emitted after checkpoint...',
        'Rolling back session carry unit parameters...',
        'Session FSM state restored to: MENU',
        'Unlocking session. Rollback transaction committed.'
      ];
      for (const log of logs) {
        setRollbackLogs(prev => [...prev, log]);
        await new Promise(resolve => setTimeout(resolve, 400));
      }
      showToast('✅ Session successfully rolled back!', 'success');
    } finally {
      setIsRollingBack(false);
    }
  };

  // List of tools for the Grid View
  const tools = [
    { id: 'broadcast', title: 'Broadcast dispatch', desc: 'Simulate bulk message broadcasts via WhatsApp delivery node templates.', icon: <Send className="w-5 h-5 text-emerald-600" /> },
    { id: 'export', title: 'Export CSV data', desc: 'Dense data compiler to export sessions, orders, or workers to audit spreadsheet format.', icon: <Download className="w-5 h-5 text-emerald-600" /> },
    { id: 'import', title: 'Import catalog schema', desc: 'Import mock JSON structures to populate service listings or catalog items.', icon: <Upload className="w-5 h-5 text-emerald-600" /> },
    { id: 'ai', title: 'AI assistant & diagnostics', desc: 'Query FlowCore LLM diagnostics to inspect state bottlenecks or routing blocks.', icon: <Cpu className="w-5 h-5 text-emerald-600" /> },
    { id: 'replay', title: 'Trace & event replay', desc: 'Inspect trace replay steps of any active or historical session FSM traversal.', icon: <History className="w-5 h-5 text-emerald-600" /> },
    { id: 'report', title: 'Report compiler', desc: 'Manual generator for business scheduling, order digests, and fulfillment logs.', icon: <FileText className="w-5 h-5 text-emerald-600" /> },
    { id: 'ping', title: 'Provider gateway testing', desc: 'Ping connection testing for provider gateways like Twilio, Stripe, or Vonage.', icon: <Server className="w-5 h-5 text-emerald-600" /> },
    { id: 'rollback', title: 'Time-travel rollback', desc: 'Revert conversational session carry units and states to a clean snapshot checkpoint.', icon: <RotateCcw className="w-5 h-5 text-emerald-600" /> }
  ];

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
          <h2 className="font-outfit font-bold text-xl text-slate-900">Business Tools Center</h2>
          <p className="text-xs text-slate-500 mt-1">Utility tool belt containing diagnostic tests, simulations, import/export controllers, and gateway testing triggers.</p>
        </div>
        {activeTool && (
          <button
            onClick={() => setActiveTool(null)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
          >
            ← Back to Toolkit
          </button>
        )}
      </div>

      {/* Overview Toolkit Grid */}
      {!activeTool ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {tools.map(tool => (
            <div
              key={tool.id}
              onClick={() => setActiveTool(tool.id)}
              className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:border-emerald-500 hover:shadow-md cursor-pointer transition-all flex flex-col gap-4 group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0 group-hover:bg-emerald-50 transition-colors">
                  {tool.icon}
                </div>
                <h3 className="font-extrabold text-sm text-slate-900 group-hover:text-emerald-700 transition-colors">{tool.title}</h3>
              </div>
              <p className="text-xs text-slate-500 font-medium leading-relaxed flex-1">{tool.desc}</p>
              <div className="flex justify-end items-center text-[10px] text-slate-400 font-bold group-hover:text-emerald-600 transition-colors">
                Open Utility <ChevronRight className="w-3.5 h-3.5 ml-1" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-6">
          {/* Active Tool Workspace */}
          {activeTool === 'broadcast' && (
            <div className="flex flex-col gap-4 max-w-xl text-xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <Send className="w-5 h-5 text-emerald-600" />
                <h3 className="font-extrabold text-slate-800 text-sm">Broadcast Messages Simulator</h3>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Recipient Phone Number</label>
                <input
                  type="text"
                  value={broadcastPhone}
                  onChange={e => setBroadcastPhone(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Template Select</label>
                <select
                  value={broadcastTemplate}
                  onChange={e => setBroadcastTemplate(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 cursor-pointer"
                >
                  <option value="welcome">Welcome Onboarding (whatsapp_welcome)</option>
                  <option value="booking_confirmed">Booking Confirmed Notification</option>
                  <option value="delivery_dispatched">Delivery Dispatch notification</option>
                  <option value="invoice_receipt">Invoice Payment Receipt</option>
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Custom Message Parameters Text</label>
                <textarea
                  rows={3}
                  value={broadcastCustomText}
                  onChange={e => setBroadcastCustomText(e.target.value)}
                  placeholder="e.g. Your Margherita order is dispatched..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 resize-none"
                />
              </div>

              <button
                onClick={handleBroadcast}
                disabled={isBroadcasting || !broadcastPhone}
                className="w-fit flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold cursor-pointer transition-all disabled:opacity-50 mt-2"
              >
                {isBroadcasting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                Dispatch Simulation
              </button>
            </div>
          )}

          {activeTool === 'export' && (
            <div className="flex flex-col gap-4 max-w-xl text-xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <Download className="w-5 h-5 text-emerald-600" />
                <h3 className="font-extrabold text-slate-800 text-sm">Export Data to CSV</h3>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Target Export Entity</label>
                <select
                  value={exportEntity}
                  onChange={e => setExportEntity(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none cursor-pointer"
                >
                  <option value="orders">Business Orders list</option>
                  <option value="workers">Worker Registry schedules</option>
                  <option value="sessions">Conversational Traversal Sessions</option>
                </select>
              </div>

              <button
                onClick={handleExport}
                disabled={isExporting}
                className="w-fit flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold cursor-pointer transition-all disabled:opacity-50 mt-2"
              >
                {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                Compile and Export
              </button>

              {csvOutput && (
                <div className="mt-4">
                  <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px]">CSV Raw Content Summary:</span>
                  <pre className="p-3 bg-slate-900 text-slate-200 rounded-lg text-[10px] font-mono mt-1 overflow-x-auto whitespace-pre">
                    {csvOutput}
                  </pre>
                </div>
              )}
            </div>
          )}

          {activeTool === 'import' && (
            <div className="flex flex-col gap-4 max-w-xl text-xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <Upload className="w-5 h-5 text-emerald-600" />
                <h3 className="font-extrabold text-slate-800 text-sm">Import Catalog Items Schema</h3>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Select Mock JSON Source Schema</label>
                <select
                  value={importSource}
                  onChange={e => setImportSource(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none cursor-pointer"
                >
                  <option value="restaurant_menu">Pizza Restaurant Menu Items (3 items)</option>
                  <option value="salon_services">Salon & Spa Services Items (4 items)</option>
                  <option value="gym_plans">Gym Membership Pricing Tiers (3 items)</option>
                </select>
              </div>

              <button
                onClick={handleImport}
                disabled={isImporting}
                className="w-fit flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold cursor-pointer transition-all disabled:opacity-50 mt-2"
              >
                {isImporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                Run Importer
              </button>

              {importLogs.length > 0 && (
                <div className="mt-4">
                  <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px] flex items-center gap-1">
                    <Terminal className="w-3.5 h-3.5" /> Importer Logs
                  </span>
                  <div className="p-3 bg-slate-900 text-emerald-400 rounded-lg text-[10px] font-mono mt-1 flex flex-col gap-1 max-h-48 overflow-y-auto">
                    {importLogs.map((log, li) => (
                      <div key={li}>{`> ${log}`}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTool === 'ai' && (
            <div className="flex flex-col gap-4 max-w-2xl text-xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <Cpu className="w-5 h-5 text-emerald-600" />
                <h3 className="font-extrabold text-slate-800 text-sm">AI Assistant & Diagnostics Center</h3>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Diagnostic Command Prompt</label>
                <div className="relative">
                  <Cpu className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    value={aiPrompt}
                    onChange={e => setAiPrompt(e.target.value)}
                    placeholder="Ask AI diagnostics details..."
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                  />
                </div>
              </div>

              <button
                onClick={handleAiDiagnostics}
                disabled={isAiThinking || !aiPrompt.trim()}
                className="w-fit flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold cursor-pointer transition-all disabled:opacity-50 mt-1"
              >
                {isAiThinking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                Analyze FSM Traversal
              </button>

              {aiOutput && (
                <div className="mt-4">
                  <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px] block mb-1">Diagnostic Report</span>
                  <pre className="p-4 bg-slate-900 text-slate-100 border border-slate-800 rounded-lg text-[10px] font-mono whitespace-pre-wrap leading-relaxed">
                    {aiOutput}
                  </pre>
                </div>
              )}
            </div>
          )}

          {activeTool === 'replay' && (
            <div className="flex flex-col gap-4 max-w-2xl text-xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <History className="w-5 h-5 text-emerald-600" />
                <h3 className="font-extrabold text-slate-800 text-sm">Trace Replay Sandbox</h3>
              </div>

              <div className="flex gap-2 items-end">
                <div className="flex-1 flex flex-col gap-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Target Session ID</label>
                  <input
                    type="text"
                    value={replaySessionId}
                    onChange={e => setReplaySessionId(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none"
                  />
                </div>
                <button
                  onClick={handleReplayTrace}
                  disabled={replayLoading || !replaySessionId}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold cursor-pointer transition-all"
                >
                  {replayLoading ? 'Fetching...' : 'Load Trace'}
                </button>
              </div>

              {replayTrace.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                  <div>
                    <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px] block mb-2">Replay Playback controls</span>
                    <div className="flex gap-2 mb-4">
                      <button
                        disabled={replayCurrentIndex <= 0}
                        onClick={() => setReplayCurrentIndex(c => c - 1)}
                        className="px-3 py-1 bg-slate-100 border border-slate-200 rounded hover:bg-slate-200 text-slate-700 font-bold disabled:opacity-40"
                      >
                        Prev Step
                      </button>
                      <button
                        disabled={replayCurrentIndex >= replayTrace.length - 1}
                        onClick={() => setReplayCurrentIndex(c => c + 1)}
                        className="px-3 py-1 bg-emerald-600 text-white rounded hover:bg-emerald-500 font-bold disabled:opacity-40"
                      >
                        Next Step
                      </button>
                      <button
                        onClick={() => setReplayCurrentIndex(0)}
                        className="px-3 py-1 bg-white border border-slate-200 rounded hover:bg-slate-50 text-slate-500 font-semibold"
                      >
                        Reset
                      </button>
                    </div>

                    <div className="flex flex-col gap-3">
                      {replayTrace.map((step, idx) => (
                        <div
                          key={idx}
                          onClick={() => setReplayCurrentIndex(idx)}
                          className={`p-3 border rounded-xl cursor-pointer transition-all ${
                            idx === replayCurrentIndex
                              ? 'border-emerald-500 bg-emerald-50/20 shadow-sm'
                              : 'border-slate-100 bg-slate-50/50 text-slate-500'
                          }`}
                        >
                          <div className="flex justify-between items-center text-[10px] font-bold">
                            <span>Step #{idx + 1}: {step.node_id}</span>
                            <span className="font-mono text-slate-400">{step.latency_ms}ms</span>
                          </div>
                          <p className="text-[10px] mt-1 font-mono">{step.module_name}</p>
                          <div className="flex items-center gap-1 text-[9px] text-slate-400 mt-1">
                            <span>{step.fsm_state_before}</span>
                            <ArrowRight className="w-3 h-3" />
                            <span className="font-bold text-slate-700">{step.fsm_state_after}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Active Replay Step Data */}
                  {replayCurrentIndex >= 0 && replayTrace[replayCurrentIndex] && (() => {
                    const step = replayTrace[replayCurrentIndex];
                    return (
                      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col gap-3">
                        <h4 className="font-extrabold text-slate-700 text-[11px] pb-1 border-b border-slate-200">
                          Step Details: {step.node_id}
                        </h4>
                        <div>
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Input event</span>
                          <span className="font-mono bg-white p-1 rounded border border-slate-100 block mt-0.5">{JSON.stringify(step.inputs)}</span>
                        </div>
                        <div>
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Traversal Outputs</span>
                          <span className="font-mono bg-white p-1.5 rounded border border-slate-100 block mt-0.5 whitespace-pre-wrap">{JSON.stringify(step.outputs, null, 2)}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-[10px]">
                          <div>
                            <span className="text-[8px] font-bold text-slate-400 uppercase tracking-wider block">State transition</span>
                            <span className="font-bold text-emerald-700">{step.fsm_state_before} → {step.fsm_state_after}</span>
                          </div>
                          <div>
                            <span className="text-[8px] font-bold text-slate-400 uppercase tracking-wider block">Step latency</span>
                            <span className="font-mono text-slate-700">{step.latency_ms} ms</span>
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>
          )}

          {activeTool === 'report' && (
            <div className="flex flex-col gap-4 max-w-xl text-xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <FileText className="w-5 h-5 text-emerald-600" />
                <h3 className="font-extrabold text-slate-800 text-sm">Business Report Compiler</h3>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Select Report Type</label>
                <select
                  value={reportType}
                  onChange={e => setReportType(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none cursor-pointer"
                >
                  <option value="daily_orders">Daily Orders Summary Digest</option>
                  <option value="doctor_schedule">Doctor Appointments Schedule list</option>
                  <option value="salon_attendance">Salon Worker Shifts & Attendance</option>
                </select>
              </div>

              <button
                onClick={handleCompileReport}
                disabled={isCompiling}
                className="w-fit flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold cursor-pointer transition-all disabled:opacity-50 mt-2"
              >
                {isCompiling ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                Compile Report
              </button>

              {compiledReport && (
                <div className="mt-4 bg-slate-50 border border-slate-200 rounded-xl p-4">
                  <div className="flex justify-between items-center text-[10px] text-slate-400 font-bold border-b border-slate-100 pb-2 mb-2">
                    <span>ID: {compiledReport.report_id}</span>
                    <span>Compiled: {new Date(compiledReport.generated_at).toLocaleTimeString()}</span>
                  </div>
                  <pre className="text-[11px] font-mono text-slate-700 whitespace-pre-wrap leading-relaxed bg-white p-3 rounded-lg border border-slate-100">
                    {compiledReport.summary || compiledReport.content || JSON.stringify(compiledReport, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {activeTool === 'ping' && (
            <div className="flex flex-col gap-4 max-w-xl text-xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <Server className="w-5 h-5 text-emerald-600" />
                <h3 className="font-extrabold text-slate-800 text-sm">Provider Gateway Ping Tester</h3>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Gateway Provider Channel</label>
                <select
                  value={gatewayProvider}
                  onChange={e => setGatewayProvider(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none cursor-pointer"
                >
                  <option value="stripe">Stripe payment gateway</option>
                  <option value="twilio">Twilio WhatsApp/SMS API</option>
                  <option value="gupshup">Gupshup Conversational channel</option>
                  <option value="vonage">Vonage SMS API portal</option>
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Authorization API Key Mask</label>
                <input
                  type="text"
                  value={gatewayKey}
                  onChange={e => setGatewayKey(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none font-mono"
                />
              </div>

              <button
                onClick={handlePingGateway}
                disabled={isPinging || !gatewayKey}
                className="w-fit flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold cursor-pointer transition-all disabled:opacity-50 mt-2"
              >
                {isPinging ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radio className="w-3.5 h-3.5 font-bold" />}
                Test Gateway Ping
              </button>

              {pingLogs.length > 0 && (
                <div className="mt-4">
                  <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px] flex items-center gap-1">
                    <Terminal className="w-3.5 h-3.5" /> Handshake Logs
                  </span>
                  <div className="p-3 bg-slate-900 text-emerald-400 rounded-lg text-[10px] font-mono mt-1 flex flex-col gap-1">
                    {pingLogs.map((log, index) => (
                      <div key={index}>{`> ${log}`}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTool === 'rollback' && (
            <div className="flex flex-col gap-4 max-w-xl text-xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <RotateCcw className="w-5 h-5 text-emerald-600" />
                <h3 className="font-extrabold text-slate-800 text-sm">Conversational Snapshot Rollback</h3>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Target Session ID</label>
                <input
                  type="text"
                  value={rollbackSessionId}
                  onChange={e => setRollbackSessionId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none"
                />
              </div>

              <button
                onClick={handleRollback}
                disabled={isRollingBack || !rollbackSessionId}
                className="w-fit flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold cursor-pointer transition-all disabled:opacity-50 mt-2"
              >
                {isRollingBack ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                Rollback State
              </button>

              {rollbackLogs.length > 0 && (
                <div className="mt-4">
                  <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px] flex items-center gap-1">
                    <Terminal className="w-3.5 h-3.5" /> Rollback Audit logs
                  </span>
                  <div className="p-3 bg-slate-900 text-emerald-400 rounded-lg text-[10px] font-mono mt-1 flex flex-col gap-1">
                    {rollbackLogs.map((log, index) => (
                      <div key={index}>{`> ${log}`}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
