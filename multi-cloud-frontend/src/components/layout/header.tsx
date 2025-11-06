"use client"

import React, { useState } from "react"
import { useRouter } from "next/navigation"
import { useTheme } from "next-themes"
import { Bell, User, ChevronDown, Settings, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ThemeToggle } from "@/components/ui/theme-toggle"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useAuth } from "@/contexts/auth-context"

// Mock notifications - in real app this would come from API
const mockNotifications = [
  {
    id: "1",
    title: "Cost Alert",
    message: "AWS costs exceeded threshold by 15%",
    created_at: new Date().toISOString(),
    read: false,
  },
  {
    id: "2", 
    title: "New Insight Available",
    message: "AI detected potential savings in EC2 instances",
    created_at: new Date(Date.now() - 3600000).toISOString(),
    read: false,
  },
]

interface HeaderProps {
  className?: string
}

export function Header({ className }: HeaderProps) {
  const router = useRouter()
  const { user, logout, isLoading } = useAuth()
  const { theme, setTheme } = useTheme()
  const [showNotifications, setShowNotifications] = useState(false)
  
  // Mock notifications state - in real app this would be managed by a hook
  const [notifications] = useState(mockNotifications)
  const unreadCount = notifications.filter(n => !n.read).length

  const handleLogout = async () => {
    try {
      await logout()
      router.push("/login")
    } catch (error) {
      console.error("Logout failed:", error)
    }
  }



  return (
    <header className={`
      fixed top-0 right-0 left-0 lg:left-64 z-30 
      bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700
      ${className}
    `}>
      <div className="flex items-center justify-between px-4 sm:px-6 lg:px-8 h-16">
        {/* Left side - Page title area (will be populated by individual pages) */}
        <div className="flex-1 lg:ml-0 ml-12">
          {/* This space is reserved for page-specific titles */}
        </div>
        
        {/* Right side - Controls */}
        <div className="flex items-center space-x-4">
          {/* Theme toggle */}
          <ThemeToggle />

          {/* Notifications */}
          <DropdownMenu open={showNotifications} onOpenChange={setShowNotifications}>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                size="sm" 
                className="relative"
                aria-label={`Notifications ${unreadCount > 0 ? `(${unreadCount} unread)` : ""}`}
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <Badge 
                    variant="destructive" 
                    className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 text-xs flex items-center justify-center"
                  >
                    {unreadCount}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <DropdownMenuLabel>Notifications</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {notifications.length === 0 ? (
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                  No new notifications
                </div>
              ) : (
                notifications.slice(0, 5).map((notification) => (
                  <DropdownMenuItem 
                    key={notification.id} 
                    className="flex flex-col items-start p-4 cursor-pointer"
                  >
                    <div className="font-medium text-sm">{notification.title}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {notification.message}
                    </div>
                    <div className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                      {new Date(notification.created_at).toLocaleString()}
                    </div>
                  </DropdownMenuItem>
                ))
              )}
              {notifications.length > 5 && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-center text-sm text-primary">
                    View all notifications
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                className="flex items-center space-x-2 px-3"
                aria-label="User menu"
                disabled={isLoading}
              >
                <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
                  <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
                    {isLoading ? "..." : (user?.name?.charAt(0).toUpperCase() || "U")}
                  </span>
                </div>
                <span className="hidden md:block text-sm font-medium">
                  {isLoading ? "Loading..." : (user?.name || "User")}
                </span>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="flex flex-col space-y-1">
                  <div className="font-medium">{user?.name || "User"}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {user?.email || "No email"}
                  </div>
                  <div className="text-xs text-gray-400 dark:text-gray-500">
                    {user?.role || "MEMBER"}
                  </div>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                onClick={() => router.push("/settings")}
                className="cursor-pointer"
              >
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuItem 
                onClick={() => router.push("/settings")}
                className="cursor-pointer"
              >
                <Bell className="mr-2 h-4 w-4" />
                Notification Preferences
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                onClick={handleLogout}
                className="cursor-pointer text-red-600 dark:text-red-400"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}