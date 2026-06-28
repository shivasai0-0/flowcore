'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, BusinessListItem } from '../services/api';

import { useWorkflowStore } from '@/stores/workflowStore';

interface WorkspaceContextType {
  activeBusinessId: string | null;
  activeBusinessName: string | null;
  activeBusinessType: string | null;
  businesses: BusinessListItem[];
  setActiveBusiness: (id: string) => Promise<void>;
  loading: boolean;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeBusinessId, setActiveBusinessId] = useState<string | null>(null);
  const [activeBusinessName, setActiveBusinessName] = useState<string | null>(null);
  const [activeBusinessType, setActiveBusinessType] = useState<string | null>(null);
  const [businesses, setBusinesses] = useState<BusinessListItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Load businesses and restore selected workspace
  useEffect(() => {
    async function loadWorkspaceData() {
      try {
        const res = await api.listBusinesses();
        if (res.success && res.data && res.data.length > 0) {
          setBusinesses(res.data);
          
          let savedId = localStorage.getItem('flowcore_active_business_id');
          // Fallback to the first business if none saved or saved ID is invalid
          let active = res.data.find(b => b.id === savedId);
          if (!active) {
            active = res.data[0];
            savedId = active.id;
            localStorage.setItem('flowcore_active_business_id', savedId);
          }
          
          setActiveBusinessId(active.id);
          setActiveBusinessName(active.name);
          setActiveBusinessType(active.business_type);
          
          // Sync with backend active-dev-workspace context
          await api.setActiveDevWorkspace(active.id);

          // Sync with workflowStore if needed
          const currentStoreBizId = useWorkflowStore.getState().businessId;
          if (currentStoreBizId !== active.id) {
            await useWorkflowStore.getState().loginBusiness(active.id);
          }
        }
      } catch (err) {
        console.error('Failed to load workspace data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadWorkspaceData();
  }, []);

  const setActiveBusiness = async (id: string) => {
    const selected = businesses.find(b => b.id === id);
    if (!selected) return;

    try {
      setLoading(true);
      // Update backend active dev workspace
      await api.setActiveDevWorkspace(id);
      
      // Update local state and localStorage
      localStorage.setItem('flowcore_active_business_id', id);
      setActiveBusinessId(selected.id);
      setActiveBusinessName(selected.name);
      setActiveBusinessType(selected.business_type);

      // Sync with workflowStore
      await useWorkflowStore.getState().loginBusiness(id);
      
      // Force reload or state trigger (refresh the window to force re-render components matching new headers)
      if (typeof window !== 'undefined') {
        window.location.reload();
      }
    } catch (err) {
      console.error('Failed to switch workspace:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <WorkspaceContext.Provider
      value={{
        activeBusinessId,
        activeBusinessName,
        activeBusinessType,
        businesses,
        setActiveBusiness,
        loading,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (context === undefined) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
};
