"use client"

import React, { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { useAuth } from "@/contexts/auth-context"
import { Button } from "@/components/ui/button"
import { 
  Home, 
  BarChart3, 
  Cloud, 
  Bell, 
  Settings,
  Users,
  TrendingUp,
  Menu,
  X
} from "lucide-react"

const navigationItems = [
  { 
    name: "Dashboard", 
    href: "/dashboard", 
    icon: Home,
    roles: ["ADMIN", "MEMBER"],
    description: "Overview and metrics"
  },
  { 
    name: "Cost Analysis", 
    href: "/analysis", 
    icon: BarChart3,
    roles: ["ADMIN", "MEMBER"],
    description: "Detailed cost breakdown"
  },
  { 
    name: "AI Insights", 
    href: "/insights", 
    icon: TrendingUp,
    roles: ["ADMIN", "MEMBER"],
    description: "AI-powered recommendations"
  },
  { 
    name: "Provider Accounts", 
    href: "/connections", 
    icon: Cloud,
    roles: ["ADMIN", "MEMBER"],
    description: "Cloud account connections"
  },
  { 
    name: "Alarms", 
    href: "/alarms", 
    icon: Bell,
    roles: ["ADMIN", "MEMBER"],
    description: "Cost alerts and notifications"
  },
  { 
    name: "User Management", 
    href: "/users", 
    icon: Users,
    roles: ["ADMIN"] // Admin only
  },
  { 
    name: "Settings", 
    href: "/settings", 
    icon: Settings,
    roles: ["ADMIN", "MEMBER"]
  },
]

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname()
  const { user, isLoading } = useAuth()
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  // Filter navigation items based on user role with fallbacks
  const filteredNavItems = React.useMemo(() => {
    if (isLoading) {
      // Show basic items while loading
      return navigationItems.filter(item => 
        ['Dashboard', 'Cost Analysis', 'AI Insights'].includes(item.name)
      );
    }
    
    if (!user?.role) {
      // Show member-level items if no role
      return navigationItems.filter(item => item.roles.includes("MEMBER"));
    }
    
    return navigationItems.filter(item => item.roles.includes(user.role));
  }, [user?.role, isLoading]);

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <Link href="/dashboard" className="flex items-center">
          <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">CH</span>
          </div>
          <span className="ml-2 text-xl font-bold text-gray-900 dark:text-white">
            CostsHub
          </span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
        {filteredNavItems.length > 0 ? (
          filteredNavItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href
            
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setIsMobileOpen(false)}
                className={cn(
                  "flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
                  "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
                  isActive 
                    ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300" 
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
                )}
                aria-current={isActive ? "page" : undefined}
                title={item.description}
              >
                <Icon className="w-5 h-5 mr-3" aria-hidden="true" />
                <span className="truncate">{item.name}</span>
              </Link>
            )
          })
        ) : (
          <div className="text-center py-8">
            <p className="text-sm text-gray-500">Loading navigation...</p>
          </div>
        )}
      </nav>

      {/* User info at bottom */}
      <div className="px-4 py-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
              <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
                {isLoading ? "..." : (user?.name?.charAt(0).toUpperCase() || "U")}
              </span>
            </div>
          </div>
          <div className="ml-3 min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {isLoading ? "Loading..." : (user?.name || "User")}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {isLoading ? "..." : (user?.role || "MEMBER")}
            </p>
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <>
      {/* Mobile menu button */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="bg-white dark:bg-gray-900"
          aria-label="Toggle navigation menu"
        >
          {isMobileOpen ? (
            <X className="h-4 w-4" />
          ) : (
            <Menu className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Mobile sidebar overlay */}
      {isMobileOpen && (
        <div 
          className="lg:hidden fixed inset-0 z-40 bg-black bg-opacity-50"
          onClick={() => setIsMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Desktop sidebar */}
      <div className={cn(
        "lg:flex lg:flex-col lg:w-64 lg:fixed lg:inset-y-0",
        "bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700",
        className
      )}>
        <SidebarContent />
      </div>

      {/* Mobile sidebar */}
      <div className={cn(
        "lg:hidden fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-300 ease-in-out",
        "bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700",
        isMobileOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <SidebarContent />
      </div>
    </>
  )
}