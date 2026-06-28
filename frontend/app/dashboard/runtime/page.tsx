'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Toast, ToastMessage } from '@/components/ui/toast';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { 
  Radio, 
  MessageSquare, 
  Send, 
  Loader2, 
  History, 
  RotateCcw, 
  ShoppingCart, 
  CreditCard, 
  Truck, 
  ShieldAlert,
  ArrowRight,
  Sparkles,
  Zap,
  Play
} from 'lucide-react';

export default function RuntimePage() {
  const {
    activeSession,
    chatHistory,
    isProcessingInput,
    startChatSession,
    sendChatMessage,
    rollbackToSnapshot,
    whatsappNumber
  } = useWorkflowStore();

  const [inputVal, setInputVal] = useState('');
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [loadingSnapshots, setLoadingSnapshots] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (message: string, type: 'success' | 'error' | 'warning' | 'info') => {
    const newId = `toast_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    setToasts((prev) => [...prev, { id: newId, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== newId));
    }, 4000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Auto-scroll chat window
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // Load snapshots when activeSession shifts
  const fetchSnapshots = async () => {
    if (!activeSession) return;
    setLoadingSnapshots(true);
    const res = await api.listSnapshots(activeSession.id);
    if (res.success && res.data) {
      setSnapshots(res.data);
    }
    setLoadingSnapshots(false);
  };

  useEffect(() => {
    if (activeSession) {
      fetchSnapshots();
    }
  }, [activeSession]);

  const handleStartSession = async () => {
    try {
      const success = await startChatSession();
      if (success) {
        addToast('WhatsApp simulation session active!', 'success');
      } else {
        addToast('Failed to start chat session.', 'error');
      }
    } catch (err: any) {
      addToast(err.message || 'Failed to start chat session.', 'error');
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;
    const msg = inputVal;
    setInputVal('');
    try {
      await sendChatMessage(msg);
      // Refresh snapshot list
      await fetchSnapshots();
    } catch (err: any) {
      addToast(err.message || 'API dispatch request failed.', 'error');
    }
  };

  const handleRollback = async (snapshotId: string) => {
    if (confirm('Revert session state back to this historical snapshot?')) {
      try {
        await rollbackToSnapshot(snapshotId);
        await fetchSnapshots();
        addToast('Rolled back state machine snapshot successfully!', 'success');
      } catch (err: any) {
        addToast(err.message || 'Time travel failed.', 'error');
      }
    }
  };

  // Safe JSON/value checks for business details
  const businessData = activeSession?.carry_unit || {};
  const orderItems = businessData?.order?.items || [];
  const logistics = businessData?.logistics || {};
  const customer = businessData?.customer || {};

  return (
    <div className="flex-1 flex overflow-hidden bg-slate-50/30">
      {/* Toast Manager container */}
      <div className="fixed top-5 right-5 z-[9999] flex flex-col gap-2 max-w-sm">
        {toasts.map((t) => (
          <Toast key={t.id} message={t.message} type={t.type} onClose={() => removeToast(t.id)} />
        ))}
      </div>

      {/* Left panel: Conversation Simulator (WhatsApp Mockup) */}
      <div className="w-[450px] border-r border-slate-200 bg-slate-50/50 p-6 flex flex-col shrink-0">
        <div className="mb-4">
          <h2 className="font-outfit font-bold text-base text-slate-900 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-emerald-600" />
            WhatsApp Simulator
          </h2>
          <p className="text-[10px] text-slate-500 mt-1">Interact with your deployed workflow state machine.</p>
        </div>

        {!activeSession ? (
          <div className="flex-1 border border-dashed border-slate-200 rounded-xl flex flex-col items-center justify-center p-6 text-center gap-4 bg-white shadow-sm">
            <Radio className="w-8 h-8 text-slate-400 animate-pulse" />
            <div>
              <h4 className="text-sm font-semibold text-slate-800">No Active Session</h4>
              <p className="text-xs text-slate-500 max-w-xs mt-1">Initialize a test customer session on WhatsApp to trace traversed FSM states.</p>
            </div>
            <button 
              onClick={handleStartSession}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-all shadow-md flex items-center gap-1.5 glow-active cursor-pointer"
            >
              Start Traversal Session <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex-1 rounded-xl border border-slate-200 bg-white p-4 flex flex-col justify-between h-full relative shadow-sm">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 to-purple-500 rounded-t-xl"></div>

            {/* Simulated Chat Window Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center font-bold text-emerald-600 text-xs border border-slate-200 shrink-0">
                  C
                </div>
                <div className="min-w-0">
                  <h3 className="text-xs font-semibold text-slate-800 truncate">Customer: +{whatsappNumber}</h3>
                  <p className="text-[9px] text-slate-400 leading-none mt-0.5 font-mono">Session ID: {activeSession.id}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleStartSession}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-[10px] font-bold text-slate-700 transition-all shrink-0 cursor-pointer shadow-sm"
                title="Start a new traversal session"
              >
                <RotateCcw className="w-3 h-3 text-slate-500" />
                New Session
              </button>
            </div>

            {/* Chat Body */}
            <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-3 bg-slate-50/50 rounded-lg p-2 my-2 border border-slate-100">
              {chatHistory.map((msg, idx) => {
                const isUser = msg.sender === 'user';
                const isSystem = msg.sender === 'system';
                
                if (isSystem) {
                  return (
                    <div key={idx} className="self-center p-2 rounded bg-slate-100 border border-slate-200/50 text-[10px] text-slate-500 text-center max-w-[90%] font-semibold">
                      {msg.text}
                    </div>
                  );
                }

                return (
                  <div 
                    key={idx} 
                    className={`flex flex-col max-w-[80%] rounded-lg px-3.5 py-2 text-xs leading-relaxed shadow-sm ${
                      isUser 
                        ? 'bg-emerald-600 text-white self-end rounded-tr-none' 
                        : 'bg-white text-slate-800 border border-slate-200 self-start rounded-tl-none'
                    }`}
                  >
                    <p className="whitespace-pre-line">{msg.text}</p>
                  </div>
                );
              })}
              {isProcessingInput && (
                <div className="self-start flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-[10px] text-slate-500 font-medium rounded-tl-none shadow-sm">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" /> Traverser processing intent...
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat Footer */}
            {activeSession.fsm_state && ['CONFIRMED', 'CANCELLED', 'ERROR'].includes(activeSession.fsm_state) ? (
              <div className="pt-3 border-t border-slate-100 flex flex-col gap-3">
                <div className="flex items-start gap-2.5 p-3 rounded-lg border border-slate-200 bg-slate-50 text-slate-600">
                  <ShieldAlert className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                  <div className="flex-1 text-[11px] leading-normal font-medium">
                    <span className="text-slate-800 font-semibold">Session Locked (Terminal State Reached)</span>
                    <p className="text-[10px] text-slate-550 mt-1">
                      This traversal has completed in the <span className="font-mono text-slate-700 font-bold">{activeSession.fsm_state}</span> state.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleStartSession}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold py-2.5 rounded-lg transition-all shadow-md flex items-center justify-center gap-1.5 glow-active font-outfit cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Start New Traversal Session
                </button>
              </div>
            ) : (
              <form onSubmit={handleSend} className="pt-3 border-t border-slate-100 flex gap-2">
                <input 
                  type="text" 
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                  placeholder="Type reply..." 
                  disabled={isProcessingInput}
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                />
                <button 
                  type="submit" 
                  disabled={isProcessingInput || !inputVal.trim()}
                  className="bg-emerald-600 hover:bg-emerald-500 px-3 py-1.5 rounded-lg text-xs font-semibold text-white transition-all cursor-pointer flex items-center justify-center shadow-sm disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>
            )}
          </div>
        )}
      </div>

      {/* Right panel: Active Business Metrics & Snapshot Rollbacks */}
      <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-slate-50/20 gap-6">
        {/* Top: Simplified Business context (mapped from carry unit) */}
        <div>
          <h2 className="font-outfit font-bold text-base text-slate-900">Automation Operations Monitor</h2>
          <p className="text-[11px] text-slate-500 mt-1">Live customer context mapped dynamically by FlowCore.</p>
        </div>

        {activeSession ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Cart Panel */}
            <div className="bg-white border border-slate-200 p-5 rounded-xl flex flex-col gap-3 shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <ShoppingCart className="w-4 h-4 text-emerald-600" /> Order Details
                </span>
                <span className="text-[10px] bg-slate-50 border border-slate-200 text-slate-600 px-1.5 py-0.5 rounded font-mono uppercase">
                  {activeSession.fsm_state}
                </span>
              </div>
              
              {orderItems.length > 0 ? (
                <div className="flex flex-col gap-2">
                  {orderItems.map((item: any, idx: number) => (
                    <div key={idx} className="flex justify-between items-center text-xs p-2 rounded bg-slate-50/50 border border-slate-100">
                      <span className="text-slate-700 font-medium">Item {item.item_id || 'Item'}</span>
                      <span className="text-slate-500 font-mono">x {item.quantity || 1}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 text-[10px] text-slate-400 font-medium">
                  No items in cart context.
                </div>
              )}
            </div>

            {/* Payment Panel */}
            <div className="bg-white border border-slate-200 p-5 rounded-xl flex flex-col gap-3 shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <CreditCard className="w-4 h-4 text-emerald-600" /> Payment Config
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase border ${
                  activeSession.fsm_state === 'CONFIRMED' 
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                    : 'bg-slate-50 text-slate-600 border-slate-200'
                }`}>
                  {activeSession.fsm_state === 'CONFIRMED' ? 'PAID' : 'PENDING'}
                </span>
              </div>
              
              <div className="flex flex-col gap-1.5 text-xs text-slate-500">
                <div className="flex justify-between">
                  <span>Billing status:</span>
                  <span className="font-semibold text-slate-800 font-mono">{activeSession.fsm_state === 'CONFIRMED' ? 'Completed' : 'Awaiting Payment'}</span>
                </div>
                {customer.address && (
                  <div className="flex flex-col gap-1 border-t border-slate-100 pt-2 mt-1">
                    <span>Shipping Address:</span>
                    <span className="text-slate-800 font-medium leading-relaxed mt-0.5">{customer.address}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Delivery/Logistics Panel */}
            <div className="bg-white border border-slate-200 p-5 rounded-xl flex flex-col gap-3 shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <Truck className="w-4 h-4 text-emerald-600" /> Logistics Status
                </span>
                <span className="text-[10px] bg-slate-50 border border-slate-200 text-slate-600 px-1.5 py-0.5 rounded font-mono uppercase">
                  {logistics.status || 'UNASSIGNED'}
                </span>
              </div>
              
              <div className="flex flex-col gap-1 text-xs text-slate-500">
                <div className="flex justify-between">
                  <span>Courier Provider:</span>
                  <span className="font-semibold text-slate-800">Express Delivery</span>
                </div>
                {logistics.delivery_id && (
                  <div className="flex justify-between border-t border-slate-100 pt-2 mt-1">
                    <span>Courier ID:</span>
                    <span className="font-semibold text-slate-800 font-mono text-[10px]">{logistics.delivery_id}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="border border-dashed border-slate-250 rounded-xl p-8 text-center text-xs text-slate-400 font-medium bg-white shadow-sm">
            Start a test session to view live customer context variables.
          </div>
        )}

        {/* Bottom: Snapshot Time-travel timeline */}
        {activeSession && (
          <div className="bg-white border border-slate-200 p-6 rounded-xl flex flex-col gap-4 shadow-sm">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <h3 className="text-xs font-bold text-slate-850 uppercase tracking-wider flex items-center gap-1.5">
                <History className="w-4 h-4 text-emerald-600" />
                Time-Travel Snapshots (Rollbacks)
              </h3>
              <button 
                onClick={fetchSnapshots}
                className="p-1 rounded bg-white hover:bg-slate-50 border border-slate-200 text-slate-500 transition-colors cursor-pointer shadow-sm"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>

            {loadingSnapshots ? (
              <div className="py-6 flex justify-center">
                <Loader2 className="w-6 h-6 text-slate-450 animate-spin" />
              </div>
            ) : snapshots.length > 0 ? (
              <div className="relative border-l border-slate-200 pl-4 ml-2 flex flex-col gap-4">
                {snapshots.map((snap) => (
                  <div key={snap.id} className="relative flex justify-between items-center p-3 rounded-lg border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                    {/* Node Dot indicator */}
                    <span className="absolute -left-[21px] top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-white"></span>
                    
                    <div className="flex flex-col gap-0.5">
                      <span className="text-xs font-semibold text-slate-800">Traversed to Node: {snap.node_id}</span>
                      <span className="text-[10px] text-slate-500 font-mono">FSM state: {snap.fsm_state} | {new Date(snap.timestamp).toLocaleTimeString()}</span>
                    </div>

                    <button 
                      onClick={() => handleRollback(snap.id)}
                      className="px-2.5 py-1 bg-white hover:bg-rose-50 hover:text-rose-600 border border-slate-200 hover:border-rose-200 rounded text-[10px] font-bold text-slate-500 transition-all flex items-center gap-1 shadow-sm cursor-pointer"
                    >
                      <RotateCcw className="w-3 h-3" /> Rollback
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-slate-400 font-medium">
                No snapshots captured. Run a traversal step to write execution checkpoints.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
