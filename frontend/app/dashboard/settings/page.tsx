'use client';

import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { 
  Settings, 
  Palette, 
  Truck, 
  CreditCard, 
  Save, 
  Plus, 
  Trash2,
  CheckCircle2,
  ShoppingBag,
  Info,
  Loader2,
  XCircle,
  Eye,
  EyeOff,
  Cpu
} from 'lucide-react';

const profileSchema = z.object({
  businessName: z.string().min(2, 'Business Name must be at least 2 characters.'),
  logoUrl: z.union([z.string().url('Invalid Logo URL format.'), z.string().length(0)]),
  themeColor: z.string().regex(/^#[0-9A-Fa-f]{6}$/, 'Theme Color must be a valid Hex color (e.g. #22C55E).'),
  welcomeMessage: z.string().min(5, 'Welcome message must be at least 5 characters.')
});

const deliverySchema = z.object({
  deliveryProvider: z.string().min(1, 'Logistics carrier is required.'),
  baseFare: z.number({ invalid_type_error: 'Base Fare must be a number.' }).min(0, 'Base Fare cannot be negative.')
});

const paymentSchema = z.object({
  stripeKey: z.string().min(5, 'Stripe Secret Key is required.')
});

const catalogSchema = z.object({
  newItemName: z.string().min(2, 'Product Name must be at least 2 characters.'),
  newItemPrice: z.number({ invalid_type_error: 'Price must be a number.' }).min(0.01, 'Price must be at least $0.01.'),
  newItemCategory: z.string().min(1, 'Category is required.'),
  newItemDesc: z.string().optional()
});

const llmSchema = z.object({
  llmProvider: z.string(),
  openaiApiKey: z.string().optional(),
  geminiApiKey: z.string().optional(),
  openaiModel: z.string().optional(),
  geminiModel: z.string().optional(),
  ollamaModel: z.string().optional(),
  ollamaEndpoint: z.string().optional()
});

type ProfileFormData = z.infer<typeof profileSchema>;
type DeliveryFormData = z.infer<typeof deliverySchema>;
type PaymentFormData = z.infer<typeof paymentSchema>;
type CatalogFormData = z.infer<typeof catalogSchema>;
type LLMFormData = z.infer<typeof llmSchema>;

export default function SettingsPage() {
  const { businessId: storeBusinessId, loginBusiness } = useWorkflowStore();
  
  // Resolve active business ID
  const [businessId, setBusinessId] = useState<string | null>(null);
  
  // Loading & Error States
  const [loading, setLoading] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  const [businessType, setBusinessType] = useState('restaurant');
  const [showStripeKey, setShowStripeKey] = useState(false);
  const [showOpenAIApiKey, setShowOpenAIApiKey] = useState(false);
  const [showGeminiApiKey, setShowGeminiApiKey] = useState(false);
  const [catalogItems, setCatalogItems] = useState<any[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);

  // Forms
  const profileForm = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: { businessName: '', logoUrl: '', themeColor: '#22C55E', welcomeMessage: '' }
  });

  const deliveryForm = useForm<DeliveryFormData>({
    resolver: zodResolver(deliverySchema),
    defaultValues: { deliveryProvider: 'courier_express', baseFare: 5.0 }
  });

  const paymentForm = useForm<PaymentFormData>({
    resolver: zodResolver(paymentSchema),
    defaultValues: { stripeKey: '' }
  });

  const catalogForm = useForm<CatalogFormData>({
    resolver: zodResolver(catalogSchema),
    defaultValues: { newItemName: '', newItemPrice: 10.0, newItemCategory: 'default', newItemDesc: '' }
  });

  const llmForm = useForm<LLMFormData>({
    resolver: zodResolver(llmSchema),
    defaultValues: {
      llmProvider: 'ollama',
      openaiApiKey: '',
      geminiApiKey: '',
      openaiModel: 'gpt-4o-mini',
      geminiModel: 'gemini-1.5-flash',
      ollamaModel: 'qwen3:4b',
      ollamaEndpoint: 'http://localhost:11434'
    }
  });

  // Initialize businessId on mount
  useEffect(() => {
    const id = storeBusinessId || localStorage.getItem('flowcore_active_business_id');
    setBusinessId(id);
  }, [storeBusinessId]);

  // Load all configuration from backend
  const loadConfiguration = async (targetId: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      let bName = '';
      let bType = 'restaurant';
      let lUrl = '';
      let tColor = '#22C55E';
      let wMsg = '';
      let dProvider = 'courier_express';
      let bFare = 5.0;
      let sKey = '';

      // 1. Get branding and name config
      const configRes = await api.getBusinessConfig(targetId);
      if (configRes.success && configRes.data) {
        const data = configRes.data;
        bName = data.name || '';
        bType = data.business_type || 'restaurant';
        setBusinessType(bType);
        if (data.branding) {
          lUrl = data.branding.logo_url || '';
          tColor = data.branding.theme_color || '#22C55E';
          wMsg = data.branding.welcome_message || '';
        }
      }

      // 2. Get full business details for delivery & payments
      const bizRes = await api.getBusiness(targetId);
      if (bizRes.success && bizRes.data) {
        const settings = JSON.parse(bizRes.data.settings_json || '{}');
        if (settings.delivery) {
          dProvider = settings.delivery.provider || 'courier_express';
          bFare = parseFloat(settings.delivery.base_fare) || 5.0;
        }
        if (settings.payment) {
          sKey = settings.payment.api_key || '';
        }
      }

      // 2.5 Get LLM configuration
      let lProvider = 'ollama';
      let oApiKey = '';
      let gApiKey = '';
      let oModel = 'gpt-4o-mini';
      let gModel = 'gemini-1.5-flash';
      let olModel = 'qwen3:4b';
      let olEndpoint = 'http://localhost:11434';

      try {
        const llmRes = await api.getLLMConfig(targetId);
        if (llmRes.success && llmRes.data) {
          const llmData = llmRes.data;
          lProvider = llmData.llm_provider || 'ollama';
          oApiKey = llmData.openai_api_key || '';
          gApiKey = llmData.gemini_api_key || '';
          oModel = llmData.openai_model || 'gpt-4o-mini';
          gModel = llmData.gemini_model || 'gemini-1.5-flash';
          olModel = llmData.ollama_model || 'qwen3:4b';
          olEndpoint = llmData.ollama_endpoint || 'http://localhost:11434';
        }
      } catch (err) {
        console.error('Failed to load LLM config:', err);
      }

      // Reset forms
      profileForm.reset({
        businessName: bName,
        logoUrl: lUrl,
        themeColor: tColor,
        welcomeMessage: wMsg
      });

      deliveryForm.reset({
        deliveryProvider: dProvider,
        baseFare: bFare
      });

      paymentForm.reset({
        stripeKey: sKey
      });

      llmForm.reset({
        llmProvider: lProvider,
        openaiApiKey: oApiKey,
        geminiApiKey: gApiKey,
        openaiModel: oModel,
        geminiModel: gModel,
        ollamaModel: olModel,
        ollamaEndpoint: olEndpoint
      });

      // 3. Get Catalog Items
      const catalogRes = await api.getCatalog(targetId);
      if (catalogRes.success && catalogRes.data) {
        setCatalogItems(catalogRes.data);
      }
    } catch (err: any) {
      console.error('Failed to load configuration:', err);
      setErrorMsg('Failed to sync business parameters with the remote node.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (businessId) {
      loadConfiguration(businessId);
    }
  }, [businessId]);

  const triggerSuccessAlert = (message: string) => {
    setSaveSuccess(message);
    setTimeout(() => setSaveSuccess(null), 3000);
  };

  // Save profile, branding, and theme
  const handleSaveProfileAndBranding = async (data: ProfileFormData) => {
    if (!businessId) return;
    setErrorMsg(null);
    try {
      const res = await api.updateBusinessConfig(
        businessId,
        data.businessName,
        businessType,
        data.logoUrl,
        data.themeColor,
        data.welcomeMessage
      );
      if (res.success) {
        await loginBusiness(businessId);
        triggerSuccessAlert('Branding & profile rules saved.');
      } else {
        setErrorMsg(res.error?.message || 'Failed to update workspace config.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error occurred while saving profile.');
    }
  };

  // Save express delivery config
  const handleSaveDelivery = async (data: DeliveryFormData) => {
    if (!businessId) return;
    setErrorMsg(null);
    try {
      const res = await api.updateDelivery(businessId, {
        provider: data.deliveryProvider,
        base_fare: data.baseFare
      });
      if (res.success) {
        triggerSuccessAlert('Logistics rules saved.');
      } else {
        setErrorMsg(res.error?.message || 'Failed to update logistics settings.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error occurred while saving logistics settings.');
    }
  };

  // Save payments config
  const handleSavePayment = async (data: PaymentFormData) => {
    if (!businessId) return;
    setErrorMsg(null);
    try {
      const res = await api.updatePayment(businessId, {
        gateway: 'stripe',
        currency: 'USD',
        api_key: data.stripeKey
      });
      if (res.success) {
        triggerSuccessAlert('Payment rules saved.');
      } else {
        setErrorMsg(res.error?.message || 'Failed to update payment settings.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error occurred while saving payment config.');
    }
  };

  // Save LLM config
  const handleSaveLLM = async (data: LLMFormData) => {
    if (!businessId) return;
    setErrorMsg(null);
    try {
      const res = await api.updateLLMConfig(businessId, {
        llm_provider: data.llmProvider,
        openai_api_key: data.openaiApiKey,
        gemini_api_key: data.geminiApiKey,
        openai_model: data.openaiModel,
        gemini_model: data.geminiModel,
        ollama_model: data.ollamaModel,
        ollama_endpoint: data.ollamaEndpoint
      });
      if (res.success) {
        triggerSuccessAlert('LLM engine configuration updated.');
        await loadConfiguration(businessId);
      } else {
        setErrorMsg(res.error?.message || 'Failed to update LLM engine configuration.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error occurred while saving LLM config.');
    }
  };

  // Add Item to Catalog
  const handleAddCatalogItem = async (data: CatalogFormData) => {
    if (!businessId) return;
    setCatalogLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.createCatalogItem(businessId, {
        name: data.newItemName,
        price: data.newItemPrice,
        category: data.newItemCategory,
        description: data.newItemDesc
      });
      if (res.success) {
        const catalogRes = await api.getCatalog(businessId);
        if (catalogRes.success && catalogRes.data) {
          setCatalogItems(catalogRes.data);
        }
        catalogForm.reset({
          newItemName: '',
          newItemPrice: 10.0,
          newItemCategory: 'default',
          newItemDesc: ''
        });
        triggerSuccessAlert('Product added to catalog.');
      } else {
        setErrorMsg(res.error?.message || 'Failed to add item to catalog.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error adding item.');
    } finally {
      setCatalogLoading(false);
    }
  };

  // Remove Item from Catalog
  const handleRemoveCatalogItem = async (itemId: string) => {
    if (!businessId) return;
    if (!confirm('Are you sure you want to remove this item from the catalog?')) return;
    setCatalogLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.deleteCatalogItem(businessId, itemId);
      if (res.success) {
        const catalogRes = await api.getCatalog(businessId);
        if (catalogRes.success && catalogRes.data) {
          setCatalogItems(catalogRes.data);
        }
        triggerSuccessAlert('Product removed.');
      } else {
        setErrorMsg(res.error?.message || 'Failed to remove item.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error removing item.');
    } finally {
      setCatalogLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
        <Loader2 className="w-8 h-8 text-emerald-600 animate-spin mb-3" />
        <span className="text-xs font-semibold">Synchronizing business registry parameters...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 flex flex-col bg-slate-50/50 gap-8">
      {/* Alert overlays */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Business Settings</h2>
          <p className="text-xs text-slate-500 mt-1">Configure your product catalog, checkout gateway credentials, and WhatsApp customer branding.</p>
        </div>
        <div className="flex flex-col gap-2 items-end">
          {saveSuccess && (
            <div className="px-4 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-bold flex items-center gap-1.5 shadow-sm animate-pulse">
              <CheckCircle2 className="w-4 h-4 text-emerald-650" /> {saveSuccess}
            </div>
          )}
          {errorMsg && (
            <div className="px-4 py-1.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold flex items-center gap-1.5 shadow-sm">
              <XCircle className="w-4 h-4 text-rose-600" /> {errorMsg}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Profile & Branding Config */}
        <form onSubmit={profileForm.handleSubmit(handleSaveProfileAndBranding)} className="bg-white border border-slate-200 p-6 rounded-xl flex flex-col gap-5 shadow-sm">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider border-b border-slate-100 pb-3">
            <Palette className="w-4 h-4 text-emerald-600" /> Branding & Theme
          </h3>
          
          <div className="flex flex-col gap-4 text-xs">
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Business Workspace Name</label>
              <input 
                type="text" 
                {...profileForm.register('businessName')}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
              {profileForm.formState.errors.businessName && (
                <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{profileForm.formState.errors.businessName.message}</span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Workspace Category</label>
              <span className="self-start text-[10px] bg-slate-100 text-slate-600 border border-slate-250 font-bold px-2 py-0.5 rounded uppercase">
                {businessType}
              </span>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Branding Logo URL</label>
              <input 
                type="text" 
                {...profileForm.register('logoUrl')}
                placeholder="e.g. http://logo.com/pizzaplanet.png"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
              {profileForm.formState.errors.logoUrl && (
                <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{profileForm.formState.errors.logoUrl.message}</span>
              )}
            </div>
            
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Theme Accent Color</label>
              <div className="flex gap-2">
                <input 
                  type="color" 
                  {...profileForm.register('themeColor')}
                  className="w-9 h-9 rounded-lg bg-slate-50 border border-slate-200 p-0.5 cursor-pointer"
                />
                <input 
                  type="text" 
                  {...profileForm.register('themeColor')}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors flex-1 font-mono uppercase"
                />
              </div>
              {profileForm.formState.errors.themeColor && (
                <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{profileForm.formState.errors.themeColor.message}</span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">WhatsApp Welcome Message</label>
              <textarea 
                rows={3}
                {...profileForm.register('welcomeMessage')}
                placeholder="e.g. Welcome to Pizza Planet! Type 1 to view our menu."
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
              {profileForm.formState.errors.welcomeMessage && (
                <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{profileForm.formState.errors.welcomeMessage.message}</span>
              )}
            </div>
          </div>

          <button 
            type="submit"
            className="w-full mt-2 py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-xs font-bold text-white flex items-center justify-center gap-1.5 shadow-md transition-all cursor-pointer"
          >
            <Save className="w-3.5 h-3.5" /> Save Branding Settings
          </button>
        </form>

        {/* Catalog Setup */}
        <div className="bg-white border border-slate-200 p-6 rounded-xl flex flex-col gap-5 shadow-sm row-span-2">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider border-b border-slate-100 pb-3">
            <ShoppingBag className="w-4 h-4 text-emerald-600" /> Product Catalog & Menu
          </h3>
          
          {/* List of items */}
          <div className="flex flex-col gap-2 max-h-[380px] overflow-y-auto pr-1">
            {catalogItems.length === 0 ? (
              <div className="text-center p-6 border border-dashed border-slate-200 rounded-lg text-slate-400 text-xs font-semibold bg-slate-50/30">
                Your menu catalog is empty. Add products below!
              </div>
            ) : (
              catalogItems.map((item) => (
                <div key={item.id} className="flex justify-between items-center text-xs p-3 rounded-lg bg-slate-50/50 border border-slate-100 hover:bg-slate-50 transition-colors">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-bold text-slate-800">{item.name}</span>
                    <span className="text-[10px] text-slate-400 font-medium">Category: {item.category || 'default'}</span>
                    {item.description && (
                      <span className="text-[10px] text-slate-500 leading-normal mt-0.5">{item.description}</span>
                    )}
                    <span className="text-[9px] text-slate-400 font-mono mt-0.5">ID: {item.id}</span>
                  </div>
                  <div className="flex items-center gap-4 shrink-0 pl-2">
                    <span className="font-bold text-emerald-600 font-mono">${(item.price || 0).toFixed(2)}</span>
                    <button 
                      type="button"
                      disabled={catalogLoading}
                      onClick={() => handleRemoveCatalogItem(item.id)}
                      className="p-1.5 rounded-lg bg-white hover:bg-rose-50 border border-slate-200 hover:border-rose-200 text-slate-400 hover:text-rose-600 shadow-sm transition-colors cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Add new item */}
          <form onSubmit={catalogForm.handleSubmit(handleAddCatalogItem)} className="flex flex-col gap-3 border-t border-slate-100 pt-4 mt-1 text-xs">
            <h4 className="font-bold text-slate-800 text-[11px] uppercase tracking-wider">Add New Product</h4>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Product Name</label>
                <input 
                  type="text" 
                  {...catalogForm.register('newItemName')}
                  placeholder="e.g. French Fries"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                />
                {catalogForm.formState.errors.newItemName && (
                  <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{catalogForm.formState.errors.newItemName.message}</span>
                )}
              </div>
              
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Price ($)</label>
                <input 
                  type="number" 
                  step="0.1"
                  {...catalogForm.register('newItemPrice', { valueAsNumber: true })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                />
                {catalogForm.formState.errors.newItemPrice && (
                  <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{catalogForm.formState.errors.newItemPrice.message}</span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Category</label>
                <input 
                  type="text" 
                  {...catalogForm.register('newItemCategory')}
                  placeholder="e.g. Sides, Mains"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                />
                {catalogForm.formState.errors.newItemCategory && (
                  <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{catalogForm.formState.errors.newItemCategory.message}</span>
                )}
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Short Description</label>
                <input 
                  type="text" 
                  {...catalogForm.register('newItemDesc')}
                  placeholder="e.g. Crispy golden fries."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                />
                {catalogForm.formState.errors.newItemDesc && (
                  <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{catalogForm.formState.errors.newItemDesc.message}</span>
                )}
              </div>
            </div>

            <button 
              type="submit"
              disabled={catalogLoading}
              className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 rounded-lg text-xs font-bold text-white flex items-center justify-center gap-1.5 shadow transition-all cursor-pointer disabled:opacity-50"
            >
              {catalogLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />} Add Product to Catalog
            </button>
          </form>
        </div>

        {/* Delivery Settings */}
        <form onSubmit={deliveryForm.handleSubmit(handleSaveDelivery)} className="bg-white border border-slate-200 p-6 rounded-xl flex flex-col gap-5 shadow-sm">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider border-b border-slate-100 pb-3">
            <Truck className="w-4 h-4 text-emerald-600" /> Express Delivery Config
          </h3>
          
          <div className="flex flex-col gap-4 text-xs">
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Logistics Delivery Carrier</label>
              <input 
                type="text" 
                {...deliveryForm.register('deliveryProvider')}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
              {deliveryForm.formState.errors.deliveryProvider && (
                <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{deliveryForm.formState.errors.deliveryProvider.message}</span>
              )}
            </div>
            
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Base Shipping Fare ($)</label>
              <input 
                type="number" 
                step="0.5"
                {...deliveryForm.register('baseFare', { valueAsNumber: true })}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
              {deliveryForm.formState.errors.baseFare && (
                <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{deliveryForm.formState.errors.baseFare.message}</span>
              )}
            </div>
          </div>

          <button 
            type="submit"
            className="w-full mt-2 py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-xs font-bold text-white flex items-center justify-center gap-1.5 shadow-md transition-all cursor-pointer"
          >
            <Save className="w-3.5 h-3.5" /> Save Delivery Settings
          </button>
        </form>

        {/* Payments Config */}
        <form onSubmit={paymentForm.handleSubmit(handleSavePayment)} className="bg-white border border-slate-200 p-6 rounded-xl flex flex-col gap-5 shadow-sm">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider border-b border-slate-100 pb-3">
            <CreditCard className="w-4 h-4 text-emerald-600" /> Stripe Payment Integration
          </h3>
          
          <div className="flex flex-col gap-4 text-xs">
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Stripe API Secret Key</label>
              <div className="relative">
                <input 
                  type={showStripeKey ? 'text' : 'password'} 
                  {...paymentForm.register('stripeKey')}
                  placeholder="sk_test_••••••••••••••••••••"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-10 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowStripeKey(!showStripeKey)}
                  className="absolute right-3 top-2.5 text-slate-405 hover:text-slate-650 transition-colors"
                >
                  {showStripeKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {paymentForm.formState.errors.stripeKey && (
                <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{paymentForm.formState.errors.stripeKey.message}</span>
              )}
            </div>
          </div>

          <button 
            type="submit"
            className="w-full mt-2 py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-xs font-bold text-white flex items-center justify-center gap-1.5 shadow-md transition-all cursor-pointer"
          >
            <Save className="w-3.5 h-3.5" /> Save Payment Gateways
          </button>
        </form>

        {/* LLM Engine Settings */}
        <form onSubmit={llmForm.handleSubmit(handleSaveLLM)} className="bg-white border border-slate-200 p-6 rounded-xl flex flex-col gap-5 shadow-sm">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider border-b border-slate-100 pb-3">
            <Cpu className="w-4 h-4 text-emerald-600" /> LLM Generation Engine
          </h3>
          
          <div className="flex flex-col gap-4 text-xs">
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Active LLM Provider</label>
              <select 
                {...llmForm.register('llmProvider')}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              >
                <option value="ollama">Ollama (Local / Self-hosted)</option>
                <option value="gemini">Google Gemini (Cloud)</option>
                <option value="openai">OpenAI GPT (Cloud)</option>
              </select>
            </div>

            {llmForm.watch('llmProvider') === 'ollama' && (
              <>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Ollama API Endpoint</label>
                  <input 
                    type="text" 
                    {...llmForm.register('ollamaEndpoint')}
                    placeholder="http://localhost:11434"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Ollama Model name</label>
                  <input 
                    type="text" 
                    {...llmForm.register('ollamaModel')}
                    placeholder="qwen3:4b"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                  />
                </div>
              </>
            )}

            {llmForm.watch('llmProvider') === 'gemini' && (
              <>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Gemini API Key</label>
                  <div className="relative">
                    <input 
                      type={showGeminiApiKey ? 'text' : 'password'} 
                      {...llmForm.register('geminiApiKey')}
                      placeholder="AIzaSy••••••••••••••••••••"
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-10 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => setShowGeminiApiKey(!showGeminiApiKey)}
                      className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 transition-colors bg-transparent border-0 cursor-pointer"
                    >
                      {showGeminiApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Gemini Model name</label>
                  <input 
                    type="text" 
                    {...llmForm.register('geminiModel')}
                    placeholder="gemini-1.5-flash"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                  />
                </div>
              </>
            )}

            {llmForm.watch('llmProvider') === 'openai' && (
              <>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">OpenAI API Key</label>
                  <div className="relative">
                    <input 
                      type={showOpenAIApiKey ? 'text' : 'password'} 
                      {...llmForm.register('openaiApiKey')}
                      placeholder="sk-••••••••••••••••••••"
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-10 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => setShowOpenAIApiKey(!showOpenAIApiKey)}
                      className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 transition-colors bg-transparent border-0 cursor-pointer"
                    >
                      {showOpenAIApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">OpenAI Model name</label>
                  <input 
                    type="text" 
                    {...llmForm.register('openaiModel')}
                    placeholder="gpt-4o-mini"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                  />
                </div>
              </>
            )}
          </div>

          <button 
            type="submit"
            className="w-full mt-2 py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-xs font-bold text-white flex items-center justify-center gap-1.5 shadow-md transition-all cursor-pointer"
          >
            <Save className="w-3.5 h-3.5" /> Save LLM Settings
          </button>
        </form>
      </div>

      <div className="p-4 rounded-xl border border-slate-200 bg-white flex items-center gap-3 mt-4 shadow-sm">
        <Info className="w-4 h-4 text-emerald-600 shrink-0" />
        <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
          FlowCore automatically binds all transactions, express logistics dispatches, and WhatsApp outbound customer messaging triggers to this configuration layer. Updates take effect instantly in the simulator.
        </p>
      </div>
    </div>
  );
}
