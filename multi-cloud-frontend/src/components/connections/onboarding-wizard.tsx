'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { 
  ChevronLeft, 
  ChevronRight, 
  CheckCircle, 
  Copy, 
  ExternalLink,
  AlertCircle,
  Loader2,
  Download,
  HelpCircle,
  BookOpen,
  Zap,
  Shield,
  Clock,
  Plus
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { toast } from 'sonner';
import { ProviderIcon } from '@/components/providers/provider-icon';
import { CloudProviderAccount } from '@/types/models';

// Form validation schemas for each step
const accountInfoSchema = z.object({
  accountName: z.string().min(1, 'Account name is required'),
  accountId: z.string().regex(/^\d{12}$/, 'AWS Account ID must be 12 digits'),
  displayName: z.string().optional(),
  description: z.string().optional(),
});

const iamRoleSchema = z.object({
  roleArn: z.string().regex(
    /^arn:aws:iam::\d{12}:role\/[\w+=,.@-]+$/,
    'Invalid IAM Role ARN format'
  ),
  externalId: z.string().min(8, 'External ID must be at least 8 characters'),
});

type AccountInfoForm = z.infer<typeof accountInfoSchema>;
type IAMRoleForm = z.infer<typeof iamRoleSchema>;

interface OnboardingWizardProps {
  onComplete: (account: Partial<CloudProviderAccount>) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

const WIZARD_STEPS = [
  { 
    id: 'account-info', 
    title: 'Account Information', 
    description: 'Basic account details',
    icon: <BookOpen className="h-4 w-4" />,
    estimatedTime: '2 min'
  },
  { 
    id: 'iam-setup', 
    title: 'IAM Role Setup', 
    description: 'Configure AWS permissions',
    icon: <Shield className="h-4 w-4" />,
    estimatedTime: '5-10 min'
  },
  { 
    id: 'test-connection', 
    title: 'Test Connection', 
    description: 'Verify configuration',
    icon: <Zap className="h-4 w-4" />,
    estimatedTime: '1 min'
  },
  { 
    id: 'complete', 
    title: 'Complete', 
    description: 'Finalize setup',
    icon: <CheckCircle className="h-4 w-4" />,
    estimatedTime: '1 min'
  },
];

export function OnboardingWizard({ onComplete, onCancel, isLoading = false }: OnboardingWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [accountInfo, setAccountInfo] = useState<AccountInfoForm | null>(null);
  const [iamRole, setIamRole] = useState<IAMRoleForm | null>(null);
  const [testResult, setTestResult] = useState<any>(null);
  const [isTestingConnection, setIsTestingConnection] = useState(false);

  // Generate external ID for IAM role
  const [externalId] = useState(() => 
    `costshub-${Math.random().toString(36).substr(2, 16)}`
  );

  // Form for account information
  const accountForm = useForm<AccountInfoForm>({
    resolver: zodResolver(accountInfoSchema),
    defaultValues: {
      accountName: '',
      accountId: '',
      displayName: '',
      description: '',
    },
  });

  // Form for IAM role configuration
  const iamForm = useForm<IAMRoleForm>({
    resolver: zodResolver(iamRoleSchema),
    defaultValues: {
      roleArn: '',
      externalId,
    },
  });

  const handleAccountInfoSubmit = (data: AccountInfoForm) => {
    setAccountInfo(data);
    setCurrentStep(1);
  };

  const handleIAMRoleSubmit = (data: IAMRoleForm) => {
    setIamRole(data);
    setCurrentStep(2);
  };

  const handleTestConnection = async () => {
    if (!accountInfo || !iamRole) return;

    setIsTestingConnection(true);
    try {
      // Simulate connection test - in real implementation, this would call the API
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      const mockResult = {
        success: true,
        permissions: ['cost:GetCostAndUsage', 'cost:GetUsageReport', 'organizations:ListAccounts'],
        regions: ['us-east-1', 'us-west-2', 'eu-west-1'],
        services: ['EC2', 'S3', 'RDS', 'Lambda'],
      };
      
      setTestResult(mockResult);
      
      if (mockResult.success) {
        toast.success('Connection test successful!');
        setCurrentStep(3);
      } else {
        toast.error('Connection test failed. Please check your configuration.');
      }
    } catch {
      toast.error('Connection test failed');
      setTestResult({ success: false, error: 'Connection failed' });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleComplete = async () => {
    if (!accountInfo || !iamRole) return;

    const accountData: Partial<CloudProviderAccount> = {
      provider: 'aws',
      account_id: accountInfo.accountId,
      account_name: accountInfo.accountName,
      display_name: accountInfo.displayName || accountInfo.accountName,
      status: 'pending',
      configuration: {
        role_arn: iamRole.roleArn,
        external_id: iamRole.externalId,
        regions: testResult?.regions || [],
      },
    };

    await onComplete(accountData);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  // Troubleshooting Guide Component
  const TroubleshootingGuide = () => (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="text-base flex items-center">
          <HelpCircle className="h-5 w-5 mr-2 text-blue-500" />
          Troubleshooting Guide
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {troubleshootingGuide.map((item, index) => (
          <Collapsible key={index}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between p-3 h-auto">
                <div className="text-left">
                  <div className="font-medium text-sm">{item.issue}</div>
                  <div className="text-xs text-gray-500 mt-1">{item.solution}</div>
                </div>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="px-3 pb-3">
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">Steps to resolve:</p>
                <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600">
                  {item.steps.map((step, stepIndex) => (
                    <li key={stepIndex}>{step}</li>
                  ))}
                </ol>
              </div>
            </CollapsibleContent>
          </Collapsible>
        ))}
      </CardContent>
    </Card>
  );

  // Help Resources Component
  const HelpResources = () => (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="text-base flex items-center">
          <BookOpen className="h-5 w-5 mr-2 text-green-500" />
          Help & Documentation
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {helpResources.map((resource, index) => (
          <div key={index} className="flex items-start space-x-3 p-3 border rounded-lg hover:bg-gray-50">
            <div className="flex-shrink-0 mt-1">
              {resource.type === 'external' ? (
                <ExternalLink className="h-4 w-4 text-blue-500" />
              ) : (
                <BookOpen className="h-4 w-4 text-green-500" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <Button
                variant="link"
                className="p-0 h-auto font-medium text-left justify-start"
                onClick={() => window.open(resource.url, resource.type === 'external' ? '_blank' : '_self')}
              >
                {resource.title}
              </Button>
              <p className="text-sm text-gray-600 mt-1">{resource.description}</p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );

  // Troubleshooting guide data
  const troubleshootingGuide = [
    {
      issue: "Invalid IAM Role ARN format",
      solution: "Ensure your ARN follows the format: arn:aws:iam::123456789012:role/RoleName",
      steps: [
        "Check that your account ID is exactly 12 digits",
        "Verify the role name matches exactly (case-sensitive)",
        "Ensure there are no extra spaces or characters"
      ]
    },
    {
      issue: "Access Denied when testing connection",
      solution: "The IAM role may not have the required permissions or trust relationship",
      steps: [
        "Verify the trust relationship includes our account ID",
        "Check that the External ID matches exactly",
        "Ensure the role has the Billing policy attached",
        "Wait 2-3 minutes after creating the role for AWS to propagate changes"
      ]
    },
    {
      issue: "Role not found error",
      solution: "The IAM role may not exist or the ARN is incorrect",
      steps: [
        "Double-check the role exists in your AWS account",
        "Verify you're using the correct AWS account ID",
        "Ensure the role name is spelled correctly",
        "Check that you have permission to view IAM roles"
      ]
    }
  ];

  const helpResources = [
    {
      title: "AWS IAM Roles Documentation",
      description: "Official AWS guide on creating and managing IAM roles",
      url: "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html",
      type: "external"
    },
    {
      title: "Cost Explorer API Permissions",
      description: "Required permissions for cost data access",
      url: "https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-api.html",
      type: "external"
    },
    {
      title: "CostsHub Setup Guide",
      description: "Complete setup guide with screenshots",
      url: "/docs/setup-guide",
      type: "internal"
    },
    {
      title: "Video Tutorial",
      description: "Step-by-step video walkthrough",
      url: "/docs/video-tutorial",
      type: "internal"
    }
  ];

  const downloadCloudFormationTemplate = () => {
    const template = {
      AWSTemplateFormatVersion: '2010-09-09',
      Description: 'CostsHub IAM Role for Cost Analytics',
      Parameters: {
        ExternalId: {
          Type: 'String',
          Default: externalId,
          Description: 'External ID for the IAM role',
        },
      },
      Resources: {
        CostsHubRole: {
          Type: 'AWS::IAM::Role',
          Properties: {
            RoleName: 'CostsHubAnalyticsRole',
            AssumeRolePolicyDocument: {
              Version: '2012-10-17',
              Statement: [
                {
                  Effect: 'Allow',
                  Principal: {
                    AWS: 'arn:aws:iam::123456789012:root', // Replace with actual CostsHub account
                  },
                  Action: 'sts:AssumeRole',
                  Condition: {
                    StringEquals: {
                      'sts:ExternalId': { Ref: 'ExternalId' },
                    },
                  },
                },
              ],
            },
            ManagedPolicyArns: [
              'arn:aws:iam::aws:policy/job-function/Billing',
            ],
            Policies: [
              {
                PolicyName: 'CostsHubCostAnalytics',
                PolicyDocument: {
                  Version: '2012-10-17',
                  Statement: [
                    {
                      Effect: 'Allow',
                      Action: [
                        'ce:GetCostAndUsage',
                        'ce:GetUsageReport',
                        'ce:GetReservationCoverage',
                        'ce:GetReservationPurchaseRecommendation',
                        'ce:GetReservationUtilization',
                        'ce:ListCostCategoryDefinitions',
                        'organizations:ListAccounts',
                        'organizations:DescribeOrganization',
                      ],
                      Resource: '*',
                    },
                  ],
                },
              },
            ],
          },
        },
      },
      Outputs: {
        RoleArn: {
          Description: 'ARN of the created IAM role',
          Value: { 'Fn::GetAtt': ['CostsHubRole', 'Arn'] },
        },
      },
    };

    const blob = new Blob([JSON.stringify(template, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'costshub-iam-role.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            {/* Help text for account information */}
            <Alert>
              <BookOpen className="h-4 w-4" />
              <AlertDescription>
                We need some basic information about your AWS account to set up cost analytics. 
                You can find your AWS Account ID in the top-right corner of your AWS Console.
              </AlertDescription>
            </Alert>

            <form onSubmit={accountForm.handleSubmit(handleAccountInfoSubmit)} className="space-y-6">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="accountName" className="flex items-center">
                    Account Name *
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="ml-2 h-auto p-1"
                      onClick={() => toast.info("Choose a descriptive name to identify this account in your dashboard")}
                    >
                      <HelpCircle className="h-3 w-3" />
                    </Button>
                  </Label>
                  <Input
                    id="accountName"
                    placeholder="e.g., Production Account, Development, Staging"
                    {...accountForm.register('accountName')}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    This name will appear in your dashboard and reports
                  </p>
                  {accountForm.formState.errors.accountName && (
                    <p className="text-sm text-red-600 mt-1">
                      {accountForm.formState.errors.accountName.message}
                    </p>
                  )}
                </div>

                <div>
                  <Label htmlFor="accountId" className="flex items-center">
                    AWS Account ID *
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="ml-2 h-auto p-1"
                      onClick={() => window.open('https://docs.aws.amazon.com/IAM/latest/UserGuide/console_account-alias.html#FindingYourAWSId', '_blank')}
                    >
                      <HelpCircle className="h-3 w-3" />
                    </Button>
                  </Label>
                  <Input
                    id="accountId"
                    placeholder="123456789012"
                    maxLength={12}
                    {...accountForm.register('accountId')}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    12-digit number found in the top-right corner of your AWS Console
                  </p>
                  {accountForm.formState.errors.accountId && (
                    <p className="text-sm text-red-600 mt-1">
                      {accountForm.formState.errors.accountId.message}
                    </p>
                  )}
                </div>

                <div>
                  <Label htmlFor="displayName">Display Name</Label>
                  <Input
                    id="displayName"
                    placeholder="Optional friendly name"
                    {...accountForm.register('displayName')}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Alternative name for easier identification (optional)
                  </p>
                </div>

                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    placeholder="e.g., Main production environment for web applications"
                    {...accountForm.register('description')}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Additional context about this account (optional)
                  </p>
                </div>
              </div>

              <div className="flex justify-between">
                <Button type="button" variant="outline" onClick={onCancel}>
                  Cancel
                </Button>
                <Button type="submit">
                  Next
                  <ChevronRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </form>

            {/* Help resources for account setup */}
            <HelpResources />
          </div>
        );

      case 1:
        return (
          <div className="space-y-6">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                You need to create an IAM role in your AWS account that allows CostsHub to access your cost data.
              </AlertDescription>
            </Alert>

            <Tabs defaultValue="cloudformation" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="cloudformation">CloudFormation</TabsTrigger>
                <TabsTrigger value="manual">Manual Setup</TabsTrigger>
              </TabsList>

              <TabsContent value="cloudformation" className="space-y-4">
                <div className="space-y-4">
                  <h4 className="font-medium">Automated Setup with CloudFormation</h4>
                  <p className="text-sm text-gray-600">
                    Download and deploy this CloudFormation template to automatically create the required IAM role.
                  </p>
                  
                  <div className="flex items-center space-x-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={downloadCloudFormationTemplate}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Download Template
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => window.open('https://console.aws.amazon.com/cloudformation', '_blank')}
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Open CloudFormation
                    </Button>
                  </div>

                  <div className="bg-gray-50 p-4 rounded-md">
                    <h5 className="font-medium mb-2">External ID</h5>
                    <div className="flex items-center space-x-2">
                      <code className="bg-white px-2 py-1 rounded border text-sm flex-1">
                        {externalId}
                      </code>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(externalId)}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="manual" className="space-y-4">
                <div className="space-y-4">
                  <h4 className="font-medium">Manual IAM Role Creation</h4>
                  
                  <div className="space-y-3">
                    <div>
                      <h5 className="font-medium text-sm">1. Create IAM Role</h5>
                      <p className="text-sm text-gray-600">
                        Go to IAM → Roles → Create Role → AWS Account → Another AWS Account
                      </p>
                    </div>
                    
                    <div>
                      <h5 className="font-medium text-sm">2. Account ID</h5>
                      <div className="flex items-center space-x-2">
                        <code className="bg-gray-100 px-2 py-1 rounded text-sm">123456789012</code>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard('123456789012')}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>

                    <div>
                      <h5 className="font-medium text-sm">3. External ID</h5>
                      <div className="flex items-center space-x-2">
                        <code className="bg-gray-100 px-2 py-1 rounded text-sm">{externalId}</code>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(externalId)}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>

                    <div>
                      <h5 className="font-medium text-sm">4. Attach Policies</h5>
                      <ul className="text-sm text-gray-600 list-disc list-inside">
                        <li>Billing (AWS Managed Policy)</li>
                        <li>Cost Explorer Read Access</li>
                        <li>Organizations Read Access</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            <form onSubmit={iamForm.handleSubmit(handleIAMRoleSubmit)} className="space-y-4">
              <div>
                <Label htmlFor="roleArn" className="flex items-center">
                  IAM Role ARN *
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="ml-2 h-auto p-1"
                    onClick={() => toast.info("Copy the ARN from your IAM role after creating it. It should start with 'arn:aws:iam::'")}
                  >
                    <HelpCircle className="h-3 w-3" />
                  </Button>
                </Label>
                <Input
                  id="roleArn"
                  placeholder="arn:aws:iam::123456789012:role/CostsHubAnalyticsRole"
                  {...iamForm.register('roleArn')}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Copy this from the IAM role summary page after creation
                </p>
                {iamForm.formState.errors.roleArn && (
                  <p className="text-sm text-red-600 mt-1">
                    {iamForm.formState.errors.roleArn.message}
                  </p>
                )}
              </div>

              <div className="flex justify-between">
                <Button type="button" variant="outline" onClick={() => setCurrentStep(0)}>
                  <ChevronLeft className="h-4 w-4 mr-2" />
                  Back
                </Button>
                <Button type="submit">
                  Next
                  <ChevronRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </form>

            {/* Troubleshooting guide for IAM setup */}
            <TroubleshootingGuide />
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-lg font-medium mb-2">Test Connection</h3>
              <p className="text-gray-600">
                We'll test the connection to verify your IAM role configuration.
              </p>
            </div>

            {accountInfo && iamRole && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Configuration Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Account Name:</span>
                    <span className="text-sm">{accountInfo.accountName}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Account ID:</span>
                    <span className="text-sm">{accountInfo.accountId}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">IAM Role:</span>
                    <span className="text-sm font-mono text-xs">{iamRole.roleArn}</span>
                  </div>
                </CardContent>
              </Card>
            )}

            {testResult && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center">
                    {testResult.success ? (
                      <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
                    )}
                    Connection Test {testResult.success ? 'Successful' : 'Failed'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {testResult.success ? (
                    <div className="space-y-3">
                      <div>
                        <h5 className="font-medium text-sm mb-1">Verified Permissions</h5>
                        <div className="flex flex-wrap gap-1">
                          {testResult.permissions.map((permission: string) => (
                            <Badge key={permission} variant="secondary" className="text-xs">
                              {permission}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <h5 className="font-medium text-sm mb-1">Available Regions</h5>
                        <div className="flex flex-wrap gap-1">
                          {testResult.regions.map((region: string) => (
                            <Badge key={region} variant="outline" className="text-xs">
                              {region}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-red-600">{testResult.error}</p>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Connection testing progress */}
            {isTestingConnection && (
              <Card className="border-blue-200 bg-blue-50">
                <CardContent className="pt-6">
                  <div className="flex items-center space-x-3">
                    <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                    <div>
                      <p className="font-medium text-blue-900">Testing connection...</p>
                      <p className="text-sm text-blue-700">This may take up to 30 seconds</p>
                    </div>
                  </div>
                  <div className="mt-3">
                    <div className="text-xs text-blue-600 space-y-1">
                      <div>✓ Validating IAM role ARN format</div>
                      <div>✓ Checking role existence</div>
                      <div>⏳ Verifying trust relationship</div>
                      <div className="text-gray-400">⏳ Testing permissions</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex justify-between">
              <Button type="button" variant="outline" onClick={() => setCurrentStep(1)}>
                <ChevronLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              {!testResult ? (
                <Button onClick={handleTestConnection} disabled={isTestingConnection}>
                  {isTestingConnection && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Test Connection
                </Button>
              ) : testResult.success ? (
                <Button onClick={() => setCurrentStep(3)}>
                  Continue
                  <ChevronRight className="h-4 w-4 ml-2" />
                </Button>
              ) : (
                <div className="space-x-2">
                  <Button 
                    variant="outline"
                    onClick={() => setCurrentStep(1)}
                  >
                    Fix Configuration
                  </Button>
                  <Button onClick={handleTestConnection} disabled={isTestingConnection}>
                    {isTestingConnection && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                    Retry Test
                  </Button>
                </div>
              )}
            </div>

            {/* Show troubleshooting guide if test failed */}
            {testResult && !testResult.success && (
              <TroubleshootingGuide />
            )}
          </div>
        );

      case 3:
        return (
          <div className="space-y-6 text-center">
            <div className="flex justify-center">
              <CheckCircle className="h-16 w-16 text-green-500" />
            </div>
            
            <div>
              <h3 className="text-xl font-semibold mb-2">Setup Complete!</h3>
              <p className="text-gray-600">
                Your AWS account has been successfully configured for cost analytics.
              </p>
            </div>

            <Card>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-center space-x-2">
                    <ProviderIcon provider="aws" className="h-6 w-6" />
                    <span className="font-medium">{accountInfo?.accountName}</span>
                  </div>
                  <div className="text-center space-y-2">
                    <p className="text-sm text-gray-600">
                      Cost data collection will begin within the next few minutes.
                    </p>
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <h4 className="font-medium text-green-800 text-sm mb-2">What happens next?</h4>
                      <ul className="text-xs text-green-700 space-y-1 text-left">
                        <li>• Initial cost data sync (5-15 minutes)</li>
                        <li>• AI insights generation (30-60 minutes)</li>
                        <li>• Email notification when ready</li>
                        <li>• Dashboard will show live data</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Next steps and quick actions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <Button variant="outline" size="sm" className="justify-start">
                    <BookOpen className="h-4 w-4 mr-2" />
                    View Dashboard
                  </Button>
                  <Button variant="outline" size="sm" className="justify-start">
                    <Zap className="h-4 w-4 mr-2" />
                    Set Up Alerts
                  </Button>
                  <Button variant="outline" size="sm" className="justify-start">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Another Account
                  </Button>
                  <Button variant="outline" size="sm" className="justify-start">
                    <HelpCircle className="h-4 w-4 mr-2" />
                    Get Help
                  </Button>
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-between">
              <Button type="button" variant="outline" onClick={() => setCurrentStep(2)}>
                <ChevronLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <Button onClick={handleComplete} disabled={isLoading}>
                {isLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Complete Setup
              </Button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Enhanced Progress indicator */}
      <div className="mb-8">
        {/* Step indicators with icons and time estimates */}
        <div className="flex items-center justify-between mb-6">
          {WIZARD_STEPS.map((step, index) => (
            <div key={step.id} className="flex flex-col items-center flex-1">
              <div className="flex items-center w-full">
                <div className={`
                  flex items-center justify-center w-10 h-10 rounded-full text-sm font-medium transition-all duration-200
                  ${index < currentStep 
                    ? 'bg-green-500 text-white' 
                    : index === currentStep
                    ? 'bg-primary text-primary-foreground ring-4 ring-primary/20'
                    : 'bg-gray-200 text-gray-600'
                  }
                `}>
                  {index < currentStep ? (
                    <CheckCircle className="h-5 w-5" />
                  ) : (
                    step.icon
                  )}
                </div>
                {index < WIZARD_STEPS.length - 1 && (
                  <div className={`
                    flex-1 h-0.5 mx-3 transition-all duration-200
                    ${index < currentStep ? 'bg-green-500' : 'bg-gray-200'}
                  `} />
                )}
              </div>
              <div className="text-center mt-2">
                <div className={`text-xs font-medium ${
                  index <= currentStep ? 'text-gray-900' : 'text-gray-500'
                }`}>
                  {step.title}
                </div>
                <div className="text-xs text-gray-400 flex items-center mt-1">
                  <Clock className="h-3 w-3 mr-1" />
                  {step.estimatedTime}
                </div>
              </div>
            </div>
          ))}
        </div>
        
        {/* Current step info */}
        <div className="text-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900 mb-1">
            {WIZARD_STEPS[currentStep].title}
          </h2>
          <p className="text-sm text-gray-600 mb-2">
            {WIZARD_STEPS[currentStep].description}
          </p>
          <div className="flex items-center justify-center text-xs text-gray-500">
            <Clock className="h-3 w-3 mr-1" />
            Estimated time: {WIZARD_STEPS[currentStep].estimatedTime}
          </div>
        </div>
        
        {/* Progress bar */}
        <div className="space-y-2">
          <Progress value={(currentStep / (WIZARD_STEPS.length - 1)) * 100} className="h-2" />
          <div className="flex justify-between text-xs text-gray-500">
            <span>Step {currentStep + 1} of {WIZARD_STEPS.length}</span>
            <span>{Math.round((currentStep / (WIZARD_STEPS.length - 1)) * 100)}% Complete</span>
          </div>
        </div>
      </div>

      {/* Step content */}
      <Card>
        <CardContent className="pt-6">
          {renderStepContent()}
        </CardContent>
      </Card>
    </div>
  );
}