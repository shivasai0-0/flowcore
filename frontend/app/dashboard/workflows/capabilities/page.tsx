'use client';

import React, { useEffect, useState } from 'react';
import { api, ModuleContract } from '@/services/api';
import { useWorkflowStore } from '@/stores/workflowStore';
import { Layers, RefreshCw, Box, ShieldAlert, Cpu } from 'lucide-react';

export default function CapabilitiesPage() {
  const { businessId } = useWorkflowStore();
  const [modules, setModules] = useState<ModuleContract[]>([]);
  const [businessType, setBusinessType] = useState<string>('restaurant');
  const [loading, setLoading] = useState(true);

  const fetchModules = async () => {
    try {
      if (businessId) {
        const bizRes = await api.getBusiness(businessId);
        if (bizRes.success && bizRes.data) {
          setBusinessType(bizRes.data.business_type || 'restaurant');
        }
      }
      const res = await api.listModules();
      if (res.success && res.data) {
        setModules(res.data || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModules();
  }, [businessId]);

  const displayModules = modules.filter(
    (mod) =>
      mod.domain === '*' ||
      mod.domain.toLowerCase() === businessType.toLowerCase()
  );

  return (
    <div className="flex-1 p-8 flex flex-col gap-6 bg-slate-50/50">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Capability Modules Registry</h2>
          <p className="text-xs text-slate-500 mt-1">Review FSM operations, functional input/output parameters, and dependency side-effects.</p>
        </div>
        <button 
          onClick={fetchModules}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
          <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin mb-2" />
          <span className="text-xs font-semibold">Loading capability contracts...</span>
        </div>
      ) : displayModules.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayModules.map((mod) => (
            <div key={mod.module_name} className="bg-white border border-slate-200 p-5 rounded-xl flex flex-col gap-4 shadow-sm hover:border-slate-350 transition-colors">
              {/* Header */}
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center">
                    <Box className="w-4.5 h-4.5 text-emerald-600" />
                  </div>
                  <div>
                    <h4 className="font-extrabold text-xs text-slate-800 font-mono leading-none">{mod.display_name}</h4>
                    <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider block mt-1">v{mod.version} • {mod.domain}</span>
                  </div>
                </div>
                <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded uppercase ${
                  mod.is_idempotent ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                }`}>
                  {mod.is_idempotent ? 'Idempotent' : 'Non-Idempotent'}
                </span>
              </div>

              {/* FSM allowed states */}
              <div className="flex flex-wrap gap-1">
                {mod.allowed_fsm_states.map((st) => (
                  <span key={st} className="text-[9px] font-bold bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">
                    {st}
                  </span>
                ))}
              </div>

              {/* Requires & Produces Context */}
              <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-150 text-[10px]">
                <div>
                  <span className="font-bold text-slate-400 uppercase text-[8px] tracking-wider block mb-1">Requires Context</span>
                  {Object.keys(mod.requires).length > 0 ? (
                    <ul className="flex flex-col gap-0.5 font-mono text-[9px] text-slate-600">
                      {Object.entries(mod.requires).map(([k, v]) => (
                        <li key={k} className="truncate" title={`${k}: ${v}`}>
                          • <strong>{k}</strong>: {v}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-400 italic">None</span>
                  )}
                </div>
                <div>
                  <span className="font-bold text-slate-400 uppercase text-[8px] tracking-wider block mb-1">Produces Context</span>
                  {Object.keys(mod.produces).length > 0 ? (
                    <ul className="flex flex-col gap-0.5 font-mono text-[9px] text-slate-600">
                      {Object.entries(mod.produces).map(([k, v]) => (
                        <li key={k} className="truncate" title={`${k}: ${v}`}>
                          • <strong>{k}</strong>: {v}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-400 italic">None</span>
                  )}
                </div>
              </div>

              {/* Side Effects & User inputs */}
              <div className="flex justify-between items-center text-[10px] text-slate-500 font-semibold border-t border-slate-100 pt-3">
                <div className="flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
                  <span>
                    {mod.side_effects.length > 0 
                      ? `${mod.side_effects.length} side effect(s)`
                      : 'Zero Side Effects'}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Cpu className="w-3.5 h-3.5 text-slate-400" />
                  <span>{mod.expects_user_input ? 'User Input Expected' : 'Auto transition'}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-12 text-center text-xs text-slate-400 font-semibold border border-dashed border-slate-200 rounded-xl bg-white shadow-sm flex flex-col items-center gap-2">
          <Layers className="w-8 h-8 text-slate-300" />
          No capability contracts registered in the database.
        </div>
      )}
    </div>
  );
}
