import React from 'react';
import { motion, MotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
  variant?: 'default' | 'gradient' | 'animated';
}

export const Progress = React.forwardRef<
  HTMLDivElement,
  ProgressProps & MotionProps
>(({ className, value = 0, max = 100, variant = "default", ...props }, ref) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const progressVariants = {
    default: "bg-blue-600",
    gradient: "bg-gradient-to-r from-blue-500 to-purple-600",
    animated: "bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 bg-[length:200%_100%] animate-pulse",
  };

  return (
    <div
      ref={ref}
      className={cn(
        "relative h-3 w-full overflow-hidden rounded-full bg-slate-100",
        className
      )}
      {...props}
    >
      <motion.div
        className={cn("h-full transition-all duration-300", progressVariants[variant])}
        initial={{ width: 0 }}
        animate={{ width: `${percentage}%` }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      />
    </div>
  );
});

Progress.displayName = "Progress";
