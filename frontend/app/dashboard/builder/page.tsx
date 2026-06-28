'use client';

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
  addEdge,
  useReactFlow,
  ReactFlowProvider
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Toast, ToastMessage } from '@/components/ui/toast';
import { SmartEdge } from '@/components/ui/SmartEdge';
import { getLayoutedGraph } from '@/lib/layout';
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/dist/style.css';

import { 
  Sparkles, 
  Send, 
  Loader2, 
  Check, 
  ShoppingCart,
  MessageSquare,
  Calculator,
  Database,
  CreditCard,
  CheckSquare,
  MapPin,
  Truck,
  Bell,
  Play,
  ArrowRight,
  RotateCcw,
  Calendar,
  UserPlus,
  FileText,
  AlertTriangle,
  HelpCircle,
  Plus,
  Trash2,
  Copy,
  Save,
  Inbox,
  AlertOctagon,
  Settings,
  Grid,
  PlusCircle,
  MinusCircle
} from 'lucide-react';

// Icons lookup mapping by module name
const nodeIcons: Record<string, any> = {
  show_menu: MessageSquare,
  collect_cart: ShoppingCart,
  calculate_total: Calculator,
  create_order: Database,
  collect_address: MapPin,
  create_payment: CreditCard,
  confirm_payment: CheckSquare,
  create_delivery: Truck,
  notify_customer: Bell,
  create_booking: Calendar,
  assign_staff: UserPlus,
  generate_report: FileText,
  request_feedback: Sparkles,
  create_support_ticket: Inbox,
  escalate_support: AlertOctagon
};

const nodeFriendlyNames: Record<string, string> = {
  show_menu: 'Welcome & Show Menu',
  collect_cart: 'Collect Order Items',
  calculate_total: 'Calculate Cart Total',
  create_order: 'Save Order Details',
  collect_address: 'Request Delivery Address',
  create_payment: 'Generate Payment Link',
  confirm_payment: 'Confirm Payment Status',
  create_delivery: 'Dispatch Courier',
  notify_customer: 'Send Customer Confirmation',
  create_booking: 'Book Appointment Slot',
  assign_staff: 'Assign Staff Member',
  generate_report: 'Compile Industry Report',
  request_feedback: 'Request Customer Rating',
  create_support_ticket: 'Open Support Ticket',
  escalate_support: 'Escalate to Manager'
};

const nodeColors: Record<string, string> = {
  show_menu: 'from-purple-50 to-purple-100/30 border-purple-200 text-purple-700',
  collect_cart: 'from-blue-50 to-blue-100/30 border-blue-200 text-blue-700',
  calculate_total: 'from-emerald-50 to-emerald-100/30 border-emerald-200 text-emerald-700',
  create_order: 'from-indigo-50 to-indigo-100/30 border-indigo-200 text-indigo-700',
  collect_address: 'from-orange-50 to-orange-100/30 border-orange-200 text-orange-700',
  create_payment: 'from-yellow-50 to-yellow-100/30 border-yellow-250 text-yellow-800',
  confirm_payment: 'from-green-50 to-green-100/30 border-green-200 text-green-700',
  create_delivery: 'from-rose-50 to-rose-100/30 border-rose-200 text-rose-700',
  notify_customer: 'from-teal-50 to-teal-100/30 border-teal-200 text-teal-700',
  create_booking: 'from-sky-50 to-sky-100/30 border-sky-200 text-sky-700',
  assign_staff: 'from-cyan-50 to-cyan-100/30 border-cyan-200 text-cyan-700',
  generate_report: 'from-violet-50 to-violet-100/30 border-violet-200 text-violet-700',
  request_feedback: 'from-pink-50 to-pink-100/30 border-pink-200 text-pink-700',
  create_support_ticket: 'from-amber-50 to-amber-100/30 border-amber-200 text-amber-700',
  escalate_support: 'from-red-50 to-red-100/30 border-red-200 text-red-700'
};

const configSchemas: Record<string, Array<{ key: string; label: string; type: 'text' | 'number' | 'date' | 'datetime' | 'array' }>> = {
  show_menu: [
    { key: 'menu_header', label: 'Menu Header Text', type: 'text' },
    { key: 'welcome_message', label: 'Welcome Message', type: 'text' }
  ],
  collect_cart: [
    { key: 'allowed_items', label: 'Allowed Item Tags', type: 'array' }
  ],
  calculate_total: [
    { key: 'discount_percentage', label: 'Discount Percentage', type: 'number' },
    { key: 'tax_rate', label: 'Tax Rate (%)', type: 'number' }
  ],
  create_order: [
    { key: 'order_prefix', label: 'Order ID Prefix', type: 'text' }
  ],
  collect_address: [
    { key: 'delivery_radius_km', label: 'Delivery Radius Limit (KM)', type: 'number' }
  ],
  create_payment: [
    { key: 'amount', label: 'Static Payment Amount', type: 'number' },
    { key: 'expiry_date', label: 'Link Expiration Date', type: 'date' }
  ],
  confirm_payment: [
    { key: 'timeout_seconds', label: 'Wait Timeout (seconds)', type: 'number' }
  ],
  create_delivery: [
    { key: 'scheduled_time', label: 'Delivery Dispatch Time', type: 'datetime' },
    { key: 'provider', label: 'Delivery Service Provider', type: 'text' }
  ],
  notify_customer: [
    { key: 'message', label: 'Notification Message Bubble', type: 'text' },
    { key: 'channels', label: 'Notification Channels', type: 'array' }
  ],
  create_booking: [
    { key: 'booking_date', label: 'Scheduled Booking Date', type: 'date' },
    { key: 'slot_duration_minutes', label: 'Slot Duration (mins)', type: 'number' }
  ],
  assign_staff: [
    { key: 'eligible_staff_roles', label: 'Eligible Staff Roles', type: 'array' }
  ],
  generate_report: [
    { key: 'report_date', label: 'Report Target Date', type: 'date' },
    { key: 'include_metrics', label: 'Metrics to Include', type: 'array' }
  ],
  request_feedback: [
    { key: 'feedback_prompt', label: 'Feedback Prompt Text', type: 'text' },
    { key: 'scale_max', label: 'Rating Scale Max Limit', type: 'number' }
  ],
  create_support_ticket: [
    { key: 'priority_level', label: 'Ticket Priority Level', type: 'text' },
    { key: 'initial_tags', label: 'Ticket Tags', type: 'array' }
  ],
  escalate_support: [
    { key: 'escalated_at', label: 'Escalation Timestamp', type: 'datetime' },
    { key: 'manager_id', label: 'Escalated Manager ID', type: 'number' }
  ]
};

// Custom visual node component inside React Flow canvas
const CustomWorkflowNode = ({ data }: any) => {
  const Icon = nodeIcons[data.module_name] || HelpCircle;
  const friendlyName = nodeFriendlyNames[data.module_name] || data.module_name;
  const colorClass = nodeColors[data.module_name] || 'from-slate-50 to-slate-100 border-slate-200 text-slate-700';

  const isEntry = data.isEntryNode;
  const errorCount = data.validationErrors?.length || 0;

  return (
    <div className={`p-4 rounded-xl border bg-gradient-to-br ${colorClass} shadow-sm w-56 flex flex-col gap-2 text-left relative bg-white transition-all ${
      data.isSelected ? 'ring-2 ring-emerald-500 ring-offset-2' : ''
    } ${errorCount > 0 ? 'border-dashed border-rose-400 ring-1 ring-rose-300' : ''}`}>
      
      {/* Input Target Connection Point */}
      <Handle 
        type="target" 
        position={Position.Left} 
        id="target"
        className="!w-2 h-2 !bg-slate-400 hover:!bg-emerald-500 transition-colors border border-white"
      />

      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded bg-white flex items-center justify-center border border-slate-200 shadow-sm shrink-0">
          <Icon className="w-4 h-4 text-emerald-600" />
        </div>
        <div className="flex flex-col min-w-0">
          <span className="text-[9px] uppercase font-bold text-slate-400 leading-none">Operation</span>
          <span className="text-xs font-bold truncate text-slate-800 mt-0.5" title={friendlyName}>{friendlyName}</span>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-slate-100/80 pt-2 mt-1">
        <div className="text-[9px] text-slate-400 font-mono flex items-center gap-1">
          <span className={`w-1.5 h-1.5 rounded-full ${isEntry ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'}`}></span> 
          ID: {data.id}
        </div>
        
        {data.fsm_transition_to && (
          <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200/50">
            → {data.fsm_transition_to}
          </span>
        )}
      </div>

      {isEntry && (
        <span className="absolute -top-2 -left-2 bg-amber-500 border border-amber-600 text-white font-extrabold text-[8px] px-1 py-0.5 rounded shadow-sm uppercase tracking-wider select-none">
          ★ Entry Node
        </span>
      )}

      {errorCount > 0 && (
        <span className="absolute -top-2.5 -right-2 bg-rose-500 border border-rose-600 text-white font-extrabold text-[9px] w-5 h-5 rounded-full flex items-center justify-center shadow-sm select-none" title={data.validationErrors.join('\n')}>
          !
        </span>
      )}

      {/* Output Source Connection Point */}
      <Handle 
        type="source" 
        position={Position.Right} 
        id="source"
        className="!w-2 h-2 !bg-slate-400 hover:!bg-emerald-500 transition-colors border border-white"
      />
    </div>
  );
};

// Canvas Inner component that uses React Flow hooks
function BuilderCanvas() {
  const {
    businessId,
    businessName,
    businessCategory,
    customCategoryDescription,
    graphJson,
    workflowStatus,
    registerAndCompileGraph,
    activateCurrentWorkflow,
    setGraph
  } = useWorkflowStore();

  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Selection states
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [entryNodeId, setEntryNodeId] = useState<string>('node_welcome');

  // Interactive configurations
  const [refineInput, setRefineInput] = useState('');
  const [isRefining, setIsRefining] = useState(false);
  const [aiRefinementChat, setAiRefinementChat] = useState<Array<{ sender: 'user' | 'assistant'; text: string }>>([]);

  const [isDeploying, setIsDeploying] = useState(false);
  const [isCompiling, setIsCompiling] = useState(false);
  
  // Real-time compilation validation
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isValidating, setIsValidating] = useState(false);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // React Flow instance view-fitting handles
  const { fitView } = useReactFlow();

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

  const nodeTypes = useMemo(() => ({
    customNode: CustomWorkflowNode
  }), []);

  const edgeTypes = useMemo(() => ({
    smart: SmartEdge
  }), []);

  // Load Graph from JSON structure
  const loadGraphJson = useCallback((graph: any) => {
    if (!graph || !graph.nodes) return;
    
    setEntryNodeId(graph.entry_node_id || 'node_welcome');

    const flowNodes: any[] = [];
    const flowEdges: any[] = [];

    const nodeIds = Object.keys(graph.nodes);
    const spacingX = 260;

    nodeIds.forEach((id, index) => {
      const node = graph.nodes[id];
      const metadata = node.config?._metadata || {};
      
      const xPos = typeof metadata.x === 'number' ? metadata.x : (50 + index * spacingX);
      const yPos = typeof metadata.y === 'number' ? metadata.y : (180 + (index % 2) * 50);

      flowNodes.push({
        id,
        type: 'customNode',
        position: { x: xPos, y: yPos },
        data: {
          id,
          module_name: node.module_name,
          config: { ...node.config },
          fsm_transition_to: node.fsm_transition_to || '',
          isEntryNode: id === (graph.entry_node_id || 'node_welcome'),
          isSelected: id === selectedNodeId,
          validationErrors: []
        }
      });
    });

    if (graph.edges && Array.isArray(graph.edges)) {
      graph.edges.forEach((edge: any, index: number) => {
        const edgeId = `edge-${edge.from_node}-${edge.to_node}-${index}`;
        flowEdges.push({
          id: edgeId,
          source: edge.from_node,
          target: edge.to_node,
          animated: true,
          label: edge.condition?.value ? `${edge.condition.type}: ${edge.condition.value}` : undefined,
          style: { stroke: '#cbd5e1', strokeWidth: 2 },
          data: {
            condition: edge.condition || { type: 'always' }
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#cbd5e1'
          }
        });
      });
    }

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [selectedNodeId, setNodes, setEdges]);

  // Sync active workspace loading
  useEffect(() => {
    if (graphJson) {
      loadGraphJson(graphJson);
    }
  }, [graphJson, loadGraphJson]);

  // Auto Zoom-to-fit on Graph Load (Task 2)
  useEffect(() => {
    if (graphJson) {
      const timer = setTimeout(() => {
        fitView({ padding: 0.2, duration: 400 });
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [graphJson, fitView]);

  // Convert visual nodes back to backend WorkflowGraph JSON format
  const serializeGraph = useCallback(() => {
    const nodesMap: Record<string, any> = {};

    nodes.forEach((flowNode) => {
      const config = { ...flowNode.data.config };
      config._metadata = {
        x: flowNode.position.x,
        y: flowNode.position.y
      };

      nodesMap[flowNode.id] = {
        id: flowNode.id,
        module_name: flowNode.data.module_name,
        config,
        fsm_transition_to: flowNode.data.fsm_transition_to || null
      };
    });

    const serializedEdges = edges.map((e) => {
      const cond = e.data?.condition || { type: 'always' };
      return {
        from_node: e.source,
        to_node: e.target,
        condition: {
          type: cond.type || 'always',
          key: cond.key || null,
          value: cond.value || null
        }
      };
    });

    // Reconstruct FSM transition table dynamically
    const fsmTable = buildFsmTransitionTable(nodes, edges);

    return {
      business_id: businessId || 'temp_biz_id',
      version_number: 1,
      entry_node_id: entryNodeId,
      nodes: nodesMap,
      edges: serializedEdges,
      fsm_transition_table: fsmTable,
      trigger_events: []
    };
  }, [nodes, edges, entryNodeId, businessId]);

  // Construct FSM transition table from node target transitions
  const buildFsmTransitionTable = (nodesList: any[], edgesList: any[]) => {
    const table: Record<string, Record<string, string>> = {};
    const FSM_in: Record<string, Set<string>> = {};
    const FSM_out: Record<string, Set<string>> = {};
    
    nodesList.forEach(node => {
      FSM_in[node.id] = new Set();
      FSM_out[node.id] = new Set();
    });

    if (FSM_in[entryNodeId]) {
      FSM_in[entryNodeId].add('START');
    }

    const queue: string[] = [entryNodeId];
    const visited = new Set<string>();

    const getChildren = (nodeId: string) => {
      return edgesList
        .filter(e => e.source === nodeId)
        .map(e => e.target);
    };

    while (queue.length > 0) {
      const curr = queue.shift()!;
      if (visited.has(curr)) continue;
      visited.add(curr);

      const nodeData = nodesList.find(n => n.id === curr);
      if (!nodeData) continue;

      const moduleName = nodeData.data?.module_name;
      const fsmTransition = nodeData.data?.fsm_transition_to;

      const currentIncoming = FSM_in[curr];
      if (currentIncoming && currentIncoming.size > 0) {
        currentIncoming.forEach(stateIn => {
          let stateOut = stateIn;
          if (fsmTransition) {
            stateOut = fsmTransition;
            
            if (stateIn !== stateOut) {
              if (!table[stateIn]) {
                table[stateIn] = {};
              }
              table[stateIn][stateOut] = moduleName;
            }
          }
          FSM_out[curr].add(stateOut);
        });
      }

      const children = getChildren(curr);
      children.forEach(child => {
        if (FSM_in[child]) {
          FSM_out[curr].forEach(s => FSM_in[child].add(s));
        }
        if (!visited.has(child)) {
          queue.push(child);
        }
      });
    }

    const finalTable: Record<string, Record<string, string>> = {};
    Object.entries(table).forEach(([fromState, transitions]) => {
      finalTable[fromState] = transitions;
    });

    return finalTable;
  };

  // Run dry-run validation (Debounced or on request)
  const handleValidate = async () => {
    if (nodes.length === 0) return;
    setIsValidating(true);
    try {
      const payload = serializeGraph();
      const res = await api.validateWorkflow(payload);
      if (res.success && res.data) {
        setValidationErrors(res.data.errors || []);
        
        // Propagate errors to visual nodes in state
        setNodes((prevNodes) =>
          prevNodes.map((n) => {
            const nodeErrors = (res.data.errors || []).filter((err: string) => 
              err.includes(`'${n.id}'`) || err.includes(`node '${n.id}'`) || err.includes(`Node '${n.id}'`)
            );
            return {
              ...n,
              data: {
                ...n.data,
                validationErrors: nodeErrors
              }
            };
          })
        );
      }
    } catch (e: any) {
      console.error(e);
    } finally {
      setIsValidating(false);
    }
  };

  // Save / Register Workflow
  const handleSaveDraft = async () => {
    if (!businessId) {
      addToast('Error: No active business selected.', 'error');
      return;
    }
    setIsCompiling(true);
    try {
      const payload = serializeGraph();
      const res = await registerAndCompileGraph(payload);
      if (res.success) {
        addToast('Workflow registered & compiled successfully!', 'success');
        setGraph(payload);
        handleValidate();
      } else {
        addToast('Validation Warning: Saved as Draft but failed compilation.', 'warning');
        setGraph(payload);
        handleValidate();
      }
    } catch (err: any) {
      addToast(`Error: ${err.message}`, 'error');
    } finally {
      setIsCompiling(false);
    }
  };

  // Deploy to WhatsApp
  const handleDeploy = async () => {
    setIsDeploying(true);
    try {
      const success = await activateCurrentWorkflow();
      if (success) {
        addToast('🚀 Automation deployed to live WhatsApp routing!', 'success');
      } else {
        addToast('Deployment failed. Verify that current version is compiled and approved.', 'error');
      }
    } catch (err: any) {
      addToast(`Error: ${err.message}`, 'error');
    } finally {
      setIsDeploying(false);
    }
  };

  // Auto layout organizes nodes orthogonally (Task 1)
  const handleAutoLayout = async () => {
    if (nodes.length === 0) return;
    const { nodes: layoutedNodes, edges: layoutedEdges } = await getLayoutedGraph(nodes, edges);
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
    addToast('Canvas layout organized successfully!', 'success');
    // Follow up fitView trigger
    setTimeout(() => {
      fitView({ padding: 0.2, duration: 400 });
    }, 100);
  };

  // Canvas interaction hooks
  const onConnect = useCallback((params: any) => {
    setEdges((eds) => addEdge({
      ...params,
      animated: true,
      label: undefined,
      style: { stroke: '#cbd5e1', strokeWidth: 2 },
      data: { condition: { type: 'always' } },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#cbd5e1' }
    }, eds));
  }, [setEdges]);

  // Click handler to select node/edge
  const onNodeClick = useCallback((event: React.MouseEvent, node: any) => {
    setSelectedNodeId(node.id);
    setSelectedEdgeId(null);
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          isSelected: n.id === node.id
        }
      }))
    );
  }, [setNodes]);

  const onEdgeClick = useCallback((event: React.MouseEvent, edge: any) => {
    setSelectedEdgeId(edge.id);
    setSelectedNodeId(null);
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          isSelected: false
        }
      }))
    );
  }, [setNodes]);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          isSelected: false
        }
      }))
    );
  }, [setNodes]);

  // Drag and Drop implementation
  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      if (!reactFlowWrapper.current || !reactFlowInstance) return;

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });
      
      const newNodeId = `node_${type}_${Math.random().toString(36).substring(2, 6)}`;
      const newNode = {
        id: newNodeId,
        type: 'customNode',
        position,
        data: {
          id: newNodeId,
          module_name: type,
          config: {},
          fsm_transition_to: '',
          isEntryNode: false,
          isSelected: false,
          validationErrors: []
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
  );

  // Helper: Quick-click select templates
  const addNodeToCanvas = (type: string) => {
    const position = { x: 100 + Math.random() * 80, y: 150 + Math.random() * 80 };
    const newNodeId = `node_${type}_${Math.random().toString(36).substring(2, 6)}`;
    const newNode = {
      id: newNodeId,
      type: 'customNode',
      position,
      data: {
        id: newNodeId,
        module_name: type,
        config: {},
        fsm_transition_to: '',
        isEntryNode: false,
        isSelected: false,
        validationErrors: []
      },
    };
    setNodes((nds) => nds.concat(newNode));
  };

  // Node Inspector functions
  const activeNode = useMemo(() => {
    return nodes.find(n => n.id === selectedNodeId);
  }, [nodes, selectedNodeId]);

  const handleUpdateNodeId = (newId: string) => {
    if (!selectedNodeId || !newId.trim()) return;
    
    // Validate uniqueness
    if (nodes.some(n => n.id === newId && n.id !== selectedNodeId)) {
      addToast('Error: Node ID must be unique.', 'error');
      return;
    }

    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === selectedNodeId) {
          return {
            ...n,
            id: newId,
            data: {
              ...n.data,
              id: newId
            }
          };
        }
        return n;
      })
    );

    // Update edge references
    setEdges((eds) =>
      eds.map((e) => {
        let updated = { ...e };
        if (e.source === selectedNodeId) updated.source = newId;
        if (e.target === selectedNodeId) updated.target = newId;
        return updated;
      })
    );

    if (entryNodeId === selectedNodeId) {
      setEntryNodeId(newId);
    }
    
    setSelectedNodeId(newId);
  };

  const handleUpdateNodeFsm = (fsmTarget: string) => {
    if (!selectedNodeId) return;
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === selectedNodeId) {
          return {
            ...n,
            data: {
              ...n.data,
              fsm_transition_to: fsmTarget
            }
          };
        }
        return n;
      })
    );
  };

  const handleUpdateNodeConfig = (key: string, value: any) => {
    if (!selectedNodeId) return;
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === selectedNodeId) {
          const updatedConfig = { ...n.data.config, [key]: value };
          return {
            ...n,
            data: {
              ...n.data,
              config: updatedConfig
            }
          };
        }
        return n;
      })
    );
  };

  const handleDeleteNode = (nodeId: string) => {
    if (confirm('Delete this node and all of its connections?')) {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
      setSelectedNodeId(null);
    }
  };

  const handleDuplicateNode = (node: any) => {
    const type = node.data.module_name;
    const position = { x: node.position.x + 50, y: node.position.y + 50 };
    const newNodeId = `node_${type}_${Math.random().toString(36).substring(2, 6)}`;
    const newNode = {
      id: newNodeId,
      type: 'customNode',
      position,
      data: {
        id: newNodeId,
        module_name: type,
        config: { ...node.data.config },
        fsm_transition_to: node.data.fsm_transition_to,
        isEntryNode: false,
        isSelected: false,
        validationErrors: []
      },
    };
    setNodes((nds) => nds.concat(newNode));
    addToast('Node duplicated!', 'success');
  };

  // Edge Inspector functions
  const activeEdge = useMemo(() => {
    return edges.find(e => e.id === selectedEdgeId);
  }, [edges, selectedEdgeId]);

  const handleUpdateEdgeCondition = (field: string, value: any) => {
    if (!selectedEdgeId) return;
    setEdges((eds) =>
      eds.map((e) => {
        if (e.id === selectedEdgeId) {
          const prevCond = e.data?.condition || { type: 'always' };
          const updatedCond = { ...prevCond, [field]: value };
          
          let label = undefined;
          if (updatedCond.value) {
            label = `${updatedCond.type}: ${updatedCond.value}`;
          } else if (updatedCond.type !== 'always') {
            label = updatedCond.type;
          }

          return {
            ...e,
            label,
            data: {
              ...e.data,
              condition: updatedCond
            }
          };
        }
        return e;
      })
    );
  };

  const handleDeleteEdge = (edgeId: string) => {
    setEdges((eds) => eds.filter((e) => e.id !== edgeId));
    setSelectedEdgeId(null);
  };

  // AI Refinement logic
  const handleRefine = async () => {
    if (!refineInput.trim()) return;

    const userMsg = refineInput;
    setAiRefinementChat(prev => [...prev, { sender: 'user', text: userMsg }]);
    setRefineInput('');
    setIsRefining(true);

    try {
      const currentPayload = serializeGraph();
      const res = await api.generateAIWorkflow(
        businessId || 'temp_biz_id',
        `Adjust our current workflow with this directive: "${userMsg}". Here is the existing graph layout to refine: ${JSON.stringify(currentPayload)}`,
        [],
        false
      );

      if (res.success && res.data && res.data.workflows) {
        const workflowsObj = res.data.workflows;
        const mainWfName = Object.keys(workflowsObj)[0];
        const refinedGraph = workflowsObj[mainWfName];
        
        loadGraphJson(refinedGraph);
        
        setAiRefinementChat(prev => [
          ...prev,
          { sender: 'assistant', text: `Success! I have modified the workflow nodes and recalculated FSM safety parameters.` }
        ]);
        addToast('Workflow updated via AI Refinement!', 'success');
        handleValidate();
      } else {
        setAiRefinementChat(prev => [
          ...prev,
          { sender: 'assistant', text: `Failed to refine graph: ${res.error?.message || 'Verification rejected.'}` }
        ]);
      }
    } catch (err: any) {
      setAiRefinementChat(prev => [
        ...prev,
        { sender: 'assistant', text: `Sorry, I failed to connect to the generator service. Error: ${err.message}` }
      ]);
    } finally {
      setIsRefining(false);
    }
  };

  // Reset to clean template
  const handleResetWorkflow = () => {
    if (confirm('Reset canvas to standard template?')) {
      const cleanGraph = {
        entry_node_id: 'node_welcome',
        nodes: {
          node_welcome: {
            id: 'node_welcome',
            module_name: 'show_menu',
            config: {
              menu_header: 'Welcome to our store! Reply with the items you wish to buy.',
              _metadata: { x: 80, y: 200 }
            },
            fsm_transition_to: 'MENU'
          },
          node_collect: {
            id: 'node_collect',
            module_name: 'collect_cart',
            config: {
              _metadata: { x: 380, y: 200 }
            },
            fsm_transition_to: 'CART'
          },
          node_notify: {
            id: 'node_notify',
            module_name: 'notify_customer',
            config: {
              message: 'Thank you for your order! Your payment is confirmed.',
              _metadata: { x: 680, y: 200 }
            },
            fsm_transition_to: 'CONFIRMED'
          }
        },
        edges: [
          { from_node: 'node_welcome', to_node: 'node_collect', condition: { type: 'always' } },
          { from_node: 'node_collect', to_node: 'node_notify', condition: { type: 'always' } }
        ]
      };
      loadGraphJson(cleanGraph);
      addToast('Canvas reset to basic template.', 'info');
    }
  };

  // Render Widget Helper based on Schema type (Task 4)
  const renderConfigWidget = (field: any) => {
    const value = activeNode?.data.config[field.key] || '';
    
    // 1. Date/Datetime Picker using Lightweight react-day-picker / popover select (Task 4)
    if (field.type === 'date' || field.type === 'datetime') {
      return (
        <div className="flex flex-col gap-1 border border-slate-100 p-2.5 rounded-lg bg-slate-50">
          <label className="text-[10px] font-bold text-slate-500">{field.label}</label>
          <input
            type={field.type === 'date' ? 'date' : 'datetime-local'}
            value={value}
            onChange={(e) => handleUpdateNodeConfig(field.key, e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500 font-medium"
          />
        </div>
      );
    }

    // 2. Stepper layout for Numeric fields (Task 4)
    if (field.type === 'number') {
      const numValue = Number(value) || 0;
      return (
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold text-slate-500">{field.label}</label>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => handleUpdateNodeConfig(field.key, numValue - 1)}
              className="p-1 rounded hover:bg-slate-200 text-slate-500 cursor-pointer border border-slate-200 bg-white"
            >
              <MinusCircle className="w-4 h-4" />
            </button>
            <input
              type="number"
              value={numValue}
              onChange={(e) => handleUpdateNodeConfig(field.key, Number(e.target.value) || 0)}
              className="flex-1 text-center bg-slate-50 border border-slate-200 rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500 font-bold font-mono"
            />
            <button
              onClick={() => handleUpdateNodeConfig(field.key, numValue + 1)}
              className="p-1 rounded hover:bg-slate-200 text-slate-500 cursor-pointer border border-slate-200 bg-white"
            >
              <PlusCircle className="w-4 h-4" />
            </button>
          </div>
        </div>
      );
    }

    // 3. Dynamic row array builder list (Task 4)
    if (field.type === 'array') {
      const arrayVal = Array.isArray(value) ? value : [];
      return (
        <div className="flex flex-col gap-1 border border-slate-100 p-2.5 rounded-lg bg-slate-50">
          <label className="text-[10px] font-bold text-slate-500">{field.label}</label>
          
          <div className="flex flex-col gap-1 mt-1 max-h-24 overflow-y-auto pr-1">
            {arrayVal.map((item: string, index: number) => (
              <div key={index} className="flex justify-between items-center gap-1.5 p-1 bg-white border border-slate-200 rounded-md">
                <span className="text-[10px] truncate pl-1 font-mono">{item}</span>
                <button
                  onClick={() => {
                    const filtered = arrayVal.filter((_: any, idx: number) => idx !== index);
                    handleUpdateNodeConfig(field.key, filtered);
                  }}
                  className="p-0.5 rounded text-rose-500 hover:bg-rose-50 cursor-pointer shrink-0"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>

          <form
            onSubmit={(e: React.FormEvent<HTMLFormElement>) => {
              e.preventDefault();
              const form = e.currentTarget;
              const input = form.elements.namedItem('array_new_val') as HTMLInputElement;
              if (input && input.value.trim()) {
                handleUpdateNodeConfig(field.key, [...arrayVal, input.value.trim()]);
                input.value = '';
              }
            }}
            className="flex gap-1 mt-1.5"
          >
            <input
              name="array_new_val"
              type="text"
              placeholder="Add value..."
              className="flex-1 bg-white border border-slate-200 rounded px-2 py-0.5 text-[10px] focus:outline-none"
            />
            <button
              type="submit"
              className="px-2 bg-emerald-600 text-white rounded text-[10px] font-bold cursor-pointer hover:bg-emerald-500 flex items-center justify-center shrink-0"
            >
              Add
            </button>
          </form>
        </div>
      );
    }

    // Default: text field fallback
    return (
      <div className="flex flex-col gap-1">
        <label className="text-[10px] font-bold text-slate-500">{field.label}</label>
        <textarea
          value={value}
          onChange={(e) => handleUpdateNodeConfig(field.key, e.target.value)}
          placeholder={`Enter ${field.label}...`}
          rows={3}
          className="w-full bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-500 resize-none font-medium"
        />
      </div>
    );
  };

  return (
    <div className="flex-1 flex overflow-hidden bg-slate-50/50">
      
      {/* Toast Manager container */}
      <div className="fixed top-5 right-5 z-[9999] flex flex-col gap-2 max-w-sm">
        {toasts.map((t) => (
          <Toast key={t.id} message={t.message} type={t.type} onClose={() => removeToast(t.id)} />
        ))}
      </div>

      {/* Sidebar Panel 1: Drag & Drop Node Templates */}
      <div className="w-64 border-r border-slate-200 bg-white p-5 flex flex-col justify-between shrink-0 overflow-y-auto">
        <div className="flex flex-col gap-5">
          <div>
            <h2 className="font-outfit font-bold text-sm text-slate-900">Draggable Operations</h2>
            <p className="text-[10px] text-slate-500 mt-1">Drag elements onto the canvas or click to place them.</p>
          </div>

          <div className="flex flex-col gap-3.5">
            {/* Category: Conversational */}
            <div className="flex flex-col gap-2">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Conversational</span>
              <div className="flex flex-col gap-1.5">
                {['show_menu', 'notify_customer', 'request_feedback'].map((type) => (
                  <div
                    key={type}
                    draggable
                    onDragStart={(e) => onDragStart(e, type)}
                    onClick={() => addNodeToCanvas(type)}
                    className="px-3 py-2 rounded-lg border border-slate-200/80 bg-slate-50/30 text-[10px] font-semibold text-slate-700 hover:border-emerald-500 hover:bg-emerald-50/20 cursor-grab active:cursor-grabbing transition-all flex items-center gap-2 select-none"
                  >
                    <div className="w-5 h-5 rounded bg-white flex items-center justify-center border border-slate-200 shadow-sm">
                      {React.createElement(nodeIcons[type] || HelpCircle, { className: 'w-3 h-3 text-emerald-600' })}
                    </div>
                    <span>{nodeFriendlyNames[type]}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Category: Commerce & Order */}
            <div className="flex flex-col gap-2">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Commerce & Ordering</span>
              <div className="flex flex-col gap-1.5">
                {['collect_cart', 'calculate_total', 'create_order', 'collect_address'].map((type) => (
                  <div
                    key={type}
                    draggable
                    onDragStart={(e) => onDragStart(e, type)}
                    onClick={() => addNodeToCanvas(type)}
                    className="px-3 py-2 rounded-lg border border-slate-200/80 bg-slate-50/30 text-[10px] font-semibold text-slate-700 hover:border-emerald-500 hover:bg-emerald-50/20 cursor-grab active:cursor-grabbing transition-all flex items-center gap-2 select-none"
                  >
                    <div className="w-5 h-5 rounded bg-white flex items-center justify-center border border-slate-200 shadow-sm">
                      {React.createElement(nodeIcons[type] || HelpCircle, { className: 'w-3 h-3 text-emerald-600' })}
                    </div>
                    <span>{nodeFriendlyNames[type]}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Category: Payments */}
            <div className="flex flex-col gap-2">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Payments</span>
              <div className="flex flex-col gap-1.5">
                {['create_payment', 'confirm_payment'].map((type) => (
                  <div
                    key={type}
                    draggable
                    onDragStart={(e) => onDragStart(e, type)}
                    onClick={() => addNodeToCanvas(type)}
                    className="px-3 py-2 rounded-lg border border-slate-200/80 bg-slate-50/30 text-[10px] font-semibold text-slate-700 hover:border-emerald-500 hover:bg-emerald-50/20 cursor-grab active:cursor-grabbing transition-all flex items-center gap-2 select-none"
                  >
                    <div className="w-5 h-5 rounded bg-white flex items-center justify-center border border-slate-200 shadow-sm">
                      {React.createElement(nodeIcons[type] || HelpCircle, { className: 'w-3 h-3 text-emerald-600' })}
                    </div>
                    <span>{nodeFriendlyNames[type]}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Category: Fulfillment */}
            <div className="flex flex-col gap-2">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Fulfillment & Operations</span>
              <div className="flex flex-col gap-1.5">
                {['create_delivery', 'create_booking', 'assign_staff', 'generate_report'].map((type) => (
                  <div
                    key={type}
                    draggable
                    onDragStart={(e) => onDragStart(e, type)}
                    onClick={() => addNodeToCanvas(type)}
                    className="px-3 py-2 rounded-lg border border-slate-200/80 bg-slate-50/30 text-[10px] font-semibold text-slate-700 hover:border-emerald-500 hover:bg-emerald-50/20 cursor-grab active:cursor-grabbing transition-all flex items-center gap-2 select-none"
                  >
                    <div className="w-5 h-5 rounded bg-white flex items-center justify-center border border-slate-200 shadow-sm">
                      {React.createElement(nodeIcons[type] || HelpCircle, { className: 'w-3 h-3 text-emerald-600' })}
                    </div>
                    <span>{nodeFriendlyNames[type]}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Category: Support */}
            <div className="flex flex-col gap-2">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Governance & Support</span>
              <div className="flex flex-col gap-1.5">
                {['create_support_ticket', 'escalate_support'].map((type) => (
                  <div
                    key={type}
                    draggable
                    onDragStart={(e) => onDragStart(e, type)}
                    onClick={() => addNodeToCanvas(type)}
                    className="px-3 py-2 rounded-lg border border-slate-200/80 bg-slate-50/30 text-[10px] font-semibold text-slate-700 hover:border-emerald-500 hover:bg-emerald-50/20 cursor-grab active:cursor-grabbing transition-all flex items-center gap-2 select-none"
                  >
                    <div className="w-5 h-5 rounded bg-white flex items-center justify-center border border-slate-200 shadow-sm">
                      {React.createElement(nodeIcons[type] || HelpCircle, { className: 'w-3 h-3 text-emerald-600' })}
                    </div>
                    <span>{nodeFriendlyNames[type]}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Validation Checkbox Card */}
        <div className="mt-5 border-t border-slate-100 pt-4 flex flex-col gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            className="w-full text-slate-650"
            onClick={handleValidate} 
            isLoading={isValidating}
            leftIcon={<CheckSquare className="w-3.5 h-3.5" />}
          >
            Dry-Run Validate
          </Button>
        </div>
      </div>

      {/* Center: React Flow Canvas */}
      <div className="flex-1 relative bg-slate-50/20 flex flex-col" ref={reactFlowWrapper}>
        
        {/* Save & Deploy Controls Toolbar */}
        <div className="absolute top-4 left-4 right-4 z-10 flex justify-between items-center pointer-events-none">
          <div className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 text-[10px] font-bold flex items-center gap-1.5 shadow-sm pointer-events-auto">
            <span className={`w-1.5 h-1.5 rounded-full ${
              workflowStatus === 'ACTIVE' ? 'bg-emerald-500 glow-active' : 'bg-amber-500 animate-pulse'
            }`} />
            <span>Status: {workflowStatus || 'UNSAVED'}</span>
          </div>

          <div className="flex gap-2 pointer-events-auto">
            {/* Auto-Layout button (Task 1) */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleAutoLayout}
              className="bg-white"
              leftIcon={<Grid className="w-3.5 h-3.5 text-slate-500" />}
            >
              Auto-layout
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleSaveDraft}
              isLoading={isCompiling}
              className="bg-white"
              leftIcon={<Save className="w-3.5 h-3.5 text-slate-500" />}
            >
              Save Draft
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleDeploy}
              isLoading={isDeploying}
              leftIcon={<Play className="w-3.5 h-3.5 text-white" />}
            >
              Deploy to Live
            </Button>
          </div>
        </div>

        {/* React Flow Component */}
        <div className="flex-1 h-full">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            defaultEdgeOptions={{ type: 'smart' }}
            snapToGrid={true}
            snapGrid={[10, 10]}
            fitView
          >
            <Background color="#cbd5e1" gap={20} size={1} />
            <Controls className="!bg-white !border-slate-200 !text-slate-600 shadow-sm rounded-lg overflow-hidden" />
          </ReactFlow>
        </div>

        {/* Validation Errors Overlay Panel (Bottom) */}
        {validationErrors.length > 0 && (
          <div className="border-t border-rose-200 bg-rose-50/50 p-4 max-h-40 overflow-y-auto shrink-0 flex flex-col gap-1.5">
            <span className="text-[10px] font-bold text-rose-800 uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4" /> Static Validation Warnings ({validationErrors.length})
            </span>
            <div className="flex flex-col gap-1 font-mono text-[9px] text-rose-700 leading-normal font-semibold">
              {validationErrors.map((err, i) => (
                <div key={i} className="flex gap-1.5 items-start">
                  <span>•</span>
                  <span>{err}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Sidebar Panel 2: Right Inspector / Config & AI Assistant */}
      <div className="w-80 border-l border-slate-200 bg-white flex flex-col justify-between shrink-0 overflow-y-auto">
        <div className="flex flex-col divide-y divide-slate-100">
          
          {/* Section: Selected Node Inspector */}
          {activeNode ? (
            <div className="p-5 flex flex-col gap-4">
              <div>
                <h3 className="text-xs font-bold text-slate-900 flex items-center gap-1.5 uppercase tracking-wider">
                  <Settings className="w-3.5 h-3.5 text-slate-500" />
                  Node Configuration
                </h3>
                <p className="text-[9px] text-slate-400 mt-0.5">Parameters driving computational logic at this state.</p>
              </div>

              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] font-bold text-slate-400 uppercase">Node ID</label>
                  <input
                    type="text"
                    value={activeNode.id}
                    onChange={(e) => handleUpdateNodeId(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono"
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-[9px] font-bold text-slate-400 uppercase">Module Name</label>
                  <span className="px-2.5 py-1.5 rounded bg-slate-100 border border-slate-200/50 text-xs font-semibold text-slate-500 font-mono">
                    {activeNode.data.module_name}
                  </span>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-[9px] font-bold text-slate-400 uppercase">FSM Target Transition</label>
                  <select
                    value={activeNode.data.fsm_transition_to || ''}
                    onChange={(e) => handleUpdateNodeFsm(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-md px-2 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
                  >
                    <option value="">None (Keep same state)</option>
                    {['START', 'MENU', 'CART', 'CHECKOUT', 'PAYMENT', 'CONFIRMED', 'CANCELLED', 'ERROR'].map((state) => (
                      <option key={state} value={state}>
                        {state}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Dynamic Config Input Forms based on Module Schema variables (Task 4) */}
                <div className="border-t border-slate-100 pt-3 mt-1 flex flex-col gap-3">
                  <span className="text-[9px] font-bold text-slate-400 uppercase">Config Variables</span>
                  
                  {configSchemas[activeNode.data.module_name] ? (
                    <div className="flex flex-col gap-3">
                      {configSchemas[activeNode.data.module_name].map((field) => (
                        <div key={field.key} className="flex flex-col gap-1">
                          {renderConfigWidget(field)}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-[9px] text-slate-400 font-medium italic p-2 rounded bg-slate-50 border border-slate-100 text-center">
                      No custom fields registered for this module. Auto-resolved by system parameters.
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 border-t border-slate-100 pt-4 mt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 hover:bg-slate-100 hover:text-slate-700"
                    leftIcon={<Copy className="w-3 h-3" />}
                    onClick={() => handleDuplicateNode(activeNode)}
                  >
                    Duplicate
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="flex-1"
                    leftIcon={<Trash2 className="w-3 h-3" />}
                    onClick={() => handleDeleteNode(activeNode.id)}
                  >
                    Delete
                  </Button>
                </div>

                <div className="border-t border-slate-100 pt-3 mt-1 flex justify-between items-center">
                  <span className="text-[9px] font-bold text-slate-400 uppercase">Entry Point</span>
                  <Button
                    variant={entryNodeId === activeNode.id ? 'success' : 'outline'}
                    size="sm"
                    onClick={() => {
                      setEntryNodeId(activeNode.id);
                      setNodes(nds => nds.map(n => ({
                        ...n,
                        data: {
                          ...n.data,
                          isEntryNode: n.id === activeNode.id
                        }
                      })));
                      addToast('Entry point updated.', 'success');
                    }}
                    className="px-2 py-1 h-fit"
                  >
                    {entryNodeId === activeNode.id ? '★ Entry Point' : 'Set as Entry'}
                  </Button>
                </div>
              </div>
            </div>
          ) : activeEdge ? (
            <div className="p-5 flex flex-col gap-4">
              <div>
                <h3 className="text-xs font-bold text-slate-900 flex items-center gap-1.5 uppercase tracking-wider">
                  <Settings className="w-3.5 h-3.5 text-slate-500" />
                  Connection Rules
                </h3>
                <p className="text-[9px] text-slate-400 mt-0.5">Define state condition routing guidelines.</p>
              </div>

              <div className="flex flex-col gap-3">
                <div className="flex justify-between text-[10px] font-mono text-slate-500 bg-slate-50 border border-slate-200/50 p-2 rounded">
                  <span>From: {activeEdge.source}</span>
                  <span>→</span>
                  <span>To: {activeEdge.target}</span>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-[9px] font-bold text-slate-400 uppercase">Condition Rule Type</label>
                  <select
                    value={activeEdge.data?.condition?.type || 'always'}
                    onChange={(e) => handleUpdateEdgeCondition('type', e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
                  >
                    <option value="always">Always Cascade</option>
                    <option value="input_equals">Input Exact Action Match</option>
                    <option value="input_in">Input Contained in Options</option>
                    <option value="carry_equals">Carry namespace Variable Matches</option>
                    <option value="carry_greater_than">Carry Variable Greater than</option>
                  </select>
                </div>

                {activeEdge.data?.condition?.type !== 'always' && (
                  <>
                    {['carry_equals', 'carry_greater_than'].includes(activeEdge.data?.condition?.type) && (
                      <div className="flex flex-col gap-1">
                        <label className="text-[9px] font-bold text-slate-555">Namespace parameter Key</label>
                        <input
                          type="text"
                          value={activeEdge.data?.condition?.key || ''}
                          onChange={(e) => handleUpdateEdgeCondition('key', e.target.value)}
                          placeholder="e.g. order.total"
                          className="w-full bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono"
                        />
                      </div>
                    )}

                    <div className="flex flex-col gap-1">
                      <label className="text-[9px] font-bold text-slate-555">Matching Constraint Value</label>
                      <input
                        type="text"
                        value={activeEdge.data?.condition?.value || ''}
                        onChange={(e) => handleUpdateEdgeCondition('value', e.target.value)}
                        placeholder="e.g. 10.0 or PAY"
                        className="w-full bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono"
                      />
                    </div>
                  </>
                )}

                <Button
                  variant="destructive"
                  size="sm"
                  className="w-full mt-2"
                  leftIcon={<Trash2 className="w-3.5 h-3.5" />}
                  onClick={() => handleDeleteEdge(activeEdge.id)}
                >
                  Delete Connection
                </Button>
              </div>
            </div>
          ) : (
            <div className="p-5 text-center text-[10px] text-slate-400 font-medium py-10">
              Select any node or connection link on the canvas to configure parameters.
            </div>
          )}

          {/* Section: AI Refinement Assistant */}
          <div className="p-5 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold text-slate-900 flex items-center gap-1.5 uppercase tracking-wider">
                  <Sparkles className="w-3.5 h-3.5 text-purple-500 animate-pulse" />
                  AI Refinement
                </h3>
                <p className="text-[9px] text-slate-400 mt-0.5">Request updates via LLM instruction models.</p>
              </div>
              <button
                onClick={handleResetWorkflow}
                title="Reset Workflow layout"
                className="p-1 rounded bg-white hover:bg-rose-50 text-slate-400 hover:text-rose-600 border border-slate-200 hover:border-rose-200 transition-all flex items-center justify-center cursor-pointer shadow-xs"
              >
                <RotateCcw className="w-3 h-3" />
              </button>
            </div>

            {/* Chat Log history */}
            <div className="h-32 rounded-lg border border-slate-200 bg-slate-50/50 p-2.5 overflow-y-auto flex flex-col gap-2">
              {aiRefinementChat.length === 0 ? (
                <div className="text-[9px] text-slate-400 font-medium italic text-center py-6">
                  Explain adjustments (e.g. "Add French Fries item to order collections") and AI will refactor the canvas.
                </div>
              ) : (
                aiRefinementChat.map((msg, idx) => (
                  <div 
                    key={idx}
                    className={`p-2 rounded-lg text-[10px] leading-relaxed max-w-[85%] font-medium ${
                      msg.sender === 'user' 
                        ? 'bg-purple-50 text-purple-700 border border-purple-100 self-end shadow-xs' 
                        : 'bg-white text-slate-700 border border-slate-200/80 self-start shadow-xs'
                    }`}
                  >
                    {msg.text}
                  </div>
                ))
              )}
              {isRefining && (
                <div className="flex items-center gap-1.5 text-[9px] text-slate-500 font-semibold self-start p-1 border border-slate-200 rounded bg-white shadow-xs">
                  <Loader2 className="w-3 h-3 text-purple-500 animate-spin" /> Refinement model mapping changes...
                </div>
              )}
            </div>

            <div className="flex gap-1.5">
              <input 
                type="text" 
                value={refineInput}
                onChange={(e) => setRefineInput(e.target.value)}
                placeholder="e.g. Add French Fries slot..."
                disabled={isRefining}
                className="flex-1 bg-slate-50 border border-slate-200 rounded-md px-2 py-1.5 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-purple-500 transition-all"
              />
              <button 
                onClick={handleRefine}
                disabled={isRefining || !refineInput.trim()}
                className="bg-purple-600 hover:bg-purple-500 px-3 rounded-md text-xs font-bold text-white transition-all flex items-center justify-center cursor-pointer shadow-xs"
              >
                <Send className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Default export wraps BuilderCanvas with ReactFlowProvider to support useReactFlow hooks (Task 2)
export default function BuilderPage() {
  return (
    <ReactFlowProvider>
      <BuilderCanvas />
    </ReactFlowProvider>
  );
}
