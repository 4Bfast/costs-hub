"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAccessibility } from "@/components/providers/accessibility-provider"
import { useToast } from "@/hooks/use-toast"
import { 
  Eye, 
  Palette, 
  Type, 
  Focus, 
  Volume2,
  RotateCcw
} from "lucide-react"

export function AccessibilitySettings() {
  const { settings, updateSetting, resetSettings } = useAccessibility()
  const { toast } = useToast()

  const handleReset = () => {
    resetSettings()
    toast({
      title: "Settings Reset",
      description: "Accessibility settings have been reset to defaults.",
    })
  }

  const fontSizeOptions = [
    { value: 'small', label: 'Small', description: '14px base size' },
    { value: 'medium', label: 'Medium', description: '16px base size (default)' },
    { value: 'large', label: 'Large', description: '18px base size' },
    { value: 'extra-large', label: 'Extra Large', description: '20px base size' },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <Eye className="w-5 h-5 mr-2" />
          Accessibility Settings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-6 md:grid-cols-2">
          {/* Visual Settings */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium flex items-center">
              <Palette className="w-4 h-4 mr-2" />
              Visual Preferences
            </h4>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="highContrast">High Contrast Mode</Label>
                <p className="text-xs text-gray-500">
                  Increase contrast for better visibility
                </p>
              </div>
              <Switch
                id="highContrast"
                checked={settings.highContrast}
                onCheckedChange={(checked) => updateSetting('highContrast', checked)}
                aria-describedby="highContrast-description"
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="reducedMotion">Reduce Motion</Label>
                <p className="text-xs text-gray-500">
                  Minimize animations and transitions
                </p>
              </div>
              <Switch
                id="reducedMotion"
                checked={settings.reducedMotion}
                onCheckedChange={(checked) => updateSetting('reducedMotion', checked)}
                aria-describedby="reducedMotion-description"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="fontSize" className="flex items-center">
                <Type className="w-4 h-4 mr-2" />
                Font Size
              </Label>
              <Select 
                value={settings.fontSize} 
                onValueChange={(value: 'small' | 'medium' | 'large' | 'extra-large') => 
                  updateSetting('fontSize', value)
                }
              >
                <SelectTrigger id="fontSize" aria-describedby="fontSize-description">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {fontSizeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      <div className="flex flex-col">
                        <span>{option.label}</span>
                        <span className="text-xs text-gray-500">{option.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p id="fontSize-description" className="text-xs text-gray-500">
                Adjust the base font size for better readability
              </p>
            </div>
          </div>

          {/* Navigation Settings */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium flex items-center">
              <Focus className="w-4 h-4 mr-2" />
              Navigation & Focus
            </h4>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="focusVisible">Enhanced Focus Indicators</Label>
                <p className="text-xs text-gray-500">
                  Show prominent focus outlines for keyboard navigation
                </p>
              </div>
              <Switch
                id="focusVisible"
                checked={settings.focusVisible}
                onCheckedChange={(checked) => updateSetting('focusVisible', checked)}
                aria-describedby="focusVisible-description"
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="screenReaderOptimized">Screen Reader Optimizations</Label>
                <p className="text-xs text-gray-500">
                  Optimize interface for screen reader users
                </p>
              </div>
              <Switch
                id="screenReaderOptimized"
                checked={settings.screenReaderOptimized}
                onCheckedChange={(checked) => updateSetting('screenReaderOptimized', checked)}
                aria-describedby="screenReaderOptimized-description"
              />
            </div>
          </div>
        </div>

        {/* Keyboard Shortcuts Info */}
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <h4 className="text-sm font-medium mb-2">Keyboard Shortcuts</h4>
          <div className="grid gap-2 text-xs text-gray-600 dark:text-gray-400">
            <div className="flex justify-between">
              <span>Navigate between sections:</span>
              <kbd className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs">Tab</kbd>
            </div>
            <div className="flex justify-between">
              <span>Activate buttons/links:</span>
              <kbd className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs">Enter</kbd>
            </div>
            <div className="flex justify-between">
              <span>Toggle dropdowns:</span>
              <kbd className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs">Space</kbd>
            </div>
            <div className="flex justify-between">
              <span>Navigate dropdown items:</span>
              <kbd className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs">↑↓</kbd>
            </div>
          </div>
        </div>

        {/* Reset Button */}
        <div className="flex justify-end">
          <Button variant="outline" onClick={handleReset}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset to Defaults
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}