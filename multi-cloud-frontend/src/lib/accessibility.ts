'use client';

import { useEffect, useState, useCallback } from 'react';

// Accessibility utilities
export class AccessibilityManager {
  private static instance: AccessibilityManager;
  private focusableElements: string[] = [
    'a[href]',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable="true"]',
  ];

  static getInstance(): AccessibilityManager {
    if (!AccessibilityManager.instance) {
      AccessibilityManager.instance = new AccessibilityManager();
    }
    return AccessibilityManager.instance;
  }

  // Focus management
  trapFocus(container: HTMLElement) {
    const focusableElements = this.getFocusableElements(container);
    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    container.addEventListener('keydown', handleTabKey);
    firstElement.focus();

    return () => {
      container.removeEventListener('keydown', handleTabKey);
    };
  }

  getFocusableElements(container: HTMLElement): HTMLElement[] {
    const selector = this.focusableElements.join(', ');
    return Array.from(container.querySelectorAll(selector)) as HTMLElement[];
  }

  // Announce to screen readers
  announce(message: string, priority: 'polite' | 'assertive' = 'polite') {
    if (typeof document === 'undefined') return;

    const announcer = document.createElement('div');
    announcer.setAttribute('aria-live', priority);
    announcer.setAttribute('aria-atomic', 'true');
    announcer.className = 'sr-only';
    announcer.textContent = message;

    document.body.appendChild(announcer);

    setTimeout(() => {
      document.body.removeChild(announcer);
    }, 1000);
  }

  // Check color contrast
  checkColorContrast(foreground: string, background: string): number {
    const getLuminance = (color: string): number => {
      const rgb = this.hexToRgb(color);
      if (!rgb) return 0;

      const [r, g, b] = [rgb.r, rgb.g, rgb.b].map(c => {
        c = c / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
      });

      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };

    const l1 = getLuminance(foreground);
    const l2 = getLuminance(background);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);

    return (lighter + 0.05) / (darker + 0.05);
  }

  private hexToRgb(hex: string): { r: number; g: number; b: number } | null {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  }

  // Keyboard navigation helpers
  handleArrowNavigation(
    event: KeyboardEvent,
    items: HTMLElement[],
    currentIndex: number,
    orientation: 'horizontal' | 'vertical' = 'vertical'
  ): number {
    const { key } = event;
    let newIndex = currentIndex;

    if (orientation === 'vertical') {
      if (key === 'ArrowDown') {
        newIndex = (currentIndex + 1) % items.length;
      } else if (key === 'ArrowUp') {
        newIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
      }
    } else {
      if (key === 'ArrowRight') {
        newIndex = (currentIndex + 1) % items.length;
      } else if (key === 'ArrowLeft') {
        newIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
      }
    }

    if (newIndex !== currentIndex) {
      event.preventDefault();
      items[newIndex]?.focus();
    }

    return newIndex;
  }

  // Check if user prefers reduced motion
  prefersReducedMotion(): boolean {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  // Check if user prefers high contrast
  prefersHighContrast(): boolean {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-contrast: high)').matches;
  }

  // Check if user is using a screen reader
  isUsingScreenReader(): boolean {
    if (typeof navigator === 'undefined') return false;
    return navigator.userAgent.includes('NVDA') || 
           navigator.userAgent.includes('JAWS') || 
           navigator.userAgent.includes('VoiceOver');
  }
}

// React hooks for accessibility
export function useAccessibility() {
  const manager = AccessibilityManager.getInstance();
  
  return {
    announce: manager.announce.bind(manager),
    trapFocus: manager.trapFocus.bind(manager),
    getFocusableElements: manager.getFocusableElements.bind(manager),
    handleArrowNavigation: manager.handleArrowNavigation.bind(manager),
    checkColorContrast: manager.checkColorContrast.bind(manager),
    prefersReducedMotion: manager.prefersReducedMotion.bind(manager),
    prefersHighContrast: manager.prefersHighContrast.bind(manager),
    isUsingScreenReader: manager.isUsingScreenReader.bind(manager),
  };
}

// Hook for focus management
export function useFocusTrap(isActive: boolean) {
  const [container, setContainer] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!container || !isActive) return;

    const manager = AccessibilityManager.getInstance();
    const cleanup = manager.trapFocus(container);

    return cleanup;
  }, [container, isActive]);

  return setContainer;
}

// Hook for keyboard navigation
export function useKeyboardNavigation(
  items: HTMLElement[],
  orientation: 'horizontal' | 'vertical' = 'vertical'
) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const manager = AccessibilityManager.getInstance();

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const newIndex = manager.handleArrowNavigation(event, items, currentIndex, orientation);
    setCurrentIndex(newIndex);
  }, [items, currentIndex, orientation, manager]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return { currentIndex, setCurrentIndex };
}

// Hook for reduced motion preference
export function useReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return prefersReducedMotion;
}

// Hook for high contrast preference
export function useHighContrast() {
  const [prefersHighContrast, setPrefersHighContrast] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-contrast: high)');
    setPrefersHighContrast(mediaQuery.matches);

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersHighContrast(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return prefersHighContrast;
}

// Hook for screen reader detection
export function useScreenReader() {
  const [isUsingScreenReader, setIsUsingScreenReader] = useState(false);

  useEffect(() => {
    const manager = AccessibilityManager.getInstance();
    setIsUsingScreenReader(manager.isUsingScreenReader());
  }, []);

  return isUsingScreenReader;
}

// ARIA helpers
export const ARIA = {
  // Generate unique IDs for ARIA relationships
  generateId: (prefix: string = 'aria'): string => {
    return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
  },

  // Common ARIA attributes
  button: (expanded?: boolean, controls?: string) => ({
    role: 'button',
    tabIndex: 0,
    ...(expanded !== undefined && { 'aria-expanded': expanded }),
    ...(controls && { 'aria-controls': controls }),
  }),

  dialog: (labelledBy?: string, describedBy?: string) => ({
    role: 'dialog',
    'aria-modal': true,
    ...(labelledBy && { 'aria-labelledby': labelledBy }),
    ...(describedBy && { 'aria-describedby': describedBy }),
  }),

  menu: (orientation: 'horizontal' | 'vertical' = 'vertical') => ({
    role: 'menu',
    'aria-orientation': orientation,
  }),

  menuItem: (disabled?: boolean) => ({
    role: 'menuitem',
    tabIndex: -1,
    ...(disabled && { 'aria-disabled': true }),
  }),

  tab: (selected: boolean, controls: string) => ({
    role: 'tab',
    'aria-selected': selected,
    'aria-controls': controls,
    tabIndex: selected ? 0 : -1,
  }),

  tabPanel: (labelledBy: string) => ({
    role: 'tabpanel',
    'aria-labelledby': labelledBy,
    tabIndex: 0,
  }),

  listbox: (multiselectable?: boolean) => ({
    role: 'listbox',
    ...(multiselectable && { 'aria-multiselectable': true }),
  }),

  option: (selected: boolean, disabled?: boolean) => ({
    role: 'option',
    'aria-selected': selected,
    ...(disabled && { 'aria-disabled': true }),
  }),
};