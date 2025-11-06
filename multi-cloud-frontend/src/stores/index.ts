// Export all stores from a central location
export * from './auth-store';
export * from './ui-store';

// Store initialization helper
export const initializeStores = () => {
  // Initialize theme on app startup
  const { initializeTheme } = require('./ui-store');
  return initializeTheme();
};