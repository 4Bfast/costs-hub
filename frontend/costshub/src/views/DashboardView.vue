<script setup>
import { ref, onMounted, computed } from 'vue';
import { apiService } from '@/services/api';
import flatPickr from 'vue-flatpickr-component';
import 'flatpickr/dist/flatpickr.css';
import { Portuguese } from 'flatpickr/dist/l10n/pt.js';

// PrimeVue Components
import Card from 'primevue/card';
import Button from 'primevue/button';
import ButtonGroup from 'primevue/buttongroup';
import Chart from 'primevue/chart';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import ProgressBar from 'primevue/progressbar';
import ProgressSpinner from 'primevue/progressspinner';
import Message from 'primevue/message';

// --- GERENCIAMENTO DE ESTADO ---
const dashboardData = ref(null);
const isLoading = ref(true);
const error = ref(null);
const dateRange = ref([
  new Date(Date.now() - 29 * 24 * 60 * 60 * 1000), // 29 dias atrás
  new Date() // hoje
]);

// --- PROPRIEDADES COMPUTADAS ---
const kpis = computed(() => dashboardData.value?.kpis || {
  totalCost: 0,
  totalVariationPercentage: 0,
  totalVariationValue: 0,
  taxCost: 0,
  credits: 0
});

const chartData = computed(() => {
  if (!dashboardData.value?.timeSeries) return { labels: [], datasets: [] };
  
  const currentPeriod = dashboardData.value.timeSeries.currentPeriod || [];
  const previousPeriod = dashboardData.value.timeSeries.previousPeriod || [];
  
  // Criar labels baseados nas datas ou índices
  const maxLength = Math.max(currentPeriod.length, previousPeriod.length);
  const labels = currentPeriod.map((item, index) => {
    if (item.date) {
      return new Date(item.date).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
    }
    return `Dia ${index + 1}`;
  });
  
  return {
    labels,
    datasets: [
      {
        label: 'Período Atual',
        backgroundColor: '#007BFF',
        borderColor: '#007BFF',
        data: currentPeriod.map(d => d.cost || 0),
        tension: 0.4,
        fill: false,
        pointRadius: 4,
        pointHoverRadius: 6
      },
      {
        label: 'Período Anterior',
        backgroundColor: '#6c757d',
        borderColor: '#6c757d',
        borderDash: [5, 5],
        data: previousPeriod.map(d => d.cost || 0),
        tension: 0.4,
        fill: false,
        pointRadius: 3,
        pointHoverRadius: 5
      }
    ]
  };
});

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  aspectRatio: 0.5, // Força altura maior
  devicePixelRatio: 2, // Melhora qualidade
  layout: {
    padding: {
      top: 10,
      right: 10,
      bottom: 10,
      left: 10
    }
  },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: {
        usePointStyle: true,
        padding: 30,
        color: '#333',
        font: {
          size: 16,
          weight: 'bold'
        }
      }
    },
    tooltip: {
      mode: 'index',
      intersect: false,
      titleFont: {
        size: 16
      },
      bodyFont: {
        size: 14
      },
      callbacks: {
        label: function(context) {
          return `${context.dataset.label}: $${context.parsed.y.toFixed(2)}`;
        }
      }
    }
  },
  scales: {
    x: {
      display: true,
      title: {
        display: true,
        text: 'Período',
        color: '#666',
        font: {
          size: 16,
          weight: 'bold'
        }
      },
      grid: {
        color: '#e9ecef'
      },
      ticks: {
        font: {
          size: 14
        }
      }
    },
    y: {
      display: true,
      title: {
        display: true,
        text: 'Custo ($)',
        color: '#666',
        font: {
          size: 16,
          weight: 'bold'
        }
      },
      beginAtZero: true,
      grid: {
        color: '#e9ecef'
      },
      ticks: {
        font: {
          size: 14
        },
        callback: function(value) {
          return '$' + value.toFixed(2);
        }
      }
    }
  },
  elements: {
    point: {
      radius: 8,
      hoverRadius: 12
    },
    line: {
      borderWidth: 4
    }
  },
  interaction: {
    mode: 'nearest',
    axis: 'x',
    intersect: false
  }
}));

const serviceVariationData = computed(() => {
  const data = dashboardData.value?.serviceVariation || [];
  return data.sort((a, b) => Math.abs(b.variationValue || 0) - Math.abs(a.variationValue || 0));
});

const costByAccountData = computed(() => dashboardData.value?.costByAccount || []);

// --- CONFIGURAÇÃO DO DATE PICKER ---
const datePickerConfig = {
  mode: 'range',
  dateFormat: 'd/m/Y',
  locale: Portuguese,
  maxDate: new Date(),
  defaultDate: dateRange.value
};

// --- FUNÇÕES ---
async function fetchData() {
  if (!dateRange.value || dateRange.value.length !== 2) return;
  
  isLoading.value = true;
  error.value = null;
  dashboardData.value = null;

  try {
    const startDate = new Date(dateRange.value[0]);
    const endDate = new Date(dateRange.value[1]);
    
    if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
      throw new Error('Datas inválidas selecionadas');
    }
    
    const startDateStr = startDate.toISOString().split('T')[0];
    const endDateStr = endDate.toISOString().split('T')[0];
    
    console.log('Fetching dashboard data:', { startDateStr, endDateStr });
    dashboardData.value = await apiService.getDashboardData(startDateStr, endDateStr);
    console.log('Dashboard data received:', dashboardData.value);
  } catch (err) {
    console.error('Error fetching dashboard data:', err);
    error.value = err.message || 'Ocorreu um erro ao carregar os dados do dashboard.';
    dashboardData.value = null;
  } finally {
    isLoading.value = false;
  }
}

function onDateRangeChange(selectedDates) {
  if (selectedDates.length === 2) {
    dateRange.value = selectedDates;
    fetchData();
  }
}

// Funções dos botões de período pré-definido
function setLast7Days() {
  const endDate = new Date();
  const startDate = new Date(endDate);
  startDate.setDate(endDate.getDate() - 6);
  
  dateRange.value = [startDate, endDate];
  fetchData();
}

function setThisMonth() {
  const now = new Date();
  const startDate = new Date(now.getFullYear(), now.getMonth(), 1);
  const endDate = new Date();
  
  dateRange.value = [startDate, endDate];
  fetchData();
}

function setLastMonth() {
  const now = new Date();
  const startDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const endDate = new Date(now.getFullYear(), now.getMonth(), 0);
  
  dateRange.value = [startDate, endDate];
  fetchData();
}

// --- LIFECYCLE ---
onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="dashboard-strategic">
    <!-- Header -->
    <div class="dashboard-header">
      <div class="header-content">
        <h1>Dashboard Estratégico</h1>
        <p class="header-subtitle">Insights avançados sobre seus custos de nuvem</p>
      </div>
    </div>

    <!-- Seção de Controles -->
    <Card class="controls-card mb-4">
      <template #content>
        <div class="controls-section">
          <!-- Botões de Período Pré-definido -->
          <div class="period-buttons">
            <label class="control-label">Períodos Rápidos:</label>
            <ButtonGroup>
              <Button 
                label="Últimos 7 dias" 
                @click="setLast7Days"
                size="small"
                outlined
              />
              <Button 
                label="Este Mês" 
                @click="setThisMonth"
                size="small"
                outlined
              />
              <Button 
                label="Mês Passado" 
                @click="setLastMonth"
                size="small"
                outlined
              />
            </ButtonGroup>
          </div>

          <!-- Seletor de Calendário Customizado -->
          <div class="custom-date-picker">
            <label for="date-picker" class="control-label">Período Customizado:</label>
            <flat-pickr
              id="date-picker"
              v-model="dateRange"
              :config="datePickerConfig"
              class="date-picker"
              @on-change="onDateRangeChange"
            />
          </div>
        </div>
      </template>
    </Card>

    <!-- Estado de Loading -->
    <div v-if="isLoading" class="loading-state">
      <ProgressSpinner />
      <p class="ml-3">Carregando dados estratégicos...</p>
    </div>

    <!-- Estado de Erro -->
    <Message v-else-if="error" severity="error" :closable="false" class="mb-4">
      {{ error }}
    </Message>

    <!-- Conteúdo Principal -->
    <div v-else-if="dashboardData">
      <!-- Seção de KPIs -->
      <div class="kpis-section mb-4">
        <!-- KPI 1 - Custo Total -->
        <Card class="kpi-card kpi-primary">
          <template #content>
            <div class="kpi-content">
              <div class="kpi-icon">💰</div>
              <div class="kpi-info">
                <h3>Custo Total</h3>
                <p class="kpi-value">${{ kpis.totalCost.toFixed(2) }}</p>
                <span class="kpi-period">Período selecionado</span>
              </div>
            </div>
          </template>
        </Card>

        <!-- KPI 2 - Variação -->
        <Card :class="['kpi-card', kpis.totalVariationPercentage >= 0 ? 'kpi-warning' : 'kpi-success']">
          <template #content>
            <div class="kpi-content">
              <div class="kpi-icon">📈</div>
              <div class="kpi-info">
                <h3>Variação</h3>
                <p :class="['kpi-value', kpis.totalVariationPercentage >= 0 ? 'negative' : 'positive']">
                  {{ kpis.totalVariationPercentage >= 0 ? '+' : '' }}{{ kpis.totalVariationPercentage.toFixed(1) }}%
                </p>
                <span class="kpi-detail">
                  ${{ kpis.totalVariationValue >= 0 ? '+' : '' }}{{ kpis.totalVariationValue.toFixed(2) }}
                </span>
              </div>
            </div>
          </template>
        </Card>

        <!-- KPI 3 - Taxas -->
        <Card class="kpi-card kpi-info">
          <template #content>
            <div class="kpi-content">
              <div class="kpi-icon">🏛️</div>
              <div class="kpi-info">
                <h3>Custos com Taxas</h3>
                <p class="kpi-value">${{ kpis.taxCost.toFixed(2) }}</p>
                <span class="kpi-period">TAX</span>
              </div>
            </div>
          </template>
        </Card>

        <!-- KPI 4 - Créditos -->
        <Card class="kpi-card kpi-success">
          <template #content>
            <div class="kpi-content">
              <div class="kpi-icon">💳</div>
              <div class="kpi-info">
                <h3>Créditos Aplicados</h3>
                <p class="kpi-value positive">${{ kpis.credits.toFixed(2) }}</p>
                <span class="kpi-period">Credits</span>
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Gráfico Principal - Largura Total -->
      <Card class="chart-card-full-width mb-4">
        <template #title>
          <i class="pi pi-chart-line mr-2"></i>
          Evolução de Custos (Período Atual vs. Anterior)
        </template>
        <template #content>
          <div class="chart-container">
            <Chart 
              type="line" 
              :data="chartData" 
              :options="chartOptions"
              style="width: 100% !important; height: 100% !important; min-height: 600px !important;"
            />
          </div>
        </template>
      </Card>

      <!-- Tabelas de Insights -->
      <div class="insights-grid">
        <!-- Tabela 1 - Maiores Variações por Serviço -->
        <Card class="table-card">
          <template #title>
            <i class="pi pi-sort-amount-down mr-2"></i>
            Maiores Variações por Serviço
          </template>
          <template #content>
            <DataTable 
              :value="serviceVariationData" 
              :paginator="true" 
              :rows="10"
              responsiveLayout="scroll"
              size="small"
              sortMode="single"
              :sortField="'variationValue'"
              :sortOrder="-1"
              class="p-datatable-sm"
            >
              <Column 
                field="service" 
                header="Serviço" 
                :sortable="true"
                style="min-width: 200px"
              >
                <template #body="slotProps">
                  <strong>{{ slotProps.data.service }}</strong>
                </template>
              </Column>
              
              <Column 
                field="currentCost" 
                header="Custo Atual ($)" 
                :sortable="true"
                style="min-width: 120px"
              >
                <template #body="slotProps">
                  ${{ (slotProps.data.currentCost || 0).toFixed(2) }}
                </template>
              </Column>
              
              <Column 
                field="previousCost" 
                header="Custo Anterior ($)" 
                :sortable="true"
                style="min-width: 130px"
              >
                <template #body="slotProps">
                  ${{ (slotProps.data.previousCost || 0).toFixed(2) }}
                </template>
              </Column>
              
              <Column 
                field="variationValue" 
                header="Variação ($)" 
                :sortable="true"
                style="min-width: 120px"
              >
                <template #body="slotProps">
                  <span :class="[(slotProps.data.variationValue || 0) >= 0 ? 'negative' : 'positive']">
                    {{ (slotProps.data.variationValue || 0) >= 0 ? '+' : '' }}${{ (slotProps.data.variationValue || 0).toFixed(2) }}
                  </span>
                </template>
              </Column>
              
              <Column 
                field="variationPercentage" 
                header="Variação (%)" 
                :sortable="true"
                style="min-width: 120px"
              >
                <template #body="slotProps">
                  <span :class="[(slotProps.data.variationPercentage || 0) >= 0 ? 'negative' : 'positive']">
                    {{ (slotProps.data.variationPercentage || 0) >= 0 ? '+' : '' }}{{ (slotProps.data.variationPercentage || 0).toFixed(1) }}%
                  </span>
                </template>
              </Column>
            </DataTable>
          </template>
        </Card>

        <!-- Tabela 2 - Custo por Conta -->
        <Card class="table-card">
          <template #title>
            <i class="pi pi-building mr-2"></i>
            Custo por Conta
          </template>
          <template #content>
            <DataTable 
              :value="costByAccountData" 
              :paginator="true" 
              :rows="10"
              responsiveLayout="scroll"
              size="small"
              sortMode="single"
              :sortField="'totalCost'"
              :sortOrder="-1"
              class="p-datatable-sm"
            >
              <Column 
                field="accountName" 
                header="Nome da Conta" 
                :sortable="true"
                style="min-width: 200px"
              >
                <template #body="slotProps">
                  <strong>{{ slotProps.data.accountName }}</strong>
                </template>
              </Column>
              
              <Column 
                field="totalCost" 
                header="Custo Total ($)" 
                :sortable="true"
                style="min-width: 150px"
              >
                <template #body="slotProps">
                  ${{ (slotProps.data.totalCost || 0).toFixed(2) }}
                </template>
              </Column>
              
              <Column 
                field="percentageOfTotal" 
                header="% do Total" 
                :sortable="true"
                style="min-width: 200px"
              >
                <template #body="slotProps">
                  <div class="percentage-container">
                    <span class="percentage-text">{{ (slotProps.data.percentageOfTotal || 0).toFixed(1) }}%</span>
                    <ProgressBar 
                      :value="slotProps.data.percentageOfTotal || 0" 
                      class="progress-bar-custom"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </template>
        </Card>
      </div>
    </div>

    <!-- Estado Vazio -->
    <Message v-else severity="info" :closable="false" class="mb-4">
      Nenhum dado disponível para o período selecionado.
    </Message>
  </div>
</template>

<style scoped>
.dashboard-strategic {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

/* Header */
.dashboard-header {
  margin-bottom: 2rem;
}

.header-content h1 {
  color: #333;
  margin-bottom: 0.5rem;
}

.header-subtitle {
  color: #666;
  font-size: 1.1rem;
  margin: 0;
}

.mb-4 {
  margin-bottom: 2rem;
}

/* Controles */
.controls-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  align-items: end;
}

.control-label {
  display: block;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.5rem;
}

.period-buttons {
  display: flex;
  flex-direction: column;
}

.custom-date-picker {
  display: flex;
  flex-direction: column;
}

.date-picker {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.95rem;
  width: 100%;
}

/* Estados */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #666;
}

/* KPIs */
.kpis-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.kpi-card {
  border-left: 4px solid #007BFF;
}

.kpi-primary { border-left-color: #007BFF; }
.kpi-warning { border-left-color: #ffc107; }
.kpi-success { border-left-color: #28a745; }
.kpi-info { border-left-color: #17a2b8; }

.kpi-content {
  display: flex;
  align-items: center;
  padding: 1rem;
}

.kpi-icon {
  font-size: 2.5rem;
  margin-right: 1rem;
}

.kpi-info h3 {
  margin: 0 0 0.5rem 0;
  color: #666;
  font-size: 0.9rem;
  text-transform: uppercase;
  font-weight: 600;
}

.kpi-value {
  font-size: 1.8rem;
  font-weight: 700;
  margin: 0.25rem 0;
  color: #333;
  line-height: 1;
}

.kpi-value.positive { color: #28a745; }
.kpi-value.negative { color: #dc3545; }

.kpi-period, .kpi-detail {
  font-size: 0.8rem;
  color: #888;
}

/* Gráfico Principal - Largura Total */
.chart-card-full-width {
  width: 100%;
  margin-bottom: 2rem;
}

.chart-container {
  min-height: 600px !important;
  height: 600px !important;
  position: relative;
  width: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* Forçar o gráfico PrimeVue a ocupar todo o container */
.chart-container .p-chart,
.chart-container .p-chart canvas,
.chart-container canvas {
  width: 100% !important;
  height: 100% !important;
  max-width: none !important;
  max-height: none !important;
  min-width: 100% !important;
  min-height: 100% !important;
}

/* Remover qualquer padding/margin do PrimeVue */
.chart-card-full-width .p-card-content {
  padding: 1rem !important;
}

.chart-card-full-width .p-chart {
  display: block !important;
  width: 100% !important;
  height: 100% !important;
}

/* Tabelas de Insights */
.insights-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.table-card {
  height: fit-content;
}

/* Tabelas */
.positive { color: #28a745; font-weight: 600; }
.negative { color: #dc3545; font-weight: 600; }

.percentage-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.percentage-text {
  min-width: 50px;
  font-weight: 600;
}

.progress-bar-custom {
  flex: 1;
  height: 8px;
}

/* Responsividade */
@media (max-width: 1200px) {
  .kpis-section {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .insights-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .controls-section {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .kpis-section {
    grid-template-columns: 1fr;
  }
  
  .chart-container {
    min-height: 400px;
    height: 400px;
  }
}
</style>
