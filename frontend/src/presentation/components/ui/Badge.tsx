import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'income' | 'expense' | 'transfer' | 'paid' | 'pending';
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'expense' }) => {
  let variantClass = 'badge-type-despesa';

  if (variant === 'income') variantClass = 'badge-type-receita';
  else if (variant === 'transfer') variantClass = 'badge-type-transferência';
  else if (variant === 'paid') variantClass = 'badge-status-paid';
  else if (variant === 'pending') variantClass = 'badge-status-pending';

  return <span className={`badge ${variantClass}`}>{children}</span>;
};
