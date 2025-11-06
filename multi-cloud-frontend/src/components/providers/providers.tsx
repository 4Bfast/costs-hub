"use client"

import React, { useEffect } from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import { ThemeProvider } from "next-themes"
import { Toaster } from "@/components/ui/toaster"
import { AccessibilityProvider } from "@/components/providers/accessibility-provider"
import { PerformanceProvider } from "@/components/providers/performance-provider"
import { queryClient } from "@/lib/query-client"

interface ProvidersProps {
  children: React.ReactNode
}

export function Providers({ children }: ProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
        storageKey="costhub-theme"
      >
        <PerformanceProvider>
          <AccessibilityProvider>
            {children}
            <Toaster />
          </AccessibilityProvider>
        </PerformanceProvider>
      </ThemeProvider>
      {process.env.NODE_ENV === 'development' && <ReactQueryDevtools />}
    </QueryClientProvider>
  )
}