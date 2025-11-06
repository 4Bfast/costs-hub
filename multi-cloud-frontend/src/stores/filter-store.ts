import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { CostFilters } from '@/types/models'

interface SavedFilter {
  id: string
  name: string
  filters: CostFilters
  created_at: string
  updated_at: string
}

interface FilterStore {
  savedFilters: SavedFilter[]
  activeFilterId: string | null
  
  // Actions
  saveFilter: (name: string, filters: CostFilters) => void
  loadFilter: (id: string) => void
  deleteFilter: (id: string) => void
  updateFilter: (id: string, name: string, filters: CostFilters) => void
  clearActiveFilter: () => void
}

export const useFilterStore = create<FilterStore>()(
  persist(
    (set, get) => ({
      savedFilters: [],
      activeFilterId: null,

      saveFilter: (name: string, filters: CostFilters) => {
        const newFilter: SavedFilter = {
          id: crypto.randomUUID(),
          name,
          filters,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }

        set((state) => ({
          savedFilters: [...state.savedFilters, newFilter],
          activeFilterId: newFilter.id,
        }))
      },

      loadFilter: (id: string) => {
        set({ activeFilterId: id })
      },

      deleteFilter: (id: string) => {
        set((state) => ({
          savedFilters: state.savedFilters.filter((filter) => filter.id !== id),
          activeFilterId: state.activeFilterId === id ? null : state.activeFilterId,
        }))
      },

      updateFilter: (id: string, name: string, filters: CostFilters) => {
        set((state) => ({
          savedFilters: state.savedFilters.map((filter) =>
            filter.id === id
              ? {
                  ...filter,
                  name,
                  filters,
                  updated_at: new Date().toISOString(),
                }
              : filter
          ),
        }))
      },

      clearActiveFilter: () => {
        set({ activeFilterId: null })
      },
    }),
    {
      name: 'cost-analysis-filters',
      partialize: (state) => ({
        savedFilters: state.savedFilters,
        activeFilterId: state.activeFilterId,
      }),
    }
  )
)