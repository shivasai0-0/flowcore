'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useWorkflowStore } from '../../stores/workflowStore';
import { 
  Building2, 
  ArrowRight, 
  Loader2, 
  Zap, 
  LogIn, 
  AlertCircle,
  Copy,
  Check,
  Utensils,
  HeartPulse,
  Scissors,
  ShoppingCart,
  GraduationCap
} from 'lucide-react';

const DEV_WORKSPACES = [
  {
    id: 'restaurant_test',
    name: 'Pizza Planet',
    type: 'Restaurant',
    icon: Utensils,
    color: 'text-orange-600',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    badge: 'bg-orange-100 text-orange-700',
  },
  {
    id: 'hospital_test',
    name: 'City Hospital',
    type: 'Hospital',
    icon: HeartPulse,
    color: 'text-rose-600',
    bg: 'bg-rose-50',
    border: 'border-rose-200',
    badge: 'bg-rose-100 text-rose-700',
  },
  {
    id: 'salon_test',
    name: 'Elite Salon',
    type: 'Salon',
    icon: Scissors,
    color: 'text-purple-600',
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    badge: 'bg-purple-100 text-purple-700',
  },
  {
    id: 'supermarket_test',
    name: 'SuperMart',
    type: 'Supermarket',
    icon: ShoppingCart,
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    badge: 'bg-emerald-100 text-emerald-700',
  },
  {
    id: 'education_test',
    name: 'Education Academy',
    type: 'Education',
    icon: GraduationCap,
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    badge: 'bg-blue-100 text-blue-700',
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { loginBusiness } = useWorkflowStore();

  const [businessIdInput, setBusinessIdInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessIdInput.trim()) return;

    setLoading(true);
    setErrorMessage('');

    try {
      const success = await loginBusiness(businessIdInput.trim());
      if (success) {
        router.push('/dashboard');
      } else {
        setErrorMessage('Business ID not found. Enter one of the test workspace IDs below.');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred during workspace login.');
    } finally {
      setLoading(false);
    }
  };

  const handleUseWorkspace = (id: string) => {
    setBusinessIdInput(id);
    setErrorMessage('');
  };

  const handleCopy = async (id: string) => {
    try {
      await navigator.clipboard.writeText(id);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // fallback: just fill the input
      setBusinessIdInput(id);
    }
  };

  return (
    <div className="bg-slate-50 text-slate-800 min-h-screen flex items-center justify-center p-6 font-sans">
      {/* Login Box */}
      <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-8 shadow-xl relative">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-purple-500 to-emerald-500 rounded-t-xl"></div>
        
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center glow-active shrink-0">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-outfit font-bold text-xl text-slate-900 leading-none">FlowCore Login</h1>
            <span className="text-[9px] text-emerald-600 font-bold tracking-widest uppercase mt-1 block">Development Workspace Access</span>
          </div>
        </div>

        <form onSubmit={handleLogin} className="flex flex-col gap-5 text-xs">
          <div>
            <h2 className="text-base font-extrabold text-slate-900 mb-1">Enter Business ID</h2>
            <p className="text-xs text-slate-500">Select a workspace below or type a Business ID directly.</p>
          </div>

          {errorMessage && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5 font-medium">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="font-semibold text-slate-650 uppercase tracking-wider text-[10px]">Business ID</label>
            <input 
              type="text" 
              value={businessIdInput}
              onChange={(e) => setBusinessIdInput(e.target.value)}
              placeholder="e.g. restaurant_test"
              disabled={loading}
              className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-xs text-slate-800 font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
            />
          </div>

          {/* Available Test Workspaces Panel */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-bold text-slate-800">Available Test Workspaces</span>
            </div>
            <div className="flex flex-col gap-1.5">
              {DEV_WORKSPACES.map((ws) => {
                const Icon = ws.icon;
                const isCopied = copiedId === ws.id;
                const isSelected = businessIdInput === ws.id;
                return (
                  <div
                    key={ws.id}
                    className={`flex items-center gap-3 p-2.5 rounded-lg border transition-all ${
                      isSelected
                        ? `${ws.border} ${ws.bg} ring-1 ${ws.border.replace('border-', 'ring-')}`
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    {/* Icon */}
                    <div className={`w-7 h-7 rounded-md ${ws.bg} ${ws.border} border flex items-center justify-center shrink-0`}>
                      <Icon className={`w-3.5 h-3.5 ${ws.color}`} />
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-bold text-[11px] text-slate-800">{ws.name}</span>
                        <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full ${ws.badge}`}>
                          {ws.type}
                        </span>
                      </div>
                      <span className="font-mono text-[10px] text-slate-500 truncate block">{ws.id}</span>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleCopy(ws.id)}
                        title="Copy ID"
                        className="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                      >
                        {isCopied
                          ? <Check className="w-3 h-3 text-emerald-600" />
                          : <Copy className="w-3 h-3" />
                        }
                      </button>
                      <button
                        type="button"
                        onClick={() => handleUseWorkspace(ws.id)}
                        className={`px-2 py-1 rounded text-[10px] font-bold transition-colors cursor-pointer ${
                          isSelected
                            ? `${ws.color} ${ws.bg}`
                            : 'text-slate-600 bg-slate-100 hover:bg-slate-200'
                        }`}
                      >
                        {isSelected ? 'Selected' : 'Use'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <button 
            type="submit"
            disabled={loading || !businessIdInput.trim()}
            className={`w-full py-2.5 rounded-lg text-xs font-bold text-white transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer ${
              businessIdInput.trim() 
                ? 'bg-emerald-600 hover:bg-emerald-500 glow-active' 
                : 'bg-slate-200 text-slate-450 border border-slate-300/30 cursor-not-allowed'
            }`}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Loading workspace...
              </>
            ) : (
              <>
                <LogIn className="w-4 h-4" /> Load Workspace <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-100 text-center">
          <Link 
            href="/onboarding" 
            className="text-xs font-semibold text-slate-500 hover:text-slate-850 transition-colors"
          >
            Need a new workspace? Onboard Business
          </Link>
        </div>
      </div>
    </div>
  );
}

