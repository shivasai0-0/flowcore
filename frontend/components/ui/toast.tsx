import React from 'react';
import { CheckCircle, XCircle, AlertCircle, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
}

interface ToastProps {
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  onClose: () => void;
}

export const Toast: React.FC<ToastProps> = ({ message, type, onClose }) => {
  const styles = {
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    error: 'bg-rose-50 border-rose-200 text-rose-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
  };

  const icons = {
    success: <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />,
    error: <XCircle className="w-4 h-4 text-rose-600 shrink-0" />,
    warning: <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />,
    info: <AlertCircle className="w-4 h-4 text-blue-600 shrink-0" />,
  };

  return (
    <div className={`flex items-start gap-2.5 px-4 py-3 rounded-xl border shadow-lg text-xs font-bold transition-all duration-300 animate-slide-in ${styles[type]}`}>
      {icons[type]}
      <span className="flex-1 leading-normal">{message}</span>
      <button 
        onClick={onClose} 
        className="text-slate-400 hover:text-slate-600 p-0.5 rounded cursor-pointer shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
