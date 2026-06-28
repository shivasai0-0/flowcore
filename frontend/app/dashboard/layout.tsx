'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useWorkflowStore } from '@/stores/workflowStore';
import { useWorkspace } from '@/context/workspace-context';
import { 
  LayoutDashboard, 
  Sparkles, 
  Settings, 
  Radio, 
  Server,
  Zap,
  Loader2,
  Users,
  BarChart3,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  ClipboardList,
  Briefcase,
  ShieldAlert,
  FileText,
  Wrench,
  PlayCircle,
  Calendar,
  Play
} from 'lucide-react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { businessName, businessId } = useWorkflowStore();
  const { activeBusinessId, activeBusinessName, activeBusinessType, businesses, setActiveBusiness } = useWorkspace();
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [mounted, setMounted] = useState(false);
  
  // State to track expanded nested menus
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    Operations: true,
    Workflows: true,
    Analytics: true,
    Business: true,
  });

  const [isOwnerMode, setIsOwnerMode] = useState<boolean>(true);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem('flowcore_role_mode');
    if (saved) {
      setIsOwnerMode(saved === 'owner');
    }
  }, []);

  const handleToggleMode = (mode: 'owner' | 'worker') => {
    setIsOwnerMode(mode === 'owner');
    localStorage.setItem('flowcore_role_mode', mode);
  };

  useEffect(() => {
    if (mounted && !businessId) {
      router.push('/login');
    }
  }, [mounted, businessId, router]);

  useEffect(() => {
    // Check FastAPI health
    const checkHealth = async () => {
      try {
        const res = await fetch('http://localhost:8000/');
        if (res.ok) {
          setBackendOnline(true);
        } else {
          setBackendOnline(false);
        }
      } catch {
        setBackendOnline(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const toggleGroup = (groupName: string) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupName]: !prev[groupName]
    }));
  };

  const navGroups = isOwnerMode ? [
    { name: 'Overview', href: '/dashboard', icon: LayoutDashboard },
    {
      name: 'Operations',
      icon: Server,
      subItems: [
        { name: 'Orders', href: '/dashboard/operations/orders' },
        { name: 'Bookings', href: '/dashboard/operations/bookings' },
        { name: 'Deliveries', href: '/dashboard/operations/deliveries' },
        { name: 'Payments', href: '/dashboard/operations/payments' },
        { name: 'Support', href: '/dashboard/operations/support' },
      ]
    },
    { name: 'Customers', href: '/dashboard/customers', icon: Users },
    { name: 'Worker Registry', href: '/dashboard/workers', icon: Briefcase },
    { name: 'Tasks Registry', href: '/dashboard/tasks', icon: ClipboardList },
    { name: 'Approval Queue', href: '/dashboard/approvals', icon: ShieldAlert },
    { name: 'Reports Center', href: '/dashboard/reports', icon: FileText },
    {
      name: 'Workflows',
      icon: Radio,
      subItems: [
        { name: 'Portfolio', href: '/dashboard/workflows/portfolio' },
        { name: 'Events', href: '/dashboard/events' },
        { name: 'Capabilities', href: '/dashboard/workflows/capabilities' },
      ]
    },
    {
      name: 'Analytics',
      icon: BarChart3,
      subItems: [
        { name: 'Revenue', href: '/dashboard/analytics/revenue' },
        { name: 'Customers', href: '/dashboard/analytics/customers' },
        { name: 'Conversions', href: '/dashboard/analytics/conversions' },
        { name: 'Workflow Analytics', href: '/dashboard/analytics/workflows' },
      ]
    },
    {
      name: 'Business',
      icon: Settings,
      subItems: [
        { name: 'Catalog', href: '/dashboard/business/catalog' },
        { name: 'Providers', href: '/dashboard/business/providers' },
        { name: 'Branding', href: '/dashboard/business/branding' },
      ]
    },
    { name: 'AI Builder', href: '/dashboard/builder', icon: Sparkles },
    { name: 'Simulator', href: '/dashboard/runtime', icon: Play },
    { name: 'Tools Center', href: '/dashboard/tools', icon: Wrench },
    { name: 'Generation Jobs', href: '/dashboard/generation-jobs', icon: PlayCircle },
    { name: 'Developer Debug', href: '/dashboard/developer/debug', icon: ShieldCheck },
    { name: 'Settings', href: '/dashboard/settings', icon: Settings },
  ] : [
    { name: 'Task Dashboard', href: '/dashboard/worker', icon: ClipboardList },
    { name: 'Availability Calendar', href: '/dashboard/worker/availability', icon: Calendar },
    { name: 'Settings', href: '/dashboard/settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-slate-50 text-slate-800 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-200 bg-white flex flex-col justify-between shrink-0 overflow-y-auto">
        <div className="flex flex-col h-full justify-between">
          <div>
            {/* Logo */}
            <div className="p-5 border-b border-slate-100 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center glow-active shrink-0">
                <Zap className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="font-outfit font-bold text-base leading-none text-slate-900 tracking-wide">FlowCore</h1>
                <span className="text-[9px] text-emerald-600 font-bold tracking-widest uppercase">OS v2.5</span>
              </div>
            </div>

            {/* Active Business Identification — with dropdown workspace switcher */}
            {mounted && (activeBusinessName || businessName) && (
              <div className="mx-4 my-3 p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1.5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">Active Workspace</span>
                  <span className="text-[8px] bg-emerald-50 text-emerald-700 font-bold px-1.5 py-0.5 rounded border border-emerald-200/50">
                    {(() => {
                      const t = activeBusinessType || '';
                      const mapping: Record<string, string> = {
                        restaurant: 'Restaurant', hospital: 'Hospital', salon: 'Salon',
                        supermarket: 'Supermarket', education: 'Education', real_estate: 'Real Estate'
                      };
                      return mapping[t.toLowerCase()] || (t ? t.toUpperCase() : 'SYSTEM');
                    })()}
                  </span>
                </div>
                {businesses.length > 0 ? (
                  <div className="relative">
                    <select
                      value={activeBusinessId || ''}
                      onChange={(e) => setActiveBusiness(e.target.value)}
                      className="w-full bg-white border border-slate-200 rounded-md px-2 py-1 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer appearance-none pr-6 shadow-sm"
                    >
                      {businesses.map((biz) => (
                        <option key={biz.id} value={biz.id}>
                          {biz.name}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
                  </div>
                ) : (
                  <span className="text-xs font-semibold text-slate-800 truncate">{activeBusinessName || businessName}</span>
                )}
                <span className="text-[9px] text-slate-400 font-mono truncate" title={activeBusinessId || businessId || ''}>
                  {(activeBusinessId || businessId || '').slice(0, 24)}{(activeBusinessId || businessId || '').length > 24 ? '…' : ''}
                </span>
              </div>
            )}

            {/* Role-Based Mode Toggle */}
            {mounted && (
              <div className="mx-4 my-2 p-1 rounded-lg bg-slate-100/80 border border-slate-200 flex gap-1">
                <button
                  onClick={() => { handleToggleMode('owner'); router.push('/dashboard'); }}
                  className={`flex-1 text-center py-1 rounded text-[10px] font-bold transition-all cursor-pointer ${
                    isOwnerMode 
                      ? 'bg-white text-emerald-700 shadow-sm border border-slate-200/50' 
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Owner
                </button>
                <button
                  onClick={() => { handleToggleMode('worker'); router.push('/dashboard/worker'); }}
                  className={`flex-1 text-center py-1 rounded text-[10px] font-bold transition-all cursor-pointer ${
                    !isOwnerMode 
                      ? 'bg-white text-emerald-700 shadow-sm border border-slate-200/50' 
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Worker
                </button>
              </div>
            )}

            {/* Nested Sidebar Navigation */}
            <nav className="px-3 py-2 flex flex-col gap-1 overflow-y-auto">
              {navGroups.map((group) => {
                const Icon = group.icon;
                
                if (group.subItems) {
                  const isExpanded = !!expandedGroups[group.name];
                  const hasActiveChild = group.subItems.some(sub => pathname === sub.href);
                  
                  return (
                    <div key={group.name} className="flex flex-col gap-0.5">
                      <button
                        onClick={() => toggleGroup(group.name)}
                        className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors text-left ${
                          hasActiveChild 
                            ? 'text-emerald-700 bg-slate-100/50' 
                            : 'text-slate-400 hover:text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <Icon className={`w-3.5 h-3.5 ${hasActiveChild ? 'text-emerald-600' : 'text-slate-400'}`} />
                          <span>{group.name}</span>
                        </div>
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                        )}
                      </button>
                      
                      {isExpanded && (
                        <div className="pl-6 pr-1 py-1 flex flex-col gap-1 border-l border-slate-100 ml-5">
                          {group.subItems.map((sub) => {
                            const isSubActive = pathname === sub.href;
                            return (
                              <Link
                                key={sub.href}
                                href={sub.href}
                                className={`block px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                                  isSubActive
                                    ? 'bg-emerald-50 text-emerald-700 font-bold border-l-2 border-emerald-500 pl-2'
                                    : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100/60'
                                }`}
                              >
                                {sub.name}
                              </Link>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                }

                // Simple flat link
                const isActive = pathname === group.href;
                return (
                  <Link
                    key={group.href}
                    href={group.href}
                    className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${
                      isActive
                        ? 'bg-emerald-50 text-emerald-700 border-l-2 border-emerald-500 pl-2.5'
                        : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-emerald-600' : 'text-slate-400'}`} />
                    <span>{group.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Footer/Health Indicator */}
          <div className="p-4 border-t border-slate-100 bg-white">
            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
              <div className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-[10px] font-bold text-slate-500">FastAPI Node</span>
              </div>
              <div className="flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${
                  backendOnline === null ? 'bg-amber-500 animate-pulse' :
                  backendOnline ? 'bg-emerald-500 glow-active' : 'bg-rose-500 animate-pulse'
                }`} />
                <span className="text-[9px] font-bold text-slate-500">
                  {backendOnline === null ? 'PING' :
                   backendOnline ? 'ONLINE' : 'OFFLINE'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        {mounted ? (
          children
        ) : (
          <div className="flex-1 flex items-center justify-center text-center p-6 flex-col gap-2">
            <Loader2 className="w-6 h-6 text-emerald-600 animate-spin" />
            <p className="text-xs text-slate-400 font-semibold">Resolving session workspace...</p>
          </div>
        )}
      </main>
    </div>
  );
}
