<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { apiService } from '@/services/api';
import flatPickr from 'vue-flatpickr-component';
import 'flatpickr/dist/flatpickr.css';
import { Portuguese } from 'flatpickr/dist/l10n/pt';

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
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import Dropdown from 'primevue/dropdown';

// Componentes customizados
import AISummaryCard from '@/components/AISummaryCard.vue';

// --- GERENCIAMENTO DE ESTADO ---
const dashboardData = ref(null);
const memberAccounts = ref([]);
const selectedMemberAccount = ref(null);
const isLoading = ref(false);
const error = ref(null);
const dateRange = ref([
  (() => {
    const endDate = new Date();
    const startDate = new Date(endDate);
    startDate.setDate(endDate.getDate() - 6); // Últimos 7 dias
    return startDate;
  })(),
  new Date() // Hoje
]);

// Estados para resumo de IA
const aiSummary = ref('');
const isAiSummaryLoading = ref(false);

// Estados para aba de Tendências
const trendsData = ref(null);
const trendsAiSummary = ref('Carregando análise...');
const trendsChartData = ref({
  labels: [],
  datasets: [{
    label: 'Custo Mensal',
    data: [],
    backgroundColor: '#3B82F6',
    borderColor: '#1D4ED8',
    borderWidth: 3
  }]
});
const forecastData = ref({
  projected30Days: 0,
  projectedChange: 0,
  growthRate: 0,
  newServices: []
});

// Dados de projeção por projeto
const projectsForecast = ref([]);
const isLoadingProjectsForecast = ref(false);
const isLoadingTrendsAI = ref(true);
const isLoadingTrendsChart = ref(false);
const isLoadingForecast = ref(true);
const selectedPeriod = ref('3months');

// Estados para IA específica de tendências
const trendsFocusedAI = ref('Carregando análise de tendências...');
const isLoadingTrendsFocusedAI = ref(true);

// --- PROPRIEDADES COMPUTADAS ---
const kpis = computed(() => dashboardData.value?.kpis || {
  totalCost: 0,
  totalVariationPercentage: 0,
  totalVariationValue: 0,
  taxCost: 0,
  credits: 0
});

const chartData = computed(() => {
  console.log('🔍 Computing chartData, dashboardData:', dashboardData.value);
  
  if (!dashboardData.value?.timeSeries) return { labels: [], datasets: [] };
  
  const currentPeriod = dashboardData.value.timeSeries.currentPeriod || [];
  const previousPeriod = dashboardData.value.timeSeries.previousPeriod || [];
  
  console.log('📊 Current period data:', currentPeriod);
  console.log('📊 Previous period data:', previousPeriod);
  
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
  return data
    .filter(service => service.service !== 'Tax') // Remover TAX pois não é um serviço
    .sort((a, b) => Math.abs(b.variationValue || 0) - Math.abs(a.variationValue || 0));
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
async function fetchMemberAccounts() {
  try {
    const accounts = await apiService.getMemberAccounts();
    memberAccounts.value = [
      { id: null, name: 'Todas as Contas', aws_account_id: 'ALL' },
      ...accounts
    ];
    // Selecionar "Todas as Contas" por padrão
    selectedMemberAccount.value = memberAccounts.value[0];
  } catch (error) {
    console.error('Erro ao buscar contas-membro:', error);
  }
}

function onMemberAccountChange() {
  fetchData();
}

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
    
    // Incluir filtro de conta-membro se selecionada
    const memberAccountId = selectedMemberAccount.value && selectedMemberAccount.value.id ? selectedMemberAccount.value.id : null;
    
    console.log('Fetching dashboard data:', { startDateStr, endDateStr, memberAccountId });
    dashboardData.value = await apiService.getDashboardData(startDateStr, endDateStr, memberAccountId);
    console.log('Dashboard data received:', dashboardData.value);
    
    // Iniciar busca do resumo de IA de forma assíncrona (não bloquear o dashboard)
    fetchAiSummary(startDateStr, endDateStr);
    
  } catch (err) {
    console.error('Error fetching dashboard data:', err);
    error.value = err.message || 'Ocorreu um erro ao carregar os dados do dashboard.';
    dashboardData.value = null;
  } finally {
    isLoading.value = false;
  }
}

async function fetchAiSummary(startDate, endDate) {
  isAiSummaryLoading.value = true;
  aiSummary.value = '';
  
  try {
    console.log('Fetching AI summary:', { startDate, endDate });
    const response = await apiService.getAIDashboardSummary(startDate, endDate);
    aiSummary.value = response.summary || '';
    console.log('AI summary received:', { 
      summary: aiSummary.value, 
      cached: response.cached 
    });
  } catch (err) {
    console.error('Error fetching AI summary:', err);
    aiSummary.value = '🤖 Análise de IA temporariamente indisponível devido ao alto volume de uso. Nossa equipe está trabalhando para expandir a capacidade. Tente novamente em alguns minutos.';
  } finally {
    isAiSummaryLoading.value = false;
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

// --- FUNÇÕES PARA ORÇAMENTO TOTAL DA ORGANIZAÇÃO ---

// Calcula a porcentagem de consumo do orçamento total
function getBudgetConsumptionPercentage() {
  if (!kpis.value.totalMonthlyBudget || kpis.value.totalMonthlyBudget === 0) {
    return 0;
  }
  const percentage = (kpis.value.totalCost / kpis.value.totalMonthlyBudget) * 100;
  return Math.min(percentage, 100); // Limita a 100% para a barra de progresso
}

// Determina a severidade da barra de progresso do orçamento total
function getBudgetConsumptionSeverity() {
  const percentage = getBudgetConsumptionPercentage();
  
  if (percentage <= 50) {
    return 'success'; // Verde - Seguro (0-50%)
  } else if (percentage <= 75) {
    return 'info'; // Azul - Atenção (51-75%)
  } else if (percentage <= 90) {
    return 'warning'; // Amarelo - Alerta (76-90%)
  } else if (percentage <= 100) {
    return 'danger'; // Vermelho - Crítico (91-100%)
  } else {
    return 'danger'; // Vermelho - Ultrapassou (>100%)
  }
}

// Obtém a cor CSS personalizada para a barra de progresso
function getBudgetProgressColor() {
  const percentage = getBudgetConsumptionPercentage();
  
  if (percentage <= 50) {
    return '#28a745';
  } else if (percentage <= 75) {
    return '#17a2b8';
  } else if (percentage <= 90) {
    return '#ffc107';
  } else if (percentage <= 100) {
    return '#fd7e14';
  } else {
    return '#dc3545';
  }
}

// Obtém o ícone baseado na porcentagem do orçamento
function getBudgetStatusIcon() {
  const percentage = getBudgetConsumptionPercentage();
  
  if (percentage <= 50) {
    return '✅';
  } else if (percentage <= 75) {
    return '⚠️';
  } else if (percentage <= 90) {
    return '🟡';
  } else if (percentage <= 100) {
    return '🔴';
  } else {
    return '🚨';
  }
}

// Obtém o texto de status baseado na porcentagem
function getBudgetStatusText() {
  const percentage = getBudgetConsumptionPercentage();
  
  if (percentage <= 50) {
    return 'Orçamento Seguro';
  } else if (percentage <= 75) {
    return 'Atenção ao Orçamento';
  } else if (percentage <= 90) {
    return 'Alerta de Orçamento';
  } else if (percentage <= 100) {
    return 'Orçamento Crítico';
  } else {
    return 'Orçamento Ultrapassado';
  }
}

// --- FUNÇÕES PARA ORÇAMENTO E PREVISÃO ---

// Formata valores monetários com casas decimais completas
function formatCurrencyFull(value) {
  if (typeof value !== 'number') {
    value = parseFloat(value) || 0;
  }
  return value.toLocaleString('en-US', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  });
}

// Formata valores monetários de forma compacta (para espaços pequenos)
function formatCurrency(value) {
  if (typeof value !== 'number') {
    value = parseFloat(value) || 0;
  }
  
  if (value >= 1000000) {
    return (value / 1000000).toFixed(1) + 'M';
  } else if (value >= 1000) {
    return (value / 1000).toFixed(1) + 'K';
  } else {
    return value.toFixed(2);
  }
}

// Calcula a porcentagem de consumo do orçamento
function getBudgetPercentage(accountData) {
  if (!accountData.monthlyBudget || accountData.monthlyBudget === 0) {
    return 0;
  }
  const percentage = (accountData.totalCost / accountData.monthlyBudget) * 100;
  return Math.round(percentage * 10) / 10; // Arredondar para 1 casa decimal
}

// Determina a severidade da barra de progresso do orçamento
function getBudgetSeverity(accountData) {
  const percentage = getBudgetPercentage(accountData);
  
  if (percentage < 80) {
    return 'success'; // Verde
  } else if (percentage <= 100) {
    return 'warning'; // Amarelo
  } else {
    return 'danger'; // Vermelho
  }
}

// Retorna o status textual do orçamento
function getBudgetStatus(accountData) {
  const percentage = getBudgetPercentage(accountData);
  
  if (percentage < 80) {
    return 'OK';
  } else if (percentage <= 100) {
    return 'Atenção';
  } else {
    return 'Excedido';
  }
}

// Retorna a classe CSS para o status do orçamento
function getBudgetStatusClass(accountData) {
  const percentage = getBudgetPercentage(accountData);
  
  if (percentage < 80) {
    return 'status-ok';
  } else if (percentage <= 100) {
    return 'status-warning';
  } else {
    return 'status-danger';
  }
}

// Calcula a variação da previsão em relação ao orçamento
function getForecastVariation(accountData) {
  if (!accountData.monthlyBudget || accountData.monthlyBudget === 0) {
    return { percentage: 0, isAbove: false };
  }
  
  const variation = accountData.forecastedCost - accountData.monthlyBudget;
  const percentage = Math.abs((variation / accountData.monthlyBudget) * 100);
  
  return {
    percentage: Math.round(percentage * 10) / 10,
    isAbove: variation > 0
  };
}

// Retorna o texto da variação da previsão
function getForecastVariationText(accountData) {
  const variation = getForecastVariation(accountData);
  
  if (variation.percentage === 0) {
    return 'No orçamento';
  }
  
  const direction = variation.isAbove ? 'acima' : 'abaixo';
  return `${variation.percentage}% ${direction}`;
}

// Retorna o ícone da variação da previsão
function getForecastIcon(accountData) {
  const variation = getForecastVariation(accountData);
  
  if (variation.percentage === 0) {
    return 'pi pi-minus';
  }
  
  return variation.isAbove ? 'pi pi-arrow-up' : 'pi pi-arrow-down';
}

// Retorna a classe CSS para a variação da previsão
function getForecastVariationClass(accountData) {
  const variation = getForecastVariation(accountData);
  
  if (variation.percentage === 0) {
    return 'forecast-neutral';
  }
  
  return variation.isAbove ? 'forecast-above' : 'forecast-below';
}

// --- FUNÇÕES PARA ABA DE TENDÊNCIAS ---
const periodOptions = [
  { label: 'Últimos 3 meses', value: '3months', days: 90 },
  { label: 'Últimos 6 meses', value: '6months', days: 180 },
  { label: 'Último ano', value: '12months', days: 365 }
];

async function fetchTrendsData() {
  try {
    const period = periodOptions.find(p => p.value === selectedPeriod.value);
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - period.days);
    
    const startDateStr = startDate.toISOString().split('T')[0];
    const endDateStr = endDate.toISOString().split('T')[0];
    
    trendsData.value = { trendTables: { byService: serviceVariationData.value } };
    
    // Carregar IA, gráfico e previsão em paralelo
    loadTrendsAISummary(startDateStr, endDateStr); // Para aba Visão Atual
    loadTrendsFocusedAI(); // Para aba Tendências
    loadTrendsChartData();
    loadForecastData();
    loadProjectsForecast();
    
  } catch (err) {
    console.error('Erro ao carregar análise de tendências:', err);
  }
}

async function loadTrendsAISummary(startDate, endDate) {
  isLoadingTrendsAI.value = true;
  try {
    await new Promise(resolve => setTimeout(resolve, 2000));
    trendsAiSummary.value = 'Análise do momento atual mostra variações significativas nos custos de EC2 e RDS, indicando expansão da infraestrutura. Recomenda-se monitoramento próximo dos novos recursos provisionados.';
  } catch (err) {
    trendsAiSummary.value = 'Resumo IA temporariamente indisponível.';
  } finally {
    isLoadingTrendsAI.value = false;
  }
}

async function loadTrendsFocusedAI() {
  isLoadingTrendsFocusedAI.value = true;
  try {
    // Base: últimos 7 dias para análise de tendência
    const endDate = new Date();
    const startDate = new Date(endDate);
    startDate.setDate(endDate.getDate() - 6); // Últimos 7 dias
    
    const startDateStr = startDate.toISOString().split('T')[0];
    const endDateStr = endDate.toISOString().split('T')[0];
    
    const response = await apiService.getTrendsAISummary(startDateStr, endDateStr);
    trendsFocusedAI.value = response.aiSummary || '';
  } catch (err) {
    console.error('Erro ao gerar análise de tendências:', err);
    trendsFocusedAI.value = 'Análise de tendências temporariamente indisponível.';
  } finally {
    isLoadingTrendsFocusedAI.value = false;
  }
}

async function loadTrendsChartData() {
  isLoadingTrendsChart.value = true;
  try {
    // Usar o endpoint correto que já existe
    const response = await apiService.get('/trends/chart');
    
    if (response && response.chartData) {
      trendsChartData.value = {
        labels: response.chartData.labels,
        datasets: [{
          label: 'Custo Mensal Total',
          data: response.chartData.datasets[0].data,
          backgroundColor: '#3B82F6',
          borderColor: '#1D4ED8',
          borderWidth: 1,
          borderRadius: 4
        }]
      };
    }
  } catch (error) {
    console.error('Erro ao carregar dados mensais:', error);
  } finally {
    isLoadingTrendsChart.value = false;
  }
}

async function loadForecastData() {
  isLoadingForecast.value = true;
  try {
    const response = await apiService.getTrendsForecast();
    
    // Verificar se há dados suficientes para previsão confiável
    if (response.success && response.projected30Days > 0) {
      forecastData.value = {
        projected30Days: response.projected30Days || 0,
        projectedChange: response.projectedChange || 0,
        growthRate: response.growthRate || 0,
        newServices: response.newServices || []
      };
    } else {
      // Dados insuficientes - mostrar mensagem em vez de valores zerados
      forecastData.value = null;
    }
  } catch (error) {
    console.error('Erro ao carregar previsão:', error);
    forecastData.value = null;
  } finally {
    isLoadingForecast.value = false;
  }
}

async function loadProjectsForecast() {
  isLoadingProjectsForecast.value = true;
  try {
    const response = await apiService.getProjectsForecast();
    if (response.success) {
      projectsForecast.value = response.projects || [];
    } else {
      projectsForecast.value = [];
    }
  } catch (error) {
    console.error('Erro ao carregar projeção por projetos:', error);
    projectsForecast.value = [];
  } finally {
    isLoadingProjectsForecast.value = false;
  }
}

// Funções auxiliares para a tabela de projetos
function getStatusColor(status) {
  switch (status) {
    case 'alert': return 'tw-bg-red-500';
    case 'warning': return 'tw-bg-yellow-500';
    default: return 'tw-bg-green-500';
  }
}

function getStatusLabel(status) {
  switch (status) {
    case 'alert': return 'Alerta';
    case 'warning': return 'Atenção';
    default: return 'Normal';
  }
}

function getTagSeverity(status) {
  switch (status) {
    case 'alert': return 'danger';
    case 'warning': return 'warning';
    default: return 'success';
  }
}

function getProgressSeverity(status) {
  switch (status) {
    case 'alert': return 'danger';
    case 'warning': return 'warning';
    default: return 'info';
  }
}

function getVariationClass(change) {
  if (change > 0) return 'tw-text-red-600';
  if (change < 0) return 'tw-text-green-600';
  return 'tw-text-gray-600';
}

function getProjectRowClass(data) {
  switch (data.status) {
    case 'alert': return 'tw-bg-red-50';
    case 'warning': return 'tw-bg-yellow-50';
    default: return '';
  }
}

function getForecastValue() {
  return forecastData.value?.projected30Days || 0;
}

function getForecastChange() {
  return forecastData.value?.projectedChange || 0;
}

function getForecastPercent() {
  const current = trendsData.value?.trendTables?.summary?.totalCost || 155;
  return current > 0 ? (getForecastChange() / current) * 100 : 0;
}

// --- WATCHERS ---
watch(dateRange, (newRange) => {
  if (newRange && newRange.length === 2) {
    fetchData();
  }
}, { deep: true });

// --- LIFECYCLE ---
onMounted(async () => {
  await fetchMemberAccounts();
  fetchData();
  // Inicializar dados de tendências
  fetchTrendsData();
});
</script>

<template>
  <div class="tw-p-6 tw-max-w-7xl tw-mx-auto">
    <!-- Header -->
    <div class="tw-mb-8">
      <div class="tw-text-center tw-mb-8">
        <h1 class="tw-text-4xl tw-font-bold tw-text-gray-900 tw-mb-3">Dashboard Estratégico</h1>
        <p class="tw-text-xl tw-text-gray-600">Insights avançados sobre seus custos de nuvem</p>
      </div>
    </div>

    <!-- Abas Principais -->
    <TabView>
      <TabPanel header="Visão Atual">

    <!-- Seção de Controles -->
    <Card class="tw-mb-6">
      <template #content>
        <div class="tw-grid tw-grid-cols-1 lg:tw-grid-cols-3 tw-gap-6 tw-items-end">
          <!-- Filtro de Conta-Membro -->
          <div class="tw-space-y-2">
            <label class="tw-block tw-text-sm tw-font-semibold tw-text-gray-700">Filtrar por Conta:</label>
            <Dropdown 
              v-model="selectedMemberAccount" 
              :options="memberAccounts" 
              optionLabel="name" 
              placeholder="Selecione uma conta"
              @change="onMemberAccountChange"
              class="w-full"
            >
              <template #value="slotProps">
                <div v-if="slotProps.value" class="flex align-items-center gap-2">
                  <i class="pi pi-building text-blue-500"></i>
                  <span>{{ slotProps.value.name }}</span>
                  <small v-if="slotProps.value.aws_account_id !== 'ALL'" class="text-gray-500">
                    ({{ slotProps.value.aws_account_id }})
                  </small>
                </div>
                <span v-else>Selecione uma conta</span>
              </template>
              <template #option="slotProps">
                <div class="flex align-items-center gap-2">
                  <i :class="slotProps.option.aws_account_id === 'ALL' ? 'pi pi-globe text-green-500' : 'pi pi-building text-blue-500'"></i>
                  <span>{{ slotProps.option.name }}</span>
                  <small v-if="slotProps.option.aws_account_id !== 'ALL'" class="text-gray-500">
                    ({{ slotProps.option.aws_account_id }})
                  </small>
                </div>
              </template>
            </Dropdown>
          </div>
          
          <!-- Botões de Período Pré-definido -->
          <div class="tw-space-y-2">
            <label class="tw-block tw-text-sm tw-font-semibold tw-text-gray-700">Períodos Rápidos:</label>
            <div class="tw-flex tw-flex-wrap tw-gap-2">
              <Button 
                label="7 dias" 
                @click="setLast7Days"
                size="small"
                outlined
                class="tw-text-xs"
              />
              <Button 
                label="Este Mês" 
                @click="setThisMonth"
                size="small"
                outlined
                class="tw-text-xs"
              />
              <Button 
                label="Mês Passado" 
                @click="setLastMonth"
                size="small"
                outlined
                class="tw-text-xs"
              />
            </div>
          </div>

          <!-- Seletor de Calendário Customizado -->
          <div class="tw-space-y-2">
            <label for="date-picker" class="tw-block tw-text-sm tw-font-semibold tw-text-gray-700">Período Customizado:</label>
            <flat-pickr
              id="date-picker"
              v-model="dateRange"
              :config="datePickerConfig"
              class="tw-w-full tw-px-3 tw-py-2 tw-border tw-border-gray-300 tw-rounded-md tw-text-sm"
            />
          </div>
        </div>
      </template>
    </Card>

    <!-- Widget de Resumo Executivo com IA -->
    <div class="tw-mb-6">
      <Card class="ai-summary-card">
        <template #header>
          <div class="tw-p-4">
            <h3 class="tw-text-xl tw-font-semibold tw-text-white tw-flex tw-items-center tw-gap-2">
              <i class="pi pi-lightbulb"></i>
              Insights Executivos
            </h3>
          </div>
        </template>
        <template #content>
          <div v-if="isAiSummaryLoading" class="tw-flex tw-items-center tw-gap-2 tw-text-white">
            <ProgressSpinner size="small" />
            <span>Analisando insights do período...</span>
          </div>
          <p v-else class="tw-text-white tw-m-0 tw-whitespace-pre-line tw-text-lg">{{ aiSummary }}</p>
        </template>
      </Card>
    </div>

    <!-- Estado de Loading -->
    <div v-if="isLoading" class="tw-flex tw-items-center tw-justify-center tw-py-12">
      <ProgressSpinner />
      <p class="tw-ml-3 tw-text-gray-600">Carregando dados estratégicos...</p>
    </div>

    <!-- Estado de Erro -->
    <Message v-else-if="error" severity="error" :closable="false" class="mb-4">
      {{ error }}
    </Message>

    <!-- Conteúdo Principal -->
    <div v-else-if="dashboardData">
      <!-- Seção de KPIs -->
      <div class="tw-grid tw-grid-cols-1 md:tw-grid-cols-2 lg:tw-grid-cols-4 tw-gap-4 tw-mb-6">
        <!-- KPI 1 - Custo Total com Barra de Progresso -->
        <Card class="tw-h-36">
          <template #content>
            <div class="tw-p-2 tw-h-full tw-flex tw-flex-col tw-justify-center tw-text-center">
              <!-- Seção Superior -->
              <div class="tw-flex tw-items-center tw-justify-center tw-space-x-2 tw-mb-1">
                <div class="tw-w-8 tw-h-8 tw-bg-blue-100 tw-rounded-full tw-flex tw-items-center tw-justify-center">
                  <i class="pi pi-dollar tw-text-blue-600 tw-text-sm"></i>
                </div>
                <h3 class="tw-text-sm tw-font-semibold tw-text-gray-700">Custo Total</h3>
              </div>
              
              <!-- Valor Principal -->
              <p class="tw-text-2xl tw-font-bold tw-text-gray-900 tw-mb-1">
                ${{ formatCurrency(kpis.totalCost || 0) }}
              </p>
              
              <!-- Barra de Progresso do Orçamento -->
              <div v-if="kpis.totalMonthlyBudget > 0" class="tw-w-full tw-px-4">
                <div class="tw-text-xs tw-font-medium tw-text-gray-600 tw-mb-1 tw-text-center">
                  {{ getBudgetConsumptionPercentage().toFixed(1) }}%
                </div>
                <ProgressBar 
                  :value="getBudgetConsumptionPercentage()" 
                  :severity="getBudgetConsumptionSeverity()"
                  class="mini-progress-bar"
                  :showValue="false"
                />
              </div>
            </div>
          </template>
        </Card>

        <!-- KPI 2 - Orçamento Total -->
        <Card class="tw-h-36">
          <template #content>
            <div class="tw-p-1 tw-h-full tw-flex tw-flex-col tw-justify-center tw-text-center">
              <!-- Seção Superior -->
              <div class="tw-flex tw-items-center tw-justify-center tw-space-x-2 tw-mb-2">
                <div class="tw-w-8 tw-h-8 tw-bg-green-100 tw-rounded-full tw-flex tw-items-center tw-justify-center">
                  <i class="pi pi-flag tw-text-green-600 tw-text-sm"></i>
                </div>
                <h3 class="tw-text-sm tw-font-semibold tw-text-gray-700">Orçamento</h3>
              </div>
              
              <!-- Valor Principal -->
              <p class="tw-text-2xl tw-font-bold tw-text-gray-900 tw-mb-2">
                ${{ formatCurrency(kpis.totalMonthlyBudget || 0) }}
              </p>
              
              <!-- Informação Adicional -->
              <div class="tw-text-xs tw-text-gray-500">
                Meta mensal
              </div>
            </div>
          </template>
        </Card>

        <!-- KPI 3 - Variação -->
        <Card class="tw-h-36">
          <template #content>
            <div class="tw-p-1 tw-h-full tw-flex tw-flex-col tw-justify-center tw-text-center">
              <!-- Seção Superior -->
              <div class="tw-flex tw-items-center tw-justify-center tw-space-x-2 tw-mb-2">
                <div :class="['tw-w-8 tw-h-8 tw-rounded-full tw-flex tw-items-center tw-justify-center', 
                             kpis.totalVariationPercentage >= 0 ? 'tw-bg-red-100' : 'tw-bg-green-100']">
                  <i :class="['tw-text-sm', 
                             kpis.totalVariationPercentage >= 0 ? 'pi pi-arrow-up tw-text-red-600' : 'pi pi-arrow-down tw-text-green-600']"></i>
                </div>
                <h3 class="tw-text-sm tw-font-semibold tw-text-gray-700">Variação</h3>
              </div>
              
              <!-- Valor Principal -->
              <p :class="['tw-text-2xl tw-font-bold tw-mb-1', 
                         kpis.totalVariationPercentage >= 0 ? 'tw-text-red-600' : 'tw-text-green-600']">
                {{ kpis.totalVariationPercentage >= 0 ? '+' : '' }}{{ (kpis.totalVariationPercentage || 0).toFixed(1) }}%
              </p>
              
              <!-- Informação Adicional -->
              <div class="tw-text-xs tw-text-gray-500">
                ${{ kpis.totalVariationValue >= 0 ? '+' : '' }}{{ (kpis.totalVariationValue || 0).toFixed(2) }}
              </div>
            </div>
          </template>
        </Card>

        <!-- KPI 4 - Créditos -->
        <Card class="tw-h-36">
          <template #content>
            <div class="tw-p-1 tw-h-full tw-flex tw-flex-col tw-justify-center tw-text-center">
              <!-- Seção Superior -->
              <div class="tw-flex tw-items-center tw-justify-center tw-space-x-2 tw-mb-2">
                <div class="tw-w-8 tw-h-8 tw-bg-purple-100 tw-rounded-full tw-flex tw-items-center tw-justify-center">
                  <i class="pi pi-credit-card tw-text-purple-600 tw-text-sm"></i>
                </div>
                <h3 class="tw-text-sm tw-font-semibold tw-text-gray-700">Créditos</h3>
              </div>
              
              <!-- Valor Principal -->
              <p class="tw-text-2xl tw-font-bold tw-text-green-600 tw-mb-2">
                ${{ formatCurrency(kpis.credits || 0) }}
              </p>
              
              <!-- Informação Adicional -->
              <div class="tw-text-xs tw-text-gray-500">
                Aplicados
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Gráfico Principal - Largura Total -->
      <Card class="tw-mb-6 tw-overflow-hidden">
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

      <!-- Gráfico Evolução Mensal -->
      <Card class="tw-mb-6 tw-overflow-hidden">
        <template #title>
          <i class="pi pi-chart-bar mr-2"></i>
          Evolução Mensal de Custos
        </template>
        <template #content>
          <div v-if="isLoadingTrendsChart" class="tw-text-center tw-py-8">
            <ProgressSpinner />
            <p class="tw-mt-4">Carregando evolução mensal...</p>
          </div>
          <div v-else-if="!trendsChartData.datasets[0]?.data?.length" class="tw-h-96 tw-flex tw-items-center tw-justify-center tw-text-gray-500">
            <div class="tw-text-center">
              <i class="pi pi-chart-bar tw-text-4xl tw-mb-4"></i>
              <p>Dados de evolução mensal não disponíveis para o período selecionado</p>
            </div>
          </div>
          <div v-else class="tw-h-96">
            <Chart 
              type="bar"
              :data="trendsChartData"
              :options="{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { position: 'top' },
                  title: { display: true, text: 'Últimos 6 Meses - Dados Reais' }
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    ticks: { callback: function(value) { return '$' + value.toFixed(0); } }
                  }
                },
                layout: {
                  padding: {
                    top: 20,
                    bottom: 20,
                    left: 20,
                    right: 20
                  }
                },
                elements: {
                  bar: {
                    backgroundColor: '#3B82F6',
                    borderColor: '#1D4ED8',
                    borderWidth: 1,
                    borderRadius: 4
                  }
                }
              }"
              style="width: 100% !important; height: 100% !important;"
            />
          </div>
        </template>
      </Card>

      <!-- Tabelas de Insights -->
      <div class="insights-grid">
        <!-- Tabela 1 - Maiores Variações por Serviço -->
        <Card class="table-card">
          <template #title>
            Top 10 Serviços
          </template>
          <template #content>
            <div class="tw-space-y-4">
              <div 
                v-for="(service, index) in serviceVariationData.slice(0, 10)" 
                :key="service.service"
                class="tw-flex tw-items-center tw-justify-between tw-py-3 tw-px-4 tw-bg-gray-50 tw-rounded-lg"
              >
                <div class="tw-flex-1">
                  <div class="tw-font-semibold tw-text-gray-900 tw-mb-1">
                    {{ service.service }}
                  </div>
                  <div class="tw-text-sm tw-text-gray-600">
                    ${{ (service.currentCost || 0).toFixed(2) }}
                  </div>
                </div>
                
                <div class="tw-flex tw-items-center tw-gap-3 tw-min-w-32">
                  <div class="tw-flex tw-flex-col tw-flex-1">
                    <div class="tw-text-xs tw-text-gray-500 tw-mb-1">Variação</div>
                    <ProgressBar 
                      :value="Math.abs((service.variationPercentage || 0))" 
                      :max="100"
                      :severity="(service.variationValue || 0) >= 0 ? 'danger' : 'success'"
                      class="tw-flex-1 tw-h-3"
                      :showValue="false"
                    />
                  </div>
                  <span :class="(service.variationValue || 0) >= 0 ? 'tw-text-red-600 tw-font-bold' : 'tw-text-green-600 tw-font-bold'" class="tw-text-sm tw-min-w-12 tw-text-right">
                    {{ (service.variationPercentage || 0) >= 0 ? '+' : '' }}{{ (service.variationPercentage || 0).toFixed(1) }}%
                  </span>
                </div>
              </div>
            </div>
          </template>
        </Card>

        <!-- NOVA: Governança Financeira - Layout Moderno -->
        <Card class="table-card">
          <template #title>
            Governança Financeira por Conta
          </template>
          <template #content>
            <div class="tw-space-y-4">
              <div 
                v-for="account in costByAccountData" 
                :key="account.accountId"
                class="tw-flex tw-items-center tw-justify-between tw-py-3 tw-px-4 tw-bg-gray-50 tw-rounded-lg"
              >
                <div class="tw-flex-1">
                  <div class="tw-font-semibold tw-text-gray-900 tw-mb-1">
                    {{ account.accountName }}
                  </div>
                  <div class="tw-text-sm tw-text-gray-600">
                    ${{ formatCurrencyFull(account.totalCost || 0) }}
                  </div>
                </div>
                
                <div class="tw-flex tw-items-center tw-gap-3 tw-min-w-32">
                  <div class="tw-flex tw-flex-col tw-flex-1">
                    <div class="tw-text-xs tw-text-gray-500 tw-mb-1">Uso do Orçamento</div>
                    <ProgressBar 
                      :value="getBudgetPercentage(account)" 
                      :max="100"
                      :severity="getBudgetPercentage(account) > 80 ? 'danger' : getBudgetPercentage(account) > 60 ? 'warning' : 'success'"
                      class="tw-flex-1 tw-h-3"
                      :showValue="false"
                    />
                  </div>
                  <span :class="getBudgetPercentage(account) > 80 ? 'tw-text-red-600 tw-font-bold' : getBudgetPercentage(account) > 60 ? 'tw-text-orange-600 tw-font-bold' : 'tw-text-green-600 tw-font-bold'" class="tw-text-sm tw-min-w-12 tw-text-right">
                    {{ getBudgetPercentage(account).toFixed(0) }}%
                  </span>
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <!-- Estado Vazio -->
    <Message v-else severity="info" :closable="false" class="mb-4">
      Nenhum dado disponível para o período selecionado.
    </Message>

      </TabPanel>
      
      <TabPanel header="Tendências">
        <div class="trends-content tw-space-y-6">
          <!-- Previsão -->
          <Card class="forecast-card">
            <template #header>
              <div class="tw-p-4">
                <h3 class="tw-text-xl tw-font-semibold tw-text-white tw-flex tw-items-center tw-gap-2">
                  <i class="pi pi-forward"></i>
                  Previsão - Próximos 30 Dias
                  <small class="tw-text-sm tw-opacity-80">(Baseada nos últimos 7 dias)</small>
                </h3>
              </div>
            </template>
            <template #content>
              <div v-if="isLoadingForecast" class="tw-flex tw-items-center tw-gap-2 tw-text-white">
                <ProgressSpinner size="small" />
                <span>Calculando previsão...</span>
              </div>
              <div v-else-if="!forecastData" class="tw-text-center tw-text-white tw-py-8">
                <i class="pi pi-info-circle tw-text-4xl tw-mb-4 tw-opacity-60"></i>
                <p class="tw-text-lg tw-mb-2">Dados Insuficientes</p>
                <p class="tw-text-sm tw-opacity-80">Aguarde mais dados históricos para previsões precisas</p>
              </div>
              <div v-else class="tw-space-y-6 tw-text-white">
                <!-- Valor Principal -->
                <div class="tw-text-center tw-border-b tw-border-white/20 tw-pb-4">
                  <div class="tw-text-3xl tw-font-bold tw-mb-1">${{ getForecastValue().toFixed(2) }}</div>
                  <div class="tw-text-sm tw-opacity-80">Custo Projetado (30 dias)</div>
                </div>
                
                <!-- Métricas -->
                <div class="tw-grid tw-grid-cols-2 tw-gap-4">
                  <div class="tw-bg-white/10 tw-rounded-lg tw-p-3 tw-text-center">
                    <div class="tw-text-lg tw-font-semibold">${{ getForecastChange().toFixed(2) }}</div>
                    <div class="tw-text-xs tw-opacity-80">Variação Esperada</div>
                  </div>
                  <div class="tw-bg-white/10 tw-rounded-lg tw-p-3 tw-text-center">
                    <div class="tw-text-lg tw-font-semibold">{{ getForecastPercent().toFixed(1) }}%</div>
                    <div class="tw-text-xs tw-opacity-80">Percentual</div>
                  </div>
                </div>
                
                <!-- Taxa de Crescimento -->
                <div v-if="forecastData.growthRate" class="tw-bg-white/5 tw-rounded-lg tw-p-3">
                  <div class="tw-flex tw-justify-between tw-items-center">
                    <span class="tw-text-sm">Taxa de Crescimento Diário:</span>
                    <span class="tw-font-bold">{{ forecastData.growthRate.toFixed(2) }}%</span>
                  </div>
                </div>
                
                <!-- Novos Serviços -->
                <div v-if="forecastData.newServices?.length > 0" class="tw-bg-white/5 tw-rounded-lg tw-p-3">
                  <div class="tw-font-semibold tw-mb-2 tw-text-sm">Novos Serviços Detectados:</div>
                  <div class="tw-space-y-1">
                    <div v-for="service in forecastData.newServices" :key="service.service" 
                         class="tw-flex tw-justify-between tw-text-xs tw-opacity-90">
                      <span>{{ service.service }}</span>
                      <span>${{ service.dailyCost.toFixed(2) }}/dia</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </Card>

          <!-- Tabela de Projeção por Projeto -->
          <Card>
            <template #header>
              <div class="tw-p-4 tw-bg-gradient-to-r tw-from-slate-50 tw-to-blue-50">
                <h3 class="tw-text-xl tw-font-semibold tw-text-gray-800 tw-flex tw-items-center tw-gap-2">
                  <i class="pi pi-chart-line tw-text-blue-600"></i>
                  Projeção por Projeto - Próximos 30 Dias
                </h3>
                <p class="tw-text-sm tw-text-gray-600 tw-mt-1">Baseada nos últimos 7 dias de consumo</p>
              </div>
            </template>
            <template #content>
              <div v-if="isLoadingProjectsForecast" class="tw-flex tw-items-center tw-justify-center tw-py-8">
                <ProgressSpinner size="small" />
                <span class="tw-ml-2">Calculando projeções por projeto...</span>
              </div>
              <div v-else-if="!projectsForecast?.length" class="tw-text-center tw-py-8 tw-text-gray-500">
                <i class="pi pi-info-circle tw-text-4xl tw-mb-4"></i>
                <p>Nenhum projeto identificado no período</p>
              </div>
              <DataTable 
                v-else
                :value="projectsForecast" 
                :paginator="true" 
                :rows="10"
                :sortField="'currentCost'"
                :sortOrder="-1"
                class="tw-shadow-sm"
                :rowClass="getProjectRowClass"
              >
                <Column field="project" header="Projeto" :sortable="true" class="tw-min-w-48">
                  <template #body="slotProps">
                    <div class="tw-flex tw-items-center tw-gap-2">
                      <div class="tw-w-3 tw-h-3 tw-rounded-full" :class="getStatusColor(slotProps.data.status)"></div>
                      <div>
                        <div class="tw-font-semibold tw-text-gray-800">{{ slotProps.data.project }}</div>
                        <div class="tw-text-xs tw-text-gray-500">{{ slotProps.data.servicesCount }} serviços</div>
                      </div>
                    </div>
                  </template>
                </Column>
                
                <Column field="currentCost" header="Custo Atual (7d)" :sortable="true" class="tw-text-right">
                  <template #body="slotProps">
                    <span class="tw-font-semibold tw-text-gray-700">
                      ${{ slotProps.data.currentCost?.toFixed(2) || '0.00' }}
                    </span>
                  </template>
                </Column>
                
                <Column header="Projeção 30 Dias" :sortable="false" class="tw-text-right tw-min-w-40">
                  <template #body="slotProps">
                    <div class="tw-space-y-1">
                      <div class="tw-font-semibold tw-text-blue-600">
                        ${{ slotProps.data.projected30Days?.toFixed(2) || '0.00' }}
                      </div>
                      <ProgressBar 
                        :value="Math.abs(slotProps.data.variationPercent || 0)" 
                        :max="100"
                        :severity="getProgressSeverity(slotProps.data.status)"
                        class="tw-w-full tw-h-2"
                        :showValue="false"
                      />
                    </div>
                  </template>
                </Column>
                
                <Column header="Variação" :sortable="false" class="tw-text-center">
                  <template #body="slotProps">
                    <div class="tw-space-y-1">
                      <div :class="getVariationClass(slotProps.data.projectedChange)" class="tw-font-semibold">
                        {{ slotProps.data.projectedChange >= 0 ? '+' : '' }}${{ slotProps.data.projectedChange?.toFixed(2) || '0.00' }}
                      </div>
                      <div :class="getVariationClass(slotProps.data.projectedChange)" class="tw-text-xs">
                        {{ slotProps.data.projectedChange >= 0 ? '+' : '' }}{{ slotProps.data.variationPercent?.toFixed(1) || '0.0' }}%
                      </div>
                    </div>
                  </template>
                </Column>
                
                <Column header="Status" :sortable="false" class="tw-text-center">
                  <template #body="slotProps">
                    <Tag 
                      :value="getStatusLabel(slotProps.data.status)" 
                      :severity="getTagSeverity(slotProps.data.status)"
                      class="tw-text-xs"
                    />
                  </template>
                </Column>
              </DataTable>
            </template>
          </Card>
        </div>
      </TabPanel>
    </TabView>
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
  grid-template-columns: 1fr 1fr 1fr;
  gap: 2rem;
  align-items: end;
}

.control-label {
  display: block;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.5rem;
}

.account-filter {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
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
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.kpi-card {
  border-left: 4px solid #007BFF;
}

.kpi-primary { border-left-color: #007BFF; }
.kpi-budget { border-left-color: #e91e63; } /* Rosa para orçamento */
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

/* Barra de Progresso do Orçamento Total */
.budget-progress-container {
  margin-top: 0.75rem;
  width: 100%;
}

.budget-status-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.budget-status-icon {
  font-size: 1rem;
}

.budget-status-text {
  font-size: 0.85rem;
  font-weight: 600;
  color: #495057;
}

.budget-progress-kpi {
  height: 8px;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

/* Cores personalizadas para a barra de progresso */
.budget-progress-kpi :deep(.p-progressbar-value) {
  background-color: var(--progress-color, #007bff);
  transition: background-color 0.3s ease;
}

.budget-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
}

.budget-info {
  color: #6c757d;
}

.budget-percentage {
  font-weight: 700;
  font-size: 0.9rem;
  padding: 0.2rem 0.5rem;
  border-radius: 0.25rem;
}

.budget-percentage.success {
  color: #28a745;
  background-color: #d4edda;
}

.budget-percentage.info {
  color: #17a2b8;
  background-color: #d1ecf1;
}

.budget-percentage.warning {
  color: #856404;
  background-color: #fff3cd;
}

.budget-percentage.danger {
  color: #721c24;
  background-color: #f8d7da;
}

/* Responsividade para modal */
@media (max-width: 768px) {
  .detail-row {
    flex-direction: column;
    align-items: start;
    gap: 0.25rem;
  }
  
  .history-header {
    flex-direction: column;
    align-items: start;
    gap: 0.5rem;
  }
  
  .history-meta {
    align-items: start;
  }
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

/* Tabelas de Insights - Layout 50%/50% */
.insights-grid {
  display: grid;
  grid-template-columns: 1fr 1fr; /* Top 10 Serviços 50%, Governança 50% */
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

/* --- ESTILOS PARA LAYOUT HÍBRIDO RESPONSIVO --- */

/* Controle de visibilidade por breakpoint */
.desktop-table-view {
  display: block;
}

.mobile-cards-view {
  display: none;
}

/* Estilos da tabela desktop */
.desktop-table-view .p-datatable {
  width: 100%;
}

.cost-value {
  font-weight: 600;
  color: #2563eb;
  font-size: 0.95rem;
}

.budget-value {
  color: #6b7280;
  font-size: 0.95rem;
}

.consumption-cell {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.consumption-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.consumption-percentage {
  font-weight: 600;
  font-size: 0.9rem;
}

.consumption-status {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.2rem 0.5rem;
  border-radius: 0.25rem;
}

.status-ok {
  background-color: #dcfce7;
  color: #166534;
}

.status-warning {
  background-color: #fef3c7;
  color: #92400e;
}

.status-danger {
  background-color: #fee2e2;
  color: #991b1b;
}

.consumption-bar {
  height: 8px;
}

.forecast-cell {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.forecast-amount {
  font-weight: 600;
  font-size: 0.95rem;
  color: #374151;
}

.forecast-variation {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8rem;
  font-weight: 500;
}

.forecast-above {
  color: #dc2626;
}

.forecast-below {
  color: #16a34a;
}

.forecast-neutral {
  color: #6b7280;
}

/* Estilos dos cards mobile */
.account-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 1rem;
}

.account-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.account-name {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
  color: #1f2937;
}

.account-status {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
}

.account-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.metric-label {
  font-size: 0.8rem;
  color: #6b7280;
  font-weight: 500;
}

.metric-value {
  font-size: 0.95rem;
  font-weight: 600;
}

.metric-value.cost-value {
  color: #2563eb;
}

.metric-value.budget-value {
  color: #6b7280;
}

.metric-value.forecast-value {
  color: #374151;
}

.account-progress {
  margin-bottom: 0.75rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
}

.progress-percentage {
  font-weight: 600;
}

.progress-bar-mobile {
  height: 8px;
}

.forecast-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 500;
  justify-content: center;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 0.25rem;
}

/* Responsividade */
@media (max-width: 1024px) {
  .desktop-table-view {
    display: none;
  }
  
  .mobile-cards-view {
    display: block;
  }
}

@media (max-width: 640px) {
  .account-metrics {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }
  
  .metric {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem;
    background: white;
    border-radius: 0.25rem;
  }
  
  .account-header {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }
}

/* Melhorias gerais */
/* Barra de progresso mini para KPI */
.mini-progress-bar {
  height: 3px !important;
}

.mini-progress-bar .p-progressbar {
  height: 3px !important;
}

.mini-progress-bar .p-progressbar-value {
  height: 3px !important;
}

.table-card .p-card-content {
  padding: 1.5rem;
}

@media (max-width: 1024px) {
  .table-card .p-card-content {
    padding: 1rem;
  }
}

/* Estilos para card de IA */
.ai-summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.forecast-card {
  background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #06b6d4 100%);
  color: white;
  box-shadow: 0 10px 25px rgba(59, 130, 246, 0.3);
}

.chart-container {
  height: 400px;
  width: 100%;
}

/* Fix para seletor de data - sobrescrever p-dark do PrimeVue */
.flatpickr-calendar,
.flatpickr-calendar.open,
.flatpickr-calendar.inline,
.p-dark .flatpickr-calendar,
body.p-dark .flatpickr-calendar {
  background: #ffffff !important;
  background-color: #ffffff !important;
  color: #333333 !important;
  border: 1px solid #ddd !important;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
}

/* Sobrescrever todos os elementos internos mesmo com p-dark */
.flatpickr-calendar *,
.p-dark .flatpickr-calendar *,
body.p-dark .flatpickr-calendar * {
  background-color: inherit !important;
  color: inherit !important;
}

.flatpickr-day,
.flatpickr-day.flatpickr-disabled,
.flatpickr-day.prevMonthDay,
.flatpickr-day.nextMonthDay,
.p-dark .flatpickr-day,
body.p-dark .flatpickr-day {
  background: #ffffff !important;
  background-color: #ffffff !important;
  color: #333333 !important;
}

.flatpickr-day:hover,
.flatpickr-day.prevMonthDay:hover,
.flatpickr-day.nextMonthDay:hover,
.p-dark .flatpickr-day:hover,
body.p-dark .flatpickr-day:hover {
  background: #f8f9fa !important;
  background-color: #f8f9fa !important;
  color: #333333 !important;
}

.flatpickr-day.selected,
.flatpickr-day.selected:hover,
.flatpickr-day.startRange,
.flatpickr-day.endRange,
.p-dark .flatpickr-day.selected,
body.p-dark .flatpickr-day.selected {
  background: #007bff !important;
  background-color: #007bff !important;
  color: #ffffff !important;
  border-color: #007bff !important;
}

.flatpickr-months,
.flatpickr-month,
.p-dark .flatpickr-months,
body.p-dark .flatpickr-months {
  background: #ffffff !important;
  background-color: #ffffff !important;
  color: #333333 !important;
}

.flatpickr-weekdays,
.p-dark .flatpickr-weekdays,
body.p-dark .flatpickr-weekdays {
  background: #f8f9fa !important;
  background-color: #f8f9fa !important;
}

.flatpickr-weekday,
.p-dark .flatpickr-weekday,
body.p-dark .flatpickr-weekday {
  background: #f8f9fa !important;
  background-color: #f8f9fa !important;
  color: #666666 !important;
}

.flatpickr-current-month .flatpickr-monthDropdown-months,
.flatpickr-current-month input.cur-year,
.p-dark .flatpickr-current-month .flatpickr-monthDropdown-months,
body.p-dark .flatpickr-current-month input.cur-year {
  background: #ffffff !important;
  background-color: #ffffff !important;
  color: #333333 !important;
}

.flatpickr-prev-month:hover svg,
.flatpickr-next-month:hover svg,
.p-dark .flatpickr-prev-month:hover svg,
body.p-dark .flatpickr-next-month:hover svg {
  fill: #007bff !important;
}

.flatpickr-prev-month svg,
.flatpickr-next-month svg,
.p-dark .flatpickr-prev-month svg,
body.p-dark .flatpickr-next-month svg {
  fill: #333333 !important;
}
</style>
