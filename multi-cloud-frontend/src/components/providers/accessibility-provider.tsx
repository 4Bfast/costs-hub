"use client"

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react"
import { AccessibilityManager } from "@/lib/accessibility"

interface AccessibilitySettings {
  reducedMotion: boolean
  highContrast: boolean
  fontSize: 'small' | 'medium' | 'large' | 'extra-large'
  focusVisible: boolean
  screenReaderOptimized: boolean
  keyboardNavigation: boolean
  announcements: boolean
}

interface AccessibilityContextType {
  settings: AccessibilitySettings
  updateSetting: <K extends keyof AccessibilitySettings>(
    key: K,
    value: AccessibilitySettings[K]
  ) => void
  resetSettings: () => void
  announce: (message: string, priority?: 'polite' | 'assertive') => void
  manager: AccessibilityManager
}

const defaultSettings: AccessibilitySettings = {
  reducedMotion: false,
  highContrast: false,
  fontSize: 'medium',
  focusVisible: true,
  screenReaderOptimized: false,
  keyboardNavigation: true,
  announcements: true,
}

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(undefined)

interface AccessibilityProviderProps {
  children: ReactNode
}

export function AccessibilityProvider({ children }: AccessibilityProviderProps) {
  const [settings, setSettings] = useState<AccessibilitySettings>(defaultSettings)
  const [manager] = useState(() => AccessibilityManager.getInstance())

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedSettings = localStorage.getItem('costhub-accessibility')
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings)
        setSettings({ ...defaultSettings, ...parsed })
      } catch (error) {
        console.error('Failed to parse accessibility settings:', error)
      }
    }

    // Detect system preferences
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const prefersHighContrast = window.matchMedia('(prefers-contrast: high)').matches
    const isUsingScreenReader = manager.isUsingScreenReader()

    setSettings(prev => ({
      ...prev,
      reducedMotion: prev.reducedMotion || prefersReducedMotion,
      highContrast: prev.highContrast || prefersHighContrast,
      screenReaderOptimized: prev.screenReaderOptimized || isUsingScreenReader,
    }))

    // Listen for media query changes
    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const highContrastQuery = window.matchMedia('(prefers-contrast: high)')

    const handleReducedMotionChange = (e: MediaQueryListEvent) => {
      setSettings(prev => ({ ...prev, reducedMotion: e.matches }))
    }

    const handleHighContrastChange = (e: MediaQueryListEvent) => {
      setSettings(prev => ({ ...prev, highContrast: e.matches }))
    }

    reducedMotionQuery.addEventListener('change', handleReducedMotionChange)
    highContrastQuery.addEventListener('change', handleHighContrastChange)

    return () => {
      reducedMotionQuery.removeEventListener('change', handleReducedMotionChange)
      highContrastQuery.removeEventListener('change', handleHighContrastChange)
    }
  }, [manager])

  // Apply settings to document
  useEffect(() => {
    const root = document.documentElement

    // Apply reduced motion
    if (settings.reducedMotion) {
      root.style.setProperty('--animation-duration', '0.01ms')
      root.style.setProperty('--transition-duration', '0.01ms')
    } else {
      root.style.removeProperty('--animation-duration')
      root.style.removeProperty('--transition-duration')
    }

    // Apply high contrast
    if (settings.highContrast) {
      root.classList.add('high-contrast')
    } else {
      root.classList.remove('high-contrast')
    }

    // Apply font size
    root.classList.remove('text-small', 'text-medium', 'text-large', 'text-extra-large')
    root.classList.add(`text-${settings.fontSize}`)

    // Apply focus visible
    if (settings.focusVisible) {
      root.classList.add('focus-visible-enhanced')
    } else {
      root.classList.remove('focus-visible-enhanced')
    }

    // Apply screen reader optimizations
    if (settings.screenReaderOptimized) {
      root.classList.add('screen-reader-optimized')
    } else {
      root.classList.remove('screen-reader-optimized')
    }

    // Apply keyboard navigation enhancements
    if (settings.keyboardNavigation) {
      root.classList.add('keyboard-nav-enhanced')
    } else {
      root.classList.remove('keyboard-nav-enhanced')
    }

    // Save to localStorage
    localStorage.setItem('costhub-accessibility', JSON.stringify(settings))
  }, [settings])

  const updateSetting = <K extends keyof AccessibilitySettings>(
    key: K,
    value: AccessibilitySettings[K]
  ) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  const resetSettings = () => {
    setSettings(defaultSettings)
    localStorage.removeItem('costhub-accessibility')
  }

  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (settings.announcements) {
      manager.announce(message, priority)
    }
  }

  const value: AccessibilityContextType = {
    settings,
    updateSetting,
    resetSettings,
    announce,
    manager,
  }

  return (
    <AccessibilityContext.Provider value={value}>
      {children}
    </AccessibilityContext.Provider>
  )
}

export function useAccessibility() {
  const context = useContext(AccessibilityContext)
  if (context === undefined) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider')
  }
  return context
}