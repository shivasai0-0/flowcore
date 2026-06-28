export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: {
    error_code: string;
    message: string;
  };
}

export interface Business {
  id: string;
  name: string;
  business_type?: string;
  whatsapp_number: string;
  settings_json: string;
  catalog_json: string;
  created_at: string;
}

export interface WorkflowVersion {
  id: string;
  business_id: string;
  version_number: number;
  status: 'DRAFT' | 'VALIDATING' | 'SIMULATING' | 'APPROVED' | 'ACTIVE' | 'DEPRECATED' | 'FAILED';
  graph_json: string;
  workflow_type: 'static' | 'dynamic';
  is_current: boolean;
  created_at: string;
}

export interface Session {
  id: string;
  business_id: string;
  customer_phone: string;
  fsm_state: string;
  current_node_id?: string;
  carry_unit: any;
  workflow_version_id: string;
  updated_at: string;
}

export interface ReplayStep {
  node_id: string;
  module_name: string;
  inputs: any;
  outputs: any;
  fsm_state_before: string;
  fsm_state_after: string;
  executed_at: string;
  latency_ms?: number;
  routing_decision?: string;
  carry_diff?: any;
  fsm_transition?: string;
  side_effects: string[];
  edge_logs: string[];
}

export interface ReplayResponse {
  session_id: string;
  trace: ReplayStep[];
  final_carry_unit: any;
  final_fsm_state: string;
}

export interface ModuleContract {
  module_name: string;
  display_name: string;
  version: string;
  domain: string;
  requires: Record<string, string>;
  produces: Record<string, string>;
  allowed_fsm_states: string[];
  side_effects: string[];
  is_idempotent: boolean;
  expects_user_input?: boolean;
}

export interface BusinessListItem {
  id: string;
  name: string;
  business_type: string;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options?.headers as Record<string, string>),
    };

    if (typeof window !== 'undefined') {
      const activeId = localStorage.getItem('flowcore_active_business_id');
      if (activeId) {
        headers['X-FlowCore-Business-Id'] = activeId;
        headers['X-Business-Id'] = activeId;
      }
    }

    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    });
    const data = await res.json();
    if (!res.ok) {
      return {
        success: false,
        data: null as any,
        error: data.error || { error_code: 'API_ERROR', message: data.detail || 'Request failed' },
      };
    }
    return data;
  } catch (error: any) {
    return {
      success: false,
      data: null as any,
      error: { error_code: 'NETWORK_ERROR', message: error.message || 'Network request failed' },
    };
  }
}

export const api = {
  // Businesses
  async createBusiness(name: string, whatsappNumber: string): Promise<ApiResponse<Business>> {
    return request<Business>('/api/v1/businesses', {
      method: 'POST',
      body: JSON.stringify({ name, whatsapp_number: whatsappNumber }),
    });
  },

  async listBusinesses(): Promise<ApiResponse<BusinessListItem[]>> {
    return request<BusinessListItem[]>('/api/v1/businesses');
  },

  async setActiveDevWorkspace(businessId: string): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/businesses/active-dev-workspace/${businessId}`, {
      method: 'POST',
    });
  },

  async getBusiness(id: string): Promise<ApiResponse<Business>> {
    return request<Business>(`/api/v1/businesses/${id}`);
  },

  async updateBranding(id: string, branding: any): Promise<ApiResponse<Business>> {
    return request<Business>(`/api/v1/businesses/${id}/branding`, {
      method: 'PUT',
      body: JSON.stringify({ branding }),
    });
  },

  async updateDelivery(id: string, deliverySettings: any): Promise<ApiResponse<Business>> {
    return request<Business>(`/api/v1/businesses/${id}/delivery`, {
      method: 'PUT',
      body: JSON.stringify({ delivery_settings: deliverySettings }),
    });
  },

  async updatePayment(id: string, paymentConfig: any): Promise<ApiResponse<Business>> {
    return request<Business>(`/api/v1/businesses/${id}/payment`, {
      method: 'PUT',
      body: JSON.stringify({ payment_config: paymentConfig }),
    });
  },

  async getWorkflows(businessId: string): Promise<ApiResponse<WorkflowVersion[]>> {
    return request<WorkflowVersion[]>(`/api/v1/businesses/${businessId}/workflows`);
  },

  // Workflows
  async registerWorkflow(businessId: string, graph: any, type: 'static' | 'dynamic' = 'dynamic'): Promise<ApiResponse<{ workflow_version_id: string; status: string; validation_report: any }>> {
    return request('/api/v1/workflows/register', {
      method: 'POST',
      body: JSON.stringify({ business_id: businessId, workflow_type: type, graph }),
    });
  },

  async compileWorkflow(id: string): Promise<ApiResponse<{ workflow_version_id: string; status: string; validation_report: any }>> {
    return request(`/api/v1/workflows/compile/${id}`, { method: 'POST' });
  },

  async activateWorkflow(id: string): Promise<ApiResponse<WorkflowVersion>> {
    return request<WorkflowVersion>(`/api/v1/workflows/activate/${id}`, { method: 'POST' });
  },

  async certifyWorkflow(id: string): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/workflows/certify/${id}`, { method: 'POST' });
  },

  async validateWorkflow(graph: any): Promise<ApiResponse<any>> {
    return request<any>('/api/v1/workflows/validate', {
      method: 'POST',
      body: JSON.stringify(graph),
    });
  },

  // Sessions
  async createSession(businessId: string, customerPhone: string): Promise<ApiResponse<Session>> {
    return request<Session>('/api/v1/sessions', {
      method: 'POST',
      body: JSON.stringify({ business_id: businessId, customer_phone: customerPhone }),
    });
  },

  async dispatchInput(sessionId: string, userInput: string, metadata: any = {}): Promise<ApiResponse<any>> {
    return request(`/api/v1/sessions/dispatch/${sessionId}`, {
      method: 'POST',
      body: JSON.stringify({ user_input: userInput, metadata }),
    });
  },

  async unlockSession(sessionId: string): Promise<ApiResponse<Session>> {
    return request<Session>(`/api/v1/sessions/unlock/${sessionId}`, { method: 'PUT' });
  },

  async inspectSession(sessionId: string): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/sessions/inspect/${sessionId}`);
  },

  async getSessionReplay(sessionId: string): Promise<ApiResponse<ReplayResponse>> {
    return request<ReplayResponse>(`/api/v1/sessions/replay/${sessionId}`);
  },

  async listSnapshots(sessionId: string): Promise<ApiResponse<any[]>> {
    return request<any[]>(`/api/v1/sessions/${sessionId}/snapshots`);
  },

  async rollbackSession(sessionId: string, snapshotId: string): Promise<ApiResponse<Session>> {
    return request<Session>(`/api/v1/sessions/${sessionId}/rollback/${snapshotId}`, { method: 'POST' });
  },

  // Modules
  async listModules(): Promise<ApiResponse<ModuleContract[]>> {
    return request<ModuleContract[]>('/api/v1/modules');
  },

  // Dashboard
  async getDashboardOverview(businessId?: string): Promise<ApiResponse<any>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any>(`/api/v1/dashboard/overview${q}`);
  },

  async getDashboardTimeline(businessId?: string, limit?: number): Promise<ApiResponse<any[]>> {
    let q = businessId ? `?business_id=${businessId}` : '';
    if (limit) {
      q += businessId ? `&limit=${limit}` : `?limit=${limit}`;
    }
    return request<any[]>(`/api/v1/dashboard/timeline${q}`);
  },

  async getDashboardWidgets(businessId?: string): Promise<ApiResponse<any>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any>(`/api/v1/dashboard/widgets${q}`);
  },

  // Events
  async listEvents(businessId?: string, limit = 50, offset = 0): Promise<ApiResponse<any[]>> {
    const params = new URLSearchParams();
    if (businessId) params.append('business_id', businessId);
    params.append('limit', String(limit));
    params.append('offset', String(offset));
    return request<any[]>(`/api/v1/events?${params.toString()}`);
  },

  async listLiveEvents(businessId?: string): Promise<ApiResponse<any[]>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any[]>(`/api/v1/events/live${q}`);
  },

  // Providers
  async getProviders(businessId?: string): Promise<ApiResponse<any>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any>(`/api/v1/providers${q}`);
  },

  async updateProviders(businessId: string, providers: any, config?: any): Promise<ApiResponse<any>> {
    return request<any>('/api/v1/providers', {
      method: 'PUT',
      body: JSON.stringify({ business_id: businessId, providers, config })
    });
  },

  // Business Config & Catalog
  async getBusinessConfig(businessId?: string): Promise<ApiResponse<any>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any>(`/api/v1/business/config${q}`);
  },

  async updateBusinessConfig(
    businessId: string,
    name?: string,
    businessType?: string,
    logoUrl?: string,
    themeColor?: string,
    welcomeMessage?: string
  ): Promise<ApiResponse<any>> {
    return request<any>('/api/v1/business/config', {
      method: 'PUT',
      body: JSON.stringify({
        business_id: businessId,
        name,
        business_type: businessType,
        logo_url: logoUrl,
        theme_color: themeColor,
        welcome_message: welcomeMessage
      })
    });
  },

  async getLLMConfig(businessId: string): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/businesses/${businessId}/llm-config`);
  },

  async updateLLMConfig(businessId: string, llmConfig: any): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/businesses/${businessId}/llm-config`, {
      method: 'PUT',
      body: JSON.stringify({ llm_config: llmConfig }),
    });
  },

  async getCatalog(businessId?: string): Promise<ApiResponse<any[]>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any[]>(`/api/v1/business/catalog${q}`);
  },

  async createCatalogItem(businessId: string, item: { id?: string; name: string; price: number; category?: string; description?: string; image_url?: string }): Promise<ApiResponse<any>> {
    return request<any>('/api/v1/business/catalog/item', {
      method: 'POST',
      body: JSON.stringify({ business_id: businessId, ...item })
    });
  },

  async updateCatalogItem(businessId: string, itemId: string, item: { name: string; price: number; category?: string; description?: string; image_url?: string }): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/business/catalog/item/${itemId}`, {
      method: 'PUT',
      body: JSON.stringify({ business_id: businessId, ...item })
    });
  },

  async deleteCatalogItem(businessId: string, itemId: string): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/business/catalog/item/${itemId}?business_id=${businessId}`, {
      method: 'DELETE'
    });
  },

  // Workflows (Extend)
  async listAllWorkflows(businessId?: string): Promise<ApiResponse<any[]>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any[]>(`/api/v1/workflows${q}`);
  },

  async getWorkflowDetails(versionId: string): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/workflows/${versionId}`);
  },

  // AI Builder
  async generateAIWorkflow(businessId: string, description: string, packs: string[], useMockAI = true, llamaEndpoint = 'http://localhost:11434'): Promise<ApiResponse<any>> {
    return request<any>('/api/v1/workflows/generate', {
      method: 'POST',
      body: JSON.stringify({
        business_id: businessId,
        business_description: description,
        capability_packs: packs,
        use_mock_ai: useMockAI,
        llama_endpoint: llamaEndpoint
      })
    });
  },

  async listCustomers(businessId?: string): Promise<ApiResponse<any[]>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any[]>(`/api/v1/dashboard/customers${q}`);
  },

  async getOperations(businessId?: string): Promise<ApiResponse<any>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any>(`/api/v1/dashboard/operations${q}`);
  },

  async redeployWorkflow(versionId: string): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/workflows/redeploy/${versionId}`, { method: 'POST' });
  },

  // Workers
  async listWorkers(businessId?: string): Promise<ApiResponse<any[]>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any[]>(`/api/v1/workers${q}`);
  },

  async createWorker(worker: { business_id?: string; name: string; role: string; specialization?: string; availability?: any; capacity?: number }): Promise<ApiResponse<any>> {
    return request<any>('/api/v1/workers', {
      method: 'POST',
      body: JSON.stringify(worker),
    });
  },

  async updateWorker(workerId: string, worker: { name?: string; role?: string; specialization?: string; availability?: any; capacity?: number }): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/workers/${workerId}`, {
      method: 'PUT',
      body: JSON.stringify(worker),
    });
  },

  async deleteWorker(workerId: string): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/workers/${workerId}`, { method: 'DELETE' });
  },

  // Tasks
  async listTasks(businessId?: string, assignedWorkerId?: string, statusFilter?: string): Promise<ApiResponse<any[]>> {
    const params = new URLSearchParams();
    if (businessId) params.append('business_id', businessId);
    if (assignedWorkerId) params.append('assigned_worker_id', assignedWorkerId);
    if (statusFilter) params.append('status_filter', statusFilter);
    return request<any[]>(`/api/v1/tasks?${params.toString()}`);
  },

  async createTask(task: { business_id?: string; session_id?: string; title: string; description?: string; priority?: string; assigned_worker_id?: string; due_time?: string }): Promise<ApiResponse<any>> {
    return request<any>('/api/v1/tasks', {
      method: 'POST',
      body: JSON.stringify(task),
    });
  },

  async updateTask(taskId: string, task: { title?: string; description?: string; priority?: string; assigned_worker_id?: string; status?: string; due_time?: string }): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify(task),
    });
  },

  async deleteTask(taskId: string): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/tasks/${taskId}`, { method: 'DELETE' });
  },

  // Approvals
  async listApprovals(businessId?: string, statusFilter?: string): Promise<ApiResponse<any[]>> {
    const params = new URLSearchParams();
    if (businessId) params.append('business_id', businessId);
    if (statusFilter) params.append('status_filter', statusFilter);
    return request<any[]>(`/api/v1/approvals?${params.toString()}`);
  },

  async takeApprovalAction(approvalId: string, action: 'APPROVE' | 'REJECT' | 'MODIFY' | 'ESCALATE', notes?: string, resolvedBy?: string): Promise<ApiResponse<any>> {
    return request<any>(`/api/v1/approvals/${approvalId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action, notes, resolved_by: resolvedBy }),
    });
  },

  // Reports
  async listReportsHistory(businessId?: string): Promise<ApiResponse<any[]>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any[]>(`/api/v1/reports/history${q}`);
  },

  async generateReport(businessId: string, reportType: string): Promise<ApiResponse<any>> {
    return request<any>('/api/v1/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ business_id: businessId, report_type: reportType }),
    });
  },

  async sendReportWhatsapp(recipientPhone: string, reportContent: string): Promise<ApiResponse<any>> {
    return request<any>('/api/v1/reports/send-whatsapp', {
      method: 'POST',
      body: JSON.stringify({ recipient_phone: recipientPhone, report_content: reportContent }),
    });
  },

  // Generation Jobs
  async listGenerationJobs(businessId?: string): Promise<ApiResponse<any[]>> {
    const q = businessId ? `?business_id=${businessId}` : '';
    return request<any[]>(`/api/v1/generation-jobs${q}`);
  },

  async triggerGenerationJob(businessId: string, description: string, packs: string[], useMockAI = true, llamaEndpoint = 'http://localhost:11434'): Promise<ApiResponse<any>> {
    return request<any>('/api/v1/generation-jobs', {
      method: 'POST',
      body: JSON.stringify({
        business_id: businessId,
        business_description: description,
        capability_packs: packs,
        use_mock_ai: useMockAI,
        llama_endpoint: llamaEndpoint,
      }),
    });
  }
};


