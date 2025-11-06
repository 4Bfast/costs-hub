'use client';

import { useState } from 'react';
import { Plus, RefreshCw, Settings, Trash2, TestTube, AlertCircle, CheckCircle, Clock, HelpCircle, Cloud } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState } from '@/components/layout/empty-state';
import { LoadingSpinner } from '@/components/layout/loading-spinner';
import { ProviderIcon } from '@/components/providers/provider-icon';
import { ProviderBadge } from '@/components/providers/provider-badge';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { CloudProviderAccount, AccountStatus } from '@/types/models';
import { useProviderAccounts } from '@/hooks/useProviderAccounts';
import { OnboardingWizard } from '@/components/connections/onboarding-wizard';
import { DiscoveredAccountsTable } from '@/components/connections/discovered-accounts-table';
import { AccountLinkingSuggestions } from '@/components/connections/account-linking-suggestions';
import { SetupProgress } from '@/components/connections/setup-progress';
import { HelpDocumentation } from '@/components/connections/help-documentation';
import { DiscoveredAccount, AccountLinkingSuggestion } from '@/types/discovered-accounts';

export default function ConnectionsPage() {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [accountToDelete, setAccountToDelete] = useState<CloudProviderAccount | null>(null);
  const [testingAccount, setTestingAccount] = useState<string | null>(null);
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('connected');
  const [showHelp, setShowHelp] = useState(false);

  const {
    accounts,
    isLoading,
    error,
    refetch,
    deleteAccount,
    testConnection,
    createAccount,
    isCreating,
  } = useProviderAccounts();

  const handleDeleteAccount = async () => {
    if (!accountToDelete) return;

    try {
      await deleteAccount(accountToDelete.id);
      toast.success('Account deleted successfully');
      setDeleteDialogOpen(false);
      setAccountToDelete(null);
    } catch {
      toast.error('Failed to delete account');
    }
  };

  const handleTestConnection = async (account: CloudProviderAccount) => {
    setTestingAccount(account.id);
    try {
      const result = await testConnection(account.id);
      if (result.success) {
        toast.success('Connection test successful');
      } else {
        toast.error(`Connection test failed: ${result.errors?.[0] || 'Unknown error'}`);
      }
    } catch {
      toast.error('Connection test failed');
    } finally {
      setTestingAccount(null);
    }
  };

  const handleOnboardingComplete = async (accountData: Partial<CloudProviderAccount>) => {
    try {
      await createAccount(accountData);
      toast.success('Account added successfully');
      setOnboardingOpen(false);
      refetch();
    } catch {
      toast.error('Failed to add account');
    }
  };

  const handleDiscoveredAccountLink = (discoveredAccount: DiscoveredAccount) => {
    toast.success(`Account ${discoveredAccount.account_id} linked successfully`);
    // Refresh connected accounts to show the newly linked account
    refetch();
  };

  const handleSuggestionAction = (suggestion: AccountLinkingSuggestion, action: 'link' | 'dismiss') => {
    if (action === 'link') {
      // Switch to discovered accounts tab to show the linking interface
      setActiveTab('discovered');
    }
  };

  // Generate setup progress steps based on current state
  const getSetupSteps = () => {
    const hasAccounts = accounts.length > 0;
    const hasActiveAccounts = accounts.some(acc => acc.status === 'active');
    const hasRecentData = accounts.some(acc => acc.last_sync && 
      new Date(acc.last_sync).getTime() > Date.now() - 24 * 60 * 60 * 1000
    );

    return [
      {
        id: 'connect-account',
        title: 'Connect AWS Account',
        description: hasAccounts ? 'AWS account connected successfully' : 'Connect your first AWS account to start cost analytics',
        status: hasAccounts ? 'completed' as const : 'pending' as const,
        estimatedTime: '10 min'
      },
      {
        id: 'verify-permissions',
        title: 'Verify Permissions',
        description: hasActiveAccounts ? 'Permissions verified and working' : 'Test connection and verify IAM permissions',
        status: hasActiveAccounts ? 'completed' as const : hasAccounts ? 'in-progress' as const : 'pending' as const,
        estimatedTime: '2 min'
      },
      {
        id: 'sync-data',
        title: 'Sync Cost Data',
        description: hasRecentData ? 'Cost data synced successfully' : 'Initial cost data synchronization',
        status: hasRecentData ? 'completed' as const : hasActiveAccounts ? 'in-progress' as const : 'pending' as const,
        estimatedTime: '15 min'
      },
      {
        id: 'setup-alerts',
        title: 'Configure Alerts (Optional)',
        description: 'Set up cost alerts and notifications',
        status: 'pending' as const,
        estimatedTime: '5 min'
      }
    ];
  };

  const getStatusIcon = (status: AccountStatus) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
      case 'syncing':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadgeVariant = (status: AccountStatus) => {
    switch (status) {
      case 'active':
        return 'default';
      case 'error':
        return 'destructive';
      case 'pending':
      case 'syncing':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const formatLastSync = (lastSync: string | null | undefined) => {
    if (!lastSync) return 'Never';
    try {
      const date = new Date(lastSync);
      if (isNaN(date.getTime())) return 'Invalid date';
      
      const now = new Date();
      const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
      
      if (diffInHours < 1) return 'Just now';
      if (diffInHours < 24) return `${diffInHours}h ago`;
      return date.toLocaleDateString();
    } catch {
      return 'Invalid date';
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Provider Connections"
          description="Manage your cloud provider account connections"
        />
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Provider Connections"
          description="Manage your cloud provider account connections"
        />
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Failed to load connections
              </h3>
              <p className="text-gray-600 mb-4">
                There was an error loading your provider connections.
              </p>
              <Button onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Provider Connections"
        description="Manage your cloud provider account connections and discover new accounts"
        actions={
          <div className="flex space-x-2">
            <Button variant="outline" onClick={() => setShowHelp(!showHelp)}>
              <HelpCircle className="h-4 w-4 mr-2" />
              Help
            </Button>
            <Button onClick={() => setOnboardingOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Account
            </Button>
          </div>
        }
      />

      {/* Setup Progress - Show for new users or when no accounts are connected */}
      {accounts.length === 0 && (
        <SetupProgress 
          steps={getSetupSteps()} 
          onAddAccount={() => setOnboardingOpen(true)}
        />
      )}

      {/* Help Documentation - Collapsible */}
      {showHelp && (
        <HelpDocumentation />
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="connected">Connected Accounts</TabsTrigger>
          <TabsTrigger value="discovered">Discovered Accounts</TabsTrigger>
          <TabsTrigger value="suggestions">Suggestions</TabsTrigger>
        </TabsList>

        <TabsContent value="connected" className="space-y-6">
          {accounts.length === 0 ? (
            <EmptyState
              icon={Cloud}
              title="No provider accounts connected"
              description="Connect your first cloud provider account to start analyzing costs. Use the 'Add Account' button above to get started."
            />
          ) : (
            <div className="grid gap-6">
              {accounts.map((account) => (
            <Card key={account.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <ProviderIcon provider={account.provider} className="h-8 w-8" />
                    <div>
                      <CardTitle className="text-lg">
                        {account.display_name || account.account_name || 'Unnamed Account'}
                      </CardTitle>
                      <div className="flex items-center space-x-2 mt-1">
                        <ProviderBadge provider={account.provider} />
                        <span className="text-sm text-gray-500">
                          {account.account_id || 'No ID'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="flex items-center space-x-1">
                      {getStatusIcon(account.status)}
                      <Badge variant={getStatusBadgeVariant(account.status)}>
                        {account.status}
                      </Badge>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <Settings className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => handleTestConnection(account)}
                          disabled={testingAccount === account.id}
                        >
                          <TestTube className="h-4 w-4 mr-2" />
                          {testingAccount === account.id ? 'Testing...' : 'Test Connection'}
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Settings className="h-4 w-4 mr-2" />
                          Edit Configuration
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => {
                            setAccountToDelete(account);
                            setDeleteDialogOpen(true);
                          }}
                          className="text-red-600"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete Account
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Last Sync</p>
                    <p className="text-sm text-gray-900">
                      {formatLastSync(account.last_sync)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Monthly Cost</p>
                    <p className="text-sm text-gray-900">
                      {account.cost_summary?.total_cost_30d != null
                        ? `$${Number(account.cost_summary.total_cost_30d).toLocaleString()}`
                        : 'N/A'
                      }
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Top Service</p>
                    <p className="text-sm text-gray-900">
                      {account.cost_summary?.top_services?.[0]?.service || 'N/A'}
                    </p>
                  </div>
                </div>
                
                {account.status === 'error' && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                    <div className="flex items-start">
                      <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 mr-2" />
                      <div>
                        <h4 className="text-sm font-medium text-red-800">
                          Connection Error
                        </h4>
                        <p className="text-sm text-red-700 mt-1">
                          Unable to sync data from this account. Please check your configuration.
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          className="mt-2"
                          onClick={() => handleTestConnection(account)}
                        >
                          <TestTube className="h-4 w-4 mr-2" />
                          Test Connection
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="discovered" className="space-y-6">
          <DiscoveredAccountsTable onAccountLink={handleDiscoveredAccountLink} />
        </TabsContent>

        <TabsContent value="suggestions" className="space-y-6">
          <AccountLinkingSuggestions onSuggestionAction={handleSuggestionAction} />
        </TabsContent>
      </Tabs>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Provider Account</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the connection to{' '}
              <strong>{accountToDelete?.display_name || accountToDelete?.account_name}</strong>?
              This will stop cost data collection and cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteAccount}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete Account
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={onboardingOpen} onOpenChange={setOnboardingOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add AWS Account</DialogTitle>
          </DialogHeader>
          <OnboardingWizard
            onComplete={handleOnboardingComplete}
            onCancel={() => setOnboardingOpen(false)}
            isLoading={isCreating}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}