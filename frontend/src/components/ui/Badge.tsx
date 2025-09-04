import React from 'react';
import { motion, MotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

const badgeVariants = {
  default: "bg-slate-900 text-slate-50 hover:bg-slate-900/80",
  secondary: "bg-slate-100 text-slate-900 hover:bg-slate-100/80", 
  success: "bg-green-500 text-white hover:bg-green-500/80",
  warning: "bg-yellow-500 text-white hover:bg-yellow-500/80",
  destructive: "bg-red-500 text-slate-50 hover:bg-red-500/80",
  outline: "text-slate-950 border border-slate-200 hover:bg-slate-100"
};

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: keyof typeof badgeVariants;
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps & MotionProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-slate-950 focus:ring-offset-2",
          badgeVariants[variant],
          className
        )}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
        whileHover={{ scale: 1.05 }}
        {...props}
      />
    );
  }
);

Badge.displayName = "Badge";

export { Badge };
