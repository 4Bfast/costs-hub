import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { User, Organization } from '@/types/models';

export interface AuthState {
  // State
  user: User | null;
  organization: Organization | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  
  // Actions
  setUser: (user: User | null) => void;
  setOrganization: (organization: Organization | null) => void;
  setLoading: (loading: boolean) => void;
  login: (user: User, organization: Organization) => void;
  logout: () => void;
  updateUser: (updates: Partial<User>) => void;
  updateOrganization: (updates: Partial<Organization>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      organization: null,
      isAuthenticated: false,
      isLoading: false,

      // Actions
      setUser: (user) => {
        set({ 
          user, 
          isAuthenticated: !!user 
        });
      },

      setOrganization: (organization) => {
        set({ organization });
      },

      setLoading: (isLoading) => {
        set({ isLoading });
      },

      login: (user, organization) => {
        set({
          user,
          organization,
          isAuthenticated: true,
          isLoading: false,
        });
      },

      logout: () => {
        set({
          user: null,
          organization: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },

      updateUser: (updates) => {
        const { user } = get();
        if (user) {
          set({
            user: { ...user, ...updates },
          });
        }
      },

      updateOrganization: (updates) => {
        const { organization } = get();
        if (organization) {
          set({
            organization: { ...organization, ...updates },
          });
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      // Only persist essential auth state
      partialize: (state) => ({
        user: state.user,
        organization: state.organization,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Selectors for common use cases
export const useUser = () => useAuthStore((state) => state.user);
export const useOrganization = () => useAuthStore((state) => state.organization);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);

// Helper functions
export const getUserRole = () => {
  const user = useAuthStore.getState().user;
  return user?.role || null;
};

export const isAdmin = () => {
  const user = useAuthStore.getState().user;
  return user?.role === 'ADMIN';
};

export const getOrganizationId = () => {
  const organization = useAuthStore.getState().organization;
  return organization?.id || null;
};