import React from "react"
import { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface PageHeaderProps {
  title: string
  description?: string
  icon?: LucideIcon
  children?: React.ReactNode
  actions?: React.ReactNode
  className?: string
}

export function PageHeader({
  title,
  description,
  icon: Icon,
  children,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between pb-6", className)}>
      <div className="space-y-1">
        <div className="flex items-center space-x-3">
          {Icon && (
            <div className="p-2 bg-primary/10 rounded-lg">
              <Icon className="h-6 w-6 text-primary" />
            </div>
          )}
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            {title}
          </h1>
        </div>
        {description && (
          <p className="text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {(children || actions) && (
        <div className="flex items-center space-x-2">
          {actions || children}
        </div>
      )}
    </div>
  )
}