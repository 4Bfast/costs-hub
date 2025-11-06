/**
 * Performance Optimization Utilities
 * Client-side performance enhancements and monitoring
 */

// Resource hints for critical resources
export function addResourceHints(): void {
  if (typeof window === 'undefined') return

  const head = document.head

  // Preconnect to external domains
  const preconnectDomains = [
    'https://fonts.googleapis.com',
    'https://fonts.gstatic.com',
    process.env.NEXT_PUBLIC_API_BASE_URL,
    process.env.NEXT_PUBLIC_CDN_URL,
  ].filter(Boolean)

  preconnectDomains.forEach(domain => {
    if (domain && !document.querySelector(`link[href="${domain}"]`)) {
      const link = document.createElement('link')
      link.rel = 'preconnect'
      link.href = domain
      link.crossOrigin = 'anonymous'
      head.appendChild(link)
    }
  })

  // DNS prefetch for analytics and monitoring
  const dnsPrefetchDomains = [
    'https://www.google-analytics.com',
    'https://www.googletagmanager.com',
  ]

  dnsPrefetchDomains.forEach(domain => {
    if (!document.querySelector(`link[href="${domain}"]`)) {
      const link = document.createElement('link')
      link.rel = 'dns-prefetch'
      link.href = domain
      head.appendChild(link)
    }
  })
}

// Lazy loading for images and components
export function setupLazyLoading(): void {
  if (typeof window === 'undefined') return

  // Native lazy loading support check
  if ('loading' in HTMLImageElement.prototype) {
    const images = document.querySelectorAll('img[data-src]')
    images.forEach(img => {
      const imageElement = img as HTMLImageElement
      imageElement.src = imageElement.dataset.src || ''
      imageElement.loading = 'lazy'
    })
  } else {
    // Fallback for browsers without native lazy loading
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target as HTMLImageElement
          img.src = img.dataset.src || ''
          img.classList.remove('lazy')
          observer.unobserve(img)
        }
      })
    })

    const lazyImages = document.querySelectorAll('img[data-src]')
    lazyImages.forEach(img => imageObserver.observe(img))
  }
}

// Critical CSS inlining
export function inlineCriticalCSS(): void {
  if (typeof window === 'undefined') return

  // This would typically be done at build time
  // Here we can add runtime optimizations for dynamic content
  const criticalStyles = `
    /* Critical above-the-fold styles */
    .loading-skeleton {
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: loading 1.5s infinite;
    }
    
    @keyframes loading {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
    
    .fade-in {
      opacity: 0;
      animation: fadeIn 0.3s ease-in-out forwards;
    }
    
    @keyframes fadeIn {
      to { opacity: 1; }
    }
  `

  if (!document.getElementById('critical-css')) {
    const style = document.createElement('style')
    style.id = 'critical-css'
    style.textContent = criticalStyles
    document.head.appendChild(style)
  }
}

// Service Worker registration for caching
export function registerServiceWorker(): void {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return

  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js')
      console.log('SW registered: ', registration)
      
      // Update available
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New content available, show update notification
              showUpdateNotification()
            }
          })
        }
      })
    } catch (error) {
      console.log('SW registration failed: ', error)
    }
  })
}

function showUpdateNotification(): void {
  // Show a notification to the user that an update is available
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('App Update Available', {
      body: 'A new version of CostsHub is available. Refresh to update.',
      icon: '/icon-192x192.png',
    })
  }
}

// Bundle splitting and dynamic imports
export const loadChunk = async (chunkName: string) => {
  try {
    switch (chunkName) {
      case 'charts':
        return await import('@/components/charts')
      case 'dashboard':
        return await import('@/app/dashboard/page')
      case 'analytics':
        return await import('@/lib/analytics')
      default:
        throw new Error(`Unknown chunk: ${chunkName}`)
    }
  } catch (error) {
    console.error(`Failed to load chunk ${chunkName}:`, error)
    throw error
  }
}

// Memory management
export function setupMemoryManagement(): void {
  if (typeof window === 'undefined') return

  // Clean up event listeners on page unload
  window.addEventListener('beforeunload', () => {
    // Remove all event listeners
    const elements = document.querySelectorAll('[data-cleanup]')
    elements.forEach(element => {
      const events = element.getAttribute('data-cleanup')?.split(',') || []
      events.forEach(event => {
        element.removeEventListener(event.trim(), () => {})
      })
    })
  })

  // Monitor memory usage (if available)
  if ('memory' in performance) {
    const memoryInfo = (performance as any).memory
    if (memoryInfo.usedJSHeapSize > memoryInfo.jsHeapSizeLimit * 0.9) {
      console.warn('High memory usage detected')
      // Trigger garbage collection if possible
      if ('gc' in window) {
        (window as any).gc()
      }
    }
  }
}

// Network optimization
export function optimizeNetworkRequests(): void {
  if (typeof window === 'undefined') return

  // Request deduplication
  const requestCache = new Map<string, Promise<any>>()

  const originalFetch = window.fetch
  window.fetch = function(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const url = typeof input === 'string' ? input : input.toString()
    const method = init?.method || 'GET'
    const cacheKey = `${method}:${url}`

    // Only cache GET requests
    if (method === 'GET' && requestCache.has(cacheKey)) {
      return requestCache.get(cacheKey)!
    }

    const request = originalFetch.call(this, input, init)
    
    if (method === 'GET') {
      requestCache.set(cacheKey, request)
      
      // Clean up cache after 5 minutes
      setTimeout(() => {
        requestCache.delete(cacheKey)
      }, 5 * 60 * 1000)
    }

    return request
  }
}

// Image optimization
export function optimizeImages(): void {
  if (typeof window === 'undefined') return

  // Convert images to WebP if supported
  const supportsWebP = (() => {
    const canvas = document.createElement('canvas')
    canvas.width = 1
    canvas.height = 1
    return canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0
  })()

  if (supportsWebP) {
    const images = document.querySelectorAll('img[data-webp]')
    images.forEach(img => {
      const imageElement = img as HTMLImageElement
      const webpSrc = imageElement.dataset.webp
      if (webpSrc) {
        imageElement.src = webpSrc
      }
    })
  }

  // Responsive images based on device pixel ratio
  const pixelRatio = window.devicePixelRatio || 1
  const images = document.querySelectorAll('img[data-srcset]')
  
  images.forEach(img => {
    const imageElement = img as HTMLImageElement
    const srcset = imageElement.dataset.srcset
    if (srcset) {
      const sources = srcset.split(',').map(s => s.trim())
      const appropriateSource = sources.find(source => {
        const ratio = parseFloat(source.split(' ')[1]?.replace('x', '') || '1')
        return ratio >= pixelRatio
      }) || sources[sources.length - 1]
      
      imageElement.src = appropriateSource.split(' ')[0]
    }
  })
}

// Initialize all performance optimizations
export function initializePerformanceOptimizations(): void {
  if (typeof window === 'undefined') return

  // Run optimizations after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      runOptimizations()
    })
  } else {
    runOptimizations()
  }
}

function runOptimizations(): void {
  addResourceHints()
  setupLazyLoading()
  inlineCriticalCSS()
  registerServiceWorker()
  setupMemoryManagement()
  optimizeNetworkRequests()
  optimizeImages()
}

// Performance budget monitoring
export function monitorPerformanceBudget(): void {
  if (typeof window === 'undefined') return

  const budgets = {
    firstContentfulPaint: 1500, // 1.5s
    largestContentfulPaint: 2500, // 2.5s
    firstInputDelay: 100, // 100ms
    cumulativeLayoutShift: 0.1, // 0.1
    totalBlockingTime: 300, // 300ms
  }

  // Monitor using Performance Observer
  if ('PerformanceObserver' in window) {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const entryName = entry.name.toLowerCase().replace(/\s+/g, '')
        const budget = budgets[entryName as keyof typeof budgets]
        
        if (budget && entry.value > budget) {
          console.warn(`Performance budget exceeded for ${entry.name}: ${entry.value}ms (budget: ${budget}ms)`)
          
          // Report to analytics
          if (typeof window !== 'undefined' && 'gtag' in window) {
            (window as any).gtag('event', 'performance_budget_exceeded', {
              metric_name: entry.name,
              metric_value: entry.value,
              budget_value: budget,
            })
          }
        }
      }
    })

    observer.observe({ entryTypes: ['measure', 'navigation', 'paint'] })
  }
}