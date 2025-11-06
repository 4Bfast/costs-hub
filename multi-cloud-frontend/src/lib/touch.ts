'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

// Touch gesture types
export interface TouchGesture {
  type: 'tap' | 'double-tap' | 'long-press' | 'swipe' | 'pinch' | 'pan';
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  deltaX: number;
  deltaY: number;
  distance: number;
  duration: number;
  direction?: 'up' | 'down' | 'left' | 'right';
  scale?: number;
}

export interface TouchOptions {
  tapThreshold?: number;
  longPressDelay?: number;
  swipeThreshold?: number;
  doubleTapDelay?: number;
  preventScroll?: boolean;
}

// Touch manager class
export class TouchManager {
  private element: HTMLElement;
  private options: Required<TouchOptions>;
  private startTime: number = 0;
  private startX: number = 0;
  private startY: number = 0;
  private lastTapTime: number = 0;
  private longPressTimer: NodeJS.Timeout | null = null;
  private initialDistance: number = 0;
  private initialScale: number = 1;

  constructor(element: HTMLElement, options: TouchOptions = {}) {
    this.element = element;
    this.options = {
      tapThreshold: 10,
      longPressDelay: 500,
      swipeThreshold: 50,
      doubleTapDelay: 300,
      preventScroll: false,
      ...options,
    };

    this.init();
  }

  private init() {
    this.element.addEventListener('touchstart', this.handleTouchStart, { passive: !this.options.preventScroll });
    this.element.addEventListener('touchmove', this.handleTouchMove, { passive: !this.options.preventScroll });
    this.element.addEventListener('touchend', this.handleTouchEnd, { passive: true });
    this.element.addEventListener('touchcancel', this.handleTouchCancel, { passive: true });
  }

  private handleTouchStart = (e: TouchEvent) => {
    if (this.options.preventScroll) {
      e.preventDefault();
    }

    const touch = e.touches[0];
    this.startTime = Date.now();
    this.startX = touch.clientX;
    this.startY = touch.clientY;

    // Handle multi-touch for pinch gestures
    if (e.touches.length === 2) {
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      this.initialDistance = this.getDistance(touch1, touch2);
    }

    // Set up long press timer
    this.longPressTimer = setTimeout(() => {
      this.dispatchGesture({
        type: 'long-press',
        startX: this.startX,
        startY: this.startY,
        endX: this.startX,
        endY: this.startY,
        deltaX: 0,
        deltaY: 0,
        distance: 0,
        duration: Date.now() - this.startTime,
      });
    }, this.options.longPressDelay);
  };

  private handleTouchMove = (e: TouchEvent) => {
    if (this.options.preventScroll) {
      e.preventDefault();
    }

    const touch = e.touches[0];
    const deltaX = touch.clientX - this.startX;
    const deltaY = touch.clientY - this.startY;
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

    // Cancel long press if moved too much
    if (distance > this.options.tapThreshold && this.longPressTimer) {
      clearTimeout(this.longPressTimer);
      this.longPressTimer = null;
    }

    // Handle pinch gesture
    if (e.touches.length === 2) {
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const currentDistance = this.getDistance(touch1, touch2);
      const scale = currentDistance / this.initialDistance;

      this.dispatchGesture({
        type: 'pinch',
        startX: this.startX,
        startY: this.startY,
        endX: touch.clientX,
        endY: touch.clientY,
        deltaX,
        deltaY,
        distance,
        duration: Date.now() - this.startTime,
        scale,
      });
    }

    // Handle pan gesture
    if (distance > this.options.tapThreshold) {
      this.dispatchGesture({
        type: 'pan',
        startX: this.startX,
        startY: this.startY,
        endX: touch.clientX,
        endY: touch.clientY,
        deltaX,
        deltaY,
        distance,
        duration: Date.now() - this.startTime,
      });
    }
  };

  private handleTouchEnd = (e: TouchEvent) => {
    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer);
      this.longPressTimer = null;
    }

    const touch = e.changedTouches[0];
    const endTime = Date.now();
    const duration = endTime - this.startTime;
    const deltaX = touch.clientX - this.startX;
    const deltaY = touch.clientY - this.startY;
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

    // Determine gesture type
    if (distance < this.options.tapThreshold) {
      // Check for double tap
      if (endTime - this.lastTapTime < this.options.doubleTapDelay) {
        this.dispatchGesture({
          type: 'double-tap',
          startX: this.startX,
          startY: this.startY,
          endX: touch.clientX,
          endY: touch.clientY,
          deltaX,
          deltaY,
          distance,
          duration,
        });
      } else {
        this.dispatchGesture({
          type: 'tap',
          startX: this.startX,
          startY: this.startY,
          endX: touch.clientX,
          endY: touch.clientY,
          deltaX,
          deltaY,
          distance,
          duration,
        });
      }
      this.lastTapTime = endTime;
    } else if (distance > this.options.swipeThreshold) {
      // Determine swipe direction
      const direction = this.getSwipeDirection(deltaX, deltaY);
      this.dispatchGesture({
        type: 'swipe',
        startX: this.startX,
        startY: this.startY,
        endX: touch.clientX,
        endY: touch.clientY,
        deltaX,
        deltaY,
        distance,
        duration,
        direction,
      });
    }
  };

  private handleTouchCancel = () => {
    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer);
      this.longPressTimer = null;
    }
  };

  private getDistance(touch1: Touch, touch2: Touch): number {
    const deltaX = touch2.clientX - touch1.clientX;
    const deltaY = touch2.clientY - touch1.clientY;
    return Math.sqrt(deltaX * deltaX + deltaY * deltaY);
  }

  private getSwipeDirection(deltaX: number, deltaY: number): 'up' | 'down' | 'left' | 'right' {
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      return deltaX > 0 ? 'right' : 'left';
    } else {
      return deltaY > 0 ? 'down' : 'up';
    }
  }

  private dispatchGesture(gesture: TouchGesture) {
    const event = new CustomEvent('gesture', { detail: gesture });
    this.element.dispatchEvent(event);
  }

  destroy() {
    this.element.removeEventListener('touchstart', this.handleTouchStart);
    this.element.removeEventListener('touchmove', this.handleTouchMove);
    this.element.removeEventListener('touchend', this.handleTouchEnd);
    this.element.removeEventListener('touchcancel', this.handleTouchCancel);

    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer);
    }
  }
}

// React hook for touch gestures
export function useTouchGestures(
  options: TouchOptions = {},
  onGesture?: (gesture: TouchGesture) => void
) {
  const elementRef = useRef<HTMLElement>(null);
  const managerRef = useRef<TouchManager | null>(null);

  useEffect(() => {
    if (!elementRef.current) return;

    managerRef.current = new TouchManager(elementRef.current, options);

    const handleGesture = (e: CustomEvent<TouchGesture>) => {
      onGesture?.(e.detail);
    };

    elementRef.current.addEventListener('gesture', handleGesture as EventListener);

    return () => {
      if (managerRef.current) {
        managerRef.current.destroy();
      }
      if (elementRef.current) {
        elementRef.current.removeEventListener('gesture', handleGesture as EventListener);
      }
    };
  }, [options, onGesture]);

  return elementRef;
}

// Hook for swipe gestures
export function useSwipeGesture(
  onSwipe: (direction: 'up' | 'down' | 'left' | 'right') => void,
  options: TouchOptions = {}
) {
  return useTouchGestures(options, (gesture) => {
    if (gesture.type === 'swipe' && gesture.direction) {
      onSwipe(gesture.direction);
    }
  });
}

// Hook for tap gestures
export function useTapGesture(
  onTap: () => void,
  onDoubleTap?: () => void,
  options: TouchOptions = {}
) {
  return useTouchGestures(options, (gesture) => {
    if (gesture.type === 'tap') {
      onTap();
    } else if (gesture.type === 'double-tap' && onDoubleTap) {
      onDoubleTap();
    }
  });
}

// Hook for long press gesture
export function useLongPress(
  onLongPress: () => void,
  options: TouchOptions = {}
) {
  return useTouchGestures(options, (gesture) => {
    if (gesture.type === 'long-press') {
      onLongPress();
    }
  });
}

// Hook for pinch gesture
export function usePinchGesture(
  onPinch: (scale: number) => void,
  options: TouchOptions = {}
) {
  return useTouchGestures(options, (gesture) => {
    if (gesture.type === 'pinch' && gesture.scale) {
      onPinch(gesture.scale);
    }
  });
}

// Mobile viewport utilities
export function isMobile(): boolean {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= 768;
}

export function isTablet(): boolean {
  if (typeof window === 'undefined') return false;
  return window.innerWidth > 768 && window.innerWidth <= 1024;
}

export function isDesktop(): boolean {
  if (typeof window === 'undefined') return false;
  return window.innerWidth > 1024;
}

export function isTouchDevice(): boolean {
  if (typeof window === 'undefined') return false;
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

// Hook for responsive breakpoints
export function useBreakpoint() {
  const [breakpoint, setBreakpoint] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');

  useEffect(() => {
    const updateBreakpoint = () => {
      if (isMobile()) {
        setBreakpoint('mobile');
      } else if (isTablet()) {
        setBreakpoint('tablet');
      } else {
        setBreakpoint('desktop');
      }
    };

    updateBreakpoint();
    window.addEventListener('resize', updateBreakpoint);
    return () => window.removeEventListener('resize', updateBreakpoint);
  }, []);

  return {
    breakpoint,
    isMobile: breakpoint === 'mobile',
    isTablet: breakpoint === 'tablet',
    isDesktop: breakpoint === 'desktop',
    isTouchDevice: isTouchDevice(),
  };
}