"use client"

import React from "react"
import { Sidebar } from "@/components/layout/sidebar"
import { Header } from "@/components/layout/header"

interface DashboardLayoutProps {
  children: React.ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Sidebar />
      <div className="lg:pl-64">
        <Header />
        <main 
          id="main-content"
          className="pt-16 px-4 sm:px-6 lg:px-8 py-8"
          role="main"
          aria-label="Main dashboard content"
        >
          {children}
        </main>
      </div>
    </div>
  )
}