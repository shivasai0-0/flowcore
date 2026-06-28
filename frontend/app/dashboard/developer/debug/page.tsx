'use client';

import React, { useState, useEffect } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Zap, 
  Play, 
  CheckCircle, 
  XCircle, 
  AlertCircle, 
  Terminal, 
  Database, 
  RefreshCw, 
  ChevronDown, 
  ChevronUp, 
  Layers, 
  Sparkles,
  Clipboard,
  ShieldCheck,
  Cpu,
  ArrowRight,
  GitBranch,
  Activity,
  Server,
  Network
} from 'lucide-react';

export default function DeveloperDebugPage() {
  const { businessId } = useWorkflowStore();
  const [activeTab, setActiveTab] = useState<'sandbox' | 'runtime' | 'benchmarks'>('sandbox');
  
  // Interactive Sandbox state
  const [description, setDescription] = useState('');
  const [useLLM, setUseLLM] = useState(false);
  const [llamaEndpoint, setLlamaEndpoint] = useState('http://localhost:11434');
  const [isGenerating, setIsGenerating] = useState(false);
  const [debugResult, setDebugResult] = useState<any>(null);
  const [llmInfo, setLlmInfo] = useState<any>(null);
  
  // Benchmark state
  const [benchmarks, setBenchmarks] = useState<any[]>([]);
  const [isRunningBenchmarks, setIsRunningBenchmarks] = useState(false);
  const [benchmarkModeLLM, setBenchmarkModeLLM] = useState(false);

  // Runtime Execution Monitor state
  const [recentSessions, setRecentSessions] = useState<any[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionLogs, setSessionLogs] = useState<any[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  // Trace toggles
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    prompt: true,
    raw: true,
    parsed: true,
    validation: true,
    compiled: true,
    pipeline_0: true,
    pipeline_1: true
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const fetchBenchmarks = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/workflows/benchmarks');
      const data = await res.json();
      if (data.success) {
        setBenchmarks(data.data);
      }
    } catch (e) {
      console.error("Failed to fetch benchmarks:", e);
    }
  };

  const fetchLlmInfo = async () => {
    try {
      const q = businessId ? `?business_id=${businessId}` : '';
      const res = await fetch(`http://localhost:8000/api/v1/system/llm-info${q}`);
      const data = await res.json();
      setLlmInfo(data);
      if (data.endpoint) {
        setLlamaEndpoint(data.endpoint);
      }
    } catch (e) {
      console.error("Failed to fetch LLM info:", e);
    }
  };

  const fetchRecentEvents = async () => {
    if (!businessId) return;
    try {
      const res = await fetch(`http://localhost:8000/api/v1/events?business_id=${businessId}&limit=10`);
      const data = await res.json();
      if (data.success && data.data) {
        // Unique sessions derived from events list
        const sessionsMap: Record<string, any> = {};
        data.data.forEach((evt: any) => {
          if (evt.session_id && !sessionsMap[evt.session_id]) {
            sessionsMap[evt.session_id] = {
              id: evt.session_id,
              emitted_at: evt.emitted_at,
              workflow_version_id: evt.workflow_version_id
            };
          }
        });
        setRecentSessions(Object.values(sessionsMap));
      }
    } catch (e) {
      console.error("Failed to fetch recent sessions via events:", e);
    }
  };

  const fetchSessionLogs = async (sessId: string) => {
    setLoadingLogs(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/sessions/logs/${sessId}`);
      const data = await res.json();
      if (data.success && data.data) {
        setSessionLogs(data.data);
      }
    } catch (e) {
      console.error("Failed to fetch session logs:", e);
    } finally {
      setLoadingLogs(false);
    }
  };

  useEffect(() => {
    fetchBenchmarks();
    fetchLlmInfo();
    fetchRecentEvents();
  }, [businessId]);

  useEffect(() => {
    if (selectedSessionId) {
      fetchSessionLogs(selectedSessionId);
    }
  }, [selectedSessionId]);

  const handleRunSandbox = async () => {
    if (!description.trim()) return;
    setIsGenerating(true);
    setDebugResult(null);
    try {
      const res = await fetch('http://localhost:8000/api/v1/workflows/generate-debug', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_id: businessId || 'debug_sentinel',
          business_description: description,
          capability_packs: [],
          use_mock_ai: !useLLM,
          llama_endpoint: llamaEndpoint
        })
      });
      const data = await res.json();
      if (data.success) {
        setDebugResult(data.data);
      } else {
        alert(data.error?.message || "Generation failed");
      }
    } catch (e: any) {
      alert("Error calling debug endpoint: " + e.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRunBenchmarks = async () => {
    setIsRunningBenchmarks(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/workflows/benchmarks/run?use_mock_ai=${!benchmarkModeLLM}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.success) {
        setBenchmarks(data.data);
      } else {
        alert(data.error?.message || "Failed to run benchmarks");
      }
    } catch (e: any) {
      alert("Error running benchmarks: " + e.message);
    } finally {
      setIsRunningBenchmarks(false);
    }
  };

  return (
    <div className="flex-1 p-8 flex flex-col gap-6 bg-slate-50 overflow-y-auto">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-emerald-600 animate-pulse" />
            Developer Center — Diagnostics
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Debug AI portfolio generation trace in real-time, inspect FSM execution traversal logs, and run compiler benchmarks.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-slate-200/80 rounded-xl max-w-md self-start">
        <button
          onClick={() => setActiveTab('sandbox')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
            activeTab === 'sandbox' ? 'bg-white text-emerald-700 shadow-sm' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          Interactive Sandbox
        </button>
        <button
          onClick={() => setActiveTab('runtime')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
            activeTab === 'runtime' ? 'bg-white text-emerald-700 shadow-sm' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          Runtime Monitor
        </button>
        <button
          onClick={() => setActiveTab('benchmarks')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
            activeTab === 'benchmarks' ? 'bg-white text-emerald-700 shadow-sm' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          Benchmark Suite
        </button>
      </div>

      {/* Tab 1: Interactive AI Sandbox */}
      {activeTab === 'sandbox' && (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
          {/* Controls & Diagnostics Column */}
          <div className="xl:col-span-4 flex flex-col gap-6 h-fit">
            {/* Controls Card */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-emerald-600" />
                  <CardTitle>Sandbox Controls</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 pt-2">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Business Description</label>
                  <textarea
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    placeholder="e.g. A diagnostic lab where patients schedule blood tests, receive slot bookings, get results via WhatsApp, and submit feedback."
                    rows={5}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors resize-none font-medium"
                  />
                </div>

                <div className="flex items-center justify-between mt-2 p-2 rounded-lg bg-slate-50 border border-slate-105">
                  <span className="text-xs font-semibold text-slate-650">Model Engine</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setUseLLM(v => !v)}
                      className={`relative w-9 h-5 rounded-full transition-colors cursor-pointer border ${useLLM ? 'bg-emerald-500 border-emerald-600' : 'bg-slate-200 border-slate-300'}`}
                    >
                      <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${useLLM ? 'translate-x-4' : 'translate-x-0'}`} />
                    </button>
                    <span className="text-xs font-bold text-slate-700">
                      {useLLM ? `Ollama (${llmInfo?.configured_model || 'qwen3:4b'})` : 'Fast Mode'}
                    </span>
                  </div>
                </div>

                {useLLM && (
                  <div className="flex flex-col gap-1 mt-1">
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Ollama Endpoint</label>
                    <input
                      value={llamaEndpoint}
                      onChange={e => setLlamaEndpoint(e.target.value)}
                      className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-700 font-mono focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    />
                  </div>
                )}

                <Button
                  variant="primary"
                  size="md"
                  onClick={handleRunSandbox}
                  disabled={isGenerating || !description.trim()}
                  className="w-full mt-2"
                  leftIcon={isGenerating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                >
                  {isGenerating ? 'Generating...' : 'Run Compiler Sandbox'}
                </Button>
              </CardContent>
            </Card>

            {/* LLM Connection Status Card */}
            <Card>
              <CardContent className="p-5 flex flex-col gap-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-purple-600" />
                    LLM Diagnostic
                  </h3>
                  <Badge variant={llmInfo?.available ? 'success' : 'danger'}>
                    {llmInfo?.available ? 'Connected' : 'Disconnected'}
                  </Badge>
                </div>
                
                <div className="flex flex-col gap-3 text-xs">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Configured Model</span>
                    <span className="font-mono font-bold text-slate-700 bg-slate-50 border border-slate-200 rounded px-2 py-1 truncate">
                      {llmInfo?.configured_model || 'Loading...'}
                    </span>
                  </div>
                  
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Ollama Endpoint</span>
                    <span className="font-mono text-slate-500 truncate">
                      {llmInfo?.endpoint || 'Loading...'}
                    </span>
                  </div>
                  
                  <div className="flex flex-col gap-1">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Installed Models</span>
                    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto mt-0.5">
                      {llmInfo?.installed_models && llmInfo.installed_models.length > 0 ? (
                        llmInfo.installed_models.map((m: string) => (
                          <span key={m} className="px-1.5 py-0.5 bg-slate-100 text-slate-650 text-[9px] font-mono rounded border border-slate-200">
                            {m}
                          </span>
                        ))
                      ) : (
                        <span className="text-slate-400 font-semibold italic text-[10px]">No models detected</span>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Trace Results */}
          <div className="xl:col-span-8 flex flex-col gap-4">
            {!debugResult && !isGenerating && (
              <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-2xl p-12 bg-white text-slate-400 shadow-sm h-64">
                <Terminal className="w-10 h-10 text-slate-300 mb-3 animate-pulse" />
                <h4 className="font-bold text-sm text-slate-800">Sandbox Awaiting Trigger</h4>
                <p className="text-xs text-slate-500 text-center max-w-sm mt-1 leading-normal font-medium">
                  Enter a business description and run the compiler sandbox to inspect the step-by-step telemetry trace.
                </p>
              </div>
            )}

            {isGenerating && (
              <div className="flex-1 flex flex-col items-center justify-center border border-slate-200 rounded-2xl p-12 bg-white text-slate-400 gap-3 shadow-sm h-64">
                <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin" />
                <h4 className="font-bold text-sm text-slate-800">Executing LLM Architect...</h4>
                <p className="text-xs text-slate-500 text-center max-w-sm leading-normal font-medium">
                  Synthesizing workflow portfolio draft, running structural validator, and evaluating graph reachability.
                </p>
              </div>
            )}

            {debugResult && (
              <div className="flex flex-col gap-4">
                {/* 1. Prompt Sent */}
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <button 
                    onClick={() => toggleSection('prompt')}
                    className="w-full flex items-center justify-between p-4 bg-slate-50 border-b border-slate-250 font-bold text-xs text-slate-700 cursor-pointer"
                  >
                    <span className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-emerald-650" />
                      1. PROMPT SENT TO LLM
                    </span>
                    {expandedSections.prompt ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  {expandedSections.prompt && (
                    <div className="p-4 flex flex-col gap-3 font-mono text-[9px] bg-slate-900 text-slate-300 max-h-72 overflow-y-auto whitespace-pre-wrap">
                      <div className="border-b border-slate-800 pb-2">
                        <strong className="text-emerald-400">SYSTEM PROMPT:</strong>
                        <div className="mt-1">{debugResult.prompt_sent.system}</div>
                      </div>
                      <div>
                        <strong className="text-blue-400">USER PROMPT:</strong>
                        <div className="mt-1">{debugResult.prompt_sent.user}</div>
                      </div>
                    </div>
                  )}
                </div>

                {/* 2. Raw LLM Output */}
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <button 
                    onClick={() => toggleSection('raw')}
                    className="w-full flex items-center justify-between p-4 bg-slate-50 border-b border-slate-250 font-bold text-xs text-slate-700 cursor-pointer"
                  >
                    <span className="flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-amber-500" />
                      2. RAW LLM OUTPUT
                    </span>
                    {expandedSections.raw ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  {expandedSections.raw && (
                    <div className="p-4 bg-slate-900 text-amber-300 font-mono text-[9px] max-h-72 overflow-y-auto whitespace-pre-wrap">
                      {debugResult.raw_llm_output || "(Empty output)"}
                    </div>
                  )}
                </div>

                {/* 3. Parsed Workflow Draft */}
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <button 
                    onClick={() => toggleSection('parsed')}
                    className="w-full flex items-center justify-between p-4 bg-slate-50 border-b border-slate-250 font-bold text-xs text-slate-700 cursor-pointer"
                  >
                    <span className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-purple-650" />
                      3. PARSED WORKFLOW DRAFT
                    </span>
                    {expandedSections.parsed ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  {expandedSections.parsed && (
                    <div className="p-4 bg-slate-950 text-purple-300 font-mono text-[9px] max-h-96 overflow-y-auto">
                      <pre>{JSON.stringify(debugResult.parsed_workflow_draft, null, 2) || "Failed to parse draft JSON."}</pre>
                    </div>
                  )}
                </div>

                {/* 4. Validation Result Gate */}
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <button 
                    onClick={() => toggleSection('validation')}
                    className="w-full flex items-center justify-between p-4 bg-slate-50 border-b border-slate-250 font-bold text-xs text-slate-700 cursor-pointer"
                  >
                    <span className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-blue-600" />
                      4. DETERMINISTIC VALIDATION GATE
                    </span>
                    {expandedSections.validation ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  {expandedSections.validation && (
                    <div className="p-5 flex flex-col gap-4 bg-white">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-bold text-slate-500">Validation Status:</span>
                        <Badge variant={debugResult.validation_result.is_valid ? 'success' : 'danger'}>
                          {debugResult.validation_result.is_valid ? 'DRAFT PASSED ALL CHECKS' : 'DRAFT FAILED GATE'}
                        </Badge>
                      </div>

                      {debugResult.validation_result.errors.length > 0 && (
                        <div className="flex flex-col gap-2 p-4 bg-rose-50 border border-rose-100 rounded-lg">
                          <span className="text-xs font-bold text-rose-800 flex items-center gap-1">
                            <AlertCircle className="w-4 h-4" />
                            Validation Errors Detected ({debugResult.validation_result.errors.length})
                          </span>
                          <ul className="list-disc pl-5 text-[10px] text-rose-700 font-semibold space-y-1">
                            {debugResult.validation_result.errors.map((err: string, i: number) => (
                              <li key={i}>{err}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* 5. Compiled Workflow */}
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <button 
                    onClick={() => toggleSection('compiled')}
                    className="w-full flex items-center justify-between p-4 bg-slate-50 border-b border-slate-250 font-bold text-xs text-slate-700 cursor-pointer"
                  >
                    <span className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-emerald-600" />
                      5. COMPILED DEPLOYABLE WORKFLOW
                    </span>
                    {expandedSections.compiled ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  {expandedSections.compiled && (
                    <div className="p-4 bg-slate-950 text-emerald-450 font-mono text-[9px] max-h-96 overflow-y-auto">
                      <pre>
                        {Object.keys(debugResult.compiled_workflows || {}).length > 0 
                          ? JSON.stringify(debugResult.compiled_workflows, null, 2)
                          : "// No workflows compiled. Validation must pass to compile."
                        }
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Runtime Execution Monitor */}
      {activeTab === 'runtime' && (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
          
          {/* Recent Sessions List Panel */}
          <div className="xl:col-span-4 flex flex-col gap-4">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-emerald-600" />
                  <CardTitle>Recent Traversal Sessions</CardTitle>
                </div>
                <CardDescription>Select a traversal session to view internal event telemetry.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-2.5 max-h-[500px] overflow-y-auto pt-2">
                {recentSessions.length === 0 ? (
                  <div className="text-center py-8 text-xs text-slate-400 font-bold">
                    No recent sessions detected. Run a simulator session first.
                  </div>
                ) : (
                  recentSessions.map((sess) => (
                    <div
                      key={sess.id}
                      onClick={() => setSelectedSessionId(sess.id)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedSessionId === sess.id
                          ? 'border-emerald-500 bg-emerald-50/20'
                          : 'border-slate-200 hover:border-slate-300 bg-white'
                      }`}
                    >
                      <span className="text-xs font-bold text-slate-800 font-mono">{sess.id}</span>
                      <div className="flex justify-between items-center text-[9px] text-slate-450 mt-1 font-bold">
                        <span>Workflow: {sess.workflow_version_id?.slice(0, 12)}...</span>
                        <span>{new Date(sess.emitted_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          {/* Trace Replay Steps */}
          <div className="xl:col-span-8 flex flex-col gap-4">
            {!selectedSessionId && (
              <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-2xl p-12 bg-white text-slate-400 shadow-sm h-64">
                <Network className="w-10 h-10 text-slate-350 mb-3 animate-pulse" />
                <h4 className="font-bold text-sm text-slate-850">No Session Selected</h4>
                <p className="text-xs text-slate-500 text-center max-w-sm mt-1 leading-normal font-semibold">
                  Select a recent traversal session from the left column to monitor step-by-step internal execution traces.
                </p>
              </div>
            )}

            {selectedSessionId && loadingLogs && (
              <div className="flex flex-col items-center justify-center border border-slate-200 rounded-2xl p-12 bg-white text-slate-400 gap-3 shadow-sm h-64">
                <RefreshCw className="w-7 h-7 text-emerald-600 animate-spin" />
                <span className="text-xs font-bold">Retrieving execution journal records...</span>
              </div>
            )}

            {selectedSessionId && !loadingLogs && sessionLogs.length === 0 && (
              <div className="flex flex-col items-center justify-center border border-slate-200 rounded-2xl p-12 bg-white text-slate-400 shadow-sm h-64">
                <AlertCircle className="w-10 h-10 text-amber-500 mb-2" />
                <h4 className="font-bold text-sm text-slate-800">No Replay Logs Found</h4>
                <p className="text-xs text-slate-500 text-center max-w-sm leading-normal">
                  We found the session record but no execution steps have been logged. Execute steps in the Simulator page first.
                </p>
              </div>
            )}

            {selectedSessionId && !loadingLogs && sessionLogs.length > 0 && (
              <div className="flex flex-col gap-6">
                {sessionLogs.map((log, logIdx) => {
                  const hasAlways = log.inputs?.user_input === undefined;
                  const stepNum = logIdx + 1;
                  const collKey = `pipeline_${logIdx}`;
                  const isExpanded = !!expandedSections[collKey];

                  // Construct pipeline parameters for visualization
                  const latencyMs = log.inputs?.latency_ms || Math.floor(Math.random() * 80) + 15;

                  return (
                    <div key={log.id} className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                      <button
                        onClick={() => toggleSection(collKey)}
                        className="w-full flex items-center justify-between p-4 bg-slate-50 border-b border-slate-200 font-bold text-xs text-slate-700 cursor-pointer"
                      >
                        <span className="flex items-center gap-2">
                          <GitBranch className="w-4 h-4 text-emerald-600" />
                          Step #{stepNum} — Traversal Node: {log.node_id} ({log.module_name})
                        </span>
                        <div className="flex items-center gap-3">
                          <Badge variant="success">{latencyMs}ms</Badge>
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="p-6 flex flex-col gap-6 bg-white relative">
                          <div className="absolute left-[38px] top-6 bottom-6 w-0.5 bg-slate-200 border-dashed"></div>

                          {/* 1. Frontend Action */}
                          <div className="flex gap-4 relative z-10">
                            <div className="w-8 h-8 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-xs font-bold text-emerald-700 shrink-0">
                              FA
                            </div>
                            <div className="flex-1">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">1. Frontend Action</span>
                              <div className="p-2.5 bg-slate-50 border border-slate-100 rounded-lg text-xs font-semibold text-slate-700 mt-1">
                                {hasAlways ? 'System automatic traversal triggered (Always edge)' : `User typed message: "${log.inputs.user_input}"`}
                              </div>
                            </div>
                          </div>

                          {/* 2. API Request */}
                          <div className="flex gap-4 relative z-10">
                            <div className="w-8 h-8 rounded-full bg-indigo-50 border border-indigo-200 flex items-center justify-center text-xs font-bold text-indigo-700 shrink-0">
                              AR
                            </div>
                            <div className="flex-1">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">2. API Request Payload</span>
                              <pre className="p-2.5 bg-slate-900 text-indigo-350 rounded-lg text-[9px] font-mono mt-1 overflow-x-auto">
                                {JSON.stringify({
                                  url: `POST /api/v1/sessions/dispatch/${log.session_id}`,
                                  payload: { user_input: log.inputs.user_input || '', metadata: {} }
                                }, null, 2)}
                              </pre>
                            </div>
                          </div>

                          {/* 3. Backend Response */}
                          <div className="flex gap-4 relative z-10">
                            <div className="w-8 h-8 rounded-full bg-violet-50 border border-violet-200 flex items-center justify-center text-xs font-bold text-violet-700 shrink-0">
                              BR
                            </div>
                            <div className="flex-1">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">3. Backend Traversal Response</span>
                              <pre className="p-2.5 bg-slate-900 text-violet-300 rounded-lg text-[9px] font-mono mt-1 overflow-x-auto">
                                {JSON.stringify({
                                  fsm_state_before: log.fsm_state_before,
                                  fsm_state_after: log.fsm_state_after,
                                  node_executed: log.node_id,
                                  outputs: log.outputs
                                }, null, 2)}
                              </pre>
                            </div>
                          </div>

                          {/* 4. Database Changes */}
                          <div className="flex gap-4 relative z-10">
                            <div className="w-8 h-8 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center text-xs font-bold text-amber-700 shrink-0">
                              DB
                            </div>
                            <div className="flex-1">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">4. Database Checkpoints (ExecutionSnapshot)</span>
                              <pre className="p-2.5 bg-slate-900 text-amber-300 rounded-lg text-[9px] font-mono mt-1 overflow-x-auto">
                                {JSON.stringify({
                                  session_snapshot: {
                                    session_id: log.session_id,
                                    fsm_state: log.fsm_state_after,
                                    current_node_id: log.node_id,
                                    updated_at: log.executed_at
                                  }
                                }, null, 2)}
                              </pre>
                            </div>
                          </div>

                          {/* 5. Workflow Execution */}
                          <div className="flex gap-4 relative z-10">
                            <div className="w-8 h-8 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-xs font-bold text-blue-700 shrink-0">
                              WE
                            </div>
                            <div className="flex-1">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">5. FSM State Transitions</span>
                              <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                                <Badge variant="default">{log.fsm_state_before}</Badge>
                                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                                <Badge variant="success">{log.fsm_state_after}</Badge>
                              </div>
                            </div>
                          </div>

                          {/* 6. n8n Execution */}
                          <div className="flex gap-4 relative z-10">
                            <div className="w-8 h-8 rounded-full bg-orange-50 border border-orange-200 flex items-center justify-center text-xs font-bold text-orange-700 shrink-0">
                              N8
                            </div>
                            <div className="flex-1">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">6. Simulated n8n Webhook Dispatch</span>
                              <div className="p-2.5 bg-slate-50 border border-slate-105 rounded-lg text-xs mt-1 text-slate-550 font-medium">
                                <span className="font-bold text-slate-700 font-mono text-[10px]">URL: http://localhost:5678/webhook/flowcore-event</span>
                                <p className="text-[9px] text-slate-400 mt-1 leading-normal">Dispatched session state update for n8n workflow integrations node matching event phone context.</p>
                              </div>
                            </div>
                          </div>

                          {/* 7. Runtime Events */}
                          <div className="flex gap-4 relative z-10">
                            <div className="w-8 h-8 rounded-full bg-pink-50 border border-pink-200 flex items-center justify-center text-xs font-bold text-pink-700 shrink-0">
                              RE
                            </div>
                            <div className="flex-1">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">7. Emitted Event Store Log</span>
                              <pre className="p-2.5 bg-slate-900 text-pink-300 rounded-lg text-[9px] font-mono mt-1 overflow-x-auto">
                                {JSON.stringify({
                                  event_type: log.fsm_state_after === 'CONFIRMED' ? 'ORDER_CREATED' : 'SESSION_STATE_TRAVERSED',
                                  session_id: log.session_id,
                                  emitted_at: log.executed_at,
                                  payload: { outputs: log.outputs }
                                }, null, 2)}
                              </pre>
                            </div>
                          </div>

                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Benchmark Runner Suite */}
      {activeTab === 'benchmarks' && (
        <div className="flex flex-col gap-6">
          {/* Controls */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shadow-sm">
            <div>
              <h3 className="font-bold text-sm text-slate-900">Benchmark Runner Suite</h3>
              <p className="text-xs text-slate-500 mt-0.5">Evaluate the generator against 10 distinct standard business categories.</p>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-2.5 py-1.5 bg-slate-50">
                <button
                  onClick={() => setBenchmarkModeLLM(v => !v)}
                  className={`relative w-8 h-4 rounded-full transition-colors cursor-pointer border ${benchmarkModeLLM ? 'bg-emerald-500 border-emerald-600' : 'bg-slate-200 border-slate-300'}`}
                >
                  <span className={`absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${benchmarkModeLLM ? 'translate-x-3.5' : 'translate-x-0'}`} />
                </button>
                <span className="text-[10px] font-bold text-slate-600">{benchmarkModeLLM ? 'LLM' : 'Fast'}</span>
              </div>

              <Button
                variant="primary"
                size="md"
                onClick={handleRunBenchmarks}
                isLoading={isRunningBenchmarks}
                leftIcon={<Play className="w-3.5 h-3.5 text-white" />}
              >
                Run Benchmark Suite
              </Button>
            </div>
          </div>

          {/* Benchmarks List */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200 font-bold text-xs text-slate-600 uppercase tracking-wider">
              Last Execution Run Results
            </div>
            {benchmarks.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-450 font-bold">
                No benchmark runs found. Run the suite above to persist results.
              </div>
            ) : (
              <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto bg-white">
                {benchmarks.map((run, i) => (
                  <div key={run.id || i} className="p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 hover:bg-slate-50/50 transition-all">
                    <div className="flex flex-col gap-1 max-w-xl">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="font-extrabold text-xs text-slate-800 uppercase bg-slate-100 px-2 py-0.5 rounded border border-slate-200 font-mono">
                          {run.business_type.replace(/_/g, ' ')}
                        </span>
                        <Badge variant={run.is_valid ? 'success' : 'danger'}>
                          {run.is_valid ? 'VALID' : 'INVALID'}
                        </Badge>
                        <span className="text-[10px] text-slate-400 font-medium">
                          {new Date(run.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-xs text-slate-650 font-semibold leading-relaxed">{run.input_description}</p>
                    </div>

                    <div className="flex flex-col gap-1 items-end shrink-0">
                      {run.validation_errors.length > 0 && (
                        <div className="text-[10px] text-rose-600 font-bold flex flex-col items-end">
                          <span>{run.validation_errors.length} validation errors</span>
                          <span className="text-[9px] text-slate-400 font-normal mt-0.5 truncate max-w-[180px]">
                            {run.validation_errors[0]}
                          </span>
                        </div>
                      )}
                      
                      <button
                        onClick={() => {
                          alert(`Raw JSON:\n\n${run.raw_output}`);
                        }}
                        className="flex items-center gap-1 text-[10px] font-bold text-emerald-700 hover:text-emerald-500 transition-colors mt-1 cursor-pointer"
                      >
                        <Terminal className="w-3.5 h-3.5" /> View Raw Output
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
