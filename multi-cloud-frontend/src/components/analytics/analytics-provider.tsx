/**
 * Analytics Provider Component
 * Provides analytics context and automatic tracking
 */

'use client'

import { createContext, useContext, useEffect, ReactNode } from 'react'
import { usePathname } from 'next/navigation'

interface AnalyticsContextType {
  trackEvent: (eventName: string, properties?: Record<string, any>) => void
  trackUserInteraction: (action: string, element?: string, properties?: Record<string, any>) => void
  trackPerformance: (name: string, duration: number, properties?: Record<string, any>) => void
  trackConversion: (event: string, value?: number, properties?: Record<string, any>) => void
}

const AnalyticsContext = createContext<AnalyticsContextType | undefined>(undefined)

interface AnalyticsProviderProps {
  children: ReactNode
}

export function AnalyticsProvider({ children }: AnalyticsProviderProps) {
  const pathname = usePathname()

  // Track page views on route changes (simplified)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      console.log('Page view:', pathname)
    }
  }, [pathname])

  const contextValue: AnalyticsContextType = {
    trackEvent: (eventName: string, properties?: Record<string, any>) => {
      if (typeof window !== 'undefined') {
        console.log('Track event:', eventName, properties)
      }
    },
    trackUserInteraction: (action: string, element?: string, properties?: Record<string, any>) => {
      if (typeof window !== 'undefined') {
        console.log('Track interaction:', action, element, properties)
      }
    },
    trackPerformance: (name: string, duration: number, properties?: Record<string, any>) => {
      if (typeof window !== 'undefined') {
        console.log('Track performance:', name, duration, properties)
      }
    },
    trackConversion: (event: string, value?: number, properties?: Record<string, any>) => {
      if (typeof window !== 'undefined') {
        console.log('Track conversion:', event, value, properties)
      }
    },
  }

  return (
    <AnalyticsContext.Provider value={contextValue}>
      {children}
    </AnalyticsContext.Provider>
  )
}

export function useAnalytics() {
  const context = useContext(AnalyticsContext)
  if (context === undefined) {
    throw new Error('useAnalytics must be used within an AnalyticsProvider')
  }
  return context
}

// HOC for automatic interaction tracking
export function withAnalytics<T extends Record<string, any>>(
  Component: React.ComponentType<T>,
  eventName?: string
) {
  return function AnalyticsWrappedComponent(props: T) {
    const { trackUserInteraction } = useAnalytics()

    const handleClick = (event: React.MouseEvent) => {
      const element = event.currentTarget
      const elementName = element.getAttribute('data-analytics-name') || 
                         element.textContent || 
                         eventName || 
                         'unknown'
      
      trackUserInteraction('click', elementName, {
        componentName: Component.displayName || Component.name,
        ...props,
      })

      // Call original onClick if it exists
      if (props.onClick) {
        props.onClick(event)
      }
    }

    return <Component {...props} onClick={handleClick} />
  }
}