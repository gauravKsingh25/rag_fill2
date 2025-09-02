import React from 'react';
import { motion, MotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  variant?: 'default' | 'ghost';
}

export const Input = React.forwardRef<
  HTMLInputElement,
  InputProps & MotionProps
>(({ className, type = "text", variant = "default", ...props }, ref) => {
  const inputVariants = {
    default: "border-slate-200 bg-white focus:border-slate-900 focus:ring-slate-900",
    ghost: "border-transparent bg-slate-100 focus:bg-white focus:border-slate-200",
  };

  return (
    <motion.input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border px-3 py-2 text-sm ring-offset-white file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200",
        inputVariants[variant],
        className
      )}
      ref={ref}
      whileFocus={{ scale: 1.01 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      {...props}
    />
  );
});

Input.displayName = "Input";
