/**
 * Service Worker for CostsHub Frontend
 * Provides offline functionality and caching strategies
 */

const CACHE_NAME = 'costs-hub-v1.0.0'
const STATIC_CACHE = 'costs-hub-static-v1.0.0'
const DYNAMIC_CACHE = 'costs-hub-dynamic-v1.0.0'
const API_CACHE = 'costs-hub-api-v1.0.0'

// Assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/dashboard',
  '/login',
  '/offline',
  '/manifest.json',
  '/icon-192x192.png',
  '/icon-512x512.png',
  // Add other critical assets
]

// API endpoints to cache
const API_ENDPOINTS = [
  '/api/auth/me',
  '/api/dashboard/summary',
  '/api/accounts',
]

// Cache strategies
const CACHE_STRATEGIES = {
  // Cache first, then network (for static assets)
  CACHE_FIRST: 'cache-first',
  // Network first, then cache (for dynamic content)
  NETWORK_FIRST: 'network-first',
  // Stale while revalidate (for API data)
  STALE_WHILE_REVALIDATE: 'stale-while-revalidate',
  // Network only (for sensitive data)
  NETWORK_ONLY: 'network-only',
}

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...')
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('Caching static assets')
        return cache.addAll(STATIC_ASSETS)
      })
      .then(() => {
        return self.skipWaiting()
      })
  )
})

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...')
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== STATIC_CACHE && 
                cacheName !== DYNAMIC_CACHE && 
                cacheName !== API_CACHE) {
              console.log('Deleting old cache:', cacheName)
              return caches.delete(cacheName)
            }
          })
        )
      })
      .then(() => {
        return self.clients.claim()
      })
  )
})

// Fetch event - handle requests with appropriate caching strategy
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return
  }
  
  // Skip chrome-extension and other non-http requests
  if (!url.protocol.startsWith('http')) {
    return
  }
  
  // Determine caching strategy based on request
  let strategy = getCachingStrategy(request)
  
  event.respondWith(
    handleRequest(request, strategy)
  )
})

// Determine caching strategy based on request
function getCachingStrategy(request) {
  const url = new URL(request.url)
  
  // API requests
  if (url.pathname.startsWith('/api/')) {
    // Sensitive endpoints - network only
    if (url.pathname.includes('/auth/') || 
        url.pathname.includes('/settings/') ||
        url.pathname.includes('/admin/')) {
      return CACHE_STRATEGIES.NETWORK_ONLY
    }
    
    // Dashboard and analytics data - stale while revalidate
    if (url.pathname.includes('/dashboard/') ||
        url.pathname.includes('/analytics/') ||
        url.pathname.includes('/insights/')) {
      return CACHE_STRATEGIES.STALE_WHILE_REVALIDATE
    }
    
    // Other API data - network first
    return CACHE_STRATEGIES.NETWORK_FIRST
  }
  
  // Static assets (JS, CSS, images)
  if (url.pathname.match(/\.(js|css|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot|ico)$/)) {
    return CACHE_STRATEGIES.CACHE_FIRST
  }
  
  // HTML pages - network first with cache fallback
  return CACHE_STRATEGIES.NETWORK_FIRST
}

// Handle request with specified strategy
async function handleRequest(request, strategy) {
  switch (strategy) {
    case CACHE_STRATEGIES.CACHE_FIRST:
      return cacheFirst(request)
    
    case CACHE_STRATEGIES.NETWORK_FIRST:
      return networkFirst(request)
    
    case CACHE_STRATEGIES.STALE_WHILE_REVALIDATE:
      return staleWhileRevalidate(request)
    
    case CACHE_STRATEGIES.NETWORK_ONLY:
      return networkOnly(request)
    
    default:
      return networkFirst(request)
  }
}

// Cache first strategy
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request)
  
  if (cachedResponse) {
    return cachedResponse
  }
  
  try {
    const networkResponse = await fetch(request)
    
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE)
      cache.put(request, networkResponse.clone())
    }
    
    return networkResponse
  } catch (error) {
    console.error('Cache first failed:', error)
    return new Response('Offline', { status: 503 })
  }
}

// Network first strategy
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request)
    
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE)
      cache.put(request, networkResponse.clone())
    }
    
    return networkResponse
  } catch (error) {
    console.log('Network failed, trying cache:', error)
    
    const cachedResponse = await caches.match(request)
    
    if (cachedResponse) {
      return cachedResponse
    }
    
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline')
    }
    
    return new Response('Offline', { status: 503 })
  }
}

// Stale while revalidate strategy
async function staleWhileRevalidate(request) {
  const cachedResponse = await caches.match(request)
  
  // Always try to fetch from network in background
  const networkResponsePromise = fetch(request)
    .then((networkResponse) => {
      if (networkResponse.ok) {
        const cache = caches.open(API_CACHE)
        cache.then(c => c.put(request, networkResponse.clone()))
      }
      return networkResponse
    })
    .catch((error) => {
      console.log('Background fetch failed:', error)
    })
  
  // Return cached response immediately if available
  if (cachedResponse) {
    return cachedResponse
  }
  
  // If no cache, wait for network
  try {
    return await networkResponsePromise
  } catch (error) {
    return new Response('Offline', { status: 503 })
  }
}

// Network only strategy
async function networkOnly(request) {
  try {
    return await fetch(request)
  } catch (error) {
    return new Response('Network required', { status: 503 })
  }
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync())
  }
})

async function doBackgroundSync() {
  // Handle offline actions when back online
  console.log('Background sync triggered')
  
  // Example: sync offline analytics events
  try {
    const cache = await caches.open('offline-actions')
    const requests = await cache.keys()
    
    for (const request of requests) {
      try {
        await fetch(request)
        await cache.delete(request)
      } catch (error) {
        console.log('Failed to sync request:', error)
      }
    }
  } catch (error) {
    console.log('Background sync failed:', error)
  }
}

// Push notifications
self.addEventListener('push', (event) => {
  if (!event.data) {
    return
  }
  
  const data = event.data.json()
  
  const options = {
    body: data.body,
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    data: data.data,
    actions: [
      {
        action: 'view',
        title: 'View',
        icon: '/action-view.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/action-dismiss.png'
      }
    ]
  }
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  )
})

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  
  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow(event.notification.data.url || '/')
    )
  }
})

// Message handling from main thread
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
  
  if (event.data && event.data.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(DYNAMIC_CACHE)
        .then(cache => cache.addAll(event.data.urls))
    )
  }
})

// Error handling
self.addEventListener('error', (event) => {
  console.error('Service Worker error:', event.error)
})

self.addEventListener('unhandledrejection', (event) => {
  console.error('Service Worker unhandled rejection:', event.reason)
})