'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useWorkflowStore } from '../../stores/workflowStore';
import { AIService } from '../../features/ai-builder/aiService';
import { 
  Building2, 
  ArrowRight, 
  Sparkles, 
  Loader2, 
  Zap, 
  CheckCircle2 
} from 'lucide-react';

const onboardingSchema = z.object({
  businessName: z.string().min(2, 'Business Name must be at least 2 characters.'),
  whatsappNumber: z.string().regex(/^\+?[1-9]\d{1,14}$/, 'Invalid WhatsApp number format (use E.164, e.g. 15551234567).'),
  businessCategory: z.string().min(1, 'Category is required.'),
  customCategoryDescription: z.string().optional()
}).refine((data) => {
  if (data.businessCategory === 'Other') {
    return !!data.customCategoryDescription && data.customCategoryDescription.trim().length > 0;
  }
  return true;
}, {
  message: 'Please describe your other business category.',
  path: ['customCategoryDescription']
});

type OnboardingFormData = z.infer<typeof onboardingSchema>;

export default function OnboardingPage() {
  const router = useRouter();
  const {
    businessName,
    whatsappNumber,
    businessCategory,
    customCategoryDescription,
    setOnboarding,
    submitOnboarding,
    registerAndCompileGraph,
    setGraph
  } = useWorkflowStore();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [aiPrompt, setLocalPrompt] = useState('');

  const { register, handleSubmit, formState: { errors }, watch, trigger } = useForm<OnboardingFormData>({
    resolver: zodResolver(onboardingSchema),
    defaultValues: {
      businessName,
      whatsappNumber,
      businessCategory,
      customCategoryDescription
    }
  });

  const categories = [
    'Restaurant', 'Salon', 'Clinic', 'Ecommerce', 'Customer Support', 
    'Delivery Service', 'Education', 'Gym/Fitness', 'Real Estate', 
    'Travel Agency', 'Repair Services', 'Event Management', 'Finance', 
    'Coaching', 'Subscription Business', 'Other'
  ];

  const handleNextStep = async () => {
    const isValid = await trigger(['businessName', 'whatsappNumber', 'businessCategory', 'customCategoryDescription']);
    if (isValid) {
      const values = watch();
      setOnboarding(values);
      setStep(2);
    }
  };

  const handleGenerateWorkflow = async () => {
    if (!aiPrompt.trim()) {
      alert('Please describe your workflow.');
      return;
    }

    setLoading(true);
    setLoadingMessage('Initializing business profile...');
    
    // Step 1: Register business
    const registered = await submitOnboarding();
    if (!registered) {
      setLoading(false);
      alert('Failed to register business profile.');
      return;
    }

    // Step 2: Call Llama Workflow Compiler
    setLoadingMessage('Local Llama analyzing requirements...');
    try {
      const currentCategory = watch('businessCategory');
      const currentCustom = watch('customCategoryDescription');
      const generatedGraph = await AIService.generateWorkflow(
        aiPrompt,
        watch('businessName'),
        currentCategory,
        currentCategory === 'Other' ? currentCustom : undefined
      );

      // Step 3: Register and compile graph on FastAPI backend
      setLoadingMessage('Compiling workflow DAG & certifying FSM safety...');
      setGraph(generatedGraph);
      const compileRes = await registerAndCompileGraph(generatedGraph);
      
      if (compileRes.success && compileRes.versionId) {
        setLoadingMessage('Workflow certified! Redirecting...');
        setTimeout(() => {
          router.push('/dashboard/builder');
        }, 1000);
      } else {
        const errorMsg = compileRes.errors && compileRes.errors.length > 0 
          ? compileRes.errors.map(e => `• ${e}`).join('\n') 
          : 'Graph compilation failed';
        throw new Error(errorMsg);
      }
    } catch (err) {
      console.error(err);
      setLoading(false);
      const errMsg = err instanceof Error ? err.message : String(err);
      alert('Verification pipeline rejected compiled graph:\n' + errMsg);
    }
  };

  const selectedCategory = watch('businessCategory');

  return (
    <div className="bg-slate-50 text-slate-800 min-h-screen flex items-center justify-center p-6 font-sans">
      {/* Onboarding Box */}
      <div className="w-full max-w-xl rounded-xl border border-slate-200 bg-white p-8 shadow-xl relative">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-purple-500 to-emerald-500 rounded-t-xl"></div>
        
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center glow-active shrink-0">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-outfit font-bold text-xl text-slate-900 leading-none">FlowCore Setup</h1>
            <span className="text-[9px] text-emerald-600 font-bold tracking-widest uppercase mt-1 block">Business Automation Hub</span>
          </div>
        </div>

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center gap-4 text-center">
            <Loader2 className="w-10 h-10 text-emerald-650 animate-spin" />
            <h3 className="font-semibold text-slate-800 text-base mt-2">{loadingMessage}</h3>
            <p className="text-xs text-slate-500 max-w-xs leading-relaxed">
              FlowCore validates condition constraints and runs replay simulations inside memory transactions.
            </p>
          </div>
        ) : step === 1 ? (
          /* Step 1: Business Profile Setup */
          <div className="flex flex-col gap-5">
            <div>
              <h2 className="text-lg font-extrabold text-slate-900 mb-1">Step 1: Profile Setup</h2>
              <p className="text-xs text-slate-500">Provide basic parameters to seed your automated workspace.</p>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); handleNextStep(); }} className="flex flex-col gap-4 text-xs">
              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600 uppercase tracking-wider text-[10px]">Business Name</label>
                <input 
                  type="text" 
                  {...register('businessName')}
                  placeholder="e.g. Pizza Planet"
                  className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                />
                {errors.businessName && (
                  <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{errors.businessName.message}</span>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600 uppercase tracking-wider text-[10px]">WhatsApp Number</label>
                <input 
                  type="text" 
                  {...register('whatsappNumber')}
                  placeholder="e.g. 15551234567"
                  className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-xs text-slate-800 font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                />
                {errors.whatsappNumber && (
                  <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{errors.whatsappNumber.message}</span>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600 uppercase tracking-wider text-[10px]">Business Category</label>
                <select 
                  {...register('businessCategory')}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-xs text-slate-850 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                >
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
                {errors.businessCategory && (
                  <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{errors.businessCategory.message}</span>
                )}
              </div>

              {selectedCategory === 'Other' && (
                <div className="flex flex-col gap-1.5 animate-fadeIn">
                  <label className="font-semibold text-slate-600 uppercase tracking-wider text-[10px]">What type of business do you run?</label>
                  <textarea 
                    {...register('customCategoryDescription')}
                    placeholder="Describe your services, products, and general customer flows..."
                    rows={3}
                    className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors resize-none leading-relaxed"
                  />
                  {errors.customCategoryDescription && (
                    <span className="text-[10px] text-rose-500 font-semibold mt-0.5">{errors.customCategoryDescription.message}</span>
                  )}
                </div>
              )}

              <button 
                type="submit"
                className="mt-4 w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-all shadow-md flex items-center justify-center gap-1.5 cursor-pointer"
              >
                Continue to AI Builder <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          </div>
        ) : (
          /* Step 2: AI Prompt Input */
          <div className="flex flex-col gap-5">
            <div>
              <h2 className="text-lg font-extrabold text-slate-900 mb-1">Step 2: AI Workflow Generator</h2>
              <p className="text-xs text-slate-500">Describe the customer automation journey you want to construct.</p>
            </div>

            <div className="flex flex-col gap-4 text-xs">
              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600 uppercase tracking-wider text-[10px]">Workflow Instructions</label>
                <textarea 
                  value={aiPrompt}
                  onChange={(e) => setLocalPrompt(e.target.value)}
                  placeholder="Describe your conversational flow naturally. E.g., 'I want a menu that welcomes patients, lets them select a department, books a slot, and registers them. If appointment is created, confirm it.'"
                  rows={5}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors resize-none leading-relaxed"
                />
              </div>

              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex gap-3 items-start">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs font-bold text-slate-850">FlowCore Safety Verification Active</span>
                  <p className="text-[10px] text-slate-500 leading-normal">
                    AI generated outputs will automatically pass through compiling cycle checking, condition operator safety checks, and replay verification pipelines.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-4">
              <button 
                onClick={() => setStep(1)}
                className="w-1/3 py-3 border border-slate-200 bg-white hover:bg-slate-55 rounded-lg text-xs font-bold text-slate-600 transition-all cursor-pointer"
              >
                Back
              </button>
              <button 
                onClick={handleGenerateWorkflow}
                className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-all shadow-md flex items-center justify-center gap-2 glow-active cursor-pointer"
              >
                <Sparkles className="w-4 h-4 text-emerald-100" />
                Generate Workflow with AI
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

