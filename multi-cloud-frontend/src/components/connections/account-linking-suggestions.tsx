'use client';

import { useState } from 'react';
import { 
  TrendingUp, 
  Clock, 
  DollarSign, 
  AlertTriangle,
  CheckCircle,
  X,
  ExternalLink,
  Lightbulb
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { ProviderIcon } from '@/components/providers/provider-icon';
import { LoadingSpinner } from '@/components/layout/loading-spinner';
import { EmptyState } from '@/components/layout/empty-state';
import { useAccountLinkingSuggestions, useDiscoveredAccounts } from '@/hooks/useDiscoveredAccounts';
import { AccountLinkingSuggestion } from '@/types/discovered-accounts';

interface AccountLinkingSuggestionsProps {
  onSuggestionAction?: (suggestion: AccountLinkingSuggestion, action: 'link' | 'dismiss') => void;
}

export function AccountLinkingSuggestions({ onSuggestionAction }: AccountLinkingSuggestionsProps) {
  const [dismissedSuggestions, setDismissedSuggestions] = useState<Set<string>>(new Set());
  
  const { suggestions, isLoading, error } = useAccountLinkingSuggestions();
  const { accounts: discoveredAccounts } = useDiscoveredAccounts();

  const handleDismiss = (suggestion: AccountLinkingSuggestion) => {
    setDismissedSuggestions(prev => new Set([...prev, suggestion.discovered_account_id]));
    onSuggestionAction?.(suggestion, 'dismiss');
    toast.success('Suggestion dismissed');
  };

  const handleLink = (suggestion: AccountLinkingSuggestion) => {
    onSuggestionAction?.(suggestion, 'link');
  };

  const getPriorityIcon = (priority: AccountLinkingSuggestion['priority']) => {
    switch (priority) {
      case 'high':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'medium':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'low':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      default:
        return <CheckCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getPriorityBadgeVariant = (priority: AccountLinkingSuggestion['priority']) => {
    switch (priority) {
      case 'high':
        return 'destructive';
      case 'medium':
        return 'secondary';
      case 'low':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const getComplexityColor = (complexity: AccountLinkingSuggestion['setup_complexity']) => {
    switch (complexity) {
      case 'easy':
        return 'text-green-600';
      case 'medium':
        return 'text-yellow-600';
      case 'complex':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getSuggestionTypeIcon = (type: AccountLinkingSuggestion['suggestion_type']) => {
    switch (type) {
      case 'high_cost':
        return <DollarSign className="h-5 w-5 text-yellow-500" />;
      case 'new_account':
        return <TrendingUp className="h-5 w-5 text-blue-500" />;
      case 'missing_data':
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      case 'organization_member':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      default:
        return <Lightbulb className="h-5 w-5 text-purple-500" />;
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Filter out dismissed suggestions
  const visibleSuggestions = suggestions.filter(
    suggestion => !dismissedSuggestions.has(suggestion.discovered_account_id)
  );

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <AlertTriangle className="h-8 w-8 text-red-500 mx-auto mb-2" />
            <p className="text-sm text-gray-600">Failed to load linking suggestions</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (visibleSuggestions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Lightbulb className="h-5 w-5 mr-2" />
            Account Linking Suggestions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={CheckCircle}
            title="No suggestions available"
            description="All discovered accounts have been reviewed or no new suggestions are available"
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center">
            <Lightbulb className="h-5 w-5 mr-2" />
            Account Linking Suggestions
          </CardTitle>
          <Badge variant="outline">{visibleSuggestions.length} suggestions</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {visibleSuggestions.map((suggestion) => {
            const discoveredAccount = discoveredAccounts?.find(
              (account: any) => account.id === suggestion.discovered_account_id
            );

            return (
              <div
                key={suggestion.discovered_account_id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-start space-x-3">
                    {getSuggestionTypeIcon(suggestion.suggestion_type)}
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className="font-medium text-sm">{suggestion.title}</h4>
                        <div className="flex items-center space-x-1">
                          {getPriorityIcon(suggestion.priority)}
                          <Badge variant={getPriorityBadgeVariant(suggestion.priority)} className="text-xs">
                            {suggestion.priority}
                          </Badge>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600">{suggestion.description}</p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDismiss(suggestion)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                {discoveredAccount && (
                  <div className="bg-gray-50 rounded-md p-3 mb-3">
                    <div className="flex items-center space-x-3">
                      <ProviderIcon provider={discoveredAccount.provider} className="h-5 w-5" />
                      <div className="flex-1">
                        <p className="font-medium text-sm">
                          {discoveredAccount.account_name || discoveredAccount.account_id}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatCurrency(discoveredAccount.cost_summary.total_cost_30d)} (30d cost)
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
                  {suggestion.potential_savings && (
                    <div>
                      <p className="text-xs font-medium text-gray-500">Potential Savings</p>
                      <p className="text-sm font-semibold text-green-600">
                        {formatCurrency(suggestion.potential_savings)}
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs font-medium text-gray-500">Setup Time</p>
                    <p className="text-sm">{suggestion.estimated_time}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500">Complexity</p>
                    <p className={`text-sm font-medium ${getComplexityColor(suggestion.setup_complexity)}`}>
                      {suggestion.setup_complexity}
                    </p>
                  </div>
                </div>

                {suggestion.benefits.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-medium text-gray-500 mb-1">Benefits</p>
                    <ul className="text-xs text-gray-600 space-y-1">
                      {suggestion.benefits.slice(0, 3).map((benefit, index) => (
                        <li key={index} className="flex items-start">
                          <CheckCircle className="h-3 w-3 text-green-500 mr-1 mt-0.5 flex-shrink-0" />
                          {benefit}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {suggestion.requirements.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 mb-1">Requirements</p>
                    <ul className="text-xs text-gray-600 space-y-1">
                      {suggestion.requirements.slice(0, 2).map((requirement, index) => (
                        <li key={index} className="flex items-start">
                          <AlertTriangle className="h-3 w-3 text-yellow-500 mr-1 mt-0.5 flex-shrink-0" />
                          {requirement}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <Separator className="my-3" />

                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="text-xs text-gray-500">
                      Priority: <span className="font-medium">{suggestion.priority}</span>
                    </div>
                    <div className="text-xs text-gray-500">
                      Type: <span className="font-medium">{suggestion.suggestion_type.replace('_', ' ')}</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDismiss(suggestion)}
                    >
                      Dismiss
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleLink(suggestion)}
                    >
                      Link Account
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}