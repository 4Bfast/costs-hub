<script setup>
import { ref, onMounted } from 'vue';
import { apiService } from '@/services/api';

// PrimeVue Components
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import Tag from 'primevue/tag';
import InputText from 'primevue/inputtext';
import InputNumber from 'primevue/inputnumber';
import Textarea from 'primevue/textarea';
import Card from 'primevue/card';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';
import Tooltip from 'primevue/tooltip';

// --- ESTADO COMPLETO ---
const accounts = ref([]);
const isLoadingList = ref(true);
const newAccount = ref({
  account_name: '',
  iam_role_arn: '',
  focus_s3_bucket_path: '',
});
const isSubmitting = ref(false);
const message = ref({ type: '', text: '' });

// Estado para o Modal de Detalhes
const isDetailsModalVisible = ref(false);
const selectedAccountForDetails = ref(null);

// Estado para o Modal de Edição
const isEditModalVisible = ref(false);
const editingAccount = ref(null);

// NOVO: Estado para o Modal de Adicionar Conta
const isAddModalVisible = ref(false);

// NOVO: Estado para Importação de Histórico
const isImporting = ref({});
const importStatus = ref({});
const importErrors = ref({});

// --- FUNÇÕES COMPLETAS ---

async function fetchAccounts() {
  isLoadingList.value = true;
  try {
    accounts.value = await apiService.getAwsAccounts();
  } catch (error) {
    message.value = { type: 'error', text: 'Falha ao carregar contas: ' + error.message };
  } finally {
    isLoadingList.value = false;
  }
}
onMounted(() => {
  fetchAccounts();
});

// --- FUNÇÕES EXISTENTES ---

async function handleAddAccount() {
  isSubmitting.value = true;
  message.value = { type: '', text: '' };
  try {
    const result = await apiService.addAwsAccount(newAccount.value);
    message.value = { type: 'success', text: result.message };
    
    newAccount.value = { account_name: '', iam_role_arn: '', focus_s3_bucket_path: '' };
    await fetchAccounts(); 
    closeAddModal(); // NOVO: Fechar modal após sucesso

  } catch (error) {
    message.value = { type: 'error', text: error.message };
  } finally {
    isSubmitting.value = false;
  }
}

// NOVAS FUNÇÕES: Controle do modal de adicionar conta
function openAddModal() {
  isAddModalVisible.value = true;
  message.value = { type: '', text: '' };
}

function closeAddModal() {
  isAddModalVisible.value = false;
  newAccount.value = { account_name: '', iam_role_arn: '', focus_s3_bucket_path: '' };
}

function showDetails(account) {
  selectedAccountForDetails.value = account;
  isDetailsModalVisible.value = true;
}

function closeDetailsModal() {
  isDetailsModalVisible.value = false;
  selectedAccountForDetails.value = null;
}

async function handleDelete(account) {
  if (window.confirm(`Tem certeza que deseja deletar a conta "${account.account_name}"? Todos os dados de custo associados serão perdidos.`)) {
    try {
      const result = await apiService.deleteAwsAccount(account.id);
      message.value = { type: 'success', text: result.message };
      await fetchAccounts();
    } catch (error) {
      message.value = { type: 'error', text: 'Falha ao deletar conta: ' + error.message };
    }
  }
}

function openEditModal(account) {
  editingAccount.value = { ...account }; 
  isEditModalVisible.value = true;
  message.value = { type: '', text: '' };
}

function closeEditModal() {
  isEditModalVisible.value = false;
  editingAccount.value = null;
}

async function handleUpdateAccount() {
  if (!editingAccount.value) return;

  isSubmitting.value = true;
  message.value = { type: '', text: '' };
  try {
    const result = await apiService.updateAwsAccount(editingAccount.value.id, {
      account_name: editingAccount.value.account_name,
      iam_role_arn: editingAccount.value.iam_role_arn,
      focus_s3_bucket_path: editingAccount.value.focus_s3_bucket_path,
      monthly_budget: editingAccount.value.monthly_budget || 0,
    });
    message.value = { type: 'success', text: result.message };
    
    closeEditModal();
    await fetchAccounts();

  } catch (error) {
    message.value = { type: 'error', text: 'Falha ao atualizar conta: ' + error.message };
  } finally {
    isSubmitting.value = false;
  }
}

// NOVA FUNCIONALIDADE: Importador de Histórico de Custos
async function handleImportHistory(account) {
  // Verificar se já foi importado
  if (account.history_imported) {
    message.value = { 
      type: 'info', 
      text: 'Histórico já foi importado para esta conta.' 
    };
    return;
  }

  // Iniciar estado de loading
  isImporting.value[account.id] = true;
  importStatus.value[account.id] = 'Importação em andamento...';
  importErrors.value[account.id] = null;

  try {
    // Chamar API conforme especificação
    const response = await apiService.importHistory(account.id);
    
    // Feedback de sucesso imediato (202 Accepted)
    importStatus.value[account.id] = response.message || 'Importação iniciada com sucesso!';
    message.value = { 
      type: 'success', 
      text: `Importação de histórico iniciada para ${account.account_name}` 
    };

    // Simular conclusão após alguns segundos (em produção seria via WebSocket ou polling)
    setTimeout(async () => {
      try {
        // Atualizar lista de contas para refletir history_imported = true
        await fetchAccounts();
        importStatus.value[account.id] = 'Histórico importado com sucesso!';
        
        setTimeout(() => {
          importStatus.value[account.id] = null;
        }, 3000);
        
      } catch (error) {
        importErrors.value[account.id] = 'Erro na finalização da importação';
      } finally {
        isImporting.value[account.id] = false;
      }
    }, 5000); // Simular 5 segundos de processamento

  } catch (error) {
    // Tratamento de erro conforme especificação
    isImporting.value[account.id] = false;
    importErrors.value[account.id] = error.message;
    importStatus.value[account.id] = null;
    
    message.value = { 
      type: 'error', 
      text: `Falha na importação: ${error.message}` 
    };
  }
}
</script>

<template>
  <div class="settings-page">
    <h1>Configurações</h1>

    <!-- Mensagem Global -->
    <Message v-if="message.text" :severity="message.type" :closable="true" @close="message.text = ''">
      {{ message.text }}
    </Message>

    <!-- Card das Contas AWS -->
    <Card class="mb-4">
      <template #title>
        <i class="pi pi-aws mr-2"></i>
        Contas AWS Conectadas
      </template>
      
      <template #content>
        <div v-if="isLoadingList" class="flex justify-content-center align-items-center p-4">
          <ProgressSpinner />
          <span class="ml-2">Carregando contas...</span>
        </div>
        
        <div v-else-if="accounts.length === 0" class="text-center p-4">
          <i class="pi pi-info-circle text-4xl text-blue-500 mb-3"></i>
          <p class="text-lg">Nenhuma conta AWS conectada ainda.</p>
        </div>
        
        <DataTable v-else :value="accounts" responsiveLayout="scroll" size="small" class="p-datatable-sm">
          <Column field="id" header="ID" :sortable="true" style="width: 80px"></Column>
          
          <Column field="account_name" header="Nome da Conta" :sortable="true">
            <template #body="slotProps">
              <strong>{{ slotProps.data.account_name }}</strong>
            </template>
          </Column>
          
          <Column field="is_connection_active" header="Status" :sortable="true" style="width: 120px">
            <template #body="slotProps">
              <Tag 
                :value="slotProps.data.is_connection_active ? 'Ativa' : 'Inativa'"
                :severity="slotProps.data.is_connection_active ? 'success' : 'danger'"
              />
            </template>
          </Column>
          
          <Column header="Histórico" style="width: 10rem; text-align: center;">
            <template #body="slotProps">
              <Tag severity="success" value="Importado" v-if="slotProps.data.history_imported" />
              <Button 
                label="Importar" 
                class="p-button-sm p-button-outlined" 
                :loading="isImporting[slotProps.data.id]"
                @click="handleImportHistory(slotProps.data)"
                v-else 
              />
            </template>
          </Column>
          
          <Column header="Ações" style="width: 10rem; text-align: center;">
            <template #body="slotProps">
              <Button icon="pi pi-eye" class="p-button-rounded p-button-text" @click="showDetails(slotProps.data)" v-tooltip.top="'Ver Detalhes'" />
              <Button icon="pi pi-pencil" class="p-button-rounded p-button-text" @click="openEditModal(slotProps.data)" v-tooltip.top="'Editar'" />
              <Button icon="pi pi-trash" class="p-button-rounded p-button-danger p-button-text" @click="handleDelete(slotProps.data)" v-tooltip.top="'Excluir'" />
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Cartão de Ação para Conectar Nova Conta -->
    <div class="add-account-card" @click="openAddModal">
      <img src="/Amazon_Web_Services_Logo.png" alt="AWS Logo" width="48" height="29" />
      <h3>Conectar Nova Conta AWS</h3>
    </div>

    <!-- Modal de Adicionar Conta -->
    <Dialog 
      v-model:visible="isAddModalVisible" 
      modal 
      :style="{ width: '50vw' }"
      :breakpoints="{ '960px': '75vw', '641px': '90vw' }"
    >
      <template #header>
        <div class="flex align-items-center gap-2">
          <img src="/Amazon_Web_Services_Logo.png" alt="AWS Logo" width="24" height="14" />
          <span>Conectar Nova Conta AWS</span>
        </div>
      </template>
      <form @submit.prevent="handleAddAccount" class="p-fluid">
        <div class="field mb-4">
          <label for="add-account-name" class="font-semibold mb-2 block">Nome da Conta (Apelido)</label>
          <InputText 
            id="add-account-name" 
            v-model="newAccount.account_name" 
            placeholder="Ex: Conta de Produção" 
            size="large"
            class="mt-2"
            required 
          />
        </div>
        
        <div class="field mb-4">
          <label for="add-iam-role" class="font-semibold mb-2 block">IAM Role ARN</label>
          <InputText 
            id="add-iam-role" 
            v-model="newAccount.iam_role_arn" 
            placeholder="arn:aws:iam::123456789012:role/CostsHubRole" 
            size="large"
            class="mt-2 w-full"
            style="width: 100% !important; min-width: 500px !important;"
            required 
          />
        </div>
        
        <div class="field mb-5">
          <label for="add-s3-path" class="font-semibold mb-2 block">Caminho do Bucket S3 (FOCUS)</label>
          <InputText 
            id="add-s3-path" 
            v-model="newAccount.focus_s3_bucket_path" 
            placeholder="s3://seu-bucket/seu-prefixo/" 
            size="large"
            class="mt-2 w-full"
            style="width: 100% !important; min-width: 500px !important;"
            required 
          />
        </div>
      </form>
      
      <template #footer>
        <Button 
          label="Cancelar" 
          icon="pi pi-times" 
          severity="secondary"
          @click="closeAddModal" 
        />
        <Button 
          label="Conectar Conta" 
          icon="pi pi-plus"
          :loading="isSubmitting"
          @click="handleAddAccount" 
        />
      </template>
    </Dialog>

    <!-- Modal de Detalhes -->
    <Dialog 
      v-model:visible="isDetailsModalVisible" 
      modal 
      header="Detalhes da Conta AWS" 
      :style="{ width: '50vw' }"
      :breakpoints="{ '960px': '75vw', '641px': '90vw' }"
    >
      <div v-if="selectedAccountForDetails" class="p-fluid">
        <div class="field mb-3">
          <label class="font-semibold">ID:</label>
          <p>{{ selectedAccountForDetails.id }}</p>
        </div>
        
        <div class="field mb-3">
          <label class="font-semibold">Nome da Conta:</label>
          <p>{{ selectedAccountForDetails.account_name }}</p>
        </div>
        
        <div class="field mb-3">
          <label class="font-semibold">IAM Role ARN:</label>
          <p class="text-sm break-all">{{ selectedAccountForDetails.iam_role_arn }}</p>
        </div>
        
        <div class="field mb-3">
          <label class="font-semibold">Caminho S3:</label>
          <p class="text-sm break-all">{{ selectedAccountForDetails.focus_s3_bucket_path }}</p>
        </div>
        
        <div class="field mb-3">
          <label class="font-semibold">Status da Conexão:</label>
          <Tag 
            :value="selectedAccountForDetails.is_connection_active ? 'Ativa' : 'Inativa'"
            :severity="selectedAccountForDetails.is_connection_active ? 'success' : 'danger'"
          />
        </div>
        
        <div class="field mb-3">
          <label class="font-semibold">Histórico Importado:</label>
          <Tag 
            :value="selectedAccountForDetails.history_imported ? 'Sim' : 'Não'"
            :severity="selectedAccountForDetails.history_imported ? 'success' : 'warning'"
          />
        </div>
        
        <div class="field">
          <label class="font-semibold">Data de Criação:</label>
          <p>{{ new Date(selectedAccountForDetails.created_at).toLocaleString('pt-BR') }}</p>
        </div>
      </div>
      
      <template #footer>
        <Button label="Fechar" icon="pi pi-times" @click="closeDetailsModal" />
      </template>
    </Dialog>

    <!-- Modal de Edição -->
    <Dialog 
      v-model:visible="isEditModalVisible" 
      modal 
      header="Editar Conta AWS" 
      :style="{ width: '50vw' }"
      :breakpoints="{ '960px': '75vw', '641px': '90vw' }"
    >
      <form v-if="editingAccount" @submit.prevent="handleUpdateAccount" class="p-fluid">
        <div class="field mb-4">
          <label for="edit-account-name" class="font-semibold mb-2 block">Nome da Conta (Apelido)</label>
          <InputText 
            id="edit-account-name" 
            v-model="editingAccount.account_name" 
            size="large"
            class="mt-2"
            required 
          />
        </div>
        
        <div class="field mb-4">
          <label for="edit-iam-role" class="font-semibold mb-2 block">IAM Role ARN</label>
          <InputText 
            id="edit-iam-role" 
            v-model="editingAccount.iam_role_arn" 
            size="large"
            class="mt-2 w-full"
            style="width: 100% !important; min-width: 500px !important;"
            required 
          />
        </div>
        
        <div class="field mb-5">
          <label for="edit-s3-path" class="font-semibold mb-2 block">Caminho do Bucket S3 (FOCUS)</label>
          <InputText 
            id="edit-s3-path" 
            v-model="editingAccount.focus_s3_bucket_path" 
            size="large"
            class="mt-2 w-full"
            style="width: 100% !important; min-width: 500px !important;"
            required 
          />
        </div>
        
        <div class="field mb-5">
          <label for="edit-monthly-budget" class="font-semibold mb-2 block">Orçamento Mensal ($)</label>
          <InputNumber 
            id="edit-monthly-budget" 
            v-model="editingAccount.monthly_budget" 
            mode="currency" 
            currency="USD" 
            locale="en-US"
            size="large"
            class="mt-2"
            :min="0"
            :maxFractionDigits="2"
            placeholder="0.00"
          />
          <small class="text-gray-600 mt-1 block">
            Define o orçamento mensal para esta conta AWS. Usado para calcular o consumo e previsões.
          </small>
        </div>
      </form>
      
      <template #footer>
        <Button 
          label="Cancelar" 
          icon="pi pi-times" 
          severity="secondary"
          @click="closeEditModal" 
        />
        <Button 
          label="Salvar" 
          icon="pi pi-check" 
          :loading="isSubmitting"
          @click="handleUpdateAccount" 
        />
      </template>
    </Dialog>

    <!-- Modal de Criação/Edição de Alarme -->
    <Dialog 
      v-model:visible="isAlarmModalVisible" 
      modal 
      :header="isEditingAlarm ? 'Editar Regra de Alarme' : 'Criar Nova Regra de Alarme'"
      :style="{ width: '60vw' }"
      :breakpoints="{ '960px': '80vw', '641px': '95vw' }"
    >
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
        <div v-if="alarmForm.scope_type === 'AWS_ACCOUNT'" class="field mb-4">
          <label for="alarm-account" class="font-semibold mb-2 block">Conta AWS</label>
          <Dropdown
            id="alarm-account"
            v-model="alarmForm.scope_value"
            :options="accounts.map(acc => ({ label: acc.account_name, value: acc.id.toString() }))"
            optionLabel="label"
            optionValue="value"
            placeholder="Selecione a conta AWS"
          />
        </div>

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
                <div class="field">
                  <label class="severity-label">Nome:</label>
                  <InputText 
                    v-model="level.name" 
                    placeholder="Ex: Alto, Crítico"
                    required
                  />
                </div>
                <div class="field">
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
  </div>
</template>

<style scoped>
.settings-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.settings-page h1 {
  color: #333;
  margin-bottom: 2rem;
}

.mb-4 {
  margin-bottom: 2rem;
}

.break-all {
  word-break: break-all;
}

/* Cartão de Ação para Adicionar Conta */
.add-account-card {
  border: 2px dashed #6c757d;
  border-radius: 8px;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: transparent;
  margin-bottom: 2rem;
}

.add-account-card:hover {
  border-color: #007BFF;
  background-color: rgba(0, 123, 255, 0.05);
  transform: translateY(-2px);
}

.add-account-card svg {
  margin-bottom: 1rem;
  color: #6c757d;
  transition: color 0.3s ease;
}

.add-account-card:hover svg {
  color: #007BFF;
}

.add-account-card img {
  margin-bottom: 1rem;
  transition: opacity 0.3s ease;
  filter: brightness(0.8);
}

.add-account-card:hover img {
  filter: brightness(1);
}

.add-account-card h3 {
  margin: 0;
  color: #6c757d;
  font-weight: 500;
  font-size: 1.2rem;
  transition: color 0.3s ease;
}

.add-account-card h3 {
  margin: 0;
  color: #6c757d;
  font-weight: 500;
  font-size: 1.2rem;
  transition: color 0.3s ease;
}

.add-account-card:hover h3 {
  color: #007BFF;
}

/* Melhorias nos formulários dos modais */
.p-dialog .field label {
  font-size: 0.95rem;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.p-dialog .p-inputtext {
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
  margin-top: 0.5rem;
}

.p-dialog .field {
  margin-bottom: 1.5rem;
}

/* Campos específicos maiores para IAM Role e S3 Bucket */
.p-dialog .p-inputtext#add-iam-role,
.p-dialog .p-inputtext#edit-iam-role,
.p-dialog .p-inputtext#add-s3-path,
.p-dialog .p-inputtext#edit-s3-path {
  min-height: 3.5rem !important;
  height: 3.5rem !important;
  font-size: 0.9rem !important;
  line-height: 1.4 !important;
  padding: 1rem 1rem !important;
  box-sizing: border-box !important;
}

/* Textarea-like behavior para campos longos */
.long-input {
  resize: vertical !important;
  min-height: 3.5rem !important;
  word-wrap: break-word !important;
  white-space: pre-wrap !important;
}

/* Ajuste geral para todos os inputs do modal */
.p-dialog .p-inputtext {
  padding: 0.75rem 1rem !important;
  font-size: 0.95rem !important;
  margin-top: 0.5rem !important;
}

/* Específico para campos de nome (manter tamanho normal) */
.p-dialog .p-inputtext#add-account-name,
.p-dialog .p-inputtext#edit-account-name {
  min-height: 2.75rem !important;
  height: 2.75rem !important;
}

/* Forçar estilos com :deep() para PrimeVue */
:deep(.p-inputtext.long-input) {
  min-height: 4rem !important;
  height: 4rem !important;
  padding: 1rem !important;
  font-size: 0.9rem !important;
  line-height: 1.4 !important;
  box-sizing: border-box !important;
}

/* Alternativa com seletores ainda mais específicos */
.settings-page :deep(.p-dialog .p-inputtext#add-iam-role),
.settings-page :deep(.p-dialog .p-inputtext#edit-iam-role),
.settings-page :deep(.p-dialog .p-inputtext#add-s3-path),
.settings-page :deep(.p-dialog .p-inputtext#edit-s3-path) {
  min-height: 4rem !important;
  height: 4rem !important;
  padding: 1rem !important;
  font-size: 0.9rem !important;
  line-height: 1.4 !important;
  box-sizing: border-box !important;
}
</style>
