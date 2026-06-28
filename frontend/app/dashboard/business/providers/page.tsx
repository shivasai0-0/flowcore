'use client';

import React, { useEffect, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { RefreshCw, CreditCard, MessageSquare, ShieldCheck, Check } from 'lucide-react';

export default function ProvidersPage() {
  const { businessId } = useWorkflowStore();
  const [providers, setProviders] = useState<any>({ stripe: {}, whatsapp: {}, twilio: {} });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  // Form inputs
  const [stripeSecret, setStripeSecret] = useState('');
  const [stripeWebhook, setStripeWebhook] = useState('');
  const [metaPhoneId, setMetaPhoneId] = useState('');
  const [metaToken, setMetaToken] = useState('');

  const fetchProviders = async () => {
    if (!businessId) return;
    try {
      const res = await api.getProviders(businessId);
      if (res.success && res.data) {
        setProviders(res.data || {});
        // Pre-fill values
        const stripe = res.data.stripe || {};
        const whatsapp = res.data.whatsapp || {};
        setStripeSecret(stripe.secret_key || '');
        setStripeWebhook(stripe.webhook_secret || '');
        setMetaPhoneId(whatsapp.phone_number_id || '');
        setMetaToken(whatsapp.access_token || '');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();
  }, [businessId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setSaving(true);
    setSuccess(false);

    const payload = {
      stripe: {
        secret_key: stripeSecret,
        webhook_secret: stripeWebhook
      },
      whatsapp: {
        phone_number_id: metaPhoneId,
        access_token: metaToken
      }
    };

    try {
      const res = await api.updateProviders(businessId, payload);
      if (res.success) {
        setSuccess(true);
        setTimeout(() => setSuccess(false), 3000);
      } else {
        alert('Failed to save provider config: ' + (res.error?.message || 'Validation error'));
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
          <h2 className="font-outfit font-bold text-xl text-slate-900">API Provider Integrations</h2>
          <p className="text-xs text-slate-500 mt-1">Configure Stripe transactional gateways and Meta Cloud API webhooks.</p>
        </div>
        <button 
          onClick={fetchProviders}
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
          {/* Stripe Configuration */}
          <div className="bg-white border border-slate-200 p-6 rounded-xl shadow-sm flex flex-col gap-4">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <CreditCard className="w-4.5 h-4.5 text-emerald-600" /> Stripe Payment Integration
            </span>

            <div className="grid grid-cols-1 gap-4 text-xs">
              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600">Stripe Secret Key (sk_live...)</label>
                <input 
                  type="password" 
                  value={stripeSecret}
                  onChange={(e) => setStripeSecret(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                  placeholder="sk_test_..."
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600">Stripe Webhook Signing Secret (whsec_...)</label>
                <input 
                  type="password" 
                  value={stripeWebhook}
                  onChange={(e) => setStripeWebhook(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                  placeholder="whsec_..."
                />
              </div>
            </div>
          </div>

          {/* Meta WhatsApp Configuration */}
          <div className="bg-white border border-slate-200 p-6 rounded-xl shadow-sm flex flex-col gap-4">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <MessageSquare className="w-4.5 h-4.5 text-emerald-600" /> Meta Cloud WhatsApp Gateway
            </span>

            <div className="grid grid-cols-1 gap-4 text-xs">
              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600">Phone Number ID (Numeric identifier)</label>
                <input 
                  type="text" 
                  value={metaPhoneId}
                  onChange={(e) => setMetaPhoneId(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                  placeholder="e.g. 10928374928"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-slate-600">Permanent Access Token (EAAG...)</label>
                <input 
                  type="password" 
                  value={metaToken}
                  onChange={(e) => setMetaToken(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors font-mono"
                  placeholder="EAAG..."
                />
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex items-center gap-4">
            <button 
              type="submit" 
              disabled={saving}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
              Save Integrations
            </button>
            {success && (
              <span className="text-xs text-emerald-600 font-bold flex items-center gap-1 animate-pulse">
                <Check className="w-4 h-4" /> Integrations Updated Successfully!
              </span>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
