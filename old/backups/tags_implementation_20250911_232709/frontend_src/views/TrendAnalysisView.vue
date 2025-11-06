<script setup>
import { ref, onMounted } from 'vue';
import { apiService } from '@/services/api';
import Card from 'primevue/card';
import Button from 'primevue/button';
import ProgressSpinner from 'primevue/progressspinner';
import Message from 'primevue/message';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';

// Importar Chart.js
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { Line } from 'vue-chartjs';

// Registrar componentes do Chart.js
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

// Estados
const isLoading = ref(false);
const error = ref(null);
const trendsData = ref(null);
const aiSummary = ref('');
const chartData = ref(null);
const forecastData = ref(null);
const isLoadingAI = ref(false);
const isLoadingChart = ref(false);
const isLoadingForecast = ref(false);
const selectedPeriod = ref('3months');

// Opções de período
const periodOptions = [
  { label: 'Últimos 3 meses', value: '3months', days: 90 },
  { label: 'Últimos 6 meses', value: '6months', days: 180 },
  { label: 'Último ano', value: '12months', days: 365 }
];

async function fetchTrendsData() {
  isLoading.value = true;
  error.value = null;
  
  try {
    const period = periodOptions.find(p => p.value === selectedPeriod.value);
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - period.days);
    
    const startDateStr = startDate.toISOString().split('T')[0];
    const endDateStr = endDate.toISOString().split('T')[0];
    
    // Carregar dados básicos primeiro
    const response = await apiService.getTrendsAnalysis(startDateStr, endDateStr);
    trendsData.value = response;
    
    // Carregar IA e gráfico em paralelo (independentes)
    loadAISummary(startDateStr, endDateStr);
    loadChartData(); // Gráfico não precisa de parâmetros, usa últimos 6 meses
    loadForecastData();
    
  } catch (err) {
    error.value = err.message || 'Erro ao carregar análise de tendências';
  } finally {
    isLoading.value = false;
  }
}

async function loadAISummary(startDate, endDate) {
  isLoadingAI.value = true;
  try {
    const response = await apiService.getTrendsAISummary(startDate, endDate);
    aiSummary.value = response.aiSummary;
  } catch (err) {
    aiSummary.value = 'Resumo IA temporariamente indisponível.';
  } finally {
    isLoadingAI.value = false;
  }
}

async function loadChartData() {
  isLoadingChart.value = true;
  try {
    const response = await apiService.getTrendsChart();
    chartData.value = response.chartData;
  } catch (err) {
    chartData.value = {
      labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
      datasets: [{
        label: 'Custo Mensal',
        data: [100, 120, 110, 140, 130, 150],
        backgroundColor: '#3B82F6',
        borderColor: '#1D4ED8',
        borderWidth: 3,
        pointRadius: 8
      }]
    };
  } finally {
    isLoadingChart.value = false;
  }
}

async function loadForecastData() {
  isLoadingForecast.value = true;
  try {
    const response = await apiService.getTrendsForecast();
    forecastData.value = response;
  } catch (err) {
    forecastData.value = {
      projected30Days: 0,
      projectedChange: 0,
      growthRate: 0,
      newServices: []
    };
  } finally {
    isLoadingForecast.value = false;
  }
}

onMounted(() => {
  fetchTrendsData();
});

// Funções para previsão (agora usando dados reais dos últimos 7 dias)
function getForecastValue() {
  return forecastData.value?.projected30Days || 0;
}

function getForecastChange() {
  return forecastData.value?.projectedChange || 0;
}

function getForecastPercent() {
  const current = trendsData.value?.trendTables?.summary?.totalCost || 0;
  return current > 0 ? (getForecastChange() / current) * 100 : 0;
}
</script>

<template>
  <div class="trends-page">
    <div class="page-header">
      <h1>Análise de Tendências</h1>
      <p>Motor de justificativa de variações de custo</p>
    </div>

    <!-- Controles de Período -->
    <Card class="mb-4">
      <template #content>
        <div class="period-controls">
          <Button 
            v-for="period in periodOptions"
            :key="period.value"
            :label="period.label"
            :class="selectedPeriod === period.value ? 'p-button-primary' : 'p-button-outlined'"
            @click="selectedPeriod = period.value; fetchTrendsData()"
          />
        </div>
      </template>
    </Card>

    <!-- Loading -->
    <div v-if="isLoading" class="loading-section">
      <ProgressSpinner />
      <span>Analisando tendências...</span>
    </div>

    <!-- Error -->
    <Message v-else-if="error" severity="error" class="mb-4">
      {{ error }}
    </Message>

    <!-- Conteúdo -->
    <div v-else-if="trendsData">
      <!-- Resumo Executivo IA -->
      <Card class="ai-summary-card mb-4">
        <template #header>
          <div class="ai-header">
            <i class="pi pi-chart-line"></i>
            <h3>Análise Executiva</h3>
          </div>
        </template>
        <template #content>
          <div v-if="isLoadingAI" class="loading-ai">
            <ProgressSpinner size="small" />
            <span>Gerando análise...</span>
          </div>
          <p v-else class="ai-summary-text">{{ aiSummary }}</p>
        </template>
      </Card>

      <!-- Previsão 30 Dias -->
      <Card class="forecast-card mb-4" v-if="forecastData">
        <template #header>
          <div class="forecast-header">
            <i class="pi pi-forward"></i>
            <h3>Previsão - Próximos 30 Dias</h3>
            <small>(Baseada nos últimos 7 dias)</small>
          </div>
        </template>
        <template #content>
          <div v-if="isLoadingForecast" class="loading-forecast">
            <ProgressSpinner size="small" />
            <span>Calculando previsão...</span>
          </div>
          <div v-else class="forecast-content">
            <div class="forecast-item">
              <span class="forecast-label">Custo Projetado:</span>
              <span class="forecast-value">${{ getForecastValue().toFixed(2) }}</span>
            </div>
            <div class="forecast-item">
              <span class="forecast-label">Variação Esperada:</span>
              <span :class="getForecastChange() > 0 ? 'forecast-increase' : 'forecast-decrease'">
                ${{ getForecastChange().toFixed(2) }} ({{ getForecastPercent().toFixed(1) }}%)
              </span>
            </div>
            <div class="forecast-item" v-if="forecastData.growthRate">
              <span class="forecast-label">Taxa de Crescimento Diário:</span>
              <span :class="forecastData.growthRate > 0 ? 'forecast-increase' : 'forecast-decrease'">
                {{ forecastData.growthRate.toFixed(2) }}%
              </span>
            </div>
            <div v-if="forecastData.newServices?.length > 0" class="new-services">
              <strong>Novos Serviços Detectados:</strong>
              <ul>
                <li v-for="service in forecastData.newServices" :key="service.service">
                  {{ service.service }} (~${{ service.dailyCost.toFixed(2) }}/dia)
                </li>
              </ul>
            </div>
          </div>
        </template>
      </Card>

      <!-- Gráfico -->
      <Card class="mb-4">
        <template #title>Evolução Mensal de Custos</template>
        <template #content>
          <div v-if="isLoadingChart" class="loading-chart">
            <ProgressSpinner />
            <span>Carregando gráfico...</span>
          </div>
          <div v-else-if="chartData" class="chart-container">
            <Line 
              :data="chartData" 
              :options="{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'top'
                  },
                  title: {
                    display: true,
                    text: 'Evolução dos Últimos 6 Meses'
                  }
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    ticks: {
                      callback: function(value) {
                        return '$' + value.toFixed(0);
                      }
                    },
                    grid: {
                      color: '#E5E7EB'
                    }
                  },
                  x: {
                    grid: {
                      display: false
                    }
                  }
                },
                elements: {
                  point: {
                    radius: 8,
                    hoverRadius: 12,
                    backgroundColor: '#1D4ED8',
                    borderColor: '#ffffff',
                    borderWidth: 3
                  },
                  line: {
                    tension: 0.2,
                    borderWidth: 3
                  }
                },
                interaction: {
                  intersect: false,
                  mode: 'index'
                }
              }"
            />
          </div>
        </template>
      </Card>

      <!-- Tabela de Análise -->
      <Card>
        <template #title>Análise Detalhada por Serviço</template>
        <template #content>
          <DataTable :value="trendsData.trendTables.byService">
            <Column field="service" header="Serviço" />
            <Column field="currentCost" header="Custo Atual">
              <template #body="slotProps">
                ${{ slotProps.data.currentCost?.toFixed(2) }}
              </template>
            </Column>
            <Column field="previousCost" header="Custo Anterior">
              <template #body="slotProps">
                ${{ slotProps.data.previousCost?.toFixed(2) }}
              </template>
            </Column>
            <Column field="variationValue" header="Variação">
              <template #body="slotProps">
                <span :class="slotProps.data.variationValue > 0 ? 'text-red-500' : 'text-green-500'">
                  ${{ slotProps.data.variationValue?.toFixed(2) }}
                </span>
              </template>
            </Column>
          </DataTable>
        </template>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.trends-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header h1 {
  margin: 0 0 0.5rem 0;
  color: #1f2937;
}

.page-header p {
  margin: 0;
  color: #6b7280;
}

.period-controls {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.loading-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
}

.ai-summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.forecast-card {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
}

.ai-header, .forecast-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
}

.ai-header i, .forecast-header i {
  font-size: 1.5rem;
}

.ai-summary-text {
  font-size: 1.1rem;
  line-height: 1.8;
  margin: 0;
  white-space: pre-line;
}

.forecast-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.forecast-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.forecast-label {
  font-weight: 500;
}

.forecast-value {
  font-size: 1.2rem;
  font-weight: 700;
}

.forecast-increase {
  color: #ff6b6b;
  font-weight: 600;
}

.forecast-decrease {
  color: #51cf66;
  font-weight: 600;
}

.chart-container {
  height: 400px;
  width: 100%;
}
</style>
