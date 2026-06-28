'use client';

import React, { useEffect, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { RefreshCw, Palette, MessageCircle, Link2, Check } from 'lucide-react';

export default function BrandingPage() {
  const { businessId, businessName } = useWorkflowStore();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  // Form State
  const [name, setName] = useState('');
  const [bizType, setBizType] = useState('restaurant');
  const [logoUrl, setLogoUrl] = useState('');
  const [themeColor, setThemeColor] = useState('#22C55E');
  const [welcomeMessage, setWelcomeMessage] = useState('');

  const fetchBranding = async () => {
    if (!businessId) return;
    try {
      const res = await api.getBusinessConfig(businessId);
      if (res.success && res.data) {
        setName(res.data.name || '');
        setBizType(res.data.business_type || 'restaurant');
        const branding = res.data.branding || {};
        setLogoUrl(branding.logo_url || '');
        setThemeColor(branding.theme_color || '#22C55E');
        setWelcomeMessage(branding.welcome_message || '');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBranding();
  }, [businessId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setSaving(true);
    setSuccess(false);

    try {
      const res = await api.updateBusinessConfig(
        businessId,
        name,
        bizType,
        logoUrl,
        themeColor,
        welcomeMessage
      );

      if (res.success) {
        setSuccess(true);
        setTimeout(() => setSuccess(false), 3000);
      } else {
        alert('Failed to save branding: ' + (res.error?.message || 'Validation error'));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 p-8 flex flex-col gap-6 bg-slate-50/50">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Branding & Configurations</h2>
          <p className="text-xs text-slate-500 mt-1">Configure user interfaces, welcome message greetings, and chatbot brand identity assets.</p>
        </div>
        <button 
          onClick={fetchBranding}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
          <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin" />
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="max-w-2xl flex flex-col gap-6">
          <div className="bg-white border border-slate-200 p-6 rounded-xl shadow-sm flex flex-col gap-4">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <Palette className="w-4.5 h-4.5 text-emerald-600" /> Identity Settings
            </span>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600">Business Display Name</label>
                <input 
                  type="text" 
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                  placeholder="e.g. Pizza Planet"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600">Business Category / Type</label>
                <select 
                  value={bizType}
                  onChange={(e) => setBizType(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors capitalize"
                >
                  {['restaurant', 'salon', 'clinic', 'hospital', 'gym', 'ecommerce', 'realestate', 'education', 'servicebusiness'].map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600">Brand Primary Hex Color</label>
                <div className="flex gap-2">
                  <input 
                    type="color" 
                    value={themeColor}
                    onChange={(e) => setThemeColor(e.target.value)}
                    className="w-10 h-8 p-0 border border-slate-200 rounded cursor-pointer"
                  />
                  <input 
                    type="text" 
                    value={themeColor}
                    onChange={(e) => setThemeColor(e.target.value)}
                    className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                    placeholder="#22C55E"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600">Brand Logo URL</label>
                <input 
                  type="text" 
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                  placeholder="https://brand.url/logo.png"
                />
              </div>
            </div>
          </div>

          {/* Chat Greetings welcome settings */}
          <div className="bg-white border border-slate-200 p-6 rounded-xl shadow-sm flex flex-col gap-4">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <MessageCircle className="w-4.5 h-4.5 text-emerald-600" /> WhatsApp Welcomes
            </span>

            <div className="flex flex-col gap-1.5 text-xs">
              <label className="font-semibold text-slate-600">Welcome Message (WhatsApp entry state node response)</label>
              <textarea 
                value={welcomeMessage}
                onChange={(e) => setWelcomeMessage(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors h-24"
                placeholder="Welcome to Pizza Planet! Type 1 to view our menu."
              />
            </div>
          </div>

          {/* Submit */}
          <div className="flex items-center gap-4">
            <button 
              type="submit" 
              disabled={saving}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Save Configuration
            </button>
            {success && (
              <span className="text-xs text-emerald-600 font-bold flex items-center gap-1 animate-pulse">
                <Check className="w-4 h-4" /> Branding Settings Updated!
              </span>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
