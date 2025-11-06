'use client';

import { useState } from 'react';
import { 
  Eye, 
  Link, 
  EyeOff, 
  RefreshCw, 
  Filter,
  TrendingUp,
  Calendar,
  DollarSign,
  AlertCircle,
  CheckCircle,
  Clock,
  ExternalLink
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import { ProviderIcon } from '@/components/providers/provider-icon';
import { ProviderBadge } from '@/components/providers/provider-badge';
import { LoadingSpinner } from '@/components/layout/loading-spinner';
import { EmptyState } from '@/components/layout/empty-state';
import { 
  useDiscoveredAccounts, 
  useDiscoveredAccountsStats
} from '@/hooks/useDiscoveredAccounts';
import { useProviderAccounts } from '@/hooks/useProviderAccounts';
import { DiscoveredAccount, DiscoveredAccountsFilters } from '@/types/discovered-accounts';

interface DiscoveredAccountsTableProps {
  onAccountLink?: (discoveredAccount: DiscoveredAccount) => void;
}

export function DiscoveredAccountsTable({ onAccountLink }: DiscoveredAccountsTableProps) {
  const [filters, setFilters] = useState<DiscoveredAccountsFilters>({
    sort_by: 'cost',
    sort_order: 'desc',
  });
  const [selectedAccount, setSelectedAccount] = useState<DiscoveredAccount | null>(null);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
  const [selectedProviderAccount, setSelectedProviderAccount] = useState<string>('');

  const { 
    accounts, 
    isLoading, 
    error, 
    refetch,
    refreshAccounts,
    updateStatus,
    linkAccount,
    isRefreshing,
    isUpdating,
    isLinking
  } = useDiscoveredAccounts(filters);

  const { stats, isLoading: isLoadingStats } = useDiscoveredAccountsStats();
  const { accounts: providerAccounts } = useProviderAccounts();

  const handleRefresh = async () => {
    try {
      await refreshAccounts();
      toast.success('Account discovery refreshed successfully');
    } catch (error) {
      toast.error('Failed to refresh account discovery');
    }
  };

  const handleIgnoreAccount = async (account: DiscoveredAccount) => {
    try {
      await updateStatus({ id: account.id, status: 'ignored' });
      toast.success(`Account ${account.account_id} ignored`);
    } catch (error) {
      toast.error('Failed to ignore account');
    }
  };

  const handleLinkAccount = async () => {
    if (!selectedAccount || !selectedProviderAccount) return;

    try {
      await linkAccount({
        discoveredAccountId: selectedAccount.id,
        providerAccountId: selectedProviderAccount,
      });
      toast.success(`Account ${selectedAccount.account_id} linked successfully`);
      setLinkDialogOpen(false);
      setSelectedAccount(null);
      setSelectedProviderAccount('');
      onAccountLink?.(selectedAccount);
    } catch (error) {
      toast.error('Failed to link account');
    }
  };

  const handleViewDetails = (account: DiscoveredAccount) => {
    setSelectedAccount(account);
    setDetailsDialogOpen(true);
  };

  const handleStartLinking = (account: DiscoveredAccount) => {
    setSelectedAccount(account);
    setLinkDialogOpen(true);
  };

  const getStatusIcon = (status: DiscoveredAccount['status']) => {
    switch (status) {
      case 'linked':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'ignored':
        return <EyeOff className="h-4 w-4 text-gray-400" />;
      case 'discovered':
        return <Clock className="h-4 w-4 text-blue-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadgeVariant = (status: DiscoveredAccount['status']) => {
    switch (status) {
      case 'linked':
        return 'default';
      case 'ignored':
        return 'secondary';
      case 'discovered':
        return 'outline';
      default:
        return 'outline';
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-12">
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
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Failed to load discovered accounts
            </h3>
            <p className="text-gray-600 mb-4">
              There was an error loading discovered accounts from FOCUS data.
            </p>
            <Button onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Statistics Cards */}
      {stats && !isLoadingStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Discovered</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.total_discovered}</p>
                </div>
                <Eye className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Linked Accounts</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.total_linked}</p>
                </div>
                <Link className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Cost (30d)</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatCurrency(stats.total_cost_30d)}
                  </p>
                </div>
                <DollarSign className="h-8 w-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">New This Week</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.new_accounts_this_week}</p>
                </div>
                <TrendingUp className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Discovered Accounts</CardTitle>
              <p className="text-sm text-gray-600 mt-1">
                Accounts found in FOCUS cost data that are not yet connected
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={isRefreshing}
              >
                {isRefreshing ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Refresh
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Filter className="h-4 w-4 mr-2" />
                    Filter
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <div className="p-3 space-y-3">
                    <div>
                      <Label className="text-xs font-medium">Status</Label>
                      <Select
                        value={filters.status?.[0] || 'all'}
                        onValueChange={(value) => {
                          setFilters(prev => ({
                            ...prev,
                            status: value === 'all' ? undefined : [value as any]
                          }));
                        }}
                      >
                        <SelectTrigger className="h-8">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Status</SelectItem>
                          <SelectItem value="discovered">Discovered</SelectItem>
                          <SelectItem value="linked">Linked</SelectItem>
                          <SelectItem value="ignored">Ignored</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs font-medium">Sort By</Label>
                      <Select
                        value={filters.sort_by || 'cost'}
                        onValueChange={(value) => {
                          setFilters(prev => ({
                            ...prev,
                            sort_by: value as any
                          }));
                        }}
                      >
                        <SelectTrigger className="h-8">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="cost">Cost</SelectItem>
                          <SelectItem value="first_seen">First Seen</SelectItem>
                          <SelectItem value="last_seen">Last Seen</SelectItem>
                          <SelectItem value="account_name">Account Name</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {accounts.length === 0 ? (
            <EmptyState
              icon={Eye}
              title="No discovered accounts"
              description="No accounts found in FOCUS data that aren't already connected"
              action={{
                label: "Refresh Discovery",
                onClick: handleRefresh
              }}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>30d Cost</TableHead>
                  <TableHead>Top Service</TableHead>
                  <TableHead>First Seen</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accounts.map((account: any) => (
                  <TableRow key={account.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">
                          {account.account_name || account.account_id}
                        </div>
                        {account.account_name && (
                          <div className="text-sm text-gray-500">{account.account_id}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <ProviderIcon provider={account.provider} className="h-5 w-5" />
                        <ProviderBadge provider={account.provider} />
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-1">
                        {getStatusIcon(account.status)}
                        <Badge variant={getStatusBadgeVariant(account.status)}>
                          {account.status}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">
                        {formatCurrency(account.cost_summary.total_cost_30d)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>
                        {account.cost_summary.top_services[0] ? (
                          <>
                            <div className="font-medium text-sm">
                              {account.cost_summary.top_services[0].service}
                            </div>
                            <div className="text-xs text-gray-500">
                              {account.cost_summary.top_services[0].percentage.toFixed(1)}%
                            </div>
                          </>
                        ) : (
                          <span className="text-gray-400">N/A</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">{formatDate(account.first_seen)}</div>
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            Actions
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleViewDetails(account)}>
                            <Eye className="h-4 w-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                          {account.status === 'discovered' && (
                            <>
                              <DropdownMenuItem onClick={() => handleStartLinking(account)}>
                                <Link className="h-4 w-4 mr-2" />
                                Link Account
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                onClick={() => handleIgnoreAccount(account)}
                                disabled={isUpdating}
                              >
                                <EyeOff className="h-4 w-4 mr-2" />
                                Ignore Account
                              </DropdownMenuItem>
                            </>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Account Details Dialog */}
      <Dialog open={detailsDialogOpen} onOpenChange={setDetailsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Account Details</DialogTitle>
          </DialogHeader>
          {selectedAccount && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">Account ID</Label>
                  <p className="text-sm text-gray-900">{selectedAccount.account_id}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Account Name</Label>
                  <p className="text-sm text-gray-900">
                    {selectedAccount.account_name || 'N/A'}
                  </p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Provider</Label>
                  <div className="flex items-center space-x-2 mt-1">
                    <ProviderIcon provider={selectedAccount.provider} className="h-4 w-4" />
                    <ProviderBadge provider={selectedAccount.provider} />
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium">Status</Label>
                  <div className="flex items-center space-x-1 mt-1">
                    {getStatusIcon(selectedAccount.status)}
                    <Badge variant={getStatusBadgeVariant(selectedAccount.status)}>
                      {selectedAccount.status}
                    </Badge>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h4 className="font-medium mb-3">Cost Summary (30 days)</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium">Total Cost</Label>
                    <p className="text-lg font-semibold">
                      {formatCurrency(selectedAccount.cost_summary.total_cost_30d)}
                    </p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">7-day Cost</Label>
                    <p className="text-lg font-semibold">
                      {formatCurrency(selectedAccount.cost_summary.total_cost_7d)}
                    </p>
                  </div>
                </div>
              </div>

              {selectedAccount.cost_summary.top_services.length > 0 && (
                <div>
                  <h4 className="font-medium mb-3">Top Services</h4>
                  <div className="space-y-2">
                    {selectedAccount.cost_summary.top_services.slice(0, 5).map((service, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <span className="text-sm">{service.service}</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-medium">
                            {formatCurrency(service.cost)}
                          </span>
                          <span className="text-xs text-gray-500">
                            ({service.percentage.toFixed(1)}%)
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <Separator />

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">First Seen</Label>
                  <p className="text-sm text-gray-900">{formatDate(selectedAccount.first_seen)}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Last Seen</Label>
                  <p className="text-sm text-gray-900">{formatDate(selectedAccount.last_seen)}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Data Source</Label>
                  <p className="text-sm text-gray-900">{selectedAccount.metadata.source}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium">Confidence Score</Label>
                  <div className="flex items-center space-x-2">
                    <Progress 
                      value={selectedAccount.metadata.confidence_score * 100} 
                      className="flex-1"
                    />
                    <span className="text-sm">
                      {(selectedAccount.metadata.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>

              {selectedAccount.linking_suggestions && (
                <div>
                  <h4 className="font-medium mb-3">Linking Suggestions</h4>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="flex items-start space-x-3">
                      <div className="flex-1">
                        <p className="text-sm font-medium">
                          {selectedAccount.linking_suggestions.suggested_connection_type}
                        </p>
                        <p className="text-sm text-gray-600 mt-1">
                          Estimated setup time: {selectedAccount.linking_suggestions.estimated_setup_time}
                        </p>
                        <div className="mt-2">
                          {selectedAccount.linking_suggestions.reasons.map((reason, index) => (
                            <p key={index} className="text-xs text-gray-500">• {reason}</p>
                          ))}
                        </div>
                      </div>
                      <Badge variant="outline">
                        {(selectedAccount.linking_suggestions.confidence * 100).toFixed(0)}% confidence
                      </Badge>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Link Account Dialog */}
      <Dialog open={linkDialogOpen} onOpenChange={setLinkDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Link Discovered Account</DialogTitle>
          </DialogHeader>
          {selectedAccount && (
            <div className="space-y-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="flex items-center space-x-3">
                  <ProviderIcon provider={selectedAccount.provider} className="h-6 w-6" />
                  <div>
                    <p className="font-medium">
                      {selectedAccount.account_name || selectedAccount.account_id}
                    </p>
                    <p className="text-sm text-gray-600">
                      {formatCurrency(selectedAccount.cost_summary.total_cost_30d)} (30d cost)
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <Label htmlFor="provider-account">Link to Provider Account</Label>
                <Select value={selectedProviderAccount} onValueChange={setSelectedProviderAccount}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a provider account" />
                  </SelectTrigger>
                  <SelectContent>
                    {providerAccounts
                      .filter(account => account.provider === selectedAccount.provider)
                      .map((account) => (
                        <SelectItem key={account.id} value={account.id}>
                          <div className="flex items-center space-x-2">
                            <ProviderIcon provider={account.provider} className="h-4 w-4" />
                            <span>{account.display_name || account.account_name}</span>
                            <span className="text-gray-500">({account.account_id})</span>
                          </div>
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                {providerAccounts.filter(account => account.provider === selectedAccount.provider).length === 0 && (
                  <p className="text-sm text-gray-500 mt-1">
                    No {selectedAccount.provider.toUpperCase()} accounts available. 
                    <Button variant="link" className="p-0 h-auto text-sm">
                      Add one first
                    </Button>
                  </p>
                )}
              </div>

              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => setLinkDialogOpen(false)}>
                  Cancel
                </Button>
                <Button 
                  onClick={handleLinkAccount}
                  disabled={!selectedProviderAccount || isLinking}
                >
                  {isLinking ? 'Linking...' : 'Link Account'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}