<script setup>
import { defineProps } from 'vue';
import Card from 'primevue/card';
import ProgressSpinner from 'primevue/progressspinner';

// Props do componente
const props = defineProps({
  isLoading: {
    type: Boolean,
    default: false
  },
  summaryText: {
    type: String,
    default: ''
  }
});
</script>

<template>
  <Card class="ai-summary-card">
    <template #header>
      <div class="ai-header">
        <div class="ai-icon">
          <i class="pi pi-sparkles"></i>
        </div>
        <div class="ai-title">
          <h3>Resumo Executivo</h3>
          <span class="ai-subtitle">Análise inteligente dos seus custos</span>
        </div>
      </div>
    </template>
    
    <template #content>
      <!-- Estado de Loading -->
      <div v-if="isLoading" class="loading-state">
        <ProgressSpinner />
        <p>Analisando seus custos...</p>
      </div>
      
      <!-- Conteúdo do Resumo -->
      <div v-else-if="summaryText" class="summary-content">
        <p class="summary-text">{{ summaryText }}</p>
        <div class="ai-badge">
          <i class="pi pi-verified"></i>
          <span>Gerado por IA</span>
        </div>
      </div>
      
      <!-- Estado Vazio -->
      <div v-else class="empty-state">
        <i class="pi pi-info-circle"></i>
        <p>Nenhum resumo disponível para este período.</p>
      </div>
    </template>
  </Card>
</template>

<style scoped>
.ai-summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  margin-bottom: 1.5rem;
}

.ai-summary-card :deep(.p-card-header) {
  background: transparent;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  padding: 1.5rem 1.5rem 1rem 1.5rem;
}

.ai-summary-card :deep(.p-card-content) {
  background: transparent;
  padding: 1rem 1.5rem 1.5rem 1.5rem;
}

.ai-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.ai-icon {
  width: 48px;
  height: 48px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.ai-title h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.ai-subtitle {
  font-size: 0.875rem;
  opacity: 0.8;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem;
  text-align: center;
}

.loading-state p {
  margin: 0;
  font-size: 1rem;
  opacity: 0.9;
}

.summary-content {
  position: relative;
}

.summary-text {
  font-size: 1.1rem;
  line-height: 1.6;
  margin: 0 0 1rem 0;
  font-weight: 400;
}

.ai-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  opacity: 0.7;
  margin-top: 1rem;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  text-align: center;
  opacity: 0.8;
}

.empty-state i {
  font-size: 1.25rem;
}

.empty-state p {
  margin: 0;
}

/* Responsividade */
@media (max-width: 768px) {
  .ai-header {
    flex-direction: column;
    text-align: center;
    gap: 0.75rem;
  }
  
  .summary-text {
    font-size: 1rem;
  }
  
  .loading-state,
  .empty-state {
    padding: 1.5rem;
  }
}
</style>
