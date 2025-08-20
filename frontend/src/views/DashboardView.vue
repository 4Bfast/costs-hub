<script setup>
import { ref, onMounted, computed } from 'vue';
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
import Dropdown from 'primevue/dropdown';

// --- GERENCIAMENTO DE ESTADO ---
const dashboardData = ref(null);
const memberAccounts = ref([]);
const selectedMemberAccount = ref(null);
const isLoading = ref(true);
const error = ref(null);
// Função para calcular os últimos 7 dias
const getDefaultDateRange = () => {
  const endDate = new Date();
  const startDate = new Date(endDate);
  startDate.setDate(endDate.getDate() - 6); // Últimos 7 dias (incluindo hoje)
  return [startDate, endDate];
};

const dateRange = ref(getDefaultDateRange());

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



const costByAccountData = computed(() => dashboardData.value?.costByAccount || []);

// --- CONFIGURAÇÃO DO DATE PICKER ---
const datePickerConfig = computed(() => ({
  mode: 'range',
  dateFormat: 'd/m/Y',
  locale: Portuguese,
  maxDate: new Date(),
  defaultDate: dateRange.value
}));

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

// Obtém o ícone baseado na porcentagem do orçamento total
function getBudgetStatusIconKPI() {
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

// Funções específicas para os cards modernos
function getBudgetStatusIcon(accountData) {
  const percentage = getBudgetPercentage(accountData);
  
  if (percentage < 80) {
    return 'pi pi-check-circle';
  } else if (percentage <= 100) {
    return 'pi pi-exclamation-triangle';
  } else {
    return 'pi pi-times-circle';
  }
}

function getBudgetStatusCardClass(accountData) {
  const percentage = getBudgetPercentage(accountData);
  
  if (percentage < 80) {
    return 'card-status-ok';
  } else if (percentage <= 100) {
    return 'card-status-warning';
  } else {
    return 'card-status-danger';
  }
}

function getBudgetPercentageClass(accountData) {
  const percentage = getBudgetPercentage(accountData);
  
  if (percentage < 80) {
    return 'percentage-ok';
  } else if (percentage <= 100) {
    return 'percentage-warning';
  } else {
    return 'percentage-danger';
  }
}

function getRemainingBudgetClass(accountData) {
  const remaining = (accountData.monthlyBudget || 0) - (accountData.totalCost || 0);
  
  if (remaining > 0) {
    return 'remaining-positive';
  } else {
    return 'remaining-negative';
  }
}

// Calcula o valor restante do orçamento
function getRemainingBudget(accountData) {
  const remaining = (accountData.monthlyBudget || 0) - (accountData.totalCost || 0);
  return Math.max(0, remaining); // Não retorna valores negativos
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

// --- LIFECYCLE ---
onMounted(async () => {
  await fetchMemberAccounts();
  fetchData();
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
              @on-change="onDateRangeChange"
            />
          </div>
        </div>
      </template>
    </Card>

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

      <!-- Grid de Governança Financeira - Cards Modernos -->
      <Card class="tw-mb-6 tw-overflow-hidden">
        <template #title>
          <div class="tw-flex tw-items-center">
            <i class="pi pi-building tw-mr-2 tw-text-blue-600"></i>
            <span class="tw-text-lg tw-font-semibold">Governança Financeira por Conta</span>
          </div>
        </template>
        <template #content>
          <!-- Grid de Cards Responsivo -->
          <div class="governance-grid">
            <div 
              v-for="account in costByAccountData" 
              :key="account.accountId" 
              class="governance-card"
              :class="getBudgetStatusClass(account)"
            >
              <!-- Header do Card -->
              <div class="card-header">
                <div class="account-info">
                  <div class="account-icon">
                    <i class="pi pi-building"></i>
                  </div>
                  <div class="account-details">
                    <h4 class="account-name">{{ account.accountName }}</h4>
                    <span class="account-status" :class="getBudgetStatusClass(account)">
                      {{ getBudgetStatus(account) }}
                    </span>
                  </div>
                </div>
                <div class="status-badge" :class="getBudgetStatusClass(account)">
                  <i :class="getBudgetStatusIcon(account)" class="tw-mr-1"></i>
                  {{ getBudgetPercentage(account) }}%
                </div>
              </div>

              <!-- Métricas Principais -->
              <div class="metrics-grid">
                <div class="metric-item primary">
                  <div class="metric-icon">
                    <i class="pi pi-dollar"></i>
                  </div>
                  <div class="metric-content">
                    <span class="metric-label">Custo Atual</span>
                    <span class="metric-value">${{ formatCurrencyFull(account.totalCost || 0) }}</span>
                  </div>
                </div>

                <div class="metric-item">
                  <div class="metric-icon">
                    <i class="pi pi-calendar"></i>
                  </div>
                  <div class="metric-content">
                    <span class="metric-label">Orçamento</span>
                    <span class="metric-value">${{ formatCurrencyFull(account.monthlyBudget || 0) }}</span>
                  </div>
                </div>

                <div class="metric-item">
                  <div class="metric-icon">
                    <i class="pi pi-chart-line"></i>
                  </div>
                  <div class="metric-content">
                    <span class="metric-label">Previsão</span>
                    <span class="metric-value">${{ formatCurrencyFull(account.forecastedCost || 0) }}</span>
                  </div>
                </div>
              </div>

              <!-- Barra de Progresso -->
              <div class="progress-section">
                <div class="progress-header">
                  <span class="progress-label">Consumo do Orçamento</span>
                  <span class="progress-percentage">{{ getBudgetPercentage(account) }}%</span>
                </div>
                <div class="progress-bar-container">
                  <ProgressBar 
                    :value="getBudgetPercentage(account)" 
                    :severity="getBudgetSeverity(account)"
                    class="custom-progress-bar"
                    :showValue="false"
                  />
                </div>
              </div>

              <!-- Footer com Valor Restante -->
              <div class="card-footer">
                <div class="remaining-budget">
                  <span class="remaining-label">Restante:</span>
                  <span class="remaining-value" :class="getRemainingBudgetClass(account)">
                    ${{ formatCurrencyFull(getRemainingBudget(account)) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Estado Vazio -->
          <div v-if="!costByAccountData || costByAccountData.length === 0" class="empty-state">
            <i class="pi pi-inbox tw-text-4xl tw-text-gray-400 tw-mb-4"></i>
            <p class="tw-text-gray-500">Nenhuma conta AWS configurada</p>
          </div>
        </template>
      </Card>
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

/* Grid de Cards Modernos - Governança Financeira */
.governance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
  margin-top: 1rem;
}

.governance-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.governance-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* Status do Card */
.governance-card.status-ok {
  border-left: 4px solid #10b981;
}

.governance-card.status-warning {
  border-left: 4px solid #f59e0b;
}

.governance-card.status-danger {
  border-left: 4px solid #ef4444;
}

/* Header do Card */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.account-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.account-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.25rem;
}

.account-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.account-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
  line-height: 1.2;
}

.account-status {
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.account-status.status-ok {
  color: #065f46;
}

.account-status.status-warning {
  color: #92400e;
}

.account-status.status-danger {
  color: #991b1b;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.status-badge.status-ok {
  background-color: #d1fae5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.status-badge.status-warning {
  background-color: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
}

.status-badge.status-danger {
  background-color: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

/* Grid de Métricas */
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.metric-item:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.metric-item.primary {
  background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
  border-color: #bae6fd;
}

.metric-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1rem;
}

.metric-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.metric-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.metric-value {
  font-size: 1rem;
  font-weight: 700;
  color: #1f2937;
}

/* Seção de Progresso */
.progress-section {
  margin-bottom: 1.5rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.progress-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #6b7280;
}

.progress-percentage {
  font-size: 0.875rem;
  font-weight: 700;
  color: #1f2937;
}

.progress-bar-container {
  margin-bottom: 0.5rem;
}

.custom-progress-bar {
  height: 12px !important;
  border-radius: 6px !important;
}

/* Indicador de Previsão */
.forecast-indicator {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-radius: 12px;
  margin-bottom: 1.5rem;
  transition: all 0.2s ease;
}

.forecast-indicator.forecast-positive {
  background-color: #d1fae5;
  border: 1px solid #a7f3d0;
  color: #065f46;
}

.forecast-indicator.forecast-negative {
  background-color: #fee2e2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.forecast-indicator.forecast-neutral {
  background-color: #f3f4f6;
  border: 1px solid #d1d5db;
  color: #374151;
}

.forecast-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.forecast-icon {
  font-size: 1rem;
}

.forecast-text {
  font-size: 0.875rem;
  font-weight: 600;
}

.forecast-value {
  font-size: 1rem;
  font-weight: 700;
}

/* Footer do Card */
.card-footer {
  border-top: 1px solid #e2e8f0;
  padding-top: 1rem;
}

.remaining-budget {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.remaining-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #6b7280;
}

.remaining-value {
  font-size: 1rem;
  font-weight: 700;
}

.remaining-value.remaining-positive {
  color: #059669;
}

.remaining-value.remaining-negative {
  color: #dc2626;
}

/* Estado Vazio */
.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  color: #6b7280;
}

.empty-state i {
  display: block;
  margin-bottom: 1rem;
}

/* Responsividade */
@media (max-width: 1024px) {
  .governance-grid {
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 1rem;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }
}

@media (max-width: 768px) {
  .governance-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .governance-card {
    padding: 1rem;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .status-badge {
    align-self: flex-start;
  }
}

@media (max-width: 480px) {
  .governance-grid {
    grid-template-columns: 1fr;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .metric-item {
    padding: 0.75rem;
  }
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
</style>
