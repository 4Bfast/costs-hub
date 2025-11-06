import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/auth-context";
import { OnboardingProvider } from "@/contexts/onboarding-context";
import { Providers } from "@/components/providers";
import { ErrorBoundary } from "@/components/error-boundary";
import { PerformanceProvider } from "@/components/providers/performance-provider";
import { AnalyticsProvider } from "@/components/analytics/analytics-provider";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: 'swap', // Optimize font loading
  preload: true,
});

export const metadata: Metadata = {
  title: "CostsHub - Multi-Cloud Cost Analytics",
  description: "AI-powered cost analytics across AWS, GCP, and Azure",
  keywords: ["cost analytics", "AWS", "GCP", "Azure", "multi-cloud", "AI"],
  authors: [{ name: "4bfast" }],
  creator: "4bfast",
  publisher: "4bfast",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  openGraph: {
    title: "CostsHub - Multi-Cloud Cost Analytics",
    description: "AI-powered cost analytics across AWS, GCP, and Azure",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "CostsHub - Multi-Cloud Cost Analytics",
    description: "AI-powered cost analytics across AWS, GCP, and Azure",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased keyboard-nav`}>
        {/* Skip to main content for screen readers */}
        <a href="#main-content" className="skip-to-main">
          Skip to main content
        </a>
        <ErrorBoundary>
          <PerformanceProvider>
            <Providers>
              <AuthProvider>
                <OnboardingProvider>
                  <AnalyticsProvider>
                    {children}
                  </AnalyticsProvider>
                </OnboardingProvider>
              </AuthProvider>
            </Providers>
          </PerformanceProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
