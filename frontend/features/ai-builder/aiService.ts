import { api } from '../../services/api';

export interface AIServiceConfig {
  endpoint: string;
  provider: 'ollama' | 'openai-compatible';
  model: string;
}

export interface WorkflowIntent {
  business_type: string;
  payment_needed: boolean;
  delivery_needed: boolean;
  appointment_system: boolean;
  escalation_needed: boolean;
}

export class AIService {
  private static config: AIServiceConfig = {
    endpoint: 'http://localhost:11434',
    provider: 'ollama',
    model: 'llama3'
  };

  public static setConfig(newConfig: Partial<AIServiceConfig>) {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * Performs pre-generation analysis to extract business workflow intents.
   */
  public static async extractIntent(prompt: string): Promise<WorkflowIntent> {
    const promptLower = prompt.toLowerCase();
    
    // Quick regex-based local fallback in case LLM is offline or fails
    const localFallback: WorkflowIntent = {
      business_type: promptLower.includes('salon') ? 'salon' : promptLower.includes('clinic') ? 'clinic' : 'restaurant',
      payment_needed: promptLower.includes('pay') || promptLower.includes('stripe') || promptLower.includes('card') || promptLower.includes('checkout'),
      delivery_needed: promptLower.includes('delivery') || promptLower.includes('shipping') || promptLower.includes('courier') || promptLower.includes('address'),
      appointment_system: promptLower.includes('book') || promptLower.includes('appointment') || promptLower.includes('slot') || promptLower.includes('schedul'),
      escalation_needed: promptLower.includes('escalat') || promptLower.includes('support') || promptLower.includes('agent') || promptLower.includes('human')
    };

    try {
      const url = this.config.provider === 'ollama' 
        ? `${this.config.endpoint}/api/generate` 
        : `${this.config.endpoint}/v1/chat/completions`;

      const analysisPrompt = `Analyze this user workflow request and extract business automation configuration parameters as a single JSON object.
The JSON object MUST have exactly these keys:
{
  "business_type": "string (e.g. restaurant, clinic, salon, or custom)",
  "payment_needed": boolean,
  "delivery_needed": boolean,
  "appointment_system": boolean,
  "escalation_needed": boolean
}
Do not explain or add markdown blocks. Output only raw JSON.

User Request: "${prompt}"

JSON Output:`;

      const body = this.config.provider === 'ollama'
        ? JSON.stringify({
            model: this.config.model,
            prompt: analysisPrompt,
            stream: false
          })
        : JSON.stringify({
            model: this.config.model,
            messages: [{ role: 'user', content: analysisPrompt }],
            temperature: 0.1
          });

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 seconds limit for pre-extraction

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (!res.ok) return localFallback;
      
      const data = await res.json();
      const rawText = this.config.provider === 'ollama' ? data.response : data.choices[0].message.content;
      
      const jsonStart = rawText.indexOf('{');
      const jsonEnd = rawText.lastIndexOf('}') + 1;
      if (jsonStart !== -1 && jsonEnd !== -1) {
        return JSON.parse(rawText.substring(jsonStart, jsonEnd));
      }
      return localFallback;
    } catch {
      return localFallback;
    }
  }

  public static async generateWorkflow(
    prompt: string, 
    businessName: string, 
    category: string, 
    customDescription?: string
  ): Promise<any> {
    // Step 1: Perform Workflow Intent Extraction
    const intent = await this.extractIntent(prompt);

    // Step 2: Fetch the dynamic AI runtime context v1 from FastAPI backend
    let runtimeContext = '';
    try {
      const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${BASE_URL}/api/v1/workflows/ai-context`);
      if (res.ok) {
        const json = await res.json();
        if (json.success && json.data) {
          runtimeContext = json.data;
        }
      }
    } catch (e) {
      console.warn('Could not load dynamic runtime context v1 from backend, falling back to embedded prompt context.', e);
    }

    // Default static system prompt used as base / fallback context
    const baseSystemPrompt = `You are a FlowCore Graph Generator. FlowCore is a deterministic graph traversal and FSM conversational engine.
Your task is to output ONLY a valid JSON object matching the FlowCore WorkflowGraph schema based on the user's requirements.

The JSON schema must look like this:
{
  "business_id": "string",
  "version_number": 1,
  "entry_node_id": "string",
  "nodes": {
    "node_id": {
      "id": "node_id",
      "module_name": "string",
      "config": {},
      "fsm_transition_to": "string"
    }
  },
  "edges": [
    {
      "from_node": "string",
      "to_node": "string",
      "condition": {
        "type": "string",
        "value": "string"
      }
    }
  ],
  "fsm_transition_table": {
    "FSM_STATE_1": {
      "FSM_STATE_2": "module_name"
    }
  }
}

VALID MODULE NAMES (module_name):
- show_menu: Display catalog items or service options.
- collect_cart: Parse client input (e.g., '1 x 2') into carry unit. Requires expects_user_input=true.
- calculate_total: Computes cart sums.
- create_order: Saves cart items to database.
- create_payment: Generates Stripe transaction.
- confirm_payment: Processes and marks order paid.
- collect_address: Requests shipping address.
- create_delivery: Dispatches courier.
- notify_customer: Sends WhatsApp confirmation.

VALID FSM STATES:
START, MENU, BROWSING, CART, CHECKOUT, PAYMENT, CONFIRMED, CANCELLED, ERROR.

Ensure:
1. Valid edges connecting entry_node_id sequentially.
2. The fsm_transition_table maps valid transitions matching the nodes' fsm_transition_to values.
3. OUTPUT ONLY the JSON object. Do not explain anything.`;

    const systemPrompt = runtimeContext || baseSystemPrompt;

    try {
      const url = this.config.provider === 'ollama' 
        ? `${this.config.endpoint}/api/generate` 
        : `${this.config.endpoint}/v1/chat/completions`;

      const finalUserPrompt = `Generate a valid FlowCore workflow.
Business Name: ${businessName}
Category: ${category}
Description: ${customDescription || ''}
User Requirement: ${prompt}

EXTRACTED INTENT METADATA:
- Business Type: ${intent.business_type}
- Payment Integration Needed: ${intent.payment_needed ? 'YES' : 'NO'}
- Express Delivery Needed: ${intent.delivery_needed ? 'YES' : 'NO'}
- Appointment System: ${intent.appointment_system ? 'YES' : 'NO'}
- Support Escalation: ${intent.escalation_needed ? 'YES' : 'NO'}

Generate the graph JSON matching the specifications in the system context. Output only the JSON.`;

      const body = this.config.provider === 'ollama'
        ? JSON.stringify({
            model: this.config.model,
            prompt: `${systemPrompt}\n\n${finalUserPrompt}\n\nJSON Output:`,
            stream: false
          })
        : JSON.stringify({
            model: this.config.model,
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: finalUserPrompt }
            ],
            temperature: 0.1
          });

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 seconds timeout

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (!res.ok) throw new Error('API server returned error');
      
      const data = await res.json();
      const rawText = this.config.provider === 'ollama' ? data.response : data.choices[0].message.content;
      
      const jsonStart = rawText.indexOf('{');
      const jsonEnd = rawText.lastIndexOf('}') + 1;
      if (jsonStart !== -1 && jsonEnd !== -1) {
        const jsonStr = rawText.substring(jsonStart, jsonEnd);
        return JSON.parse(jsonStr);
      }
      throw new Error('No JSON block found in model output');
    } catch (e) {
      console.warn('Local LLM inference failed, generating fallback mock synthesis:', e);
      return this.generateMockGraph(businessName, category, prompt, customDescription);
    }
  }

  public static generateMockGraph(
    businessName: string, 
    category: string, 
    prompt: string, 
    customDescription?: string
  ): any {
    const catLower = category.toLowerCase();
    const promptLower = prompt.toLowerCase();
    
    // Check intents locally to pick the best mock template structure
    const hasPayment = promptLower.includes('pay') || promptLower.includes('stripe') || promptLower.includes('checkout');
    const hasDelivery = promptLower.includes('deliver') || promptLower.includes('ship') || promptLower.includes('courier');
    
    if (catLower === 'salon' || promptLower.includes('book') || promptLower.includes('slot')) {
      return {
        business_id: 'temp_biz_id',
        version_number: 1,
        entry_node_id: 'node_welcome',
        nodes: {
          node_welcome: {
            id: 'node_welcome',
            module_name: 'show_menu',
            config: {
              menu_header: `Welcome to ${businessName} Booking! Select service:\n1. Basic Option - $30\n2. Styling Option - $45\n3. Premium Option - $60`
            },
            fsm_transition_to: 'MENU'
          },
          node_select_slot: {
            id: 'node_select_slot',
            module_name: 'collect_cart',
            config: {
              expects_user_input: true,
              validation_regex: '^[1-3]$'
            },
            fsm_transition_to: 'CART'
          },
          node_total: {
            id: 'node_total',
            module_name: 'calculate_total',
            config: {},
            fsm_transition_to: 'CHECKOUT'
          },
          node_save_booking: {
            id: 'node_save_booking',
            module_name: 'create_order',
            config: {},
            fsm_transition_to: 'CHECKOUT'
          },
          node_confirm: {
            id: 'node_confirm',
            module_name: 'notify_customer',
            config: {
              message: 'Your booking has been registered successfully!'
            },
            fsm_transition_to: 'CONFIRMED'
          }
        },
        edges: [
          { from_node: 'node_welcome', to_node: 'node_select_slot', condition: { type: 'always', value: '' } },
          { from_node: 'node_select_slot', to_node: 'node_total', condition: { type: 'always', value: '' } },
          { from_node: 'node_total', to_node: 'node_save_booking', condition: { type: 'always', value: '' } },
          { from_node: 'node_save_booking', to_node: 'node_confirm', condition: { type: 'always', value: '' } }
        ],
        fsm_transition_table: {
          START: { MENU: 'show_menu' },
          MENU: { CART: 'collect_cart' },
          CART: { CHECKOUT: 'calculate_total' },
          CHECKOUT: { CONFIRMED: 'notify_customer' }
        }
      };
    }
    
    // General E-commerce / Delivery Flow
    if (hasDelivery || hasPayment) {
      return {
        business_id: 'temp_biz_id',
        version_number: 1,
        entry_node_id: 'node_welcome',
        nodes: {
          node_welcome: {
            id: 'node_welcome',
            module_name: 'show_menu',
            config: {
              menu_header: `Welcome to ${businessName}! Here is our menu:\n1. Margherita Pizza - $12.00\n2. Veggie Burger - $8.50\n3. French Fries - $4.00\nReply with items (e.g. '1 x 2')`
            },
            fsm_transition_to: 'MENU'
          },
          node_collect: {
            id: 'node_collect',
            module_name: 'collect_cart',
            config: {},
            fsm_transition_to: 'CART'
          },
          node_address: {
            id: 'node_address',
            module_name: 'collect_address',
            config: {
              expects_user_input: true
            },
            fsm_transition_to: 'CHECKOUT'
          },
          node_total: {
            id: 'node_total',
            module_name: 'calculate_total',
            config: {},
            fsm_transition_to: 'CHECKOUT'
          },
          node_payment: {
            id: 'node_payment',
            module_name: 'create_payment',
            config: {
              gateway: 'stripe',
              currency: 'USD'
            },
            fsm_transition_to: 'PAYMENT'
          },
          node_confirm_pay: {
            id: 'node_confirm_pay',
            module_name: 'confirm_payment',
            config: {},
            fsm_transition_to: 'CONFIRMED'
          },
          node_delivery: {
            id: 'node_delivery',
            module_name: 'create_delivery',
            config: {},
            fsm_transition_to: 'CONFIRMED'
          },
          node_notify: {
            id: 'node_notify',
            module_name: 'notify_customer',
            config: {
              message: 'Order completed and delivery courier scheduled! Thank you!'
            },
            fsm_transition_to: 'CONFIRMED'
          }
        },
        edges: [
          { from_node: 'node_welcome', to_node: 'node_collect', condition: { type: 'always', value: '' } },
          { from_node: 'node_collect', to_node: 'node_address', condition: { type: 'always', value: '' } },
          { from_node: 'node_address', to_node: 'node_total', condition: { type: 'always', value: '' } },
          { from_node: 'node_total', to_node: 'node_payment', condition: { type: 'always', value: '' } },
          { from_node: 'node_payment', to_node: 'node_confirm_pay', condition: { type: 'always', value: '' } },
          { from_node: 'node_confirm_pay', to_node: 'node_delivery', condition: { type: 'always', value: '' } },
          { from_node: 'node_delivery', to_node: 'node_notify', condition: { type: 'always', value: '' } }
        ],
        fsm_transition_table: {
          START: { MENU: 'show_menu' },
          MENU: { CART: 'collect_cart' },
          CART: { CHECKOUT: 'collect_address' },
          CHECKOUT: { PAYMENT: 'create_payment' },
          PAYMENT: { CONFIRMED: 'confirm_payment' }
        }
      };
    }
    
    // Default Fallback
    return {
      business_id: 'temp_biz_id',
      version_number: 1,
      entry_node_id: 'node_welcome',
      nodes: {
        node_welcome: {
          id: 'node_welcome',
          module_name: 'show_menu',
          config: {
            menu_header: `Welcome to ${businessName}! Here is our menu:\n1. Margherita Pizza - $12.00\n2. Veggie Burger - $8.50\n3. French Fries - $4.00\nReply with items (e.g. '1 x 2')`
          },
          fsm_transition_to: 'MENU'
        },
        node_collect: {
          id: 'node_collect',
          module_name: 'collect_cart',
          config: {},
          fsm_transition_to: 'CART'
        },
        node_total: {
          id: 'node_total',
          module_name: 'calculate_total',
          config: {},
          fsm_transition_to: 'CHECKOUT'
        },
        node_notify: {
          id: 'node_notify',
          module_name: 'notify_customer',
          config: {
            message: 'Order completed! Thank you!'
          },
          fsm_transition_to: 'CONFIRMED'
        }
      },
      edges: [
        { from_node: 'node_welcome', to_node: 'node_collect', condition: { type: 'always', value: '' } },
        { from_node: 'node_collect', to_node: 'node_total', condition: { type: 'always', value: '' } },
        { from_node: 'node_total', to_node: 'node_notify', condition: { type: 'always', value: '' } }
      ],
      fsm_transition_table: {
        START: { MENU: 'show_menu' },
        MENU: { CART: 'collect_cart' },
        CART: { CHECKOUT: 'calculate_total' },
        CHECKOUT: { CONFIRMED: 'notify_customer' }
      }
    };
  }
}
