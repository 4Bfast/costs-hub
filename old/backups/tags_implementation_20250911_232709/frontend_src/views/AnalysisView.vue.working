<script setup>
import { ref, onMounted, computed } from 'vue';
import { apiService } from '@/services/api';
import flatPickr from 'vue-flatpickr-component';
import 'flatpickr/dist/flatpickr.css';
import { Portuguese } from 'flatpickr/dist/l10n/pt.js';

import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Card from 'primevue/card';
import ProgressSpinner from 'primevue/progressspinner';
import Message from 'primevue/message';
import Dropdown from 'primevue/dropdown';
import InputText from 'primevue/inputtext';
import ProgressBar from 'primevue/progressbar';
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import Sidebar from 'primevue/sidebar';

// Componente de gráfico
import CostLineChart from '@/components/CostLineChart.vue';

const accounts = ref([]);
const selectedAccount = ref(null);
const dateRange = ref([
  new Date(Date.now() - 29 * 24 * 60 * 60 * 1000),
  new Date()
]);
const serviceCosts = ref([]);
const isLoading = ref(true);
const error = ref(null);
const searchTerm = ref('');
const selectedService = ref(null);
const isSidebarVisible = ref(false);

// Estados para o gráfico temporal
const serviceTimeSeriesData = ref([]);
const isLoadingTimeSeries = ref(false);
const timeSeriesError = ref(null);

// Estados para análise de variação
const variationData = ref(null);
const isLoadingVariation = ref(false);
const variationError = ref(null);

const datePickerConfig = {
  mode: 'range',
  dateFormat: 'd/m/Y',
  locale: Portuguese,
  maxDate: new Date(),
  defaultDate: dateRange.value
};

const accountOptions = computed(() => {
  const options = accounts.value.map(account => ({
    label: account.name,
    value: account.id
  }));
  options.unshift({
    label: 'Todas as Contas',
    value: null
  });
  return options;
});

const totalCost = computed(() => {
  return serviceCosts.value.reduce((sum, service) => sum + service.total_cost, 0);
});

const servicesWithPercentage = computed(() => {
  const total = totalCost.value;
  if (total === 0) return serviceCosts.value;
  
  return serviceCosts.value.map(service => ({
    ...service,
    percentage: ((service.total_cost / total) * 100).toFixed(2)
  }));
});

const filteredServices = computed(() => {
  if (!searchTerm.value) return servicesWithPercentage.value;
  
  return servicesWithPercentage.value.filter(service => {
    const serviceName = (service.service || service.aws_service || '').toLowerCase();
    return serviceName.includes(searchTerm.value.toLowerCase());
  });
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

const highestCost = computed(() => {
  if (serviceCosts.value.length === 0) return 0;
  return Math.max(...serviceCosts.value.map(s => s.total_cost));
});

const highestCostService = computed(() => {
  if (serviceCosts.value.length === 0) return '';
  const highest = serviceCosts.value.find(s => s.total_cost === highestCost.value);
  return highest ? (highest.service || highest.aws_service) : '';
});

async function loadAccounts() {
  try {
    accounts.value = await apiService.getMemberAccounts();
  } catch (err) {
    error.value = 'Erro ao carregar contas: ' + err.message;
  }
}

async function fetchData() {
  if (!dateRange.value || dateRange.value.length !== 2) return;
  
  isLoading.value = true;
  error.value = null;
  
  try {
    const startDate = new Date(dateRange.value[0]).toISOString().split('T')[0];
    const endDate = new Date(dateRange.value[1]).toISOString().split('T')[0];
    serviceCosts.value = await apiService.getCostsByService(selectedAccount.value, startDate, endDate);
  } catch (err) {
    error.value = 'Erro ao carregar dados: ' + err.message;
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

function onServiceClick(event) {
  selectedService.value = event.data;
  isSidebarVisible.value = true;
  fetchServiceTimeSeries();
  loadServiceVariationAnalysis();
  console.log('Serviço clicado:', selectedService.value);
}

function closeSidebar() {
  isSidebarVisible.value = false;
  selectedService.value = null;
  serviceTimeSeriesData.value = [];
  timeSeriesError.value = null;
  variationData.value = null;
  variationError.value = null;
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
    
    const params = {
      start_date: startDate,
      end_date: endDate,
      service_name: serviceName
    };
    
    if (selectedAccount.value !== null && selectedAccount.value !== undefined && selectedAccount.value !== '') {
      params.aws_account_id = selectedAccount.value;
    }
    
    serviceTimeSeriesData.value = await apiService.getTimeSeriesByService(params);
    
  } catch (err) {
    console.error('Error fetching time series:', err);
    timeSeriesError.value = 'Erro ao carregar dados históricos: ' + err.message;
    serviceTimeSeriesData.value = [];
  } finally {
    isLoadingTimeSeries.value = false;
  }
}

async function loadServiceVariationAnalysis() {
  if (!selectedService.value || !dateRange.value || dateRange.value.length !== 2) return;

  isLoadingVariation.value = true;
  variationError.value = null;

  try {
    const startDate = dateRange.value[0].toISOString().split('T')[0];
    const endDate = dateRange.value[1].toISOString().split('T')[0];
    const serviceName = selectedService.value.service || selectedService.value.aws_service;
    
    const params = {
      start_date: startDate,
      end_date: endDate,
      service_name: serviceName,
      min_variation: 1.0,
      limit: 20
    };

    if (selectedAccount.value !== null && selectedAccount.value !== undefined && selectedAccount.value !== '') {
      params.aws_account_id = selectedAccount.value;
    }

    const response = await apiService.getVariationAnalysis(params);
    variationData.value = response;

  } catch (err) {
    console.error('Erro ao carregar análise de variação:', err);
    variationError.value = err.response?.data?.error || err.message || 'Erro ao carregar análise de variação';
  } finally {
    isLoadingVariation.value = false;
  }
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(value);
};

const getVariationIcon = (percentage) => {
  return percentage > 0 ? 'pi pi-arrow-up' : 'pi pi-arrow-down';
};

onMounted(async () => {
  await loadAccounts();
  await fetchData();
});
</script>

<template>
  <div class="analysis-page">
    <h1>Análise por Serviço</h1>

    <!-- Controles -->
    <Card class="mb-4">
      <template #content>
        <div class="controls-grid">
          <div class="control-group">
            <label>Conta AWS:</label>
            <Dropdown
              v-model="selectedAccount"
              :options="accountOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Selecione uma conta"
              @change="onAccountChange"
            />
          </div>
          <div class="control-group">
            <label>Período:</label>
            <flat-pickr
              v-model="dateRange"
              :config="datePickerConfig"
              @on-change="onDateRangeChange"
            />
          </div>
        </div>
      </template>
    </Card>

    <!-- Loading -->
    <div v-if="isLoading">
      <ProgressSpinner />
      <p>Carregando...</p>
    </div>

    <!-- Error -->
    <Message v-else-if="error" severity="error">
      {{ error }}
    </Message>

    <!-- Empty -->
    <Message v-else-if="serviceCosts.length === 0" severity="info">
      Nenhum dado encontrado.
    </Message>

    <!-- Content -->
    <div v-else>
      <!-- Abas para KPIs e Insights -->
      <TabView class="mb-4">
        <TabPanel header="Visão Geral">
          <div class="kpi-grid">
            <div class="kpi-item">
              <h4>Custo Total</h4>
              <p class="kpi-value">${{ totalCost.toFixed(2) }}</p>
              <small>{{ formatPeriod }}</small>
            </div>
            <div class="kpi-item">
              <h4>Serviços Ativos</h4>
              <p class="kpi-value">{{ serviceCosts.length }}</p>
              <small>serviços AWS</small>
            </div>
            <div class="kpi-item">
              <h4>Maior Serviço</h4>
              <p class="kpi-value">${{ highestCost.toFixed(2) }}</p>
              <small>{{ highestCostService }}</small>
            </div>
            <div class="kpi-item">
              <h4>Média Diária</h4>
              <p class="kpi-value">${{ dailyAverage.toFixed(2) }}</p>
              <small>{{ periodDays }} dias</small>
            </div>
          </div>
        </TabPanel>
        
        <TabPanel header="Insights">
          <div class="insights-content">
            <h4>Análise de Distribuição</h4>
            <div class="insight-item">
              <strong>Concentração:</strong> 
              <span v-if="serviceCosts.length > 0">
                O serviço "{{ highestCostService }}" representa 
                {{ ((highestCost / totalCost) * 100).toFixed(1) }}% do custo total
              </span>
            </div>
            
            <div class="insight-item">
              <strong>Diversificação:</strong>
              <span v-if="serviceCosts.length <= 3">Baixa - Poucos serviços ativos</span>
              <span v-else-if="serviceCosts.length <= 8">Média - Distribuição equilibrada</span>
              <span v-else>Alta - Muitos serviços em uso</span>
            </div>

            <div class="insight-item">
              <strong>Período:</strong> {{ formatPeriod }} ({{ periodDays }} dias)
            </div>

            <div v-if="selectedService" class="selected-service-info">
              <h4>Último Serviço Selecionado:</h4>
              <p><strong>{{ selectedService.service || selectedService.aws_service }}</strong></p>
              <p>Custo: ${{ selectedService.total_cost?.toFixed(2) }} ({{ selectedService.percentage }}%)</p>
            </div>
          </div>
        </TabPanel>
      </TabView>

      <Card>
        <template #title>Serviços</template>
        <template #content>
          <!-- Busca -->
          <div class="mb-3">
            <InputText 
              v-model="searchTerm" 
              placeholder="Buscar serviço..." 
              class="w-full"
            />
          </div>

          <DataTable 
            :value="filteredServices"
            :paginator="true" 
            :rows="15"
            :sortField="'total_cost'"
            :sortOrder="-1"
            @row-click="onServiceClick"
            class="clickable-table"
          >
            <Column field="service" header="Serviço" :sortable="true"></Column>
            <Column field="total_cost" header="Custo" :sortable="true">
              <template #body="slotProps">
                ${{ slotProps.data.total_cost.toFixed(2) }}
              </template>
            </Column>
            <Column field="percentage" header="% do Total" :sortable="true">
              <template #body="slotProps">
                <div>
                  <div>{{ slotProps.data.percentage }}%</div>
                  <ProgressBar 
                    :value="parseFloat(slotProps.data.percentage)" 
                    :showValue="false"
                    style="height: 8px; margin-top: 4px;"
                  />
                </div>
              </template>
            </Column>
          </DataTable>
        </template>
      </Card>
    </div>

    <!-- Sidebar - Detalhes do Serviço -->
    <Sidebar 
      v-model:visible="isSidebarVisible" 
      position="right" 
      :style="{ width: '50vw' }"
      @hide="closeSidebar"
    >
      <template #header>
        <h3>{{ selectedService?.service || selectedService?.aws_service }}</h3>
      </template>

      <div v-if="selectedService" class="sidebar-content">
        <!-- Loading -->
        <div v-if="isLoadingTimeSeries" class="loading-section">
          <ProgressSpinner />
          <p>Carregando dados históricos...</p>
        </div>

        <!-- Error -->
        <Message v-else-if="timeSeriesError" severity="error" class="mb-3">
          {{ timeSeriesError }}
        </Message>

        <!-- Dados Vazios -->
        <Message v-else-if="serviceTimeSeriesData.length === 0" severity="info" class="mb-3">
          Nenhum dado histórico encontrado para este serviço no período selecionado.
        </Message>

        <!-- Gráfico -->
        <div v-else>
          <Card class="mb-3">
            <template #title>
              Evolução de Custos - {{ selectedService.service || selectedService.aws_service }}
            </template>
            <template #content>
              <div class="chart-container">
                <CostLineChart 
                  :chartData="{
                    labels: serviceTimeSeriesData.map(d => new Date(d.date).toLocaleDateString('pt-BR')),
                    datasets: [{
                      label: selectedService.service || selectedService.aws_service,
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

          <!-- Estatísticas do Período -->
          <Card class="mb-3">
            <template #title>Estatísticas do Período</template>
            <template #content>
              <div class="stats-grid">
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

          <!-- Análise de Variação -->
          <Card class="mb-3">
            <template #title>
              <div class="flex items-center justify-between">
                <span>Análise de Variação</span>
                <i v-if="isLoadingVariation" class="pi pi-spin pi-spinner"></i>
              </div>
            </template>
            <template #content>
              <!-- Loading -->
              <div v-if="isLoadingVariation" class="loading-section">
                <ProgressSpinner />
                <span>Analisando variações...</span>
              </div>

              <!-- Error -->
              <Message v-else-if="variationError" severity="error" class="mb-4">
                {{ variationError }}
              </Message>

              <!-- Dados de Variação -->
              <div v-else-if="variationData && (variationData.byResource?.length > 0 || variationData.byUsageType?.length > 0)" class="variation-content">
                <!-- Resumo -->
                <div class="variation-summary">
                  <div class="summary-item">
                    <div class="summary-value">{{ variationData?.byResource?.length || 0 }}</div>
                    <div class="summary-label">Recursos</div>
                  </div>
                  <div class="summary-item">
                    <div class="summary-value">{{ variationData?.byUsageType?.length || 0 }}</div>
                    <div class="summary-label">Tipos de Uso</div>
                  </div>
                </div>

                <!-- Top Variações por Recurso -->
                <div v-if="variationData?.byResource?.length > 0" class="variation-section">
                  <h5>Top Variações por Recurso</h5>
                  <div class="variation-list">
                    <div 
                      v-for="resource in variationData.byResource.slice(0, 3)" 
                      :key="resource.resourceId"
                      class="variation-item"
                    >
                      <span class="resource-id">{{ resource.resourceId }}</span>
                      <div class="variation-amount">
                        <i :class="getVariationIcon(resource.variationPercent)"></i>
                        <span :class="resource.variation > 0 ? 'text-red' : 'text-green'">
                          {{ formatCurrency(resource.variation) }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Top Variações por Tipo de Uso -->
                <div v-if="variationData?.byUsageType?.length > 0" class="variation-section">
                  <h5>Top Variações por Tipo de Uso</h5>
                  <div class="variation-list">
                    <div 
                      v-for="usage in variationData.byUsageType.slice(0, 3)" 
                      :key="usage.usageType"
                      class="variation-item"
                    >
                      <span class="usage-type">{{ usage.usageType }}</span>
                      <div class="variation-amount">
                        <i :class="getVariationIcon(usage.variationPercent)"></i>
                        <span :class="usage.variation > 0 ? 'text-red' : 'text-green'">
                          {{ formatCurrency(usage.variation) }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Estado Vazio -->
              <div v-else class="empty-state">
                <i class="pi pi-chart-line"></i>
                <p>Nenhuma variação significativa encontrada</p>
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
}

.mb-4 {
  margin-bottom: 2rem;
}

.controls-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.control-group label {
  font-weight: 600;
}

.mb-3 {
  margin-bottom: 1rem;
}

.w-full {
  width: 100%;
}

.p-input-icon-left > i {
  left: 1rem;
  color: #6c757d;
}

.p-input-icon-left > input {
  padding-left: 2.5rem;
}

.mt-4 {
  margin-top: 2rem;
}

.clickable-table :deep(tbody tr) {
  cursor: pointer;
}

.clickable-table :deep(tbody tr:hover) {
  background-color: #f8f9fa;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.kpi-item {
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  text-align: center;
}

.kpi-item small {
  color: #666;
  font-size: 0.8rem;
}

.kpi-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #007bff;
  margin: 0.5rem 0;
}

.insights-content {
  padding: 1rem 0;
}

.insight-item {
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #007bff;
}

.selected-service-info {
  margin-top: 2rem;
  padding: 1rem;
  background: #e3f2fd;
  border-radius: 8px;
  border: 1px solid #2196f3;
}

.sidebar-content {
  padding: 1rem 0;
}

.loading-section {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  gap: 1rem;
}

.chart-container {
  height: 300px;
  position: relative;
}

.stats-grid {
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

.variation-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.variation-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.summary-item {
  text-align: center;
  padding: 0.75rem;
  background: #f0f8ff;
  border-radius: 6px;
}

.summary-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #007bff;
}

.summary-label {
  font-size: 0.8rem;
  color: #666;
}

.variation-section h5 {
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  font-weight: 600;
}

.variation-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.variation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 0.85rem;
}

.resource-id, .usage-type {
  font-family: monospace;
  font-size: 0.8rem;
  flex: 1;
  margin-right: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.variation-amount {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-weight: 600;
}

.text-red {
  color: #dc3545;
}

.text-green {
  color: #28a745;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.empty-state i {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.flex {
  display: flex;
}

.items-center {
  align-items: center;
}

.justify-between {
  justify-content: space-between;
}

.service-details {
  margin-bottom: 2rem;
}

.service-details h4 {
  margin-bottom: 1rem;
  color: #333;
}

.service-details p {
  margin-bottom: 0.5rem;
}

.service-actions {
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
}
</style>
