'use client';

import { useBreakpoint } from '@/lib/touch';
import { useAccessibility } from '@/components/providers/accessibility-provider';
import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface MobileOptimizedProps {
  children: ReactNode;
  className?: string;
  mobileClassName?: string;
  tabletClassName?: string;
  desktopClassName?: string;
  touchOptimized?: boolean;
}

export function MobileOptimized({
  children,
  className,
  mobileClassName,
  tabletClassName,
  desktopClassName,
  touchOptimized = true,
}: MobileOptimizedProps) {
  const { breakpoint, isTouchDevice } = useBreakpoint();
  const { settings } = useAccessibility();

  const responsiveClassName = cn(
    className,
    {
      [mobileClassName || '']: breakpoint === 'mobile',
      [tabletClassName || '']: breakpoint === 'tablet',
      [desktopClassName || '']: breakpoint === 'desktop',
      'touch-optimized': touchOptimized && isTouchDevice,
      'keyboard-optimized': settings.keyboardNavigation,
      'screen-reader-optimized': settings.screenReaderOptimized,
    }
  );

  return <div className={responsiveClassName}>{children}</div>;
}

// Touch-optimized button component
interface TouchButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  touchOptimized?: boolean;
}

export function TouchButton({
  children,
  className,
  variant = 'primary',
  size = 'md',
  touchOptimized = true,
  ...props
}: TouchButtonProps) {
  const { isTouchDevice } = useBreakpoint();
  const { settings } = useAccessibility();

  const baseClasses = cn(
    'inline-flex items-center justify-center rounded-md font-medium transition-colors',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:opacity-50',
    {
      // Variant styles
      'bg-primary text-primary-foreground hover:bg-primary/90': variant === 'primary',
      'bg-secondary text-secondary-foreground hover:bg-secondary/80': variant === 'secondary',
      'border border-input bg-background hover:bg-accent hover:text-accent-foreground': variant === 'outline',
      'hover:bg-accent hover:text-accent-foreground': variant === 'ghost',
      
      // Size styles - enhanced for touch
      'h-9 px-3 text-sm': size === 'sm' && !touchOptimized,
      'h-10 px-4 py-2': size === 'md' && !touchOptimized,
      'h-11 px-8': size === 'lg' && !touchOptimized,
      
      // Touch-optimized sizes (minimum 44px touch target)
      'h-11 px-4 text-sm': size === 'sm' && touchOptimized && isTouchDevice,
      'h-12 px-6 py-3': size === 'md' && touchOptimized && isTouchDevice,
      'h-14 px-8': size === 'lg' && touchOptimized && isTouchDevice,
      
      // Accessibility enhancements
      'ring-4 ring-ring ring-offset-2': settings.focusVisible,
    },
    className
  );

  return (
    <button className={baseClasses} {...props}>
      {children}
    </button>
  );
}

// Mobile-optimized card component
interface MobileCardProps {
  children: ReactNode;
  className?: string;
  padding?: 'sm' | 'md' | 'lg';
  interactive?: boolean;
}

export function MobileCard({
  children,
  className,
  padding = 'md',
  interactive = false,
}: MobileCardProps) {
  const { breakpoint } = useBreakpoint();

  const cardClasses = cn(
    'rounded-lg border bg-card text-card-foreground shadow-sm',
    {
      // Responsive padding
      'p-3': padding === 'sm' && breakpoint === 'mobile',
      'p-4': (padding === 'sm' && breakpoint !== 'mobile') || (padding === 'md' && breakpoint === 'mobile'),
      'p-6': (padding === 'md' && breakpoint !== 'mobile') || (padding === 'lg' && breakpoint === 'mobile'),
      'p-8': padding === 'lg' && breakpoint !== 'mobile',
      
      // Interactive states
      'cursor-pointer hover:shadow-md transition-shadow': interactive,
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring': interactive,
    },
    className
  );

  const Component = interactive ? 'button' : 'div';

  return <Component className={cardClasses}>{children}</Component>;
}

// Mobile-optimized input component
interface MobileInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  touchOptimized?: boolean;
}

export function MobileInput({
  label,
  error,
  className,
  touchOptimized = true,
  ...props
}: MobileInputProps) {
  const { isTouchDevice } = useBreakpoint();
  const { settings } = useAccessibility();

  const inputClasses = cn(
    'flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm',
    'ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium',
    'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2',
    'focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
    {
      // Touch-optimized height
      'h-12': touchOptimized && isTouchDevice,
      'h-10': !touchOptimized || !isTouchDevice,
      
      // Error state
      'border-destructive focus-visible:ring-destructive': error,
      
      // Accessibility enhancements
      'text-lg': settings.fontSize === 'large' || settings.fontSize === 'extra-large',
    },
    className
  );

  return (
    <div className="space-y-2">
      {label && (
        <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
          {label}
        </label>
      )}
      <input className={inputClasses} {...props} />
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

// Mobile-optimized navigation component
interface MobileNavProps {
  children: ReactNode;
  orientation?: 'horizontal' | 'vertical';
  className?: string;
}

export function MobileNav({
  children,
  orientation = 'horizontal',
  className,
}: MobileNavProps) {
  const { breakpoint } = useBreakpoint();

  const navClasses = cn(
    'flex',
    {
      // Responsive orientation
      'flex-col space-y-1': orientation === 'vertical' || breakpoint === 'mobile',
      'flex-row space-x-1': orientation === 'horizontal' && breakpoint !== 'mobile',
      
      // Mobile-specific styles
      'w-full': breakpoint === 'mobile',
      'overflow-x-auto': orientation === 'horizontal' && breakpoint === 'mobile',
    },
    className
  );

  return (
    <nav className={navClasses} role="navigation">
      {children}
    </nav>
  );
}

// Mobile-optimized table component
interface MobileTableProps {
  children: ReactNode;
  className?: string;
  stackOnMobile?: boolean;
}

export function MobileTable({
  children,
  className,
  stackOnMobile = true,
}: MobileTableProps) {
  const { breakpoint } = useBreakpoint();

  if (stackOnMobile && breakpoint === 'mobile') {
    return (
      <div className={cn('space-y-4', className)}>
        {children}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className={cn('w-full', className)}>
        {children}
      </table>
    </div>
  );
}