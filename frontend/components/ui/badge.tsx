import React from 'react';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'active' | 'draft' | 'deprecated';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  className = '',
  ...props
}) => {
  const baseStyle = 'inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-extrabold uppercase tracking-wider border select-none';
  
  const variants = {
    default: 'bg-slate-100 text-slate-700 border-slate-200',
    success: 'bg-emerald-50 text-emerald-800 border-emerald-250',
    warning: 'bg-amber-50 text-amber-800 border-amber-200',
    danger: 'bg-rose-50 text-rose-800 border-rose-200',
    info: 'bg-blue-50 text-blue-800 border-blue-200',
    active: 'bg-emerald-600 text-white border-emerald-600 font-bold',
    draft: 'bg-slate-50 text-slate-600 border-slate-200',
    deprecated: 'bg-zinc-100 text-zinc-550 border-zinc-200',
  };

  const currentVariant = variants[variant];

  return (
    <span className={`${baseStyle} ${currentVariant} ${className}`} {...props}>
      {children}
    </span>
  );
};
