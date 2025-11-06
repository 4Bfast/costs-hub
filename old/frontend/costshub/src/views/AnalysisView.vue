<script setup>
import { ref, onMounted, computed } from 'vue';
import { apiService } from '@/services/api';
import flatPickr from 'vue-flatpickr-component';
import 'flatpickr/dist/flatpickr.css';
import { Portuguese } from 'flatpickr/dist/l10n/pt.js';

// PrimeVue Components
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Dropdown from 'primevue/dropdown';
import Chart from 'primevue/chart';
import Card from 'primevue/card';
import ProgressSpinner from 'primevue/progressspinner';
import Message from 'primevue/message';
import InputText from 'primevue/inputtext';
import Sidebar from 'primevue/sidebar';

// Componente de gráfico
import CostLineChart from '@/components/CostLineChart.vue';

// --- ESTADO REATIVO ---
const accounts = ref([]);
const selectedAccount = ref(null);
const dateRange = ref([
  new Date(Date.now() - 29 * 24 * 60 * 60 * 1000), // 29 dias atrás
  new Date() // hoje
]);
const serviceCosts = ref([]);
const isLoading = ref(true);
const error = ref(null);
const searchTerm = ref('');

// Estado do painel lateral
const isDrawerVisible = ref(false);
const selectedService = ref(null);
const serviceTimeSeriesData = ref([]);
const isLoadingTimeSeries = ref(false);
const timeSeriesError = ref(null);

// --- CONFIGURAÇÕES ---
const datePickerConfig = {
  mode: 'range',
  dateFormat: 'd/m/Y',
  locale: Portuguese,
  maxDate: new Date(),
  defaultDate: dateRange.value
};

// --- PROPRIEDADES COMPUTADAS ---
const totalCost = computed(() => {
  return serviceCosts.value.reduce((sum, service) => sum + service.total_cost, 0);
});

const highestCost = computed(() => {
  if (serviceCosts.value.length === 0) return 0;
  return Math.max(...serviceCosts.value.map(s => s.total_cost));
});

const highestCostService = computed(() => {
  if (serviceCosts.value.length === 0) return '';
  const highest = serviceCosts.value.find(s => s.total_cost === highestCost.value);
  return highest ? (highest.service || highest.aws_service) : '';
});

const top3Percentage = computed(() => {
  if (serviceCosts.value.length === 0) return 0;
  const sorted = [...serviceCosts.value].sort((a, b) => b.total_cost - a.total_cost);
  const top3Cost = sorted.slice(0, 3).reduce((sum, s) => sum + s.total_cost, 0);
  return (top3Cost / totalCost.value) * 100;
});

const servicesWithPercentage = computed(() => {
  const total = totalCost.value;
  if (total === 0) return [];
  
  return serviceCosts.value.map(service => ({
    ...service,
    percentage: ((service.total_cost / total) * 100).toFixed(2)
  })).sort((a, b) => b.total_cost - a.total_cost);
});

// Dados para o gráfico Donut com lógica "Top 7 + Outros"
const chartData = computed(() => {
  const services = servicesWithPercentage.value;
  if (services.length === 0) return { labels: [], datasets: [] };
  
  // Top 7 serviços
  const topServices = services.slice(0, 7);
  const otherServices = services.slice(7);
  
  // Calcular custo total dos "Outros"
  const othersTotalCost = otherServices.reduce((sum, s) => sum + s.total_cost, 0);
  const othersPercentage = otherServices.reduce((sum, s) => sum + parseFloat(s.percentage), 0);
  
  // Preparar dados para o gráfico
  const labels = [...topServices.map(s => s.service || s.aws_service)];
  const data = [...topServices.map(s => s.total_cost)];
  const colors = [
    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6384'
  ];
  
  // Adicionar "Outros" se existir
  if (otherServices.length > 0) {
    labels.push('Outros');
    data.push(othersTotalCost);
    colors.push('#C9CBCF');
  }
  
  return {
    labels,
    datasets: [{
      data,
      backgroundColor: colors,
      hoverBackgroundColor: colors.map(color => color + 'CC'), // Adiciona transparência no hover
      borderWidth: 2,
      borderColor: '#ffffff'
    }]
  };
});

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: true,
  aspectRatio: 1.2,
  plugins: {
    legend: {
      display: false // DESABILITADA - usaremos legenda customizada
    },
    tooltip: {
      callbacks: {
        label: function(context) {
          const service = context.label;
          const value = context.parsed;
          const total = context.dataset.data.reduce((a, b) => a + b, 0);
          const percentage = ((value / total) * 100).toFixed(1);
          return `${service}: $${value.toFixed(2)} (${percentage}%)`;
        }
      }
    }
  },
  layout: {
    padding: {
      left: 10,
      right: 10,
      top: 10,
      bottom: 10
    }
  }
}));

// Opções para o dropdown de contas
const accountOptions = computed(() => {
  const options = accounts.value.map(account => ({
    label: account.account_name,
    value: account.id
  }));
  
  // Adicionar opção "Todas as Contas"
  options.unshift({
    label: 'Todas as Contas',
    value: null
  });
  
  return options;
});

// Legenda customizada para o gráfico donut
const customLegend = computed(() => {
  const services = servicesWithPercentage.value;
  if (services.length === 0) return [];
  
  const topServices = services.slice(0, 7);
  const otherServices = services.slice(7);
  const colors = [
    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6384'
  ];
  
  const legendItems = topServices.map((service, index) => ({
    label: service.service || service.aws_service,
    color: colors[index],
    value: service.total_cost,
    percentage: service.percentage
  }));
  
  // Adicionar "Outros" se existir
  if (otherServices.length > 0) {
    const othersTotalCost = otherServices.reduce((sum, s) => sum + s.total_cost, 0);
    const othersPercentage = otherServices.reduce((sum, s) => sum + parseFloat(s.percentage), 0);
    
    legendItems.push({
      label: `Outros (${otherServices.length} serviços)`,
      color: '#C9CBCF',
      value: othersTotalCost,
      percentage: othersPercentage.toFixed(2)
    });
  }
  
  return legendItems;
});

// Filtro de serviços
const filteredServices = computed(() => {
  if (!searchTerm.value) return servicesWithPercentage.value;
  
  return servicesWithPercentage.value.filter(service => {
    const serviceName = (service.service || service.aws_service || '').toLowerCase();
    return serviceName.includes(searchTerm.value.toLowerCase());
  });
});

// Insights complementares adicionais
const biggestServicePercentage = computed(() => {
  return servicesWithPercentage.value.length > 0 ? parseFloat(servicesWithPercentage.value[0].percentage) : 0;
});

const biggestServiceName = computed(() => {
  return servicesWithPercentage.value.length > 0 ? 
    (servicesWithPercentage.value[0].service || servicesWithPercentage.value[0].aws_service) : '';
});

const diversificationLevel = computed(() => {
  const biggest = biggestServicePercentage.value;
  if (biggest > 60) return 'Baixa';
  if (biggest > 40) return 'Média';
  return 'Alta';
});

const diversificationDesc = computed(() => {
  const level = diversificationLevel.value;
  if (level === 'Baixa') return 'Concentrado em poucos serviços';
  if (level === 'Média') return 'Distribuição equilibrada';
  return 'Bem diversificado';
});

const recommendations = computed(() => {
  const recs = [];
  const biggest = biggestServicePercentage.value;
  const biggestName = biggestServiceName.value;
  
  if (biggest > 50) {
    recs.push({
      icon: 'pi pi-exclamation-triangle',
      color: '#ff9800',
      title: 'Alta Concentração',
      description: `${biggestName} representa ${biggest.toFixed(1)}% dos custos. Considere otimizações específicas.`
    });
  }
  
  if (servicesWithPercentage.value.length > 10) {
    recs.push({
      icon: 'pi pi-eye',
      color: '#2196f3',
      title: 'Muitos Serviços Ativos',
      description: `${servicesWithPercentage.value.length} serviços em uso. Revise serviços com baixo uso.`
    });
  }
  
  if (totalCost.value > 1000) {
    recs.push({
      icon: 'pi pi-dollar',
      color: '#4caf50',
      title: 'Oportunidade de Economia',
      description: 'Custos elevados. Considere Reserved Instances ou Savings Plans.'
    });
  }
  
  if (recs.length === 0) {
    recs.push({
      icon: 'pi pi-check-circle',
      color: '#4caf50',
      title: 'Distribuição Saudável',
      description: 'Custos bem distribuídos entre os serviços AWS.'
    });
  }
  
  return recs;
});

const formatPeriod = computed(() => {
  if (!dateRange.value || dateRange.value.length !== 2) return '';
  const start = new Date(dateRange.value[0]).toLocaleDateString('pt-BR');
  const end = new Date(dateRange.value[1]).toLocaleDateString('pt-BR');
  return `${start} - ${end}`;
});

const periodDays = computed(() => {
  if (!dateRange.value || dateRange.value.length !== 2) return 0;
  const start = new Date(dateRange.value[0]);
  const end = new Date(dateRange.value[1]);
  return Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
});

const dailyAverage = computed(() => {
  return periodDays.value > 0 ? totalCost.value / periodDays.value : 0;
});

// --- FUNÇÕES ---
async function loadAccounts() {
  try {
    accounts.value = await apiService.getAwsAccounts();
  } catch (err) {
    error.value = 'Erro ao carregar contas: ' + err.message;
  }
}

async function fetchData() {
  if (!dateRange.value || dateRange.value.length !== 2) {
    return;
  }
  
  isLoading.value = true;
  error.value = null;
  
  try {
    const startDate = new Date(dateRange.value[0]);
    const endDate = new Date(dateRange.value[1]);
    
    if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
      throw new Error('Datas inválidas selecionadas');
    }
    
    // --- CORREÇÃO PRINCIPAL AQUI ---
    // Preparamos as variáveis separadamente
    const accountId = selectedAccount.value; // Pode ser nulo para "Todas as Contas"
    const startDateStr = startDate.toISOString().split('T')[0];
    const endDateStr = endDate.toISOString().split('T')[0];

    // E passamos como TRÊS ARGUMENTOS SEPARADOS, como a api.js espera
    serviceCosts.value = await apiService.getCostsByService(accountId, startDateStr, endDateStr);
    
  } catch (err) {
    error.value = 'Erro ao carregar dados de custos: ' + err.message;
    serviceCosts.value = [];
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

function onAccountChange() {
  fetchData();
}

function getRanking(service) {
  const index = filteredServices.value.findIndex(s => 
    (s.service || s.aws_service) === (service.service || service.aws_service)
  );
  return index + 1;
}

// Funções do painel lateral
function onServiceClick(event) {
  const service = event.data;
  
  console.log('=== SERVICE CLICKED ===');
  console.log('Service data:', service);
  console.log('Service name:', service.service || service.aws_service);
  console.log('Date range:', dateRange.value);
  console.log('======================');
  
  if (!service || (!service.service && !service.aws_service)) {
    console.error('Invalid service data');
    return;
  }
  
  selectedService.value = service;
  isDrawerVisible.value = true;
  fetchServiceTimeSeries();
}

async function fetchServiceTimeSeries() {
  if (!selectedService.value || !dateRange.value || dateRange.value.length !== 2) return;
  
  isLoadingTimeSeries.value = true;
  timeSeriesError.value = null;
  serviceTimeSeriesData.value = [];
  
  try {
    const startDate = new Date(dateRange.value[0]).toISOString().split('T')[0];
    const endDate = new Date(dateRange.value[1]).toISOString().split('T')[0];
    const serviceName = selectedService.value.service || selectedService.value.aws_service;
    
    console.log('=== DEBUG SIDEBAR API CALL ===');
    console.log('startDate:', startDate);
    console.log('endDate:', endDate);
    console.log('serviceName:', serviceName);
    console.log('selectedAccount:', selectedAccount.value);
    console.log('==============================');
    
    const params = {
      start_date: startDate,
      end_date: endDate,
      service_name: serviceName
    };
    
    // Adicionar aws_account_id se uma conta específica foi selecionada
    if (selectedAccount.value !== null && selectedAccount.value !== undefined && selectedAccount.value !== '') {
      params.aws_account_id = selectedAccount.value;
    }
    
    console.log('Final params:', params);
    serviceTimeSeriesData.value = await apiService.getTimeSeriesByService(params);
    console.log('Time series data received:', serviceTimeSeriesData.value);
  } catch (err) {
    console.error('Error fetching time series:', err);
    timeSeriesError.value = 'Erro ao carregar dados históricos: ' + err.message;
    serviceTimeSeriesData.value = [];
  } finally {
    isLoadingTimeSeries.value = false;
  }
}

function closeSidebar() {
  isDrawerVisible.value = false;
  selectedService.value = null;
  serviceTimeSeriesData.value = [];
  timeSeriesError.value = null;
}

// --- LIFECYCLE ---
onMounted(async () => {
  await loadAccounts();
  await fetchData();
});
</script>

<template>
  <div class="analysis-page">
    <!-- Título da Página -->
    <div class="header-section">
      <h1>Análise por Serviço</h1>
      <p class="page-subtitle">Distribuição detalhada dos custos por serviço AWS</p>
    </div>

    <!-- Área de Controles -->
    <Card class="controls-card mb-4">
      <template #content>
        <div class="controls-grid">
          <!-- Filtro de Contas -->
          <div class="control-group">
            <label for="account-dropdown" class="font-semibold mb-2 block">Conta AWS:</label>
            <Dropdown
              id="account-dropdown"
              v-model="selectedAccount"
              :options="accountOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Selecione uma conta"
              class="w-full"
              @change="onAccountChange"
            />
          </div>

          <!-- Seletor de Datas -->
          <div class="control-group">
            <label for="date-picker" class="font-semibold mb-2 block">Período:</label>
            <flat-pickr
              id="date-picker"
              v-model="dateRange"
              :config="datePickerConfig"
              class="date-picker w-full"
              @on-change="onDateRangeChange"
            />
          </div>
        </div>
      </template>
    </Card>

    <!-- Estado de Loading -->
    <div v-if="isLoading" class="loading-state">
      <ProgressSpinner />
      <p class="ml-3">Carregando análise de custos...</p>
    </div>

    <!-- Estado de Erro -->
    <Message v-else-if="error" severity="error" :closable="false" class="mb-4">
      {{ error }}
    </Message>

    <!-- Estado Vazio -->
    <Message v-else-if="serviceCosts.length === 0" severity="info" :closable="false" class="mb-4">
      Nenhum dado encontrado para o período e conta selecionados.
    </Message>

    <!-- Conteúdo Principal -->
    <div v-else>
      <!-- KPIs Summary -->
      <div class="kpis-section mb-4">
        <Card class="kpi-card">
          <template #content>
            <div class="kpi-content">
              <div class="kpi-icon">💰</div>
              <div class="kpi-info">
                <h3>Custo Total</h3>
                <p class="kpi-value">${{ totalCost.toFixed(2) }}</p>
              </div>
            </div>
          </template>
        </Card>

        <Card class="kpi-card">
          <template #content>
            <div class="kpi-content">
              <div class="kpi-icon">🔧</div>
              <div class="kpi-info">
                <h3>Serviços Ativos</h3>
                <p class="kpi-value">{{ serviceCosts.length }}</p>
              </div>
            </div>
          </template>
        </Card>

        <Card class="kpi-card">
          <template #content>
            <div class="kpi-content">
              <div class="kpi-icon">📈</div>
              <div class="kpi-info">
                <h3>Maior Custo</h3>
                <p class="kpi-value">${{ highestCost.toFixed(2) }}</p>
                <p class="kpi-subtitle">{{ highestCostService }}</p>
              </div>
            </div>
          </template>
        </Card>

        <Card class="kpi-card">
          <template #content>
            <div class="kpi-content">
              <div class="kpi-icon">🎯</div>
              <div class="kpi-info">
                <h3>Concentração Top 3</h3>
                <p class="kpi-value">{{ top3Percentage.toFixed(1) }}%</p>
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Gráfico Principal -->
      <Card class="chart-card mb-4">
        <template #title>
          <i class="pi pi-chart-pie mr-2"></i>
          Distribuição por Serviço (Top 7 + Outros)
        </template>
        <template #content>
          <div class="chart-with-legend">
            <!-- Gráfico Donut - Meia Tela -->
            <div class="chart-container-large">
              <Chart 
                type="doughnut" 
                :data="chartData" 
                :options="chartOptions"
                class="chart-canvas-large"
              />
            </div>
            
            <!-- Painel Lateral - Apenas Legenda -->
            <div class="legend-panel">
              <!-- Legenda Customizada -->
              <div class="custom-legend">
                <h4 class="legend-title">Serviços por Custo</h4>
                <div class="legend-items">
                  <div 
                    v-for="(item, index) in customLegend" 
                    :key="index"
                    class="legend-item"
                  >
                    <div class="legend-color" :style="{ backgroundColor: item.color }"></div>
                    <div class="legend-info">
                      <div class="legend-label">{{ item.label }}</div>
                      <div class="legend-values">
                        <span class="legend-value">${{ item.value.toFixed(2) }}</span>
                        <span class="legend-percentage">({{ item.percentage }}%)</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- Resumo -->
                <div class="legend-summary">
                  <div class="summary-item">
                    <span class="summary-label">Total:</span>
                    <span class="summary-value">${{ totalCost.toFixed(2) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Tabela de Detalhamento -->
      <Card class="table-card mb-4">
        <template #title>
          <i class="pi pi-table mr-2"></i>
          Detalhamento por Serviço
        </template>
        <template #content>
          <!-- Filtro de Busca -->
          <div class="table-header mb-3">
            <div class="search-container">
              <span class="p-input-icon-left">
                <i class="pi pi-search" />
                <InputText 
                  v-model="searchTerm" 
                  placeholder="Buscar serviço..." 
                  class="search-input"
                />
              </span>
            </div>
          </div>

          <DataTable 
            :value="filteredServices" 
            :paginator="true" 
            :rows="15"
            :rowsPerPageOptions="[10, 15, 25, 50]"
            responsiveLayout="scroll"
            size="small"
            sortMode="multiple"
            class="p-datatable-sm clickable-rows"
            @row-click="onServiceClick"
          >
            <Column 
              field="service" 
              header="Serviço AWS" 
              :sortable="true"
              style="min-width: 250px"
            >
              <template #body="slotProps">
                <div class="service-cell">
                  <strong>{{ slotProps.data.service || slotProps.data.aws_service }}</strong>
                </div>
              </template>
            </Column>
            
            <Column 
              field="total_cost" 
              header="Custo Total ($)" 
              :sortable="true"
              style="min-width: 150px"
            >
              <template #body="slotProps">
                <span class="cost-value">${{ slotProps.data.total_cost.toFixed(2) }}</span>
              </template>
            </Column>
            
            <Column 
              field="percentage" 
              header="% do Total" 
              :sortable="true"
              style="min-width: 150px"
            >
              <template #body="slotProps">
                <div class="percentage-container">
                  <span class="percentage-text">{{ slotProps.data.percentage }}%</span>
                  <div class="progress-bar">
                    <div 
                      class="progress-fill" 
                      :style="{ width: slotProps.data.percentage + '%' }"
                    ></div>
                  </div>
                </div>
              </template>
            </Column>

            <Column 
              header="Ranking" 
              :sortable="false"
              style="min-width: 100px"
            >
              <template #body="slotProps">
                <div class="ranking-container">
                  <span 
                    :class="['ranking-badge', {
                      'rank-1': getRanking(slotProps.data) === 1,
                      'rank-2': getRanking(slotProps.data) === 2,
                      'rank-3': getRanking(slotProps.data) === 3,
                      'rank-other': getRanking(slotProps.data) > 3
                    }]"
                  >
                    {{ getRanking(slotProps.data) }}º
                  </span>
                </div>
              </template>
            </Column>
          </DataTable>
        </template>
      </Card>
    </div>

    <!-- Painel Lateral - Detalhes do Serviço -->
    <Sidebar 
      v-model:visible="isDrawerVisible" 
      position="right" 
      class="service-details-sidebar"
      :style="{ width: '50vw' }"
      @hide="closeSidebar"
    >
      <template #header>
        <div class="sidebar-header">
          <h3>
            <i class="pi pi-chart-line mr-2"></i>
            {{ selectedService?.service || selectedService?.aws_service }}
          </h3>
          <p class="sidebar-subtitle">Evolução histórica de custos</p>
        </div>
      </template>

      <div class="sidebar-content">
        <!-- Loading -->
        <div v-if="isLoadingTimeSeries" class="sidebar-loading">
          <ProgressSpinner />
          <p class="ml-3">Carregando dados históricos...</p>
        </div>

        <!-- Erro -->
        <Message v-else-if="timeSeriesError" severity="error" :closable="false" class="mb-3">
          {{ timeSeriesError }}
        </Message>

        <!-- Dados Vazios -->
        <Message v-else-if="serviceTimeSeriesData.length === 0" severity="info" :closable="false" class="mb-3">
          Nenhum dado histórico encontrado para este serviço no período selecionado.
        </Message>

        <!-- Gráfico -->
        <div v-else class="sidebar-chart">
          <Card>
            <template #title>
              Evolução de Custos - {{ selectedService?.service || selectedService?.aws_service }}
            </template>
            <template #content>
              <div class="chart-container-sidebar">
                <CostLineChart 
                  :chartData="{
                    labels: serviceTimeSeriesData.map(d => new Date(d.date).toLocaleDateString('pt-BR')),
                    datasets: [{
                      label: selectedService?.service || selectedService?.aws_service,
                      data: serviceTimeSeriesData.map(d => d.cost),
                      borderColor: '#007BFF',
                      backgroundColor: 'rgba(0, 123, 255, 0.1)',
                      tension: 0.4,
                      fill: true
                    }]
                  }"
                  :chartOptions="{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        display: false
                      }
                    },
                    scales: {
                      y: {
                        beginAtZero: true,
                        ticks: {
                          callback: function(value) {
                            return '$' + value.toFixed(2);
                          }
                        }
                      }
                    }
                  }"
                />
              </div>
            </template>
          </Card>

          <!-- Estatísticas do Serviço -->
          <Card class="mt-3">
            <template #title>Estatísticas do Período</template>
            <template #content>
              <div class="service-stats">
                <div class="stat-item">
                  <span class="stat-label">Custo Total:</span>
                  <span class="stat-value">
                    ${{ serviceTimeSeriesData.reduce((sum, d) => sum + d.cost, 0).toFixed(2) }}
                  </span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">Custo Médio Diário:</span>
                  <span class="stat-value">
                    ${{ (serviceTimeSeriesData.reduce((sum, d) => sum + d.cost, 0) / serviceTimeSeriesData.length).toFixed(2) }}
                  </span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">Maior Custo:</span>
                  <span class="stat-value">
                    ${{ Math.max(...serviceTimeSeriesData.map(d => d.cost)).toFixed(2) }}
                  </span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">Menor Custo:</span>
                  <span class="stat-value">
                    ${{ Math.min(...serviceTimeSeriesData.map(d => d.cost)).toFixed(2) }}
                  </span>
                </div>
              </div>
            </template>
          </Card>
        </div>
      </div>
    </Sidebar>
  </div>
</template>

<style scoped>
.analysis-page {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

/* Header */
.header-section {
  margin-bottom: 2rem;
}

.header-section h1 {
  color: #333;
  margin-bottom: 0.5rem;
}

.page-subtitle {
  color: #666;
  font-size: 1.1rem;
  margin: 0;
}

.mb-4 {
  margin-bottom: 2rem;
}

/* Controles */
.controls-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.control-group {
  display: flex;
  flex-direction: column;
}

.date-picker {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.95rem;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 12px;
  overflow: hidden;
}

.kpi-card:nth-child(2) {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.kpi-card:nth-child(3) {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.kpi-card:nth-child(4) {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.kpi-content {
  display: flex;
  align-items: center;
  padding: 1.5rem;
  color: white;
}

.kpi-icon {
  font-size: 2.5rem;
  margin-right: 1rem;
}

.kpi-info h3 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  font-weight: 500;
  opacity: 0.9;
}

.kpi-value {
  font-size: 1.8rem;
  font-weight: 700;
  margin: 0;
  line-height: 1;
}

.kpi-subtitle {
  font-size: 0.8rem;
  margin: 0.25rem 0 0 0;
  opacity: 0.8;
}

/* Gráfico com Legenda - Layout Meia Tela */
.chart-with-legend {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  align-items: start;
}

.chart-container-large {
  height: 400px;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1rem;
}

/* Painel Lateral - Apenas Legenda */
.legend-panel {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  height: 100%;
}

/* Legenda Customizada - Ajustada */
.custom-legend {
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  height: fit-content;
}

.legend-title {
  margin: 0 0 1.5rem 0;
  color: #333;
  font-size: 1.1rem;
  font-weight: 600;
  border-bottom: 2px solid #007BFF;
  padding-bottom: 0.75rem;
  text-align: center;
}

.legend-items {
  margin-bottom: 1.5rem;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
  padding: 0.75rem;
  border-radius: 6px;
  transition: all 0.2s;
  background: #ffffff;
  border: 1px solid #e9ecef;
}

.legend-item:hover {
  background-color: #f0f8ff;
  border-color: #007BFF;
  transform: translateX(2px);
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  margin-right: 1rem;
  flex-shrink: 0;
  border: 2px solid #ffffff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.legend-info {
  flex: 1;
}

.legend-label {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
  margin-bottom: 0.4rem;
  line-height: 1.3;
}

.legend-values {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.legend-value {
  font-weight: 700;
  color: #007BFF;
  font-size: 0.9rem;
}

.legend-percentage {
  color: #666;
  font-size: 0.85rem;
  font-weight: 500;
}

.legend-summary {
  border-top: 2px solid #dee2e6;
  padding-top: 1rem;
  text-align: center;
}

.summary-item {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: #ffffff;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}

.summary-label {
  color: #666;
  font-size: 1rem;
  font-weight: 500;
}

.summary-value {
  font-weight: 700;
  color: #333;
  font-size: 1.2rem;
}

.chart-canvas-large {
  max-height: 700px;
  max-width: 700px;
  width: 100% !important;
  height: 100% !important;
}

/* Tabela */
.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.search-container {
  flex: 1;
  max-width: 300px;
}

.search-input {
  width: 100%;
}

.service-cell {
  font-weight: 600;
}

.cost-value {
  font-weight: 600;
  color: #333;
}

.percentage-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.percentage-text {
  min-width: 50px;
  font-weight: 600;
}

.progress-bar {
  flex: 1;
  height: 10px;
  background: #e9ecef;
  border-radius: 5px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007BFF, #0056b3);
  transition: width 0.3s ease;
}

/* Ranking */
.ranking-container {
  display: flex;
  justify-content: center;
}

.ranking-badge {
  padding: 0.4rem 0.8rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 700;
  color: white;
  text-align: center;
  min-width: 40px;
}

.rank-1 {
  background: linear-gradient(135deg, #FFD700, #FFA500);
  box-shadow: 0 2px 8px rgba(255, 215, 0, 0.3);
}

.rank-2 {
  background: linear-gradient(135deg, #C0C0C0, #A0A0A0);
  box-shadow: 0 2px 8px rgba(192, 192, 192, 0.3);
}

.rank-3 {
  background: linear-gradient(135deg, #CD7F32, #B8860B);
  box-shadow: 0 2px 8px rgba(205, 127, 50, 0.3);
}

.rank-other {
  background: linear-gradient(135deg, #6c757d, #495057);
}

/* Variação */
.variation-container {
  display: flex;
  justify-content: center;
}

.variation-badge {
  padding: 0.3rem 0.6rem;
  border-radius: 15px;
  font-size: 0.8rem;
  font-weight: 600;
  color: white;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.variation-up {
  background: linear-gradient(135deg, #dc3545, #c82333);
}

.variation-down {
  background: linear-gradient(135deg, #28a745, #1e7e34);
}

.variation-neutral {
  background: linear-gradient(135deg, #6c757d, #495057);
}

/* Responsividade */
@media (max-width: 1200px) {
  .kpis-section {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .chart-with-legend {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
  
  .legend-panel {
    order: -1; /* Legenda vai para cima em telas menores */
  }
  
  .chart-container-large {
    height: 350px;
  }
}

@media (max-width: 768px) {
  .controls-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .kpis-section {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .chart-container-large {
    height: 300px;
    padding: 0.5rem;
  }
  
  .custom-legend {
    padding: 1rem;
  }
  
  .legend-title {
    font-size: 1rem;
  }
  
  .legend-item {
    padding: 0.5rem;
    margin-bottom: 0.75rem;
  }
}

/* Tabela clicável */
.clickable-rows :deep(.p-datatable-tbody > tr) {
  cursor: pointer;
  transition: background-color 0.2s;
}

.clickable-rows :deep(.p-datatable-tbody > tr:hover) {
  background-color: #f8f9fa !important;
}

/* Painel Lateral */
.service-details-sidebar {
  z-index: 1000;
}

.sidebar-header h3 {
  color: #333;
  margin: 0 0 0.5rem 0;
}

.sidebar-subtitle {
  color: #666;
  margin: 0;
  font-size: 0.9rem;
}

.sidebar-content {
  padding: 1rem 0;
}

.sidebar-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: #666;
}

.chart-container-sidebar {
  height: 300px;
  position: relative;
}

.service-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.stat-label {
  font-size: 0.9rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.stat-value {
  font-size: 1.2rem;
  font-weight: 600;
  color: #333;
}

.mt-3 {
  margin-top: 1rem;
}

/* Insights Complementares */
.insights-complementares {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.insight-card {
  height: fit-content;
}

/* Métricas de Concentração */
.concentration-metrics {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.metric-item {
  display: flex;
  flex-direction: column;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #007BFF;
}

.metric-label {
  font-size: 0.8rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.metric-value {
  font-size: 1.2rem;
  font-weight: 700;
  color: #007BFF;
  margin-bottom: 0.1rem;
}

.metric-desc {
  font-size: 0.75rem;
  color: #888;
}

/* Recomendações */
.recommendations {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.recommendation-item {
  display: flex;
  align-items: flex-start;
  padding: 0.75rem;
  background: #ffffff;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  transition: all 0.2s;
}

.recommendation-item:hover {
  border-color: #007BFF;
  box-shadow: 0 2px 8px rgba(0,123,255,0.1);
}

.recommendation-item i {
  font-size: 1.2rem;
  margin-right: 0.75rem;
  margin-top: 0.1rem;
}

.rec-content {
  flex: 1;
}

.rec-title {
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.rec-desc {
  color: #666;
  font-size: 0.8rem;
  line-height: 1.4;
}

/* Informações do Período */
.period-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.period-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.period-label {
  font-size: 0.8rem;
  color: #666;
}

.period-value {
  font-weight: 600;
  color: #333;
  font-size: 0.85rem;
}
</style>
