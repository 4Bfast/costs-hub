import React from "react"
import { Cloud, Database, Server } from "lucide-react"
import { cn } from "@/lib/utils"
import { getProviderColor } from "@/lib/utils"

interface ProviderIconProps {
  provider: "aws" | "gcp" | "azure" | "multi"
  size?: "sm" | "md" | "lg"
  className?: string
}

const sizeClasses = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
  lg: "h-8 w-8",
}

const providerIcons = {
  aws: Server,
  gcp: Database,
  azure: Cloud,
  multi: Cloud,
}

export function ProviderIcon({ 
  provider, 
  size = "md", 
  className 
}: ProviderIconProps) {
  const Icon = providerIcons[provider]
  const color = getProviderColor(provider)
  
  return (
    <Icon
      className={cn(sizeClasses[size], className)}
      style={{ color }}
    />
  )
}