"use client";

import { OnboardingTour } from './onboarding-tour';
import { useOnboarding } from '@/contexts/onboarding-context';
import { useAuth } from '@/contexts/auth-context';
import { 
  Cloud, 
  BarChart3, 
  Bell, 
  Users,
  Zap,
  Shield
} from 'lucide-react';

export function WelcomeOnboarding() {
  const { isOnboardingVisible, completeOnboarding, skipOnboarding } = useOnboarding();
  const { user } = useAuth();

  if (!isOnboardingVisible || !user) {
    return null;
  }

  const onboardingSteps = [
    {
      id: 'welcome',
      title: `Welcome, ${user.name}!`,
      description: 'Welcome to CostsHub! We\'re excited to help you optimize your multi-cloud costs with AI-powered insights. Let\'s take a quick tour to get you started.',
      icon: <Zap className="h-6 w-6 text-blue-600" />,
    },
    {
      id: 'connect-providers',
      title: 'Connect Your Cloud Providers',
      description: 'Start by connecting your AWS, GCP, or Azure accounts to begin collecting cost data. Don\'t worry - your credentials are securely encrypted.',
      icon: <Cloud className="h-6 w-6 text-blue-600" />,
      action: {
        label: 'Connect Providers',
        onClick: () => {
          // In a real app, this would navigate to the connections page
          console.log('Navigate to connections page');
        },
      },
    },
    {
      id: 'view-analytics',
      title: 'Explore Cost Analytics',
      description: 'Once connected, you\'ll see detailed cost breakdowns, trends, and comparisons across all your cloud providers in beautiful, interactive charts.',
      icon: <BarChart3 className="h-6 w-6 text-blue-600" />,
    },
    {
      id: 'ai-insights',
      title: 'AI-Powered Insights',
      description: 'Our AI analyzes your spending patterns to identify anomalies, suggest optimizations, and predict future costs to help you save money.',
      icon: <Zap className="h-6 w-6 text-blue-600" />,
    },
    {
      id: 'set-alerts',
      title: 'Set Up Cost Alerts',
      description: 'Never be surprised by unexpected costs again. Set up intelligent alerts to notify you when spending exceeds your thresholds.',
      icon: <Bell className="h-6 w-6 text-blue-600" />,
      action: {
        label: 'Create Alert',
        onClick: () => {
          // In a real app, this would navigate to the alerts page
          console.log('Navigate to alerts page');
        },
      },
    },
    {
      id: 'team-collaboration',
      title: 'Collaborate with Your Team',
      description: user.role === 'ADMIN' 
        ? 'As an admin, you can invite team members, manage permissions, and share cost insights across your organization.'
        : 'Collaborate with your team by sharing insights, discussing cost optimization strategies, and tracking progress together.',
      icon: user.role === 'ADMIN' ? <Shield className="h-6 w-6 text-blue-600" /> : <Users className="h-6 w-6 text-blue-600" />,
      action: user.role === 'ADMIN' ? {
        label: 'Manage Users',
        onClick: () => {
          // In a real app, this would navigate to the users page
          console.log('Navigate to users page');
        },
      } : undefined,
    },
    {
      id: 'ready',
      title: 'You\'re All Set!',
      description: 'That\'s it! You\'re ready to start optimizing your cloud costs. Remember, you can always access help and documentation from the menu.',
      icon: <Zap className="h-6 w-6 text-green-600" />,
    },
  ];

  return (
    <OnboardingTour
      steps={onboardingSteps}
      onComplete={completeOnboarding}
      onSkip={skipOnboarding}
    />
  );
}