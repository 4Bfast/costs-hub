import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'shimmer' | 'wave';
  speed?: 'slow' | 'normal' | 'fast';
}

function Skeleton({ 
  className, 
  variant = 'default',
  speed = 'normal',
  ...props 
}: SkeletonProps) {
  const speedClasses = {
    slow: 'animate-pulse [animation-duration:2s]',
    normal: 'animate-pulse',
    fast: 'animate-pulse [animation-duration:0.8s]',
  };

  const variantClasses = {
    default: 'bg-muted',
    shimmer: 'bg-gradient-to-r from-muted via-muted/50 to-muted bg-[length:200%_100%] animate-shimmer',
    wave: 'bg-muted relative overflow-hidden before:absolute before:inset-0 before:-translate-x-full before:animate-wave before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent',
  };

  return (
    <div
      className={cn(
        "rounded-md",
        speedClasses[speed],
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}

// Chart skeleton component
function ChartSkeleton({ height = "300px" }: { height?: string }) {
  return (
    <div className="space-y-4" style={{ height }}>
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-8 w-24" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
      <div className="flex-1 flex items-end space-x-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton
            key={i}
            className="flex-1"
            style={{ height: `${Math.random() * 100 + 50}px` }}
          />
        ))}
      </div>
    </div>
  );
}

// Table skeleton component
function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      <div className="flex space-x-4">
        <Skeleton className="h-10 flex-1" />
        <Skeleton className="h-10 flex-1" />
        <Skeleton className="h-10 flex-1" />
        <Skeleton className="h-10 w-24" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex space-x-4">
          <Skeleton className="h-8 flex-1" />
          <Skeleton className="h-8 flex-1" />
          <Skeleton className="h-8 flex-1" />
          <Skeleton className="h-8 w-24" />
        </div>
      ))}
    </div>
  );
}

// Card skeleton component
function CardSkeleton() {
  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-32" />
        </div>
        <Skeleton className="h-12 w-12 rounded-lg" />
      </div>
      <div className="flex items-center space-x-2">
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-20" />
      </div>
    </div>
  );
}

// Page skeleton component
function PageSkeleton() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="flex space-x-3">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 w-40" />
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="border rounded-lg">
            <CardSkeleton />
          </div>
        ))}
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="border rounded-lg p-6">
          <ChartSkeleton />
        </div>
        <div className="border rounded-lg p-6">
          <ChartSkeleton />
        </div>
      </div>
    </div>
  );
}

// Enhanced loading states with better UX
function SkeletonSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <div className="flex items-center justify-center">
      <div className={cn(
        'animate-spin rounded-full border-2 border-muted border-t-primary',
        sizeClasses[size]
      )} />
    </div>
  );
}

// Skeleton with content hints
function SkeletonText({ 
  lines = 1, 
  className,
  variant = 'default' 
}: { 
  lines?: number; 
  className?: string;
  variant?: 'default' | 'shimmer' | 'wave';
}) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          variant={variant}
          className={cn(
            'h-4',
            i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'
          )}
        />
      ))}
    </div>
  );
}

// Progressive loading skeleton
function ProgressiveSkeleton({ 
  stage = 1,
  totalStages = 3,
  className 
}: { 
  stage?: number;
  totalStages?: number;
  className?: string;
}) {
  return (
    <div className={cn('space-y-4', className)}>
      {/* Stage 1: Basic structure */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-32" variant="shimmer" />
        <Skeleton className="h-8 w-24" variant="shimmer" />
      </div>
      
      {/* Stage 2: Content areas */}
      {stage >= 2 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-32" variant="shimmer" />
          <Skeleton className="h-32" variant="shimmer" />
        </div>
      )}
      
      {/* Stage 3: Detailed content */}
      {stage >= 3 && (
        <div className="space-y-2">
          <SkeletonText lines={3} variant="shimmer" />
        </div>
      )}
      
      {/* Progress indicator */}
      <div className="flex space-x-1">
        {Array.from({ length: totalStages }).map((_, i) => (
          <div
            key={i}
            className={cn(
              'h-1 w-8 rounded-full transition-colors',
              i < stage ? 'bg-primary' : 'bg-muted'
            )}
          />
        ))}
      </div>
    </div>
  );
}

export { 
  Skeleton, 
  SkeletonSpinner,
  SkeletonText,
  ProgressiveSkeleton,
  ChartSkeleton, 
  TableSkeleton, 
  CardSkeleton, 
  PageSkeleton 
};