"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useAuth } from './auth-context';

interface OnboardingState {
  hasCompletedOnboarding: boolean;
  currentStep: number;
  isOnboardingVisible: boolean;
}

interface OnboardingContextType extends OnboardingState {
  startOnboarding: () => void;
  completeOnboarding: () => void;
  skipOnboarding: () => void;
  setOnboardingStep: (step: number) => void;
  hideOnboarding: () => void;
  showOnboarding: () => void;
}

const OnboardingContext = createContext<OnboardingContextType | undefined>(undefined);

interface OnboardingProviderProps {
  children: ReactNode;
}

export function OnboardingProvider({ children }: OnboardingProviderProps) {
  const { user, isAuthenticated } = useAuth();
  const [state, setState] = useState<OnboardingState>({
    hasCompletedOnboarding: false,
    currentStep: 0,
    isOnboardingVisible: false,
  });

  // Check if user has completed onboarding
  useEffect(() => {
    if (isAuthenticated && user) {
      const onboardingKey = `onboarding_completed_${user.id}`;
      const hasCompleted = localStorage.getItem(onboardingKey) === 'true';
      
      setState(prev => ({
        ...prev,
        hasCompletedOnboarding: hasCompleted,
        isOnboardingVisible: !hasCompleted,
      }));
    }
  }, [isAuthenticated, user]);

  const startOnboarding = () => {
    setState(prev => ({
      ...prev,
      currentStep: 0,
      isOnboardingVisible: true,
      hasCompletedOnboarding: false,
    }));
  };

  const completeOnboarding = () => {
    if (user) {
      const onboardingKey = `onboarding_completed_${user.id}`;
      localStorage.setItem(onboardingKey, 'true');
      
      setState(prev => ({
        ...prev,
        hasCompletedOnboarding: true,
        isOnboardingVisible: false,
      }));
    }
  };

  const skipOnboarding = () => {
    completeOnboarding(); // Same as completing for now
  };

  const setOnboardingStep = (step: number) => {
    setState(prev => ({
      ...prev,
      currentStep: step,
    }));
  };

  const hideOnboarding = () => {
    setState(prev => ({
      ...prev,
      isOnboardingVisible: false,
    }));
  };

  const showOnboarding = () => {
    setState(prev => ({
      ...prev,
      isOnboardingVisible: true,
    }));
  };

  const value: OnboardingContextType = {
    ...state,
    startOnboarding,
    completeOnboarding,
    skipOnboarding,
    setOnboardingStep,
    hideOnboarding,
    showOnboarding,
  };

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  );
}

export function useOnboarding() {
  const context = useContext(OnboardingContext);
  if (context === undefined) {
    throw new Error('useOnboarding must be used within an OnboardingProvider');
  }
  return context;
}