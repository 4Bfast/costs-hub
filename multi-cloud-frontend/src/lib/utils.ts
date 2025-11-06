import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(
  amount: number,
  currency: string = "USD",
  locale: string = "en-US"
): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatNumber(
  number: number,
  locale: string = "en-US"
): string {
  return new Intl.NumberFormat(locale).format(number)
}

export function formatPercentage(
  value: number,
  locale: string = "en-US"
): string {
  return new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value / 100)
}

export function formatDate(
  date: string | Date,
  locale: string = "en-US",
  options?: Intl.DateTimeFormatOptions
): string {
  const dateObj = typeof date === "string" ? new Date(date) : date
  
  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
  }
  
  return new Intl.DateTimeFormat(locale, options || defaultOptions).format(dateObj)
}

export function formatDateTime(
  date: string | Date,
  locale: string = "en-US"
): string {
  return formatDate(date, locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function getProviderColor(provider: string): string {
  switch (provider.toLowerCase()) {
    case "aws":
      return "#ff9900"
    case "gcp":
    case "google":
      return "#4285f4"
    case "azure":
    case "microsoft":
      return "#0078d4"
    default:
      return "#8b5cf6"
  }
}

export function getCostChangeColor(change: number): string {
  if (change > 0) return "#ef4444" // red for increase
  if (change < 0) return "#10b981" // green for decrease
  return "#6b7280" // gray for neutral
}

export function getCostChangeBadgeVariant(change: number): "destructive" | "default" | "secondary" {
  if (change > 10) return "destructive"
  if (change < -10) return "default"
  return "secondary"
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + "..."
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

export function generateId(): string {
  return Math.random().toString(36).substr(2, 9)
}

export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export function isValidUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}