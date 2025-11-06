"use client"

import { useEffect, useRef } from "react"
import { useAccessibility } from "@/components/providers/accessibility-provider"

/**
 * Hook for managing focus and accessibility features
 */
export function useFocusManagement() {
  const { settings } = useAccessibility()

  /**
   * Trap focus within a container element
   */
  const trapFocus = (container: HTMLElement) => {
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    const firstElement = focusableElements[0] as HTMLElement
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement.focus()
          e.preventDefault()
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement.focus()
          e.preventDefault()
        }
      }
    }

    container.addEventListener('keydown', handleTabKey)
    return () => container.removeEventListener('keydown', handleTabKey)
  }

  /**
   * Announce content to screen readers
   */
  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const announcer = document.createElement('div')
    announcer.setAttribute('aria-live', priority)
    announcer.setAttribute('aria-atomic', 'true')
    announcer.className = 'sr-only'
    announcer.textContent = message

    document.body.appendChild(announcer)
    setTimeout(() => document.body.removeChild(announcer), 1000)
  }

  /**
   * Focus the first focusable element in a container
   */
  const focusFirst = (container: HTMLElement) => {
    const focusableElement = container.querySelector(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ) as HTMLElement
    
    if (focusableElement) {
      focusableElement.focus()
    }
  }

  return {
    trapFocus,
    announce,
    focusFirst,
    settings
  }
}

/**
 * Hook for keyboard navigation
 */
export function useKeyboardNavigation() {
  const { announce } = useFocusManagement()

  /**
   * Handle arrow key navigation in a list
   */
  const handleArrowNavigation = (
    e: KeyboardEvent,
    items: HTMLElement[],
    currentIndex: number,
    onIndexChange: (index: number) => void
  ) => {
    let newIndex = currentIndex

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0
        break
      case 'ArrowUp':
        e.preventDefault()
        newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1
        break
      case 'Home':
        e.preventDefault()
        newIndex = 0
        break
      case 'End':
        e.preventDefault()
        newIndex = items.length - 1
        break
      default:
        return
    }

    onIndexChange(newIndex)
    items[newIndex]?.focus()
  }

  /**
   * Handle escape key to close modals/dropdowns
   */
  const handleEscape = (callback: () => void) => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        callback()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }

  return {
    handleArrowNavigation,
    handleEscape,
    announce
  }
}

/**
 * Hook for managing page titles and announcements
 */
export function usePageAnnouncement(title: string, description?: string) {
  const { announce } = useFocusManagement()

  useEffect(() => {
    // Update document title
    document.title = `${title} - CostsHub`

    // Announce page change to screen readers
    const message = description ? `${title}. ${description}` : title
    announce(message, 'polite')
  }, [title, description, announce])
}

/**
 * Hook for managing loading states with accessibility
 */
export function useLoadingAnnouncement() {
  const { announce } = useFocusManagement()
  const loadingRef = useRef<boolean>(false)

  const setLoading = (isLoading: boolean, message?: string) => {
    if (isLoading && !loadingRef.current) {
      announce(message || 'Loading content', 'polite')
      loadingRef.current = true
    } else if (!isLoading && loadingRef.current) {
      announce('Content loaded', 'polite')
      loadingRef.current = false
    }
  }

  return { setLoading }
}

/**
 * Hook for form accessibility
 */
export function useFormAccessibility() {
  const { announce } = useFocusManagement()

  /**
   * Announce form errors
   */
  const announceErrors = (errors: Record<string, string>) => {
    const errorCount = Object.keys(errors).length
    if (errorCount > 0) {
      const message = errorCount === 1 
        ? 'There is 1 error in the form' 
        : `There are ${errorCount} errors in the form`
      announce(message, 'assertive')
    }
  }

  /**
   * Focus the first error field
   */
  const focusFirstError = (errors: Record<string, string>) => {
    const firstErrorField = Object.keys(errors)[0]
    if (firstErrorField) {
      const element = document.getElementById(firstErrorField) || 
                    document.querySelector(`[name="${firstErrorField}"]`)
      if (element) {
        (element as HTMLElement).focus()
      }
    }
  }

  /**
   * Announce successful form submission
   */
  const announceSuccess = (message: string = 'Form submitted successfully') => {
    announce(message, 'polite')
  }

  return {
    announceErrors,
    focusFirstError,
    announceSuccess
  }
}