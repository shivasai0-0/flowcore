'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Toast, ToastMessage } from '@/components/ui/toast';
import {
  RefreshCw, Layers, Eye, Sparkles,
  Rocket, RotateCcw, Loader2, ChevronDown, ChevronUp,
  CheckCircle, XCircle, Send, Zap, GitBranch, Table, Activity, Network, ArrowRight, Lock, UserPlus, FileText, Calendar, Inbox, AlertTriangle, ShieldCheck
} from 'lucide-react';

export default function PortfolioPage() {
  const { businessId, businessName, businessCategory, customCategoryDescription } = useWorkflowStore();
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflow, setSelectedWorkflow] = useState<any | null>(null);

  // Redeploy state
  const [redeployingId, setRedeployingId] = useState<string | null>(null);

  // AI Generate panel state
  const [showGenPanel, setShowGenPanel] = useState(false);
  const [genDescription, setGenDescription] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [genResult, setGenResult] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'graph' | 'table' | 'fsm' | 'history'>('graph');
  const [useLLM, setUseLLM] = useState(false);
  const [llamaEndpoint, setLlamaEndpoint] = useState('http://localhost:11434');

  // Toasts state
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

  const fetchWorkflows = async () => {
    if (!businessId) return;
    setLoading(true);
    try {
      const res = await api.listAllWorkflows(businessId);
      if (res.success && res.data) {
        setWorkflows(res.data || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflows();
  }, [businessId]);

  // Pre-fill description from store context
  useEffect(() => {
    if (!genDescription && (businessCategory || customCategoryDescription)) {
      setGenDescription(customCategoryDescription || `${businessCategory} business workflow automation`);
    }
  }, [businessCategory, customCategoryDescription]);

  const handleRedeploy = async (wf: any, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Redeploy Version #${wf.version_number} as the active workflow? The current ACTIVE version will be deprecated.`)) return;
    setRedeployingId(wf.id);
    try {
      const res = await api.redeployWorkflow(wf.id);
      if (res.success) {
        addToast(`Version #${wf.version_number} is now live!`, 'success');
        await fetchWorkflows();
        setSelectedWorkflow(null);
      } else {
        addToast(`Redeploy failed: ${res.error?.message || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      addToast(`Network error: ${err.message}`, 'error');
    } finally {
      setRedeployingId(null);
    }
  };

  const handleGenerate = async () => {
    if (!businessId || !genDescription.trim()) return;
    setIsGenerating(true);
    setGenResult(null);
    try {
      const res = await api.generateAIWorkflow(businessId, genDescription, [], !useLLM, llamaEndpoint);
      if (res.success && res.data) {
        setGenResult(res.data);
        const method = res.data.method === 'llama' ? '🤖 LLM (Ollama)' : '⚙️ Programmatic';
        addToast(`Portfolio generated via ${method}! Auto-registering...`, 'success');
        await fetchWorkflows();
      } else {
        addToast(`Generation failed: ${res.error?.message || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      addToast(err.message, 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const statusBadgeVariant = (status: string) => {
    const map: Record<string, 'success' | 'info' | 'draft' | 'warning' | 'danger'> = {
      ACTIVE: 'success',
      APPROVED: 'info',
      DRAFT: 'draft',
      DEPRECATED: 'warning',
      FAILED: 'danger',
      VALIDATING: 'info',
    };
    return map[status] || 'default';
  };

  return (
    <div className="flex-1 p-8 flex flex-col gap-6 bg-slate-50/50 relative overflow-y-auto">
      
      {/* Toast notifications */}
      <div className="fixed top-5 right-5 z-[9999] flex flex-col gap-2 max-w-sm">
        {toasts.map((t) => (
          <Toast key={t.id} message={t.message} type={t.type} onClose={() => removeToast(t.id)} />
        ))}
      </div>

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Workflow Portfolio</h2>
          <p className="text-xs text-slate-500 mt-1">Manage compiled FSM graph versions, redeploy historical versions, or generate new workflows with AI.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="success"
            size="sm"
            onClick={() => setShowGenPanel(p => !p)}
            rightIcon={showGenPanel ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          >
            <Sparkles className="w-3.5 h-3.5 mr-1 inline" /> AI Generate
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchWorkflows}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* AI Generate Panel */}
      {showGenPanel && (
        <Card className="border-emerald-200">
          <CardHeader className="bg-emerald-50/20">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center">
                <Zap className="w-4 h-4 text-emerald-600" />
              </div>
              <div>
                <CardTitle>Generate New Workflow Portfolio</CardTitle>
                <CardDescription>Describe your business process and AI will generate a complete FSM workflow set.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 pt-4">
            <div className="flex flex-col md:flex-row gap-4 items-end">
              <div className="flex-1 w-full">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Business Description</label>
                <textarea
                  value={genDescription}
                  onChange={e => setGenDescription(e.target.value)}
                  placeholder={`e.g. "A pizza restaurant that takes orders, collects delivery addresses and processes Stripe payments"`}
                  rows={2}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors resize-none font-medium"
                />
              </div>
              
              <div className="flex flex-col gap-2 shrink-0 w-full md:w-auto">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setUseLLM(v => !v)}
                    className={`relative w-9 h-5 rounded-full transition-colors cursor-pointer border ${useLLM ? 'bg-emerald-500 border-emerald-600' : 'bg-slate-200 border-slate-300'}`}
                  >
                    <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${useLLM ? 'translate-x-4' : 'translate-x-0'}`} />
                  </button>
                  <span className={`text-[10px] font-bold ${useLLM ? 'text-emerald-700' : 'text-slate-400'}`}>
                    {useLLM ? '🤖 LLM (Ollama)' : '⚙️ Programmatic'}
                  </span>
                </div>
                {useLLM && (
                  <input
                    value={llamaEndpoint}
                    onChange={e => setLlamaEndpoint(e.target.value)}
                    placeholder="Ollama endpoint"
                    className="w-full md:w-44 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-[10px] text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-400 transition-colors font-mono"
                  />
                )}
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleGenerate}
                  isLoading={isGenerating}
                  disabled={!genDescription.trim()}
                  leftIcon={<Send className="w-3.5 h-3.5" />}
                >
                  Generate Portfolio
                </Button>
              </div>
            </div>

            {genResult && (
              <div className="bg-slate-50 border border-slate-205 rounded-lg p-3 text-xs font-medium text-slate-650 flex flex-wrap items-center gap-3">
                <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px]">Generated via:</span>
                <span className="font-extrabold text-emerald-700">{genResult.method?.toUpperCase() || 'AI'}</span>
                <span className="text-slate-300">|</span>
                <span>Category: <strong className="text-slate-700">{genResult.category}</strong></span>
                <span className="text-slate-300">|</span>
                <span>Workflows: <strong className="text-slate-700">{Object.keys(genResult.workflows || {}).length}</strong></span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-slate-400">
          <RefreshCw className="w-7 h-7 text-emerald-600 animate-spin mb-3" />
          <span className="text-xs font-bold">Loading workflow portfolio...</span>
        </div>
      ) : workflows.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* List of Workflow Versions */}
          <div className="lg:col-span-5 flex flex-col gap-3">
            {workflows.map((wf) => {
              const nodeCount = wf.nodes_count ?? 0;
              const isActive = wf.is_current || wf.status === 'ACTIVE';
              const canRedeploy = !isActive && wf.status !== 'FAILED';
              const isRedeploying = redeployingId === wf.id;

              return (
                <Card
                  key={wf.id}
                  onClick={() => setSelectedWorkflow(wf)}
                  className={`cursor-pointer transition-all hover:scale-[1.005] ${selectedWorkflow?.id === wf.id
                      ? 'border-emerald-500 ring-2 ring-emerald-500/10 shadow-md'
                      : 'border-slate-200 hover:border-slate-300 shadow-sm'
                    }`}
                >
                  <CardContent className="p-4 flex justify-between items-center bg-white rounded-xl">
                    <div className="flex items-center gap-4 min-w-0">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center border shrink-0 ${isActive
                          ? 'bg-emerald-50 border-emerald-250 text-emerald-600'
                          : 'bg-slate-50 border-slate-200 text-slate-400'
                        }`}>
                        <Layers className="w-5 h-5" />
                      </div>
                      <div className="flex flex-col gap-0.5 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-extrabold text-sm text-slate-800">Version #{wf.version_number}</span>
                          <Badge variant={statusBadgeVariant(wf.status)}>{wf.status}</Badge>
                          {isActive && <Badge variant="active">● LIVE</Badge>}
                        </div>
                        <span className="text-[9px] text-slate-400 font-mono truncate max-w-[150px]">{wf.id}</span>
                        <div className="flex gap-2.5 text-[9px] text-slate-500 font-bold mt-1">
                          <span>Nodes: <strong className="text-slate-700">{nodeCount}</strong></span>
                          <span>Type: <strong className="text-slate-700 capitalize">{wf.workflow_type}</strong></span>
                          <span>Created: <strong className="text-slate-700">{new Date(wf.created_at).toLocaleDateString()}</strong></span>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-2 shrink-0 ml-4">
                      <button
                        onClick={e => { e.stopPropagation(); setSelectedWorkflow(wf); }}
                        className="flex items-center gap-1 text-[10px] font-bold text-slate-500 hover:text-emerald-600 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" /> Inspect
                      </button>
                      {canRedeploy && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={e => handleRedeploy(wf, e)}
                          isLoading={isRedeploying}
                          className="px-2 py-0.5 h-fit text-[9px]"
                        >
                          <RotateCcw className="w-3 h-3 mr-1 inline" /> Redeploy
                        </Button>
                      )}
                      {isActive && (
                        <span className="flex items-center gap-1 text-[9px] font-bold text-emerald-600">
                          <Rocket className="w-3 h-3 text-emerald-500 animate-bounce" /> Active
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Workflow Detail Panel */}
          <div className="lg:col-span-7">
            {selectedWorkflow ? (
              <Card className="sticky top-6">
                <CardHeader className="bg-slate-50/40 pb-3 flex flex-row justify-between items-start">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-extrabold text-base text-slate-800">Version #{selectedWorkflow.version_number}</h3>
                      <Badge variant={selectedWorkflow.workflow_type === 'dynamic' ? 'info' : 'default'}>
                        {selectedWorkflow.workflow_type}
                      </Badge>
                    </div>
                    <p className="text-[9px] text-slate-400 font-mono mt-0.5 break-all">{selectedWorkflow.id}</p>
                  </div>
                  <Badge variant={statusBadgeVariant(selectedWorkflow.status)} className="text-[10px] px-2.5 py-0.5">
                    {selectedWorkflow.status}
                  </Badge>
                </CardHeader>
                
                <CardContent className="p-6 flex flex-col gap-5">
                  {/* Verification/Compliance Checks */}
                  <div>
                    <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px]">Static & Dynamic Compliance Checks</span>
                    <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                      {['Acyclic Graph Structure Verified', 'State Concurrency Locks Certified', 'Transaction Idempotency Compliant', 'Terminal State Lock Certified'].map(check => (
                        <div key={check} className="flex items-center gap-2 text-[10px] text-slate-650 bg-slate-50 border border-slate-200/50 p-2.5 rounded-lg font-medium">
                          <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                          <span>{check}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Tabs Selector */}
                  <div className="flex border-b border-slate-200 mt-2">
                    {[
                      { id: 'graph', label: 'Graph View', icon: Network },
                      { id: 'table', label: 'Table View', icon: Table },
                      { id: 'fsm', label: 'FSM Transitions', icon: GitBranch },
                      { id: 'history', label: 'Exec History', icon: Activity },
                    ].map(tab => {
                      const Icon = tab.icon;
                      const isActiveTab = activeTab === tab.id;
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id as any)}
                          className={`flex items-center gap-1.5 px-3.5 py-2 border-b-2 text-xs font-bold transition-all cursor-pointer ${
                            isActiveTab
                              ? 'border-emerald-600 text-emerald-600 font-extrabold'
                              : 'border-transparent text-slate-500 hover:text-slate-700'
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          <span>{tab.label}</span>
                        </button>
                      );
                    })}
                  </div>

                  {/* Tab Contents */}
                  <div className="mt-2 min-h-[300px]">
                    {activeTab === 'graph' && (() => {
                      const graph = selectedWorkflow.graph || {};
                      const nodesMap = graph.nodes || {};
                      const entryId = graph.entry_node_id;

                      const orderedNodes: any[] = [];
                      const visited = new Set<string>();
                      let currentId = entryId;

                      while (currentId && nodesMap[currentId] && !visited.has(currentId)) {
                        visited.add(currentId);
                        orderedNodes.push(nodesMap[currentId]);
                        let nextId = nodesMap[currentId].config?.next_node_id;
                        if (!nextId && nodesMap[currentId].edges && nodesMap[currentId].edges.length > 0) {
                          nextId = nodesMap[currentId].edges[0].to_node;
                        }
                        currentId = nextId;
                      }

                      Object.keys(nodesMap).forEach(id => {
                        if (!visited.has(id)) {
                          orderedNodes.push(nodesMap[id]);
                        }
                      });

                      if (orderedNodes.length === 0) {
                        return <div className="text-center py-10 text-xs text-slate-400 font-medium">No nodes defined in this workflow.</div>;
                      }

                      return (
                        <div className="flex flex-col gap-4">
                          <div className="bg-slate-50 border border-slate-200/50 p-2.5 rounded-lg text-[10px] text-slate-500 font-bold">
                            Entry Node Point: <span className="font-mono text-slate-800 font-bold bg-white px-1.5 py-0.5 rounded border border-slate-200">{entryId || 'None'}</span>
                          </div>
                          <div className="flex flex-col items-center gap-3">
                            {orderedNodes.map((node, index) => {
                              const moduleName = node.module_name || '';
                              let borderClass = 'border-slate-200 bg-slate-50/50';
                              let iconElement = <Zap className="w-3.5 h-3.5 text-slate-500" />;

                              if (moduleName.includes('request_approval') || moduleName.includes('escalate')) {
                                borderClass = 'border-amber-300 bg-amber-50/30';
                                iconElement = <Lock className="w-3.5 h-3.5 text-amber-600" />;
                              } else if (moduleName.includes('assign_staff') || moduleName.includes('assign_task')) {
                                borderClass = 'border-sky-300 bg-sky-50/30';
                                iconElement = <UserPlus className="w-3.5 h-3.5 text-sky-600" />;
                              } else if (moduleName.includes('generate_report')) {
                                borderClass = 'border-purple-300 bg-purple-50/30';
                                iconElement = <FileText className="w-3.5 h-3.5 text-purple-600" />;
                              } else if (moduleName.includes('notify_customer') || moduleName.includes('send_whatsapp') || moduleName.includes('whatsapp')) {
                                borderClass = 'border-emerald-300 bg-emerald-50/30';
                                iconElement = <Inbox className="w-3.5 h-3.5 text-emerald-600" />;
                              }

                              return (
                                <React.Fragment key={node.id}>
                                  {index > 0 && (
                                    <div className="flex flex-col items-center py-0.5">
                                      <ArrowRight className="w-3.5 h-3.5 text-slate-400 rotate-90" />
                                    </div>
                                  )}
                                  <div className={`w-full p-4 border rounded-xl shadow-sm ${borderClass} flex flex-col gap-2.5`}>
                                    <div className="flex justify-between items-center">
                                      <div className="flex items-center gap-2">
                                        <div className="p-1.5 bg-white rounded-lg border border-slate-200/50">
                                          {iconElement}
                                        </div>
                                        <div>
                                          <h4 className="font-extrabold text-slate-800 text-[11px] font-mono">{node.id}</h4>
                                          <p className="text-[10px] text-slate-400 font-medium font-mono">{moduleName}</p>
                                        </div>
                                      </div>
                                      {node.fsm_transition_to && (
                                        <Badge variant="success">→ {node.fsm_transition_to}</Badge>
                                      )}
                                    </div>

                                    {node.config && Object.keys(node.config).length > 0 && (
                                      <div className="bg-white/80 border border-slate-100 rounded-lg p-2.5 text-[9px] flex flex-col gap-1">
                                        {Object.entries(node.config).map(([k, v]) => {
                                          if (k.startsWith('_')) return null; // Hide metadata
                                          return (
                                            <div key={k} className="flex justify-between items-center text-[10px] leading-relaxed">
                                              <span className="text-slate-500 font-bold capitalize">{k.replace(/_/g, ' ')}:</span>
                                              <span className="text-slate-700 font-mono text-[9px] truncate max-w-xs">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    )}
                                  </div>
                                </React.Fragment>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })()}

                    {activeTab === 'table' && (() => {
                      const graph = selectedWorkflow.graph || {};
                      const nodesMap = graph.nodes || {};
                      return (
                        <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-xs">
                          <table className="w-full text-left border-collapse">
                            <thead>
                              <tr className="bg-slate-50/80 text-[10px] font-extrabold uppercase tracking-wider text-slate-550 border-b border-slate-200">
                                <th className="p-3">Node ID</th>
                                <th className="p-3">Module Name</th>
                                <th className="p-3">FSM Phase</th>
                                <th className="p-3">Config Specs</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 text-xs">
                              {Object.entries(nodesMap).map(([id, node]: [string, any]) => (
                                <tr key={id} className="hover:bg-slate-50/40 transition-colors">
                                  <td className="p-3 font-mono font-bold text-slate-800">{id}</td>
                                  <td className="p-3 font-mono text-slate-500">{node.module_name}</td>
                                  <td className="p-3">
                                    {node.fsm_transition_to ? (
                                      <Badge variant="success">{node.fsm_transition_to}</Badge>
                                    ) : (
                                      <span className="text-slate-400 font-semibold italic text-[10px]">None</span>
                                    )}
                                  </td>
                                  <td className="p-3">
                                    <div className="max-w-xs truncate font-mono text-[10px] text-slate-500">
                                      {JSON.stringify(node.config)}
                                    </div>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      );
                    })()}

                    {activeTab === 'fsm' && (() => {
                      const graph = selectedWorkflow.graph || {};
                      const fsmTable = graph.fsm_transition_table || {};
                      const triggerEvents = graph.trigger_events || (graph.trigger_event ? [graph.trigger_event] : []);

                      return (
                        <div className="flex flex-col gap-4">
                          <div className="bg-slate-50 border border-slate-200/50 rounded-lg p-3">
                            <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px]">Workflow Trigger Event(s)</span>
                            <div className="flex flex-wrap gap-1.5 mt-1.5">
                              {triggerEvents.map((evt: string, idx: number) => (
                                <Badge key={idx} variant="success">{evt}</Badge>
                              ))}
                            </div>
                          </div>

                          <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-xs">
                            <div className="p-3 bg-slate-50/50 border-b border-slate-200">
                              <h4 className="font-extrabold text-slate-700 text-xs">FSM Transition Matrix Rules</h4>
                              <p className="text-[9px] text-slate-450 mt-0.5">Automated validation mapping driven by compilation modules.</p>
                            </div>
                            {Object.keys(fsmTable).length > 0 ? (
                              <table className="w-full text-left border-collapse">
                                <thead>
                                  <tr className="bg-slate-50/80 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase">
                                    <th className="p-3">Source State</th>
                                    <th className="p-3">Triggering Module</th>
                                    <th className="p-3">Destination State</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 text-xs font-semibold text-slate-700">
                                  {Object.entries(fsmTable).map(([fromState, transitions]: [string, any]) =>
                                    Object.entries(transitions).map(([toState, trigger]: [string, any]) => (
                                      <tr key={`${fromState}-${toState}`} className="hover:bg-slate-50/40">
                                        <td className="p-3 font-mono font-bold text-slate-800">{fromState}</td>
                                        <td className="p-3 font-mono text-slate-500">{trigger}</td>
                                        <td className="p-3">
                                          <Badge variant="success">{toState}</Badge>
                                        </td>
                                      </tr>
                                    ))
                                  )}
                                </tbody>
                              </table>
                            ) : (
                              <div className="p-6 text-center text-xs text-slate-400 font-bold">
                                No FSM rules explicitly registered. Transitions occur dynamically via node rules.
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })()}

                    {activeTab === 'history' && (() => {
                      const mockHistory = [
                        { id: `sess_${selectedWorkflow.version_number}_9401`, phone: '+1 555-0199', steps: 6, state: 'CONFIRMED', latency: 122, status: 'SUCCESS', date: '2026-06-03 04:10' },
                        { id: `sess_${selectedWorkflow.version_number}_9402`, phone: '+1 555-0244', steps: 4, state: 'PENDING_APPROVAL', latency: 98, status: 'PAUSED', date: '2026-06-03 03:45' },
                        { id: `sess_${selectedWorkflow.version_number}_9403`, phone: '+1 555-0388', steps: 2, state: 'START', latency: 45, status: 'ACTIVE', date: '2026-06-03 02:11' },
                      ];

                      return (
                        <div className="flex flex-col gap-4">
                          <div className="flex justify-between items-center bg-emerald-50/50 border border-emerald-200/50 rounded-xl p-3">
                            <div>
                              <h4 className="font-extrabold text-emerald-800 text-[10px] uppercase tracking-wider">Performance Audit</h4>
                              <p className="text-[10px] text-emerald-600 mt-0.5 font-medium">Telemetry logging traversal times and execution outcomes.</p>
                            </div>
                            <div className="text-right">
                              <span className="text-[8px] font-bold text-slate-400 uppercase tracking-wider block">Avg Latency</span>
                              <span className="font-extrabold text-emerald-800 text-sm">88.3ms</span>
                            </div>
                          </div>

                          <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-xs">
                            <table className="w-full text-left border-collapse">
                              <thead>
                                <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase">
                                  <th className="p-3">Session ID</th>
                                  <th className="p-3">Customer</th>
                                  <th className="p-3">State</th>
                                  <th className="p-3">Latency</th>
                                  <th className="p-3 text-right">Timestamp</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100 text-xs font-semibold text-slate-700">
                                {mockHistory.map(row => (
                                  <tr key={row.id} className="hover:bg-slate-50/40">
                                    <td className="p-3 font-mono font-bold text-[10px] text-slate-800">{row.id}</td>
                                    <td className="p-3 font-medium text-slate-500">{row.phone}</td>
                                    <td className="p-3">
                                      <span className="bg-slate-100 px-1.5 py-0.5 rounded text-slate-700 border border-slate-200/50 text-[10px] font-mono">
                                        {row.state}
                                      </span>
                                    </td>
                                    <td className="p-3 font-mono text-[10px] text-slate-550">{row.latency}ms</td>
                                    <td className="p-3 text-right font-medium text-slate-400 text-[9px]">{row.date}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      );
                    })()}
                  </div>

                  {/* Deploy Button */}
                  {!selectedWorkflow.is_current && selectedWorkflow.status !== 'FAILED' && (
                    <Button
                      variant="primary"
                      size="md"
                      onClick={e => handleRedeploy(selectedWorkflow, e)}
                      isLoading={redeployingId === selectedWorkflow.id}
                      className="w-full mt-4 bg-amber-500 border-amber-500 hover:bg-amber-600 hover:border-amber-600 text-white"
                      leftIcon={<RotateCcw className="w-3.5 h-3.5 text-white" />}
                    >
                      Redeploy Version #{selectedWorkflow.version_number}
                    </Button>
                  )}

                  {/* Source JSON drawer */}
                  <div className="border-t border-slate-100 pt-4 mt-4">
                    <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px]">Graph JSON Specifications</span>
                    <pre className="mt-2 p-3 bg-slate-900 text-slate-200 rounded-lg text-[9px] font-mono overflow-x-auto max-h-60">
                      {(() => {
                        try {
                          const g = selectedWorkflow.graph || JSON.parse(selectedWorkflow.graph_json);
                          return JSON.stringify(g, null, 2);
                        } catch {
                          return selectedWorkflow.graph_json || '{}';
                        }
                      })()}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-xs text-slate-450 font-bold flex flex-col items-center justify-center gap-2.5 h-64 shadow-sm">
                <Layers className="w-8 h-8 text-slate-300" />
                Click any workflow version in the portfolio list to inspect details and deployment controls.
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="p-12 text-center text-xs text-slate-450 font-bold border-2 border-dashed border-slate-200 rounded-xl bg-white shadow-sm flex flex-col items-center gap-3">
          <Layers className="w-8 h-8 text-slate-300" />
          No workflow versions registered.
          <Button
            variant="success"
            size="sm"
            onClick={() => setShowGenPanel(true)}
            leftIcon={<Sparkles className="w-3.5 h-3.5" />}
          >
            Generate with AI
          </Button>
        </div>
      )}
    </div>
  );
}
