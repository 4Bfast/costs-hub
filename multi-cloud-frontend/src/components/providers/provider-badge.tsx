import React from "react"
import { Badge } from "@/components/ui/badge"
import { getProviderColor } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface ProviderBadgeProps {
  provider: "aws" | "gcp" | "azure" | "multi"
  className?: string
  variant?: "default" | "outline"
}

const providerNames = {
  aws: "AWS",
  gcp: "GCP",
  azure: "Azure",
  multi: "Multi-Cloud",
}

export function ProviderBadge({ 
  provider, 
  className,
  variant = "default" 
}: ProviderBadgeProps) {
  const color = getProviderColor(provider)
  
  return (
    <Badge
      variant={variant}
      className={cn(
        "font-medium",
        variant === "default" && {
          backgroundColor: color,
          color: "white",
          borderColor: color,
        },
        variant === "outline" && {
          color: color,
          borderColor: color,
        },
        className
      )}
      style={
        variant === "default" 
          ? { backgroundColor: color, borderColor: color }
          : { color: color, borderColor: color }
      }
    >
      {providerNames[provider]}
    </Badge>
  )
}