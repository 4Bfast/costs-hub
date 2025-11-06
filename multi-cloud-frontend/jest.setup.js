import '@testing-library/jest-dom'

// Setup MSW for API mocking - temporarily disabled
// TODO: Fix MSW setup for API integration tests
// import { server } from './src/test-utils/mocks/server'

// Establish API mocking before all tests
// beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests
// afterEach(() => server.resetHandlers())

// Clean up after the tests are finished
// afterAll(() => server.close())

// Import custom matchers
import './src/test-utils/custom-matchers'

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
    }
  },
  useSearchParams() {
    return new URLSearchParams()
  },
  usePathname() {
    return '/'
  },
}))

// Mock environment variables
process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000'
process.env.NEXT_PUBLIC_APP_NAME = 'CostsHub'
process.env.NEXT_PUBLIC_APP_VERSION = '1.0.0'

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock PerformanceObserver
global.PerformanceObserver = class PerformanceObserver {
  constructor(callback) {
    this.callback = callback
  }
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock performance API
Object.defineProperty(global, 'performance', {
  writable: true,
  value: {
    ...global.performance,
    getEntriesByType: jest.fn(() => []),
    getEntries: jest.fn(() => []),
    mark: jest.fn(),
    measure: jest.fn(),
    now: jest.fn(() => Date.now()),
    clearMarks: jest.fn(),
    clearMeasures: jest.fn(),
    timing: {
      navigationStart: Date.now(),
      loadEventEnd: Date.now() + 1000,
    },
  },
})

// Mock Web APIs that might not be available in jsdom
global.requestIdleCallback = jest.fn((cb) => setTimeout(cb, 0))
global.cancelIdleCallback = jest.fn()

// Mock Intersection Observer API
global.IntersectionObserver = class IntersectionObserver {
  constructor(callback, options) {
    this.callback = callback
    this.options = options
  }
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})