"use client"

import React from "react"
import { Sidebar } from "./sidebar"
import { Header } from "./header"
import { cn } from "@/lib/utils"

interface DashboardLayoutProps {
  children: React.ReactNode
  className?: string
}

export function DashboardLayout({ children, className }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Sidebar />
      <div className="lg:pl-64">
        <Header />
        <main 
          className={cn(
            "pt-16 px-4 sm:px-6 lg:px-8 py-8",
            className
          )}
          role="main"
          aria-label="Main content"
        >
          {children}
        </main>
      </div>
    </div>
  )
}