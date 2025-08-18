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
const dateRange = ref([
  new Date('2025-08-09'), // Data que sabemos que tem dados
  new Date('2025-08-16')  // Data que sabemos que tem dados
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

// --- LIFECYCLE ---
onMounted(async () => {
  await fetchMemberAccounts();
  fetchData();
});
</script>

<template>
  <div class="container-main py-8">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="heading-2 mb-2">Dashboard Estratégico</h1>
      <p class="text-gray-600">Insights avançados sobre seus custos de nuvem</p>
    </div>

    <!-- Seção de Controles -->
    <Card class="card-base mb-8">
      <template #content>
        <div class="p-6">
          <div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
            <!-- Filtro de Conta-Membro -->
            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium text-gray-700">Filtrar por Conta:</label>
              <Dropdown 
                v-model="selectedMemberAccount" 
                :options="memberAccounts" 
                optionLabel="name" 
                placeholder="Selecione uma conta"
                @change="onMemberAccountChange"
                class="w-full sm:w-64"
              >
                <template #value="slotProps">
                  <div v-if="slotProps.value" class="flex items-center gap-3">
                    <i class="pi pi-building text-blue-500 mr-3"></i>
                    <span>{{ slotProps.value.name }}</span>
                    <small v-if="slotProps.value.aws_account_id !== 'ALL'" class="text-gray-500">
                      ({{ slotProps.value.aws_account_id }})
                    </small>
                  </div>
                </template>
                
                <template #option="slotProps">
                  <div class="flex items-center gap-3">
                    <i :class="slotProps.option.aws_account_id === 'ALL' ? 'pi pi-globe text-green-500 mr-3' : 'pi pi-building text-blue-500 mr-3'"></i>
                    <span>{{ slotProps.option.name }}</span>
                    <small v-if="slotProps.option.aws_account_id !== 'ALL'" class="text-gray-500">
                      ({{ slotProps.option.aws_account_id }})
                    </small>
                  </div>
                </template>
              </Dropdown>
            </div>

            <!-- Controles de Período -->
            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium text-gray-700">Período:</label>
              <div class="flex gap-2">
                <ButtonGroup>
                  <Button 
                    v-for="period in quickPeriods" 
                    :key="period.key"
                    :label="period.label"
                    :class="selectedQuickPeriod === period.key ? 'p-button-primary' : 'p-button-outlined'"
                    size="small"
                    @click="selectQuickPeriod(period.key)"
                  />
                </ButtonGroup>
              </div>
            </div>
          </div>

          <!-- Seletor de Data Customizado -->
          <div v-if="selectedQuickPeriod === 'custom'" class="mt-4 pt-4 border-t border-gray-200">
            <div class="flex flex-col sm:flex-row gap-4">
              <div class="flex-1">
                <label class="text-sm font-medium text-gray-700 block mb-2">Data de Início:</label>
                <flat-pickr
                  v-model="customStartDate"
                  :config="flatPickrConfig"
                  class="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="Selecione a data de início"
                />
              </div>
              <div class="flex-1">
                <label class="text-sm font-medium text-gray-700 block mb-2">Data de Fim:</label>
                <flat-pickr
                  v-model="customEndDate"
                  :config="flatPickrConfig"
                  class="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="Selecione a data de fim"
                />
              </div>
              <div class="flex items-end">
                <Button 
                  label="Aplicar" 
                  icon="pi pi-check"
                  class="p-button-primary"
                  @click="applyCustomPeriod"
                />
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex justify-center items-center py-12">
      <ProgressSpinner />
      <span class="ml-3 text-gray-600">Carregando dados...</span>
    </div>

    <!-- Dashboard Content -->
    <div v-else>
      <!-- KPIs Grid - Layout Grid Responsivo -->
      <div class="grid-kpi mb-8">
        <!-- KPI: Custo Total -->
        <div class="kpi-card">
          <div class="kpi-title">Custo Total</div>
          <div class="kpi-value">${{ formatCurrency(totalCost) }}</div>
          <div class="kpi-subtitle">{{ getBudgetStatus() }}</div>
        </div>

        <!-- KPI: Variação -->
        <div class="kpi-card">
          <div class="kpi-title">Variação</div>
          <div class="flex items-center mt-2">
            <div class="kpi-value mr-3">${{ formatCurrency(Math.abs(costVariation.amount)) }}</div>
            <div class="flex items-center">
              <i :class="getVariationIcon(costVariation)" class="text-lg mr-2"></i>
              <span :class="getVariationColor(costVariation)" class="text-sm font-medium">
                {{ formatPercentage(costVariation.percentage) }}%
              </span>
            </div>
          </div>
          <div class="kpi-subtitle">vs período anterior</div>
        </div>

        <!-- KPI: Maior Custo -->
        <div class="kpi-card">
          <div class="kpi-title">Maior Custo</div>
          <div class="kpi-value">${{ formatCurrency(topService.cost) }}</div>
          <div class="kpi-subtitle">{{ topService.service_name }}</div>
        </div>

        <!-- KPI: Contas Ativas -->
        <div class="kpi-card">
          <div class="kpi-title">Contas Ativas</div>
          <div class="kpi-value">{{ activeAccounts }}</div>
          <div class="kpi-subtitle">{{ memberAccounts.length - 1 }} contas conectadas</div>
        </div>
      </div>

      <!-- Charts Grid -->
      <div class="grid-cards mb-8">
        <!-- Gráfico de Evolução -->
        <Card class="card-base">
          <template #title>
            <div class="flex items-center text-gray-800">
              <i class="pi pi-chart-line mr-4 text-primary-500"></i>
              <span class="heading-4">Evolução de Custos</span>
            </div>
          </template>
          <template #content>
            <div class="p-6">
              <Chart 
                type="line" 
                :data="evolutionChartData" 
                :options="evolutionChartOptions"
                class="h-80"
              />
            </div>
          </template>
        </Card>

        <!-- Tabela de Variações -->
        <Card class="card-base">
          <template #title>
            <div class="flex items-center text-gray-800">
              <i class="pi pi-sort-amount-down mr-4 text-primary-500"></i>
              <span class="heading-4">Maiores Variações</span>
            </div>
          </template>
          <template #content>
            <div class="p-6">
              <DataTable 
                :value="topVariations" 
                :rows="5"
                responsiveLayout="scroll"
                class="text-sm"
              >
                <Column field="service_name" header="Serviço" style="min-width: 150px">
                  <template #body="slotProps">
                    <span class="font-medium">{{ slotProps.data.service_name }}</span>
                  </template>
                </Column>
                <Column field="current_cost" header="Custo Atual" style="min-width: 100px">
                  <template #body="slotProps">
                    <span class="font-mono">${{ formatCurrency(slotProps.data.current_cost) }}</span>
                  </template>
                </Column>
                <Column field="variation" header="Variação" style="min-width: 120px">
                  <template #body="slotProps">
                    <div class="flex items-center">
                      <i :class="getVariationIcon(slotProps.data.variation)" class="mr-2"></i>
                      <span :class="getVariationColor(slotProps.data.variation)" class="font-medium">
                        {{ formatPercentage(slotProps.data.variation.percentage) }}%
                      </span>
                    </div>
                  </template>
                </Column>
              </DataTable>
            </div>
          </template>
        </Card>
      </div>

      <!-- Governança Financeira -->
      <Card class="card-base">
        <template #title>
          <div class="flex items-center text-gray-800">
            <i class="pi pi-building mr-4 text-primary-500"></i>
            <span class="heading-4">Governança Financeira por Conta</span>
          </div>
        </template>
        <template #content>
          <div class="p-6">
            <DataTable 
              :value="accountGovernance" 
              responsiveLayout="scroll"
              :paginator="accountGovernance.length > 10"
              :rows="10"
              class="text-sm"
            >
              <Column field="account_name" header="Conta" style="min-width: 200px">
                <template #body="slotProps">
                  <div class="flex items-center">
                    <i class="pi pi-building text-primary-500 mr-3"></i>
                    <div>
                      <div class="font-medium">{{ slotProps.data.account_name }}</div>
                      <div class="text-xs text-gray-500">{{ slotProps.data.account_id }}</div>
                    </div>
                  </div>
                </template>
              </Column>
              <Column field="total_cost" header="Custo Total" style="min-width: 120px">
                <template #body="slotProps">
                  <span class="font-mono font-medium">${{ formatCurrency(slotProps.data.total_cost) }}</span>
                </template>
              </Column>
              <Column field="budget_usage" header="Uso do Orçamento" style="min-width: 150px">
                <template #body="slotProps">
                  <div class="flex items-center gap-3">
                    <ProgressBar 
                      :value="slotProps.data.budget_usage" 
                      :class="getBudgetProgressClass(slotProps.data.budget_usage)"
                      class="flex-1"
                    />
                    <span class="text-sm font-medium">{{ slotProps.data.budget_usage }}%</span>
                  </div>
                </template>
              </Column>
              <Column field="status" header="Status" style="min-width: 100px">
                <template #body="slotProps">
                  <Tag 
                    :value="getBudgetStatusLabel(slotProps.data.budget_usage)" 
                    :severity="getBudgetStatusSeverity(slotProps.data.budget_usage)"
                    class="text-xs"
                  />
                </template>
              </Column>
            </DataTable>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>
                <div v-if="slotProps.value" class="flex align-items-center gap-2">
                  <i class="pi pi-building text-blue-500 mr-3"></i>
                  <span>{{ slotProps.value.name }}</span>
                  <small v-if="slotProps.value.aws_account_id !== 'ALL'" class="text-gray-500">
                    ({{ slotProps.value.aws_account_id }})
                  </small>
                </div>
                <span v-else>Selecione uma conta</span>
              </template>
              <template #option="slotProps">
                <div class="flex align-items-center gap-2">
                  <i :class="slotProps.option.aws_account_id === 'ALL' ? 'pi pi-globe text-green-500 mr-3' : 'pi pi-building text-blue-500 mr-3'"></i>
                  <span>{{ slotProps.option.name }}</span>
                  <small v-if="slotProps.option.aws_account_id !== 'ALL'" class="text-gray-500">
                    ({{ slotProps.option.aws_account_id }})
                  </small>
                </div>
              </template>
            </Dropdown>
          </div>
          
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
        <!-- KPI 1 - Custo Total com Barra de Progresso -->
        <Card class="kpi-card kpi-primary">
          <template #content>
            <div class="kpi-content">
              <div class="kpi-icon">💰</div>
              <div class="kpi-info">
                <h3>Custo Total no Período</h3>
                <p class="kpi-value">${{ kpis.totalCost.toFixed(2) }}</p>
                
                <!-- Barra de Progresso do Orçamento -->
                <div v-if="kpis.totalMonthlyBudget > 0" class="budget-progress-container">
                  <div class="budget-status-header">
                    <span class="budget-status-icon">{{ getBudgetStatusIcon() }}</span>
                    <span class="budget-status-text">{{ getBudgetStatusText() }}</span>
                  </div>
                  
                  <ProgressBar 
                    :value="getBudgetConsumptionPercentage()" 
                    :severity="getBudgetConsumptionSeverity()"
                    class="budget-progress-kpi"
                    :showValue="false"
                    :style="{ '--progress-color': getBudgetProgressColor() }"
                  />
                  
                  <div class="budget-details">
                    <span class="budget-info">
                      <strong>${{ kpis.totalCost.toFixed(2) }}</strong> de ${{ kpis.totalMonthlyBudget.toFixed(2) }} orçados
                    </span>
                    <span class="budget-percentage" :class="getBudgetConsumptionSeverity()">
                      {{ getBudgetConsumptionPercentage().toFixed(1) }}%
                    </span>
                  </div>
                </div>
                
                <span v-else class="kpi-period">Período selecionado</span>
              </div>
            </div>
          </template>
        </Card>

        <!-- KPI 2 - Orçamento Total (NOVO) -->
        <Card class="kpi-card kpi-budget">
          <template #content>
            <div class="kpi-content">
              <div class="kpi-icon">🎯</div>
              <div class="kpi-info">
                <h3>Orçamento Total no Mês</h3>
                <p class="kpi-value">${{ kpis.totalMonthlyBudget.toFixed(2) }}</p>
                <span class="kpi-period">Meta mensal</span>
              </div>
            </div>
          </template>
        </Card>

        <!-- KPI 3 - Variação -->
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
          <i class="pi pi-chart-line mr-4"></i>
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
            <i class="pi pi-sort-amount-down mr-4"></i>
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

        <!-- Tabela 2 - Custo por Conta com Orçamento e Previsão -->
        <Card class="table-card">
          <template #title>
            <i class="pi pi-building mr-4"></i>
            Governança Financeira por Conta
          </template>
          <template #content>
            <!-- Versão Desktop: Tabela Tradicional -->
            <div class="desktop-table-view">
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
                <Column field="accountName" header="Conta" :sortable="true" style="width: 20%">
                  <template #body="slotProps">
                    <strong>{{ slotProps.data.accountName }}</strong>
                  </template>
                </Column>
                
                <Column field="totalCost" header="Custo Atual" :sortable="true" style="width: 15%">
                  <template #body="slotProps">
                    <span class="cost-value">
                      ${{ formatCurrencyFull(slotProps.data.totalCost || 0) }}
                    </span>
                  </template>
                </Column>
                
                <Column field="monthlyBudget" header="Orçamento" :sortable="true" style="width: 15%">
                  <template #body="slotProps">
                    <span class="budget-value">
                      ${{ formatCurrencyFull(slotProps.data.monthlyBudget || 0) }}
                    </span>
                  </template>
                </Column>
                
                <Column header="Consumo" style="width: 25%">
                  <template #body="slotProps">
                    <div class="consumption-cell">
                      <div class="consumption-info">
                        <span class="consumption-percentage">{{ getBudgetPercentage(slotProps.data) }}%</span>
                        <span class="consumption-status" :class="getBudgetStatusClass(slotProps.data)">
                          {{ getBudgetStatus(slotProps.data) }}
                        </span>
                      </div>
                      <ProgressBar 
                        :value="getBudgetPercentage(slotProps.data)" 
                        :severity="getBudgetSeverity(slotProps.data)"
                        class="consumption-bar"
                        :showValue="false"
                      />
                    </div>
                  </template>
                </Column>
                
                <Column field="forecastedCost" header="Previsão" :sortable="true" style="width: 25%">
                  <template #body="slotProps">
                    <div class="forecast-cell">
                      <div class="forecast-amount">
                        ${{ formatCurrencyFull(slotProps.data.forecastedCost || 0) }}
                      </div>
                      <div class="forecast-variation" :class="getForecastVariationClass(slotProps.data)">
                        <i :class="getForecastIcon(slotProps.data)"></i>
                        {{ getForecastVariationText(slotProps.data) }}
                      </div>
                    </div>
                  </template>
                </Column>
              </DataTable>
            </div>

            <!-- Versão Mobile: Cards -->
            <div class="mobile-cards-view">
              <div v-for="account in costByAccountData" :key="account.accountId" class="account-card">
                <div class="account-header">
                  <h4 class="account-name">{{ account.accountName }}</h4>
                  <div class="account-status" :class="getBudgetStatusClass(account)">
                    {{ getBudgetStatus(account) }}
                  </div>
                </div>
                
                <div class="account-metrics">
                  <div class="metric">
                    <span class="metric-label">Custo Atual</span>
                    <span class="metric-value cost-value">
                      ${{ formatCurrencyFull(account.totalCost || 0) }}
                    </span>
                  </div>
                  
                  <div class="metric">
                    <span class="metric-label">Orçamento</span>
                    <span class="metric-value budget-value">
                      ${{ formatCurrencyFull(account.monthlyBudget || 0) }}
                    </span>
                  </div>
                  
                  <div class="metric">
                    <span class="metric-label">Previsão</span>
                    <span class="metric-value forecast-value">
                      ${{ formatCurrencyFull(account.forecastedCost || 0) }}
                    </span>
                  </div>
                </div>
                
                <div class="account-progress">
                  <div class="progress-header">
                    <span>Consumo do Orçamento</span>
                    <span class="progress-percentage">{{ getBudgetPercentage(account) }}%</span>
                  </div>
                  <ProgressBar 
                    :value="getBudgetPercentage(account)" 
                    :severity="getBudgetSeverity(account)"
                    class="progress-bar-mobile"
                    :showValue="false"
                  />
                </div>
                
                <div class="forecast-info" :class="getForecastVariationClass(account)">
                  <i :class="getForecastIcon(account)"></i>
                  <span>{{ getForecastVariationText(account) }}</span>
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
.table-card .p-card-content {
  padding: 1.5rem;
}

@media (max-width: 1024px) {
  .table-card .p-card-content {
    padding: 1rem;
  }
}
</style>
