'use client';

import { CheckCircle, Clock, AlertCircle, Plus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface SetupStep {
  id: string;
  title: string;
  description: string;
  status: 'completed' | 'in-progress' | 'pending' | 'error';
  estimatedTime?: string;
}

interface SetupProgressProps {
  steps: SetupStep[];
  onAddAccount?: () => void;
  onRetryStep?: (stepId: string) => void;
}

export function SetupProgress({ steps, onAddAccount, onRetryStep }: SetupProgressProps) {
  const completedSteps = steps.filter(step => step.status === 'completed').length;
  const totalSteps = steps.length;
  const progressPercentage = (completedSteps / totalSteps) * 100;

  const getStatusIcon = (status: SetupStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'in-progress':
        return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <div className="h-4 w-4 rounded-full border-2 border-gray-300" />;
    }
  };

  const getStatusBadge = (status: SetupStep['status']) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-100 text-green-800">Complete</Badge>;
      case 'in-progress':
        return <Badge variant="default" className="bg-blue-100 text-blue-800">In Progress</Badge>;
      case 'error':
        return <Badge variant="destructive">Error</Badge>;
      default:
        return <Badge variant="secondary">Pending</Badge>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Setup Progress</CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              {completedSteps} of {totalSteps} steps completed
            </p>
          </div>
          {onAddAccount && (
            <Button onClick={onAddAccount} size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add Account
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div className="space-y-2">
          <Progress value={progressPercentage} className="h-2" />
          <div className="flex justify-between text-xs text-gray-500">
            <span>{Math.round(progressPercentage)}% Complete</span>
            <span>{totalSteps - completedSteps} remaining</span>
          </div>
        </div>

        {/* Setup steps */}
        <div className="space-y-3">
          {steps.map((step) => (
            <div key={step.id} className="flex items-start space-x-3 p-3 rounded-lg border">
              <div className="flex-shrink-0 mt-0.5">
                {getStatusIcon(step.status)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-gray-900">{step.title}</h4>
                  {getStatusBadge(step.status)}
                </div>
                <p className="text-sm text-gray-600 mt-1">{step.description}</p>
                {step.estimatedTime && step.status === 'pending' && (
                  <p className="text-xs text-gray-500 mt-1">
                    Estimated time: {step.estimatedTime}
                  </p>
                )}
                {step.status === 'error' && onRetryStep && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    onClick={() => onRetryStep(step.id)}
                  >
                    Retry
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Completion message */}
        {completedSteps === totalSteps && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
            <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
            <h3 className="font-medium text-green-800">Setup Complete!</h3>
            <p className="text-sm text-green-700 mt-1">
              Your account is ready for cost analytics. Data collection is now active.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}