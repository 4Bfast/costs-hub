"use client"

import React, { useState } from "react"
import { useAuth } from "@/contexts/auth-context"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { useToast } from "@/hooks/use-toast"
import { 
  Building2, 
  Shield, 
  Database, 
  Download, 
  Trash2,
  Save,
  Users,
  Settings,
  AlertTriangle
} from "lucide-react"

interface OrganizationSettings {
  name: string
  description: string
  website: string
  industry: string
  size: string
  timezone: string
  currency: string
}

interface SecuritySettings {
  requireTwoFactor: boolean
  sessionTimeout: number
  allowMemberInvites: boolean
  requireEmailVerification: boolean
  passwordMinLength: number
}

interface DataSettings {
  retentionPeriod: number
  autoExport: boolean
  exportFormat: 'csv' | 'json' | 'excel'
  exportFrequency: 'daily' | 'weekly' | 'monthly'
}

export default function OrganizationSettingsPage() {
  const { user, organization } = useAuth()
  const { toast } = useToast()
  
  const [orgSettings, setOrgSettings] = useState<OrganizationSettings>({
    name: organization?.name || "",
    description: "",
    website: "",
    industry: "",
    size: "",
    timezone: "UTC",
    currency: "USD"
  })
  
  const [securitySettings, setSecuritySettings] = useState<SecuritySettings>({
    requireTwoFactor: false,
    sessionTimeout: 24,
    allowMemberInvites: true,
    requireEmailVerification: true,
    passwordMinLength: 8
  })
  
  const [dataSettings, setDataSettings] = useState<DataSettings>({
    retentionPeriod: 365,
    autoExport: false,
    exportFormat: 'csv',
    exportFrequency: 'monthly'
  })
  
  const [isLoading, setIsLoading] = useState(false)

  // Redirect if not admin
  if (user?.role !== 'ADMIN') {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <Shield className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">Access Denied</h3>
              <p className="mt-1 text-sm text-gray-500">
                You need administrator privileges to access organization settings.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const handleOrganizationUpdate = async () => {
    if (!orgSettings.name.trim()) {
      toast({
        title: "Validation Error",
        description: "Organization name is required.",
        variant: "destructive",
      })
      return
    }

    setIsLoading(true)
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      toast({
        title: "Organization Updated",
        description: "Organization settings have been updated successfully.",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update organization settings.",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSecurityUpdate = async () => {
    setIsLoading(true)
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      toast({
        title: "Security Settings Updated",
        description: "Security policies have been updated successfully.",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update security settings.",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDataSettingsUpdate = async () => {
    setIsLoading(true)
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      toast({
        title: "Data Settings Updated",
        description: "Data retention and export settings have been updated.",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update data settings.",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleExportData = async () => {
    setIsLoading(true)
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      toast({
        title: "Export Started",
        description: "Your data export has been initiated. You'll receive an email when it's ready.",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to start data export.",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteOrganization = async () => {
    // This would be a very dangerous operation
    toast({
      title: "Feature Not Available",
      description: "Organization deletion must be requested through support.",
      variant: "destructive",
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Organization Settings
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Manage your organization's profile, security, and data policies
        </p>
      </div>

      <div className="grid gap-6">
        {/* Organization Profile */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Building2 className="w-5 h-5 mr-2" />
              Organization Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="orgName">Organization Name</Label>
                <Input
                  id="orgName"
                  value={orgSettings.name}
                  onChange={(e) => setOrgSettings(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Enter organization name"
                />
              </div>
              
              <div className="grid gap-2">
                <Label htmlFor="website">Website</Label>
                <Input
                  id="website"
                  type="url"
                  value={orgSettings.website}
                  onChange={(e) => setOrgSettings(prev => ({ ...prev, website: e.target.value }))}
                  placeholder="https://example.com"
                />
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={orgSettings.description}
                onChange={(e) => setOrgSettings(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Describe your organization"
                rows={3}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="grid gap-2">
                <Label htmlFor="industry">Industry</Label>
                <Select 
                  value={orgSettings.industry} 
                  onValueChange={(value) => setOrgSettings(prev => ({ ...prev, industry: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select industry" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="technology">Technology</SelectItem>
                    <SelectItem value="finance">Finance</SelectItem>
                    <SelectItem value="healthcare">Healthcare</SelectItem>
                    <SelectItem value="retail">Retail</SelectItem>
                    <SelectItem value="manufacturing">Manufacturing</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="size">Organization Size</Label>
                <Select 
                  value={orgSettings.size} 
                  onValueChange={(value) => setOrgSettings(prev => ({ ...prev, size: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select size" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1-10">1-10 employees</SelectItem>
                    <SelectItem value="11-50">11-50 employees</SelectItem>
                    <SelectItem value="51-200">51-200 employees</SelectItem>
                    <SelectItem value="201-1000">201-1000 employees</SelectItem>
                    <SelectItem value="1000+">1000+ employees</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Select 
                  value={orgSettings.timezone} 
                  onValueChange={(value) => setOrgSettings(prev => ({ ...prev, timezone: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="UTC">UTC</SelectItem>
                    <SelectItem value="America/New_York">Eastern Time</SelectItem>
                    <SelectItem value="America/Chicago">Central Time</SelectItem>
                    <SelectItem value="America/Denver">Mountain Time</SelectItem>
                    <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                    <SelectItem value="Europe/London">London</SelectItem>
                    <SelectItem value="Europe/Paris">Paris</SelectItem>
                    <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button onClick={handleOrganizationUpdate} disabled={isLoading}>
              <Save className="w-4 h-4 mr-2" />
              {isLoading ? "Saving..." : "Save Organization Settings"}
            </Button>
          </CardContent>
        </Card>

        {/* Security Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Shield className="w-5 h-5 mr-2" />
              Security & Access Control
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="requireTwoFactor">Require Two-Factor Authentication</Label>
                    <p className="text-xs text-gray-500">
                      Enforce 2FA for all organization members
                    </p>
                  </div>
                  <Switch
                    id="requireTwoFactor"
                    checked={securitySettings.requireTwoFactor}
                    onCheckedChange={(checked) => 
                      setSecuritySettings(prev => ({ ...prev, requireTwoFactor: checked }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="allowMemberInvites">Allow Member Invitations</Label>
                    <p className="text-xs text-gray-500">
                      Let members invite new users to the organization
                    </p>
                  </div>
                  <Switch
                    id="allowMemberInvites"
                    checked={securitySettings.allowMemberInvites}
                    onCheckedChange={(checked) => 
                      setSecuritySettings(prev => ({ ...prev, allowMemberInvites: checked }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="requireEmailVerification">Require Email Verification</Label>
                    <p className="text-xs text-gray-500">
                      Verify email addresses for new members
                    </p>
                  </div>
                  <Switch
                    id="requireEmailVerification"
                    checked={securitySettings.requireEmailVerification}
                    onCheckedChange={(checked) => 
                      setSecuritySettings(prev => ({ ...prev, requireEmailVerification: checked }))
                    }
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div className="grid gap-2">
                  <Label htmlFor="sessionTimeout">Session Timeout (hours)</Label>
                  <Select 
                    value={securitySettings.sessionTimeout.toString()} 
                    onValueChange={(value) => 
                      setSecuritySettings(prev => ({ ...prev, sessionTimeout: parseInt(value) }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 hour</SelectItem>
                      <SelectItem value="4">4 hours</SelectItem>
                      <SelectItem value="8">8 hours</SelectItem>
                      <SelectItem value="24">24 hours</SelectItem>
                      <SelectItem value="168">7 days</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="passwordMinLength">Minimum Password Length</Label>
                  <Select 
                    value={securitySettings.passwordMinLength.toString()} 
                    onValueChange={(value) => 
                      setSecuritySettings(prev => ({ ...prev, passwordMinLength: parseInt(value) }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="8">8 characters</SelectItem>
                      <SelectItem value="10">10 characters</SelectItem>
                      <SelectItem value="12">12 characters</SelectItem>
                      <SelectItem value="16">16 characters</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <Button onClick={handleSecurityUpdate} disabled={isLoading}>
              <Save className="w-4 h-4 mr-2" />
              {isLoading ? "Saving..." : "Save Security Settings"}
            </Button>
          </CardContent>
        </Card>

        {/* Data Management */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Database className="w-5 h-5 mr-2" />
              Data Management
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-4">
                <div className="grid gap-2">
                  <Label htmlFor="retentionPeriod">Data Retention Period (days)</Label>
                  <Select 
                    value={dataSettings.retentionPeriod.toString()} 
                    onValueChange={(value) => 
                      setDataSettings(prev => ({ ...prev, retentionPeriod: parseInt(value) }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="90">90 days</SelectItem>
                      <SelectItem value="180">180 days</SelectItem>
                      <SelectItem value="365">1 year</SelectItem>
                      <SelectItem value="730">2 years</SelectItem>
                      <SelectItem value="1825">5 years</SelectItem>
                      <SelectItem value="-1">Indefinite</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="autoExport">Automatic Data Export</Label>
                    <p className="text-xs text-gray-500">
                      Automatically export data at regular intervals
                    </p>
                  </div>
                  <Switch
                    id="autoExport"
                    checked={dataSettings.autoExport}
                    onCheckedChange={(checked) => 
                      setDataSettings(prev => ({ ...prev, autoExport: checked }))
                    }
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div className="grid gap-2">
                  <Label htmlFor="exportFormat">Export Format</Label>
                  <Select 
                    value={dataSettings.exportFormat} 
                    onValueChange={(value: 'csv' | 'json' | 'excel') => 
                      setDataSettings(prev => ({ ...prev, exportFormat: value }))
                    }
                    disabled={!dataSettings.autoExport}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="csv">CSV</SelectItem>
                      <SelectItem value="excel">Excel</SelectItem>
                      <SelectItem value="json">JSON</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="exportFrequency">Export Frequency</Label>
                  <Select 
                    value={dataSettings.exportFrequency} 
                    onValueChange={(value: 'daily' | 'weekly' | 'monthly') => 
                      setDataSettings(prev => ({ ...prev, exportFrequency: value }))
                    }
                    disabled={!dataSettings.autoExport}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="daily">Daily</SelectItem>
                      <SelectItem value="weekly">Weekly</SelectItem>
                      <SelectItem value="monthly">Monthly</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <Button onClick={handleDataSettingsUpdate} disabled={isLoading}>
                <Save className="w-4 h-4 mr-2" />
                {isLoading ? "Saving..." : "Save Data Settings"}
              </Button>
              
              <Button variant="outline" onClick={handleExportData} disabled={isLoading}>
                <Download className="w-4 h-4 mr-2" />
                Export Data Now
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-red-200 dark:border-red-800">
          <CardHeader>
            <CardTitle className="flex items-center text-red-600 dark:text-red-400">
              <AlertTriangle className="w-5 h-5 mr-2" />
              Danger Zone
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-red-50 dark:bg-red-950 rounded-lg">
              <h4 className="text-sm font-medium text-red-800 dark:text-red-200">
                Delete Organization
              </h4>
              <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                Permanently delete this organization and all associated data. This action cannot be undone.
              </p>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" className="mt-3">
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete Organization
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This action cannot be undone. This will permanently delete your organization
                      and remove all data from our servers.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleDeleteOrganization}>
                      Delete Organization
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}