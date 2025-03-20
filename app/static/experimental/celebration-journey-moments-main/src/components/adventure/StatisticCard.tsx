
import React from 'react';
import { cn } from '@/lib/utils';

interface StatisticCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  className?: string;
  delay?: number;
}

const StatisticCard: React.FC<StatisticCardProps> = ({ 
  title, 
  value, 
  icon,
  className,
  delay = 0
}) => {
  return (
    <div 
      className={cn(
        "glass-card p-4 rounded-xl flex items-center animate-fade-in-up",
        className
      )}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="mr-4 rounded-full bg-primary/10 p-3">
        {icon}
      </div>
      <div>
        <p className="text-sm text-gray-500 font-medium">{title}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
    </div>
  );
};

export default StatisticCard;
