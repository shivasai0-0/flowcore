'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Zap, 
  MessageSquare, 
  ShieldCheck, 
  Sparkles, 
  ArrowRight, 
  CheckCircle2, 
  Coins, 
  Workflow 
} from 'lucide-react';

export default function SaaSPage() {
  const [activeStep, setActiveStep] = useState(0);

  const demoConversation = [
    { sender: 'user', text: 'Hi, I\'d like to order pizza' },
    { sender: 'bot', text: '🍕 Welcome to Pizza Planet!\n1. Margherita Pizza - $12.00\n2. Pepperoni Pizza - $14.00\nReply with item & quantity (e.g. 1 x 2)' },
    { sender: 'user', text: '1 x 2' },
    { sender: 'bot', text: 'Added 2x Margherita Pizza ($24.00) to your cart.\nPlease provide your shipping address.' },
    { sender: 'user', text: '123 Main St' },
    { sender: 'bot', text: 'Address saved.\nReply "PAY" to checkout using our Stripe link: stripe.com/pay_23f982' },
    { sender: 'user', text: 'PAY' },
    { sender: 'bot', text: '✅ Payment Confirmed! Your Margherita Pizzas are being baked and courier assigned. Order #39281.' }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % demoConversation.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const features = [
    {
      title: 'AI-First Generation',
      desc: 'Simply describe your business process in plain English and our local Llama agent builds your custom state-governed workflow.',
      icon: Sparkles
    },
    {
      title: 'Deterministic Engine',
      desc: 'No LLM hallucinations during execution. Traversal is strictly regulated by mathematical Finite State Machines.',
      icon: ShieldCheck
    },
    {
      title: 'WhatsApp Automation',
      desc: 'Seamlessly interface with Meta Cloud APIs to interact with consumers where they are active.',
      icon: MessageSquare
    },
    {
      title: 'Built-in Payments',
      desc: 'Safely collect Stripe, Razorpay, or COD transactions inside the chat flow with transactional idempotency.',
      icon: Coins
    },
    {
      title: 'Logistics Integrations',
      desc: 'Trigger background delivery courier dispatch tasks on successful payments automatically.',
      icon: Workflow
    },
    {
      title: 'Orchestration Safety',
      desc: 'Ensure session concurrency, time-travel snapshot recovery, and replay verification tests check every node.',
      icon: Zap
    }
  ];

  return (
    <div className="bg-slate-50 text-slate-800 min-h-screen font-sans">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center glow-active">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-outfit font-bold text-xl text-slate-900 tracking-wide">FlowCore</span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm font-semibold text-slate-500">
            <a href="#features" className="hover:text-slate-800 transition-colors">Features</a>
            <a href="#demo" className="hover:text-slate-800 transition-colors">Interactive Demo</a>
            <a href="#pricing" className="hover:text-slate-800 transition-colors">Pricing</a>
            <a href="#faq" className="hover:text-slate-800 transition-colors">FAQ</a>
          </nav>
          <div className="flex items-center gap-4">
            <Link 
              href="/login" 
              className="text-sm font-bold text-slate-500 hover:text-slate-800 transition-colors"
            >
              Login
            </Link>
            <Link 
              href="/onboarding" 
              className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-bold transition-all shadow-md flex items-center gap-1 cursor-pointer"
            >
              Get Started <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 px-6 max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        <div className="flex flex-col gap-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-xs font-bold self-start shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
            <span>AI-First Workflow Automation</span>
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-outfit font-extrabold text-slate-900 tracking-tight leading-none">
            Describe your business. <br/>
            <span className="gradient-text">Automate WhatsApp.</span>
          </h1>
          <p className="text-slate-500 text-base md:text-lg leading-relaxed max-w-xl">
            FlowCore runs your business operations automatically on WhatsApp. Describe what you want in plain English, and our AI builds a safe, deterministic, FSM-governed automation.
          </p>
          <div className="flex items-center gap-4 mt-2">
            <Link 
              href="/onboarding" 
              className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-3 rounded-lg text-base font-bold transition-all shadow-lg flex items-center gap-2 cursor-pointer"
            >
              Onboard Your Business <ArrowRight className="w-5 h-5" />
            </Link>
            <a 
              href="#demo" 
              className="border border-slate-200 bg-white hover:bg-slate-50 px-6 py-3 rounded-lg text-base font-bold transition-all text-slate-700 flex items-center gap-2 shadow-sm"
            >
              View Live Demo
            </a>
          </div>
        </div>

        {/* WhatsApp Mock Simulator */}
        <div id="demo" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xl relative overflow-hidden flex flex-col h-[440px] max-w-md mx-auto w-full">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-emerald-500 via-purple-500 to-emerald-500"></div>
          
          {/* Header */}
          <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center font-extrabold text-emerald-600 border border-slate-200 text-sm">
              P
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-slate-800">Pizza Planet Bot</h3>
              <p className="text-[10px] text-emerald-600 font-bold animate-pulse flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Online
              </p>
            </div>
          </div>

          {/* Messages body */}
          <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-3">
            {demoConversation.map((msg, idx) => {
              const isVisible = idx <= activeStep;
              if (!isVisible) return null;
              const isUser = msg.sender === 'user';
              return (
                <div 
                  key={idx} 
                  className={`flex flex-col max-w-[80%] rounded-xl px-3.5 py-2 text-xs leading-relaxed shadow-sm ${
                    isUser 
                      ? 'bg-emerald-500 text-white self-end rounded-tr-none' 
                      : 'bg-slate-100 text-slate-800 border border-slate-200 self-start rounded-tl-none font-medium'
                  }`}
                >
                  <p className="whitespace-pre-line">{msg.text}</p>
                </div>
              );
            })}
          </div>

          <div className="pt-3 border-t border-slate-100 flex gap-2">
            <input 
              type="text" 
              placeholder="Type message..." 
              disabled 
              suppressHydrationWarning
              className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-400 focus:outline-none"
            />
            <button disabled className="bg-slate-150 px-3.5 py-1.5 rounded-lg text-xs font-bold text-slate-400">Send</button>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 border-t border-slate-200 bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center flex flex-col items-center gap-4 mb-16">
            <h2 className="text-3xl font-outfit font-extrabold text-slate-900 tracking-tight">Designed for Production Reliability</h2>
            <p className="text-slate-500 text-sm md:text-base max-w-xl">
              FlowCore isolates business configurations from system traversal execution to deliver bulletproof automation.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feat, idx) => {
              const Icon = feat.icon;
              return (
                <div key={idx} className="glass-card p-6 rounded-xl flex flex-col gap-4 bg-slate-50/50 border border-slate-200 hover:border-emerald-500/30 transition-all">
                  <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="font-outfit font-extrabold text-slate-800 text-base mb-1.5">{feat.title}</h3>
                    <p className="text-slate-500 text-xs leading-relaxed font-medium">{feat.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Pricing Tiers */}
      <section id="pricing" className="py-24 border-t border-slate-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center flex flex-col items-center gap-4 mb-16">
            <h2 className="text-3xl font-outfit font-extrabold text-slate-900 tracking-tight">SaaS Business Tiers</h2>
            <p className="text-slate-500 text-sm max-w-md font-medium">
              Choose the volume tier that fits your WhatsApp operations.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Tier 1 */}
            <div className="rounded-xl border border-slate-200 bg-white p-8 flex flex-col justify-between shadow-sm">
              <div>
                <h3 className="text-lg font-bold text-slate-800 mb-2">Starter</h3>
                <div className="flex items-baseline gap-1 mb-6">
                  <span className="text-3xl font-extrabold text-slate-900">$29</span>
                  <span className="text-xs text-slate-400 font-semibold">/mo</span>
                </div>
                <ul className="flex flex-col gap-3 text-xs text-slate-500 font-medium">
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Up to 500 Monthly Sessions</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> AI Workflow Generation</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Basic Stripe Integration</li>
                </ul>
              </div>
              <Link href="/onboarding" className="mt-8 w-full py-2.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-xs font-bold text-slate-700 text-center block transition-all">
                Choose Starter
              </Link>
            </div>

            {/* Tier 2 */}
            <div className="rounded-xl border-2 border-emerald-500 bg-white p-8 flex flex-col justify-between relative shadow-lg glow-active">
              <div className="absolute top-0 right-6 -translate-y-1/2 bg-emerald-600 text-white px-3 py-0.5 rounded-full text-[9px] font-bold tracking-wider uppercase">Popular</div>
              <div>
                <h3 className="text-lg font-bold text-slate-850 mb-2">Professional</h3>
                <div className="flex items-baseline gap-1 mb-6">
                  <span className="text-3xl font-extrabold text-slate-900">$79</span>
                  <span className="text-xs text-slate-400 font-semibold">/mo</span>
                </div>
                <ul className="flex flex-col gap-3 text-xs text-slate-550 font-semibold">
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Up to 5,000 Monthly Sessions</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Dynamic Llama Refinements</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Multi-Tenant Config Settings</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Replay Timeline diagnostics</li>
                </ul>
              </div>
              <Link href="/onboarding" className="mt-8 w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-xs font-bold text-white text-center block transition-all shadow-md">
                Choose Pro
              </Link>
            </div>

            {/* Tier 3 */}
            <div className="rounded-xl border border-slate-200 bg-white p-8 flex flex-col justify-between shadow-sm">
              <div>
                <h3 className="text-lg font-bold text-slate-800 mb-2">Enterprise</h3>
                <div className="flex items-baseline gap-1 mb-6">
                  <span className="text-3xl font-extrabold text-slate-900">$249</span>
                  <span className="text-xs text-slate-400 font-semibold">/mo</span>
                </div>
                <ul className="flex flex-col gap-3 text-xs text-slate-500 font-medium">
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Unlimited Conversations</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Dedicated Llama Endpoint</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Direct n8n Docker connectors</li>
                  <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> 24/7 Traversal SLA monitoring</li>
                </ul>
              </div>
              <Link href="/onboarding" className="mt-8 w-full py-2.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-xs font-bold text-slate-700 text-center block transition-all">
                Choose Enterprise
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-24 border-t border-slate-200 bg-slate-50/50 shadow-inner">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-2xl font-outfit font-extrabold text-slate-900 tracking-tight text-center mb-12">Frequently Asked Questions</h2>
          <div className="flex flex-col gap-6 text-xs">
            <div className="p-5 rounded-xl bg-white border border-slate-200 flex flex-col gap-2 shadow-sm">
              <h4 className="text-sm font-extrabold text-slate-800">How does deterministic traversal guarantee reliability?</h4>
              <p className="text-slate-500 leading-relaxed font-medium">Unlike plain LLM agents which can trigger random outputs or get stuck in loops, FlowCore uses AI purely to compile/construct a structured workflow. The traversal itself is driven by deterministic transition machines governed by static SQLite configurations, ensuring 100% predictable executions.</p>
            </div>
            <div className="p-5 rounded-xl bg-white border border-slate-200 flex flex-col gap-2 shadow-sm">
              <h4 className="text-sm font-extrabold text-slate-800">Can I edit my workflow after AI has generated it?</h4>
              <p className="text-slate-500 leading-relaxed font-medium">Yes! FlowCore features an AI refinement chat. Simply prompt the agent (e.g. "Add a cash on delivery option") and Llama automatically updates the node and edge structures on the fly.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-md gradient-bg flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-outfit font-bold text-base text-slate-900">FlowCore Platform</span>
          </div>
          <span className="text-[11px] text-slate-400 font-semibold">© 2026 FlowCore Technologies. All rights reserved.</span>
        </div>
      </footer>
    </div>
  );
}
