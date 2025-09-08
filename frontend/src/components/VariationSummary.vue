<script setup>
import { computed } from 'vue';
import Tag from 'primevue/tag';

// Props
const props = defineProps({
  summaryData: {
    type: Object,
    default: () => ({})
  },
  dateRange: {
    type: Array,
    default: () => []
  }
});

// Computed properties
const formattedDateRange = computed(() => {
  if (!props.dateRange || props.dateRange.length !== 2) return '';
  const start = props.dateRange[0];
  const end = props.dateRange[1];
  return `${start.toLocaleDateString('pt-BR')} - ${end.toLocaleDateString('pt-BR')}`;
});

// Métodos de formatação
const formatCurrency = (value) => {
  if (value === null || value === undefined) return 'R$ 0,00';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value);
};

const formatPercentage = (value) => {
  if (value === null || value === undefined) return '0,00%';
  return new Intl.NumberFormat('pt-BR', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value / 100);
};
</script>

<template>
  <div class="variation-summary">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900">Resumo da Análise</h3>
      <Tag :value="formattedDateRange" severity="info" v-if="formattedDateRange" />
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Total de Recursos -->
      <div class="metric-card bg-blue-50 border-blue-200">
        <div class="metric-icon text-blue-600">
          <i class="pi pi-server text-2xl"></i>
        </div>
        <div class="metric-content">
          <div class="metric-value text-blue-600">
            {{ summaryData?.total_resources || 0 }}
          </div>
          <div class="metric-label">Recursos Analisados</div>
        </div>
      </div>

      <!-- Total de Tipos de Uso -->
      <div class="metric-card bg-green-50 border-green-200">
        <div class="metric-icon text-green-600">
          <i class="pi pi-list text-2xl"></i>
        </div>
        <div class="metric-content">
          <div class="metric-value text-green-600">
            {{ summaryData?.total_usage_types || 0 }}
          </div>
          <div class="metric-label">Tipos de Uso</div>
        </div>
      </div>

      <!-- Aumento Total de Custo -->
      <div class="metric-card bg-red-50 border-red-200">
        <div class="metric-icon text-red-600">
          <i class="pi pi-arrow-up text-2xl"></i>
        </div>
        <div class="metric-content">
          <div class="metric-value text-red-600">
            {{ formatCurrency(summaryData?.total_cost_increase || 0) }}
          </div>
          <div class="metric-label">Aumento Total</div>
        </div>
      </div>

      <!-- Variação Média -->
      <div class="metric-card bg-yellow-50 border-yellow-200">
        <div class="metric-icon text-yellow-600">
          <i class="pi pi-percentage text-2xl"></i>
        </div>
        <div class="metric-content">
          <div class="metric-value text-yellow-600">
            {{ formatPercentage(summaryData?.avg_variation || 0) }}
          </div>
          <div class="metric-label">Variação Média</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.variation-summary {
  padding: 1.5rem;
  background-color: white;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
}

.metric-card {
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid;
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: all 0.2s;
}

.metric-card:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.metric-icon {
  flex-shrink: 0;
}

.metric-content {
  flex: 1;
  min-width: 0;
}

.metric-value {
  font-size: 1.5rem;
  font-weight: bold;
  line-height: 1.2;
}

.metric-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-top: 0.25rem;
}

/* Cores específicas para cada métrica */
.bg-blue-50 {
  background-color: #eff6ff;
}

.border-blue-200 {
  border-color: #bfdbfe;
}

.bg-green-50 {
  background-color: #f0fdf4;
}

.border-green-200 {
  border-color: #bbf7d0;
}

.bg-red-50 {
  background-color: #fef2f2;
}

.border-red-200 {
  border-color: #fecaca;
}

.bg-yellow-50 {
  background-color: #fffbeb;
}

.border-yellow-200 {
  border-color: #fde68a;
}

.text-blue-600 {
  color: #2563eb;
}

.text-green-600 {
  color: #16a34a;
}

.text-red-600 {
  color: #dc2626;
}

.text-yellow-600 {
  color: #d97706;
}

.text-gray-900 {
  color: #111827;
}

.text-gray-600 {
  color: #6b7280;
}
</style>
