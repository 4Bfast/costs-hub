<script setup>
import { ref, onMounted } from 'vue';
import { apiService } from '@/services/api';

// PrimeVue Components
import Card from 'primevue/card';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Dropdown from 'primevue/dropdown';
import Tag from 'primevue/tag';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import InputNumber from 'primevue/inputnumber';
import Checkbox from 'primevue/checkbox';
import Textarea from 'primevue/textarea';

// --- ESTADO PARA EVENTOS DE ALARME ---
const alarmEvents = ref([]);
const isLoadingEvents = ref(true);
const eventsError = ref(null);

// Filtros para eventos
const statusFilter = ref(null);
const severityFilter = ref(null);

// Opções para os dropdowns de eventos
const statusOptions = [
  { label: 'Todos', value: null },
  { label: 'Novo', value: 'NEW' },
  { label: 'Em Análise', value: 'ANALYZING' },
  { label: 'Resolvido', value: 'RESOLVED' }
];

const severityOptions = ref([
  { label: 'Todas', value: null }
]);

// --- ESTADO PARA REGRAS DE ALARME ---
const alarms = ref([]);
const isLoadingAlarms = ref(true);
const alarmsError = ref(null);
const services = ref([]);

// Estado para modal de alarme
const isAlarmModalVisible = ref(false);
const isEditingAlarm = ref(false);
const editingAlarm = ref(null);
const isSubmitting = ref(false);

const alarmForm = ref({
  name: '',
  scope_type: 'ORGANIZATION',
  scope_value: '',
  time_period: 'MONTHLY',
  severity_levels: [
    { name: 'Alto', threshold: 1000, notify: false }
  ],
  is_enabled: true,
  notification_email: ''
});

// Opções para dropdowns de alarme
const scopeTypeOptions = [
  { label: 'Toda a Organização', value: 'ORGANIZATION' },
  { label: 'Conta AWS Específica', value: 'AWS_ACCOUNT' },
  { label: 'Serviço Específico', value: 'SERVICE' }
];

const timePeriodOptions = [
  { label: 'Diário', value: 'DAILY' },
  { label: 'Mensal', value: 'MONTHLY' }
];

// Opções pré-definidas para níveis de severidade
const severityNameOptions = [
  { label: 'Informativo', value: 'Informativo' },
  { label: 'Atenção', value: 'Atenção' },
  { label: 'Alto', value: 'Alto' },
  { label: 'Crítico', value: 'Crítico' }
];

// --- ESTADO PARA MODAL DE GERENCIAMENTO ---
const isManageModalVisible = ref(false);
const selectedEvent = ref(null);
const eventHistory = ref([]);
const isLoadingHistory = ref(false);
const actionComment = ref('');
const isUpdatingStatus = ref(false);

// --- FUNÇÕES PARA EVENTOS DE ALARME ---
async function fetchAlarmEvents() {
  try {
    isLoadingEvents.value = true;
    eventsError.value = null;
    
    // Construir parâmetros de query
    const params = new URLSearchParams();
    if (statusFilter.value) {
      params.append('status', statusFilter.value);
    }
    if (severityFilter.value) {
      params.append('severity', severityFilter.value);
    }
    
    const queryString = params.toString();
    const url = queryString ? `/alarm-events?${queryString}` : '/alarm-events';
    
    const response = await apiService.get(url);
    alarmEvents.value = response.events || [];
    
    // Extrair severidades únicas para o filtro
    const uniqueSeverities = [...new Set(alarmEvents.value.map(event => event.breached_severity))];
    severityOptions.value = [
      { label: 'Todas', value: null },
      ...uniqueSeverities.map(severity => ({ label: severity, value: severity }))
    ];
    
  } catch (err) {
    eventsError.value = 'Erro ao carregar eventos de alarme: ' + err.message;
  } finally {
    isLoadingEvents.value = false;
  }
}

function applyEventsFilters() {
  fetchAlarmEvents();
}

function clearEventsFilters() {
  statusFilter.value = null;
  severityFilter.value = null;
  fetchAlarmEvents();
}

// --- FUNÇÕES PARA REGRAS DE ALARME ---
async function fetchAlarms() {
  try {
    isLoadingAlarms.value = true;
    alarmsError.value = null;
    const response = await apiService.get('/alarms');
    alarms.value = response;
  } catch (error) {
    alarmsError.value = 'Erro ao carregar alarmes: ' + error.message;
  } finally {
    isLoadingAlarms.value = false;
  }
}

async function fetchServices() {
  try {
    const response = await apiService.get('/services');
    services.value = response.map(service => ({ label: service, value: service }));
  } catch (error) {
    console.error('Erro ao carregar serviços:', error);
  }
}

function openAlarmModal() {
  isEditingAlarm.value = false;
  alarmsError.value = null; // Limpar erros
  alarmForm.value = {
    name: '',
    scope_type: 'ORGANIZATION',
    scope_value: '',
    time_period: 'MONTHLY',
    severity_levels: [
      { name: 'Alto', threshold: 1000, notify: false }
    ],
    is_enabled: true,
    notification_email: ''
  };
  isAlarmModalVisible.value = true;
}

function openEditAlarmModal(alarm) {
  isEditingAlarm.value = true;
  editingAlarm.value = alarm;
  alarmsError.value = null; // Limpar erros
  alarmForm.value = {
    name: alarm.name,
    scope_type: alarm.scope_type,
    scope_value: alarm.scope_value || '',
    time_period: alarm.time_period,
    severity_levels: [...alarm.severity_levels],
    is_enabled: alarm.is_enabled,
    notification_email: alarm.notification_email || ''
  };
  isAlarmModalVisible.value = true;
}

function closeAlarmModal() {
  isAlarmModalVisible.value = false;
  editingAlarm.value = null;
  isEditingAlarm.value = false;
  alarmsError.value = null; // Limpar erros
}

function addSeverityLevel() {
  if (alarmForm.value.severity_levels.length < 4) {
    alarmForm.value.severity_levels.push({
      name: 'Informativo', // Valor padrão da primeira opção
      threshold: 0,
      notify: false
    });
  }
}

function removeSeverityLevel(index) {
  if (alarmForm.value.severity_levels.length > 1) {
    alarmForm.value.severity_levels.splice(index, 1);
  }
}

async function handleSaveAlarm() {
  try {
    isSubmitting.value = true;
    alarmsError.value = null;

    // Validações
    if (!alarmForm.value.name.trim()) {
      alarmsError.value = 'Nome do alarme é obrigatório';
      return;
    }

    if (alarmForm.value.scope_type !== 'ORGANIZATION' && !alarmForm.value.scope_value) {
      alarmsError.value = 'Valor do escopo é obrigatório para este tipo';
      return;
    }

    // Validar níveis de severidade
    for (let level of alarmForm.value.severity_levels) {
      if (!level.name || level.threshold <= 0) {
        alarmsError.value = 'Todos os níveis devem ter nome selecionado e valor válido';
        return;
      }
    }

    const alarmData = {
      ...alarmForm.value,
      scope_value: alarmForm.value.scope_type === 'ORGANIZATION' ? null : alarmForm.value.scope_value
    };

    if (isEditingAlarm.value) {
      await apiService.put(`/alarms/${editingAlarm.value.id}`, alarmData);
    } else {
      await apiService.post('/alarms', alarmData);
    }

    closeAlarmModal();
    await fetchAlarms();

  } catch (error) {
    alarmsError.value = 'Erro ao salvar alarme: ' + error.message;
  } finally {
    isSubmitting.value = false;
  }
}

async function handleDeleteAlarm(alarm) {
  if (confirm(`Tem certeza que deseja excluir o alarme "${alarm.name}"?`)) {
    try {
      await apiService.delete(`/alarms/${alarm.id}`);
      await fetchAlarms();
    } catch (error) {
      alarmsError.value = 'Erro ao excluir alarme: ' + error.message;
    }
  }
}

// --- FUNÇÕES PARA MODAL DE GERENCIAMENTO ---
async function openManageModal(event) {
  selectedEvent.value = event;
  actionComment.value = '';
  isManageModalVisible.value = true;
  await fetchEventHistory(event.id);
}

function closeManageModal() {
  isManageModalVisible.value = false;
  selectedEvent.value = null;
  eventHistory.value = [];
  actionComment.value = '';
}

async function fetchEventHistory(eventId) {
  try {
    isLoadingHistory.value = true;
    const response = await apiService.get(`/alarm-events/${eventId}/history`);
    eventHistory.value = response.history || [];
  } catch (error) {
    console.error('Erro ao carregar histórico:', error);
    eventHistory.value = [];
  } finally {
    isLoadingHistory.value = false;
  }
}

async function updateEventStatus(newStatus) {
  try {
    isUpdatingStatus.value = true;
    
    // Validar comentário obrigatório para resolução
    if (newStatus === 'RESOLVED' && !actionComment.value.trim()) {
      alarmsError.value = 'Comentário é obrigatório ao marcar como resolvido';
      return;
    }
    
    await apiService.put(`/alarm-events/${selectedEvent.value.id}/status`, {
      new_status: newStatus,
      comment: actionComment.value.trim()
    });
    
    // Atualizar evento local
    selectedEvent.value.status = newStatus;
    
    // Atualizar na lista principal
    const eventIndex = alarmEvents.value.findIndex(e => e.id === selectedEvent.value.id);
    if (eventIndex !== -1) {
      alarmEvents.value[eventIndex].status = newStatus;
    }
    
    // Recarregar histórico
    await fetchEventHistory(selectedEvent.value.id);
    
    // Limpar comentário
    actionComment.value = '';
    
  } catch (error) {
    alarmsError.value = 'Erro ao atualizar status: ' + error.message;
  } finally {
    isUpdatingStatus.value = false;
  }
}

function getStatusButtonText(currentStatus) {
  if (currentStatus === 'NEW') {
    return 'Assumir Análise';
  } else if (currentStatus === 'ANALYZING') {
    return 'Marcar como Resolvido';
  }
  return '';
}

function getNextStatus(currentStatus) {
  if (currentStatus === 'NEW') {
    return 'ANALYZING';
  } else if (currentStatus === 'ANALYZING') {
    return 'RESOLVED';
  }
  return null;
}

function canUpdateStatus(status) {
  return status === 'NEW' || status === 'ANALYZING';
}

function formatDateTime(dateString) {
  return new Date(dateString).toLocaleString('pt-BR');
}

// --- FUNÇÕES EXISTENTES ---
function getSeverityClass(severity) {
  const severityMap = {
    'Baixo': 'info',
    'Médio': 'warning', 
    'Alto': 'warning',
    'Crítico': 'danger',
    'Extremo': 'danger'
  };
  return severityMap[severity] || 'info';
}

function getStatusClass(status) {
  const statusMap = {
    'NEW': 'danger',
    'ANALYZING': 'warning',
    'RESOLVED': 'success'
  };
  return statusMap[status] || 'info';
}

function getStatusLabel(status) {
  const statusMap = {
    'NEW': 'Novo',
    'ANALYZING': 'Em Análise',
    'RESOLVED': 'Resolvido'
  };
  return statusMap[status] || status;
}

function getScopeDescription(event) {
  if (event.scope_type === 'ORGANIZATION') {
    return 'Toda a Organização';
  } else if (event.scope_type === 'AWS_ACCOUNT') {
    return `Conta AWS: ${event.scope_value}`;
  } else if (event.scope_type === 'SERVICE') {
    return `Serviço: ${event.scope_value}`;
  }
  return event.scope_type;
}

function getScopeLabel(scopeType) {
  const labels = {
    'ORGANIZATION': 'Organização',
    'AWS_ACCOUNT': 'Conta AWS',
    'SERVICE': 'Serviço'
  };
  return labels[scopeType] || scopeType;
}

function getScopeSeverity(scopeType) {
  const severities = {
    'ORGANIZATION': 'info',
    'AWS_ACCOUNT': 'warning',
    'SERVICE': 'success'
  };
  return severities[scopeType] || 'info';
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2
  }).format(value);
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('pt-BR');
}

// --- LIFECYCLE ---
onMounted(() => {
  fetchAlarmEvents();
  fetchAlarms();
  fetchServices();
});
</script>

<template>
  <div class="alarms-view">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">
        <i class="pi pi-bell mr-2"></i>
        Central de Alarmes
      </h1>
      <p class="page-description">
        Gerencie regras de alarme e visualize eventos disparados pelo sistema
      </p>
    </div>

    <!-- TabView Principal -->
    <TabView class="alarms-tabview">
      <!-- Aba 1: Eventos de Alarme -->
      <TabPanel header="Eventos de Alarme">
        <!-- Filtros -->
        <Card class="filters-card mb-4">
          <template #content>
            <div class="filters-container">
              <div class="filter-group">
                <label for="status-filter" class="filter-label">Status:</label>
                <Dropdown
                  id="status-filter"
                  v-model="statusFilter"
                  :options="statusOptions"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Selecione o status"
                  class="filter-dropdown"
                />
              </div>
              
              <div class="filter-group">
                <label for="severity-filter" class="filter-label">Severidade:</label>
                <Dropdown
                  id="severity-filter"
                  v-model="severityFilter"
                  :options="severityOptions"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Selecione a severidade"
                  class="filter-dropdown"
                />
              </div>
              
              <div class="filter-actions">
                <Button
                  label="Aplicar Filtros"
                  icon="pi pi-filter"
                  @click="applyEventsFilters"
                  class="p-button-primary"
                />
                <Button
                  label="Limpar"
                  icon="pi pi-times"
                  @click="clearEventsFilters"
                  class="p-button-secondary"
                />
              </div>
            </div>
          </template>
        </Card>

        <!-- Loading -->
        <div v-if="isLoadingEvents" class="loading-container">
          <ProgressSpinner />
          <p>Carregando eventos de alarme...</p>
        </div>

        <!-- Error -->
        <Message v-else-if="eventsError" severity="error" :closable="false" class="mb-4">
          {{ eventsError }}
        </Message>

        <!-- Tabela de Eventos -->
        <Card v-else class="events-card">
          <template #content>
            <DataTable
              :value="alarmEvents"
              :paginator="true"
              :rows="20"
              responsiveLayout="scroll"
              size="small"
              sortMode="single"
              :sortField="'trigger_date'"
              :sortOrder="-1"
              class="p-datatable-sm"
              paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
              :rowsPerPageOptions="[10, 20, 50]"
              currentPageReportTemplate="Mostrando {first} a {last} de {totalRecords} eventos"
            >
              <template #empty>
                <div class="empty-state">
                  <i class="pi pi-bell-slash empty-icon"></i>
                  <h3>Nenhum evento de alarme encontrado</h3>
                  <p>Não há eventos de alarme para os filtros selecionados.</p>
                </div>
              </template>

              <!-- Coluna: Severidade -->
              <Column field="breached_severity" header="Severidade" :sortable="true" style="width: 120px">
                <template #body="slotProps">
                  <Tag
                    :value="slotProps.data.breached_severity"
                    :severity="getSeverityClass(slotProps.data.breached_severity)"
                    class="severity-tag"
                  />
                </template>
              </Column>

              <!-- Coluna: Descrição do Alarme -->
              <Column field="alarm_name" header="Alarme" :sortable="true" style="min-width: 200px">
                <template #body="slotProps">
                  <div class="alarm-description">
                    <strong>{{ slotProps.data.alarm_name }}</strong>
                    <div class="alarm-scope">
                      {{ getScopeDescription(slotProps.data) }}
                    </div>
                  </div>
                </template>
              </Column>

              <!-- Coluna: Data do Evento -->
              <Column field="trigger_date" header="Data" :sortable="true" style="width: 120px">
                <template #body="slotProps">
                  {{ formatDate(slotProps.data.trigger_date) }}
                </template>
              </Column>

              <!-- Coluna: Status -->
              <Column field="status" header="Status" :sortable="true" style="width: 120px">
                <template #body="slotProps">
                  <Tag
                    :value="getStatusLabel(slotProps.data.status)"
                    :severity="getStatusClass(slotProps.data.status)"
                  />
                </template>
              </Column>

              <!-- Coluna: Custo Medido -->
              <Column field="cost_value" header="Custo Medido" :sortable="true" style="width: 140px">
                <template #body="slotProps">
                  <span class="cost-value">
                    {{ formatCurrency(slotProps.data.cost_value) }}
                  </span>
                </template>
              </Column>

              <!-- Coluna: Limite Violado -->
              <Column field="threshold_value" header="Limite Violado" :sortable="true" style="width: 140px">
                <template #body="slotProps">
                  <span class="threshold-value">
                    {{ formatCurrency(slotProps.data.threshold_value) }}
                  </span>
                </template>
              </Column>

              <!-- Coluna: Ações -->
              <Column header="Ações" style="width: 100px">
                <template #body="slotProps">
                  <Button
                    icon="pi pi-cog"
                    class="p-button-rounded p-button-text p-button-sm"
                    v-tooltip="'Gerenciar'"
                    @click="openManageModal(slotProps.data)"
                  />
                </template>
              </Column>
            </DataTable>
          </template>
        </Card>
      </TabPanel>

      <!-- Aba 2: Regras de Alarme -->
      <TabPanel header="Regras de Alarme">
        <!-- Botão Criar Nova Regra -->
        <div class="mb-4">
          <Button 
            label="Criar Nova Regra de Alarme" 
            icon="pi pi-plus" 
            @click="openAlarmModal"
            class="p-button-success"
          />
        </div>

        <!-- Loading -->
        <div v-if="isLoadingAlarms" class="loading-container">
          <ProgressSpinner />
          <p>Carregando regras de alarme...</p>
        </div>

        <!-- Error -->
        <Message v-else-if="alarmsError" severity="error" :closable="false" class="mb-4">
          {{ alarmsError }}
        </Message>

        <!-- Tabela de Regras -->
        <Card v-else class="alarms-card">
          <template #content>
            <DataTable 
              :value="alarms" 
              responsiveLayout="scroll"
              size="small"
              class="p-datatable-sm"
            >
              <template #empty>
                <div class="empty-state">
                  <i class="pi pi-bell-slash empty-icon"></i>
                  <h3>Nenhuma regra de alarme configurada</h3>
                  <p>Clique em "Criar Nova Regra" para começar</p>
                </div>
              </template>

              <Column field="name" header="Nome da Regra">
                <template #body="slotProps">
                  <strong>{{ slotProps.data.name }}</strong>
                </template>
              </Column>
              
              <Column field="scope_type" header="Escopo">
                <template #body="slotProps">
                  <Tag 
                    :value="getScopeLabel(slotProps.data.scope_type)" 
                    :severity="getScopeSeverity(slotProps.data.scope_type)"
                  />
                </template>
              </Column>
              
              <Column field="is_enabled" header="Status">
                <template #body="slotProps">
                  <Tag 
                    :value="slotProps.data.is_enabled ? 'Ativa' : 'Inativa'" 
                    :severity="slotProps.data.is_enabled ? 'success' : 'danger'"
                  />
                </template>
              </Column>
              
              <Column header="Ações" style="width: 120px">
                <template #body="slotProps">
                  <Button icon="pi pi-pencil" class="p-button-rounded p-button-text" @click="openEditAlarmModal(slotProps.data)" v-tooltip.top="'Editar'" />
                  <Button icon="pi pi-trash" class="p-button-rounded p-button-danger p-button-text" @click="handleDeleteAlarm(slotProps.data)" v-tooltip.top="'Excluir'" />
                </template>
              </Column>
            </DataTable>
          </template>
        </Card>
      </TabPanel>
    </TabView>

    <!-- Modal de Criação/Edição de Alarme -->
    <Dialog 
      v-model:visible="isAlarmModalVisible" 
      modal 
      :header="isEditingAlarm ? 'Editar Regra de Alarme' : 'Criar Nova Regra de Alarme'"
      :style="{ width: '60vw' }"
      :breakpoints="{ '960px': '80vw', '641px': '95vw' }"
    >
      <!-- Mensagem de Erro -->
      <Message v-if="alarmsError" severity="error" :closable="true" class="mb-4" @close="alarmsError = null">
        {{ alarmsError }}
      </Message>

      <form @submit.prevent="handleSaveAlarm" class="p-fluid">
        <!-- Nome do Alarme -->
        <div class="field mb-4">
          <label for="alarm-name" class="font-semibold mb-2 block">Nome da Regra</label>
          <InputText 
            id="alarm-name" 
            v-model="alarmForm.name" 
            placeholder="Ex: Alerta Custo EC2 Produção"
            required 
          />
        </div>

        <!-- Escopo -->
        <div class="field mb-4">
          <label for="alarm-scope-type" class="font-semibold mb-2 block">Escopo</label>
          <Dropdown
            id="alarm-scope-type"
            v-model="alarmForm.scope_type"
            :options="scopeTypeOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Selecione o escopo"
          />
        </div>

        <!-- Valor do Escopo (condicional) -->
        <div v-if="alarmForm.scope_type === 'SERVICE'" class="field mb-4">
          <label for="alarm-service" class="font-semibold mb-2 block">Serviço AWS</label>
          <Dropdown
            id="alarm-service"
            v-model="alarmForm.scope_value"
            :options="services"
            optionLabel="label"
            optionValue="value"
            placeholder="Selecione o serviço"
            :filter="true"
          />
        </div>

        <!-- Período -->
        <div class="field mb-4">
          <label for="alarm-period" class="font-semibold mb-2 block">Período de Avaliação</label>
          <Dropdown
            id="alarm-period"
            v-model="alarmForm.time_period"
            :options="timePeriodOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Selecione o período"
          />
        </div>

        <!-- Níveis de Severidade -->
        <div class="field mb-4">
          <div class="severity-header">
            <label class="font-semibold mb-2 block">Níveis de Severidade</label>
            <Button
              type="button"
              label="Adicionar Nível"
              icon="pi pi-plus"
              class="p-button-sm p-button-outlined"
              @click="addSeverityLevel"
              :disabled="alarmForm.severity_levels.length >= 4"
            />
          </div>
          
          <div class="severity-levels">
            <div 
              v-for="(level, index) in alarmForm.severity_levels" 
              :key="index"
              class="severity-level-row"
            >
              <div class="severity-inputs">
                <div class="field severity-name-field">
                  <label class="severity-label">Nome:</label>
                  <Dropdown
                    v-model="level.name"
                    :options="severityNameOptions"
                    optionLabel="label"
                    optionValue="value"
                    placeholder="Selecione a severidade"
                    required
                  />
                </div>
                <div class="field severity-threshold-field">
                  <label class="severity-label">Limite ($):</label>
                  <InputNumber 
                    v-model="level.threshold" 
                    mode="currency" 
                    currency="USD" 
                    locale="en-US"
                    :min="0"
                    required
                  />
                </div>
                <div class="field severity-notify-field">
                  <label class="severity-label">Notificar:</label>
                  <div class="field-checkbox">
                    <Checkbox 
                      v-model="level.notify" 
                      :binary="true"
                    />
                    <label class="ml-2 checkbox-label">Email</label>
                  </div>
                </div>
              </div>
              <Button
                type="button"
                icon="pi pi-trash"
                class="p-button-rounded p-button-danger p-button-text"
                @click="removeSeverityLevel(index)"
                :disabled="alarmForm.severity_levels.length <= 1"
                v-tooltip="'Remover nível'"
              />
            </div>
          </div>
        </div>

        <!-- Email de Notificação -->
        <div class="field mb-4">
          <label for="notification-email" class="font-semibold mb-2 block">Email para Notificações</label>
          <InputText 
            id="notification-email" 
            v-model="alarmForm.notification_email" 
            placeholder="email@exemplo.com"
            type="email"
            class="mb-2"
          />
          <small class="field-help-text">
            <i class="pi pi-info-circle mr-1"></i>
            Opcional. Se não informado, será usado o email da organização. 
            Notificações são enviadas apenas para severidades marcadas como "Notificar".
          </small>
        </div>

        <!-- Status Ativo -->
        <div class="field mb-4">
          <div class="field-checkbox">
            <Checkbox 
              id="alarm-enabled" 
              v-model="alarmForm.is_enabled" 
              :binary="true"
            />
            <label for="alarm-enabled" class="ml-2">Alarme ativo</label>
          </div>
        </div>
      </form>
      
      <template #footer>
        <Button 
          label="Cancelar" 
          icon="pi pi-times" 
          severity="secondary"
          @click="closeAlarmModal" 
        />
        <Button 
          :label="isEditingAlarm ? 'Atualizar' : 'Criar'"
          icon="pi pi-check" 
          :loading="isSubmitting"
          @click="handleSaveAlarm" 
        />
      </template>
    </Dialog>

    <!-- Modal de Gerenciamento de Alarme -->
    <Dialog 
      v-model:visible="isManageModalVisible" 
      modal 
      :header="`Gerenciar Alarme: ${selectedEvent?.alarm_name || ''}`"
      :style="{ width: '70vw' }"
      :breakpoints="{ '960px': '85vw', '641px': '95vw' }"
    >
      <div v-if="selectedEvent" class="manage-modal-content">
        <!-- Detalhes do Alarme -->
        <Card class="mb-4">
          <template #title>
            <div class="alarm-header">
              <Tag 
                :value="selectedEvent.breached_severity" 
                :severity="getSeverityClass(selectedEvent.breached_severity)"
                class="severity-tag-large"
              />
              <span class="alarm-title">{{ selectedEvent.alarm_name }}</span>
            </div>
          </template>
          <template #content>
            <div class="alarm-details">
              <div class="detail-row">
                <strong>Status Atual:</strong>
                <Tag 
                  :value="getStatusLabel(selectedEvent.status)" 
                  :severity="getStatusClass(selectedEvent.status)"
                />
              </div>
              <div class="detail-row">
                <strong>Data do Evento:</strong>
                <span>{{ formatDate(selectedEvent.trigger_date) }}</span>
              </div>
              <div class="detail-row">
                <strong>Custo Medido:</strong>
                <span class="cost-value">{{ formatCurrency(selectedEvent.cost_value) }}</span>
              </div>
              <div class="detail-row">
                <strong>Limite Violado:</strong>
                <span class="threshold-value">{{ formatCurrency(selectedEvent.threshold_value) }}</span>
              </div>
              <div class="detail-row">
                <strong>Escopo:</strong>
                <span>{{ getScopeDescription(selectedEvent) }}</span>
              </div>
            </div>
          </template>
        </Card>

        <!-- Ações de Status -->
        <Card v-if="canUpdateStatus(selectedEvent.status)" class="mb-4">
          <template #title>Ações</template>
          <template #content>
            <div class="action-section">
              <div class="field mb-3">
                <label for="action-comment" class="font-semibold mb-2 block">
                  {{ getNextStatus(selectedEvent.status) === 'RESOLVED' ? 'Comentário (obrigatório):' : 'Comentário (opcional):' }}
                </label>
                <Textarea 
                  id="action-comment"
                  v-model="actionComment" 
                  rows="3" 
                  :placeholder="getNextStatus(selectedEvent.status) === 'RESOLVED' ? 'Descreva a resolução do problema...' : 'Adicione um comentário sobre a ação tomada...'"
                  class="w-full"
                />
              </div>
              
              <Button 
                :label="getStatusButtonText(selectedEvent.status)"
                :icon="selectedEvent.status === 'NEW' ? 'pi pi-eye' : 'pi pi-check'"
                :loading="isUpdatingStatus"
                @click="updateEventStatus(getNextStatus(selectedEvent.status))"
                class="p-button-primary"
              />
            </div>
          </template>
        </Card>

        <!-- Histórico de Ações -->
        <Card>
          <template #title>Histórico de Ações</template>
          <template #content>
            <div v-if="isLoadingHistory" class="loading-container">
              <ProgressSpinner />
              <p>Carregando histórico...</p>
            </div>
            
            <div v-else-if="eventHistory.length === 0" class="empty-state">
              <i class="pi pi-history empty-icon"></i>
              <p>Nenhuma ação registrada ainda</p>
            </div>
            
            <div v-else class="history-timeline">
              <div 
                v-for="action in eventHistory" 
                :key="action.id"
                class="history-item"
              >
                <div class="history-header">
                  <div class="status-transition">
                    <Tag :value="action.previous_status" severity="secondary" class="status-tag" />
                    <i class="pi pi-arrow-right mx-2"></i>
                    <Tag :value="action.new_status" :severity="getStatusClass(action.new_status)" class="status-tag" />
                  </div>
                  <div class="history-meta">
                    <span class="user-name">{{ action.user_name }}</span>
                    <span class="action-date">{{ formatDateTime(action.action_timestamp) }}</span>
                  </div>
                </div>
                <div v-if="action.comment" class="history-comment">
                  {{ action.comment }}
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>
      
      <template #footer>
        <Button 
          label="Fechar" 
          icon="pi pi-times" 
          @click="closeManageModal" 
        />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.alarms-view {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

/* Header */
.page-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 0.5rem 0;
  display: flex;
  align-items: center;
}

.page-description {
  color: #6c757d;
  font-size: 1.1rem;
  margin: 0;
}

/* TabView */
.alarms-tabview {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Filtros */
.filters-card {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
}

.filters-container {
  display: flex;
  gap: 1.5rem;
  align-items: end;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 200px;
}

.filter-label {
  font-weight: 600;
  color: #495057;
  font-size: 0.9rem;
}

.filter-dropdown {
  width: 100%;
}

.filter-actions {
  display: flex;
  gap: 0.5rem;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #6c757d;
}

/* Tabelas */
.events-card, .alarms-card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.severity-tag {
  font-weight: 600;
}

.alarm-description {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.alarm-scope {
  font-size: 0.8rem;
  color: #6c757d;
}

.cost-value {
  font-weight: 600;
  color: #dc3545;
}

.threshold-value {
  font-weight: 600;
  color: #6c757d;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #6c757d;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state h3 {
  margin: 0 0 0.5rem 0;
  color: #495057;
}

.empty-state p {
  margin: 0;
}

/* Modal de alarme */
.severity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.severity-levels {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.severity-level-row {
  display: flex;
  align-items: end;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #e9ecef;
  border-radius: 0.5rem;
  background: #f8f9fa;
}

.severity-inputs {
  display: flex;
  gap: 1rem;
  flex: 1;
}

.severity-inputs .field {
  margin-bottom: 0;
}

.severity-name-field {
  flex: 2;
}

.severity-threshold-field {
  flex: 2;
}

.severity-notify-field {
  flex: 1;
  min-width: 100px;
}

.checkbox-label {
  font-size: 0.8rem;
  color: #495057;
}

.severity-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.25rem;
  display: block;
}

/* Texto de ajuda */
.field-help-text {
  color: #6c757d;
  font-size: 0.85rem;
  line-height: 1.4;
  display: block;
  margin-top: 0.25rem;
}

.field-help-text .pi {
  color: #17a2b8;
}

/* Responsividade */
@media (max-width: 768px) {
  .alarms-view {
    padding: 1rem;
  }
  
  .filters-container {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-group {
    min-width: auto;
  }
  
  .filter-actions {
    justify-content: stretch;
  }
  
  .filter-actions .p-button {
    flex: 1;
  }
  
  .severity-level-row {
    flex-direction: column;
    align-items: stretch;
  }
  
  .severity-inputs {
    flex-direction: column;
  }
}

/* Modal de Gerenciamento */
.manage-modal-content {
  max-height: 70vh;
  overflow-y: auto;
}

.alarm-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.severity-tag-large {
  font-size: 0.9rem;
  font-weight: 700;
  padding: 0.5rem 1rem;
}

.alarm-title {
  font-size: 1.2rem;
  font-weight: 600;
}

.alarm-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-row:last-child {
  border-bottom: none;
}

.action-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Histórico */
.history-timeline {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.history-item {
  padding: 1rem;
  border: 1px solid #e9ecef;
  border-radius: 0.5rem;
  background: #f8f9fa;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.status-transition {
  display: flex;
  align-items: center;
}

.status-tag {
  font-size: 0.8rem;
}

.history-meta {
  display: flex;
  flex-direction: column;
  align-items: end;
  font-size: 0.8rem;
  color: #6c757d;
}

.user-name {
  font-weight: 600;
}

.action-date {
  font-size: 0.75rem;
}

.history-comment {
  background: white;
  padding: 0.75rem;
  border-radius: 0.25rem;
  border-left: 3px solid #007bff;
  font-style: italic;
  color: #495057;
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
</style>
