import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';

export interface UIState {
  // Theme
  theme: Theme;
  
  // Sidebar
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  
  // Notifications
  notifications: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message: string;
    timestamp: number;
    read: boolean;
  }>;
  
  // Modals and dialogs
  modals: {
    onboarding: boolean;
    userInvite: boolean;
    accountConnection: boolean;
    alarmCreation: boolean;
  };
  
  // Dashboard preferences
  dashboardPreferences: {
    defaultPeriod: '7d' | '30d' | '90d' | '1y';
    defaultProviders: string[];
    refreshInterval: number; // in seconds
    compactView: boolean;
  };
  
  // Filter states (for maintaining filter state across navigation)
  filters: {
    costAnalysis: {
      dateRange: { start: string; end: string } | null;
      providers: string[];
      services: string[];
      accounts: string[];
    };
    insights: {
      severity: string[];
      type: string[];
      status: string[];
    };
    alarms: {
      status: string[];
      type: string[];
    };
  };
  
  // Actions
  setTheme: (theme: Theme) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  addNotification: (notification: Omit<UIState['notifications'][0], 'id' | 'timestamp' | 'read'>) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;
  openModal: (modal: keyof UIState['modals']) => void;
  closeModal: (modal: keyof UIState['modals']) => void;
  updateDashboardPreferences: (preferences: Partial<UIState['dashboardPreferences']>) => void;
  updateFilters: (filterType: keyof UIState['filters'], filters: any) => void;
  clearFilters: (filterType: keyof UIState['filters']) => void;
  reset: () => void;
}

const initialState = {
  theme: 'system' as Theme,
  sidebarOpen: true,
  sidebarCollapsed: false,
  notifications: [],
  modals: {
    onboarding: false,
    userInvite: false,
    accountConnection: false,
    alarmCreation: false,
  },
  dashboardPreferences: {
    defaultPeriod: '30d' as const,
    defaultProviders: [],
    refreshInterval: 300, // 5 minutes
    compactView: false,
  },
  filters: {
    costAnalysis: {
      dateRange: null,
      providers: [],
      services: [],
      accounts: [],
    },
    insights: {
      severity: [],
      type: [],
      status: [],
    },
    alarms: {
      status: [],
      type: [],
    },
  },
};

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      ...initialState,

      // Theme actions
      setTheme: (theme) => {
        set({ theme });
        
        // Apply theme to document
        if (typeof window !== 'undefined') {
          const root = window.document.documentElement;
          
          if (theme === 'system') {
            const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            root.classList.toggle('dark', systemTheme === 'dark');
          } else {
            root.classList.toggle('dark', theme === 'dark');
          }
        }
      },

      // Sidebar actions
      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }));
      },

      setSidebarCollapsed: (collapsed) => {
        set({ sidebarCollapsed: collapsed });
      },

      // Notification actions
      addNotification: (notification) => {
        const id = `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const newNotification = {
          ...notification,
          id,
          timestamp: Date.now(),
          read: false,
        };
        
        set((state) => ({
          notifications: [newNotification, ...state.notifications].slice(0, 50), // Keep only last 50
        }));
        
        return id;
      },

      markNotificationRead: (id) => {
        set((state) => ({
          notifications: state.notifications.map((notification) =>
            notification.id === id ? { ...notification, read: true } : notification
          ),
        }));
      },

      clearNotifications: () => {
        set({ notifications: [] });
      },

      // Modal actions
      openModal: (modal) => {
        set((state) => ({
          modals: { ...state.modals, [modal]: true },
        }));
      },

      closeModal: (modal) => {
        set((state) => ({
          modals: { ...state.modals, [modal]: false },
        }));
      },

      // Dashboard preferences
      updateDashboardPreferences: (preferences) => {
        set((state) => ({
          dashboardPreferences: { ...state.dashboardPreferences, ...preferences },
        }));
      },

      // Filter actions
      updateFilters: (filterType, filters) => {
        set((state) => ({
          filters: {
            ...state.filters,
            [filterType]: { ...state.filters[filterType], ...filters },
          },
        }));
      },

      clearFilters: (filterType) => {
        set((state) => ({
          filters: {
            ...state.filters,
            [filterType]: initialState.filters[filterType],
          },
        }));
      },

      // Reset all UI state
      reset: () => {
        set(initialState);
      },
    }),
    {
      name: 'ui-storage',
      storage: createJSONStorage(() => localStorage),
      // Don't persist notifications and modals
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        dashboardPreferences: state.dashboardPreferences,
        filters: state.filters,
      }),
    }
  )
);

// Selectors for common use cases
export const useTheme = () => useUIStore((state) => state.theme);
export const useSidebar = () => useUIStore((state) => ({
  isOpen: state.sidebarOpen,
  isCollapsed: state.sidebarCollapsed,
  toggle: state.toggleSidebar,
  setCollapsed: state.setSidebarCollapsed,
}));

export const useNotifications = () => useUIStore((state) => ({
  notifications: state.notifications,
  unreadCount: state.notifications.filter(n => !n.read).length,
  add: state.addNotification,
  markRead: state.markNotificationRead,
  clear: state.clearNotifications,
}));

export const useModals = () => useUIStore((state) => ({
  modals: state.modals,
  open: state.openModal,
  close: state.closeModal,
}));

export const useDashboardPreferences = () => useUIStore((state) => ({
  preferences: state.dashboardPreferences,
  update: state.updateDashboardPreferences,
}));

export const useFilters = () => useUIStore((state) => ({
  filters: state.filters,
  update: state.updateFilters,
  clear: state.clearFilters,
}));

// Theme initialization helper
export const initializeTheme = () => {
  const theme = useUIStore.getState().theme;
  
  if (typeof window !== 'undefined') {
    const root = window.document.documentElement;
    
    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      root.classList.toggle('dark', systemTheme === 'dark');
      
      // Listen for system theme changes
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e: MediaQueryListEvent) => {
        if (useUIStore.getState().theme === 'system') {
          root.classList.toggle('dark', e.matches);
        }
      };
      
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } else {
      root.classList.toggle('dark', theme === 'dark');
    }
  }
};