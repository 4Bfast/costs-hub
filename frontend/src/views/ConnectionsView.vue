<script setup>
import { ref, onMounted } from 'vue';
import { apiService } from '@/services/api';
import { useToast } from 'primevue/usetoast';

// Componentes PrimeVue
import Card from 'primevue/card';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import InputNumber from 'primevue/inputnumber';
import Textarea from 'primevue/textarea';
import Message from 'primevue/message';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Tag from 'primevue/tag';
import ConfirmDialog from 'primevue/confirmdialog';
import { useConfirm } from 'primevue/useconfirm';

const toast = useToast();

// Estado
const accounts = ref([]);
const memberAccounts = ref([]);
const isLoadingList = ref(true);
const isLoadingMembers = ref(true);
const message = ref({ type: '', text: '' });

// Estado para configuração de tags
const discoveredTags = ref([]);
const tagConfig = ref({
  selectedTags: [],
  priorityOrder: [],
  projectFilters: {}
});
const isLoadingTags = ref(false);
const isLoadingTagConfig = ref(false);

// Estado para onboarding seguro
const isOnboardingModalVisible = ref(false);
const onboardingStep = ref(1);
const onboardingError = ref(null);
const onboardingData = ref(null);
const isSubmitting = ref(false);

const onboardingForm = ref({
  payerAccountId: '',
  s3Prefix: '',
  roleArn: '',
  payerAccountIdError: null,
  s3PrefixError: null,
  roleArnError: null
});

// Funções
async function fetchAccounts() {
  try {
    isLoadingList.value = true;
    const response = await apiService.getAccounts();
    accounts.value = response;
  } catch (error) {
    console.error('Erro ao buscar contas:', error);
    message.value = { type: 'error', text: 'Erro ao carregar contas AWS' };
  } finally {
    isLoadingList.value = false;
  }
}

async function fetchMemberAccounts() {
  try {
    isLoadingMembers.value = true;
    const response = await apiService.getMemberAccounts();
    memberAccounts.value = response;
  } catch (error) {
    console.error('Erro ao buscar contas descobertas:', error);
  } finally {
    isLoadingMembers.value = false;
  }
}

function openOnboardingModal() {
  resetOnboardingForm();
  onboardingStep.value = 1;
  isOnboardingModalVisible.value = true;
}

function closeOnboardingModal() {
  isOnboardingModalVisible.value = false;
  resetOnboardingForm();
  onboardingData.value = null;
}

function resetOnboardingForm() {
  onboardingForm.value = {
    payerAccountId: '',
    s3Prefix: '',
    roleArn: '',
    payerAccountIdError: null,
    s3PrefixError: null,
    roleArnError: null
  };
  onboardingError.value = null;
}

async function handleInitiateConnection() {
  try {
    onboardingForm.value.payerAccountIdError = null;
    onboardingForm.value.s3PrefixError = null;
    onboardingError.value = null;
    
    if (!onboardingForm.value.payerAccountId) {
      onboardingForm.value.payerAccountIdError = 'ID da conta é obrigatório';
      return;
    }
    
    if (!/^\d{12}$/.test(onboardingForm.value.payerAccountId)) {
      onboardingForm.value.payerAccountIdError = 'ID deve ter exatamente 12 dígitos';
      return;
    }
    
    if (!onboardingForm.value.s3Prefix) {
      onboardingForm.value.s3PrefixError = 'Prefixo do bucket é obrigatório';
      return;
    }
    
    if (!/^[a-z0-9-]+$/.test(onboardingForm.value.s3Prefix)) {
      onboardingForm.value.s3PrefixError = 'Apenas letras minúsculas, números e hífens';
      return;
    }
    
    isSubmitting.value = true;
    
    const response = await apiService.post('/connections/initiate', {
      payer_account_id: onboardingForm.value.payerAccountId,
      s3_prefix: onboardingForm.value.s3Prefix
    });
    
    onboardingData.value = response;
    onboardingStep.value = 2;
    
    toast.add({
      severity: 'success',
      summary: 'Processo Iniciado',
      detail: 'Agora execute o template CloudFormation na AWS',
      life: 5000
    });
    
  } catch (error) {
    console.error('Erro ao iniciar conexão:', error);
    onboardingError.value = error.response?.data?.error || 'Erro ao iniciar processo de conexão';
  } finally {
    isSubmitting.value = false;
  }
}

function openCloudFormation() {
  if (onboardingData.value?.cloudformation_url) {
    window.open(onboardingData.value.cloudformation_url, '_blank');
  }
}

async function handleFinalizeConnection() {
  try {
    onboardingForm.value.roleArnError = null;
    onboardingError.value = null;
    
    if (!onboardingForm.value.roleArn) {
      onboardingForm.value.roleArnError = 'ARN da Role é obrigatório';
      return;
    }
    
    if (!onboardingForm.value.roleArn.startsWith('arn:aws:iam::')) {
      onboardingForm.value.roleArnError = 'Formato de ARN inválido';
      return;
    }
    
    isSubmitting.value = true;
    
    const response = await apiService.post(`/connections/${onboardingData.value.connection_id}/finalize`, {
      role_arn: onboardingForm.value.roleArn.trim()
    });
    
    toast.add({
      severity: 'success',
      summary: 'Conexão Ativada',
      detail: 'Conta AWS conectada com sucesso!',
      life: 5000
    });
    
    closeOnboardingModal();
    await fetchAccounts();
    await fetchMemberAccounts();
    
  } catch (error) {
    console.error('Erro ao finalizar conexão:', error);
    onboardingError.value = error.response?.data?.error || 'Erro ao finalizar conexão';
  } finally {
    isSubmitting.value = false;
  }
}

function getStatusSeverity(status) {
  const severities = {
    'ACTIVE': 'success',
    'PENDING': 'warning',
    'ERROR': 'danger'
  };
  return severities[status] || 'info';
}

// Funções para gerenciar contas existentes
const isEditModalVisible = ref(false);
const isDeleteModalVisible = ref(false);
const selectedAccount = ref(null);

function editAccount(account) {
  selectedAccount.value = { ...account };
  isEditModalVisible.value = true;
}

function editMemberAccount(account) {
  selectedAccount.value = { ...account };
  isEditModalVisible.value = true;
}

function confirmDeleteAccount(account) {
  selectedAccount.value = account;
  isDeleteModalVisible.value = true;
}

async function handleDeleteAccount() {
  try {
    isSubmitting.value = true;
    
    await apiService.deleteAccount(selectedAccount.value.id);
    
    toast.add({
      severity: 'success',
      summary: 'Conta Removida',
      detail: `${selectedAccount.value.account_name} foi removida com sucesso`,
      life: 5000
    });
    
    isDeleteModalVisible.value = false;
    selectedAccount.value = null;
    await fetchAccounts();
    
  } catch (error) {
    console.error('Erro ao remover conta:', error);
    toast.add({
      severity: 'error',
      summary: 'Erro',
      detail: error.response?.data?.error || 'Não foi possível remover a conta',
      life: 5000
    });
  } finally {
    isSubmitting.value = false;
  }
}

async function handleUpdateAccount() {
  try {
    isSubmitting.value = true;
    
    // Verificar se é uma conta descoberta (member_account) ou conexão (aws_account)
    if (selectedAccount.value.aws_account_id) {
      // É uma conta descoberta - usar API de member-accounts
      await apiService.updateMemberAccountBudget(
        selectedAccount.value.id, 
        selectedAccount.value.monthly_budget
      );
      await fetchMemberAccounts(); // Recarregar contas descobertas
    } else {
      // É uma conexão - usar API de aws-accounts
      await apiService.updateAccount(selectedAccount.value.id, {
        account_name: selectedAccount.value.account_name,
        monthly_budget: selectedAccount.value.monthly_budget
      });
      await fetchAccounts(); // Recarregar conexões
    }
    
    toast.add({
      severity: 'success',
      summary: 'Conta Atualizada',
      detail: 'Informações da conta foram atualizadas com sucesso',
      life: 5000
    });
    
    isEditModalVisible.value = false;
    selectedAccount.value = null;
    
  } catch (error) {
    console.error('Erro ao atualizar conta:', error);
    toast.add({
      severity: 'error',
      summary: 'Erro',
      detail: error.response?.data?.error || 'Não foi possível atualizar a conta',
      life: 5000
    });
  } finally {
    isSubmitting.value = false;
  }
}

onMounted(() => {
  fetchAccounts();
  fetchMemberAccounts();
  fetchDiscoveredTags();
  fetchTagConfig();
});

// Funções para configuração de tags
async function fetchDiscoveredTags() {
  try {
    isLoadingTags.value = true;
    const response = await apiService.getDiscoveredTags();
    discoveredTags.value = response.tags || [];
  } catch (error) {
    console.error('Erro ao buscar tags descobertas:', error);
    toast.add({
      severity: 'error',
      summary: 'Erro',
      detail: 'Erro ao carregar tags descobertas',
      life: 3000
    });
  } finally {
    isLoadingTags.value = false;
  }
}

async function fetchTagConfig() {
  try {
    isLoadingTagConfig.value = true;
    const response = await apiService.getTagConfig();
    if (response.config) {
      tagConfig.value = response.config;
    }
  } catch (error) {
    console.error('Erro ao buscar configuração de tags:', error);
  } finally {
    isLoadingTagConfig.value = false;
  }
}

async function saveTagConfig() {
  try {
    const response = await apiService.saveTagConfig(tagConfig.value);
    if (response.success) {
      toast.add({
        severity: 'success',
        summary: 'Sucesso',
        detail: 'Configuração de tags salva com sucesso',
        life: 3000
      });
    }
  } catch (error) {
    console.error('Erro ao salvar configuração:', error);
    toast.add({
      severity: 'error',
      summary: 'Erro',
      detail: 'Erro ao salvar configuração de tags',
      life: 3000
    });
  }
}

function toggleTagSelection(tagKey) {
  const index = tagConfig.value.selectedTags.indexOf(tagKey);
  if (index > -1) {
    tagConfig.value.selectedTags.splice(index, 1);
    const priorityIndex = tagConfig.value.priorityOrder.indexOf(tagKey);
    if (priorityIndex > -1) {
      tagConfig.value.priorityOrder.splice(priorityIndex, 1);
    }
  } else {
    tagConfig.value.selectedTags.push(tagKey);
    tagConfig.value.priorityOrder.push(tagKey);
  }
}

function moveTagUp(tagKey) {
  const index = tagConfig.value.priorityOrder.indexOf(tagKey);
  if (index > 0) {
    [tagConfig.value.priorityOrder[index], tagConfig.value.priorityOrder[index - 1]] = 
    [tagConfig.value.priorityOrder[index - 1], tagConfig.value.priorityOrder[index]];
  }
}

function moveTagDown(tagKey) {
  const index = tagConfig.value.priorityOrder.indexOf(tagKey);
  if (index < tagConfig.value.priorityOrder.length - 1) {
    [tagConfig.value.priorityOrder[index], tagConfig.value.priorityOrder[index + 1]] = 
    [tagConfig.value.priorityOrder[index + 1], tagConfig.value.priorityOrder[index]];
  }
}
</script>

<template>
  <div class="connections-page">
    <div class="page-header">
      <h1 class="page-title">
        <i class="pi pi-cloud mr-4"></i>
        Conexões AWS
      </h1>
      <p class="page-description">
        Gerencie suas conexões com contas AWS para monitoramento de custos
      </p>
    </div>

    <Message v-if="message.text" :severity="message.type" :closable="true" @close="message.text = ''" class="mb-4">
      {{ message.text }}
    </Message>

    <!-- Card das Contas AWS -->
    <Card class="mb-4">
      <template #title>
        <i class="pi pi-aws mr-4"></i>
        Contas AWS Conectadas
      </template>
      
      <template #content>
        <div v-if="isLoadingList" class="text-center py-4">
          <i class="pi pi-spin pi-spinner text-2xl text-blue-500 mb-3"></i>
          <p class="text-gray-600">Carregando contas...</p>
        </div>
        
        <div v-else-if="accounts.length === 0" class="empty-state">
          <i class="pi pi-cloud text-6xl text-gray-400 mb-4"></i>
          <h3 class="text-xl font-semibold text-gray-700 mb-2">Nenhuma conta conectada</h3>
          <p class="text-gray-600 mb-4">Conecte sua primeira conta AWS para começar a monitorar custos</p>
          <Button 
            label="Conectar Primeira Conta" 
            icon="pi pi-plus"
            size="large"
            @click="openOnboardingModal"
          />
        </div>
        
        <div v-else>
          <div class="flex justify-content-between align-items-center mb-4">
            <p class="text-gray-600">{{ accounts.length }} conta(s) conectada(s)</p>
          </div>
          
          <DataTable :value="accounts" responsiveLayout="scroll" class="p-datatable-sm">
            <Column field="account_name" header="Nome da Conta" :sortable="true">
              <template #body="slotProps">
                <strong>{{ slotProps.data.account_name }}</strong>
              </template>
            </Column>
            
            <Column field="status" header="Status" style="width: 120px">
              <template #body="slotProps">
                <Tag 
                  :value="slotProps.data.status || 'ACTIVE'" 
                  :severity="getStatusSeverity(slotProps.data.status)"
                />
              </template>
            </Column>
            
            <Column field="payer_account_id" header="Account ID" style="width: 150px">
              <template #body="slotProps">
                <code class="text-sm">{{ slotProps.data.payer_account_id || 'N/A' }}</code>
              </template>
            </Column>
            
            <Column header="Ações" style="width: 120px">
              <template #body="slotProps">
                <div class="flex gap-2">
                  <Button 
                    icon="pi pi-pencil" 
                    class="p-button-rounded p-button-text p-button-sm" 
                    @click="editAccount(slotProps.data)"
                    v-tooltip.top="'Editar'"
                  />
                  <Button 
                    icon="pi pi-trash" 
                    class="p-button-rounded p-button-text p-button-danger p-button-sm" 
                    @click="confirmDeleteAccount(slotProps.data)"
                    v-tooltip.top="'Excluir'"
                  />
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
      </template>
    </Card>

    <!-- Card das Contas Descobertas -->
    <Card class="mb-4">
      <template #title>
        <i class="pi pi-users mr-4"></i>
        Contas Descobertas
      </template>
      
      <template #content>
        <div v-if="isLoadingMembers" class="text-center py-4">
          <i class="pi pi-spin pi-spinner text-2xl text-blue-500 mb-2"></i>
          <p class="text-gray-600">Carregando contas descobertas...</p>
        </div>
        
        <div v-else-if="memberAccounts.length === 0" class="empty-state">
          <i class="pi pi-info-circle text-6xl text-gray-400 mb-4"></i>
          <h3 class="text-xl font-semibold text-gray-700 mb-2">Nenhuma conta descoberta</h3>
          <p class="text-gray-600 mb-4">As contas serão descobertas automaticamente após o processamento dos dados FOCUS</p>
        </div>
        
        <div v-else>
          <div class="flex justify-content-between align-items-center mb-4">
            <p class="text-gray-600">{{ memberAccounts.length }} conta(s) descoberta(s)</p>
          </div>
          
          <DataTable :value="memberAccounts" responsiveLayout="scroll" class="p-datatable-sm">
            <Column field="name" header="Nome da Conta" :sortable="true">
              <template #body="slotProps">
                <div class="flex align-items-center gap-2">
                  <strong>{{ slotProps.data.name }}</strong>
                  <Tag 
                    v-if="slotProps.data.is_payer" 
                    value="PAYER" 
                    severity="warning"
                    class="text-xs"
                  />
                </div>
              </template>
            </Column>
            
            <Column field="aws_account_id" header="ID da Conta AWS" style="width: 150px">
              <template #body="slotProps">
                <code class="text-sm">{{ slotProps.data.aws_account_id }}</code>
              </template>
            </Column>
            
            <Column field="monthly_budget" header="Orçamento" style="width: 140px">
              <template #body="slotProps">
                <span class="text-sm">
                  ${{ (slotProps.data.monthly_budget || 0).toFixed(2) }}
                </span>
              </template>
            </Column>
            
            <Column header="Ações" style="width: 120px">
              <template #body="slotProps">
                <div class="flex gap-2">
                  <Button 
                    icon="pi pi-pencil" 
                    class="p-button-rounded p-button-text p-button-sm" 
                    @click="editMemberAccount(slotProps.data)"
                    v-tooltip.top="'Editar Orçamento'"
                  />
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
      </template>
    </Card>

    <!-- Card de Configuração de Tags para Projetos -->
    <Card class="mb-4">
      <template #title>
        <i class="pi pi-tags mr-4"></i>
        Configuração de Tags para Projetos
      </template>
      
      <template #content>
        <div class="mb-4">
          <p class="text-gray-600 mb-3">
            Configure quais tags serão usadas para identificar e agrupar projetos nos relatórios de custos.
            As tags são descobertas automaticamente durante o processamento dos arquivos FOCUS.
          </p>
          
          <div class="flex gap-2 mb-4">
            <Button 
              label="Extrair Tags dos Dados Existentes" 
              icon="pi pi-search"
              size="small"
              severity="info"
              @click="extractTagsFromExisting"
              :loading="isLoadingTags"
              v-if="discoveredTags.length === 0"
            />
            <Button 
              label="Salvar Configuração" 
              icon="pi pi-save"
              size="small"
              severity="success"
              @click="saveTagConfig"
              :disabled="tagConfig.selectedTags.length === 0"
            />
          </div>
        </div>

        <div v-if="isLoadingTags" class="text-center py-4">
          <i class="pi pi-spin pi-spinner text-2xl text-blue-500 mb-2"></i>
          <p class="text-gray-600">Carregando tags descobertas...</p>
        </div>
        
        <div v-else-if="discoveredTags.length === 0" class="empty-state">
          <i class="pi pi-tag text-6xl text-gray-400 mb-4"></i>
          <h3 class="text-xl font-semibold text-gray-700 mb-2">Nenhuma tag descoberta</h3>
          <p class="text-gray-500 mb-4">
            As tags serão descobertas automaticamente quando os arquivos FOCUS forem processados.
            Conecte uma conta AWS e processe dados para ver as tags disponíveis.
          </p>
        </div>
        
        <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Tags Descobertas -->
          <div>
            <h4 class="text-lg font-semibold mb-3 flex items-center gap-2">
              <i class="pi pi-search text-blue-500"></i>
              Tags Descobertas
            </h4>
            
            <div class="space-y-3">
              <div 
                v-for="tag in discoveredTags" 
                :key="tag.id"
                class="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                @click="toggleTagSelection(tag.tagKey)"
              >
                <div class="flex items-center gap-3">
                  <input 
                    type="checkbox" 
                    :checked="tagConfig.selectedTags.includes(tag.tagKey)"
                    class="w-4 h-4"
                  />
                  <div>
                    <div class="font-medium">{{ tag.tagKey }}</div>
                    <div class="text-sm text-gray-500">
                      {{ tag.frequency }} recursos ({{ tag.coveragePercent.toFixed(1) }}% cobertura)
                    </div>
                    <div class="text-xs text-gray-400 mt-1">
                      Valores: {{ tag.tagValues.slice(0, 3).join(', ') }}
                      <span v-if="tag.tagValues.length > 3">...</span>
                    </div>
                  </div>
                </div>
                
                <div class="text-right">
                  <div class="w-16 bg-gray-200 rounded-full h-2">
                    <div 
                      class="bg-blue-500 h-2 rounded-full" 
                      :style="{ width: tag.coveragePercent + '%' }"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Configuração de Prioridade -->
          <div>
            <h4 class="text-lg font-semibold mb-3 flex items-center gap-2">
              <i class="pi pi-sort-alt text-green-500"></i>
              Ordem de Prioridade
            </h4>
            
            <div v-if="tagConfig.priorityOrder.length === 0" class="text-center py-8 text-gray-500">
              <i class="pi pi-info-circle text-4xl mb-2"></i>
              <p>Selecione tags à esquerda para definir a ordem de prioridade</p>
            </div>
            
            <div v-else class="space-y-2">
              <div 
                v-for="(tagKey, index) in tagConfig.priorityOrder" 
                :key="tagKey"
                class="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg"
              >
                <div class="flex items-center gap-3">
                  <div class="w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                    {{ index + 1 }}
                  </div>
                  <span class="font-medium">{{ tagKey }}</span>
                </div>
                
                <div class="flex gap-1">
                  <Button 
                    icon="pi pi-chevron-up"
                    size="small"
                    text
                    :disabled="index === 0"
                    @click="moveTagUp(tagKey)"
                  />
                  <Button 
                    icon="pi pi-chevron-down"
                    size="small"
                    text
                    :disabled="index === tagConfig.priorityOrder.length - 1"
                    @click="moveTagDown(tagKey)"
                  />
                </div>
              </div>
              
              <div class="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div class="flex items-start gap-2">
                  <i class="pi pi-info-circle text-yellow-600 mt-1"></i>
                  <div class="text-sm text-yellow-800">
                    <strong>Como funciona:</strong> O sistema tentará identificar projetos usando as tags na ordem definida. 
                    Se a primeira tag não estiver presente, tentará a segunda, e assim por diante.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Cartão de Ação para Conectar Nova Conta -->
    <div class="add-account-card" @click="openOnboardingModal">
      <i class="pi pi-plus-circle text-4xl text-blue-500 mb-3"></i>
      <h3>Conectar Conta de Faturamento (Payer)</h3>
      <p class="add-account-description">Processo seguro em 2 etapas</p>
    </div>

    <!-- Modal de Onboarding Seguro -->
    <Dialog 
      v-model:visible="isOnboardingModalVisible" 
      modal 
      :style="{ width: '600px' }"
      :breakpoints="{ '960px': '80vw', '641px': '95vw' }"
      :closable="!isSubmitting"
    >
      <template #header>
        <div class="flex align-items-center gap-2">
          <i class="pi pi-aws text-orange-500 mr-3"></i>
          <span>{{ onboardingStep === 1 ? 'Conectar Conta AWS - Etapa 1/2' : 'Conectar Conta AWS - Etapa 2/2' }}</span>
        </div>
      </template>

      <!-- Etapa 1: Coleta de Dados -->
      <div v-if="onboardingStep === 1" class="onboarding-step-1">
        <div class="step-header">
          <i class="pi pi-info-circle text-blue-500 text-2xl mb-3"></i>
          <h3 class="step-title">Informações da Conta AWS</h3>
          <p class="step-description">
            Informe os dados da sua conta AWS Payer para iniciar o processo de conexão segura.
          </p>
        </div>

        <Message v-if="onboardingError" severity="error" :closable="true" class="mb-4" @close="onboardingError = null">
          {{ onboardingError }}
        </Message>

        <div class="field mb-4">
          <label for="payer-account-id" class="font-semibold mb-2 block">ID da Conta AWS Payer</label>
          <InputText 
            id="payer-account-id" 
            v-model="onboardingForm.payerAccountId" 
            placeholder="123456789012"
            maxlength="12"
            required
            :class="{ 'p-invalid': onboardingForm.payerAccountIdError }"
          />
          <small v-if="onboardingForm.payerAccountIdError" class="p-error">{{ onboardingForm.payerAccountIdError }}</small>
          <small class="text-gray-600 mt-1 block">
            <i class="pi pi-info-circle mr-3"></i>
            ID de 12 dígitos da conta AWS que recebe a fatura consolidada.
          </small>
        </div>

        <div class="field mb-4">
          <label for="s3-prefix" class="font-semibold mb-2 block">Prefixo do Bucket S3</label>
          <InputText 
            id="s3-prefix" 
            v-model="onboardingForm.s3Prefix" 
            placeholder="minhaempresa-costs"
            maxlength="30"
            required
            :class="{ 'p-invalid': onboardingForm.s3PrefixError }"
          />
          <small v-if="onboardingForm.s3PrefixError" class="p-error">{{ onboardingForm.s3PrefixError }}</small>
          <small class="text-gray-600 mt-1 block">
            <i class="pi pi-info-circle mr-3"></i>
            Nome único para o bucket S3 (apenas letras minúsculas, números e hífens).
          </small>
        </div>

        <div class="security-notice">
          <div class="security-header">
            <i class="pi pi-shield text-green-500 mr-3"></i>
            <strong>Conexão Segura</strong>
          </div>
          <ul class="security-features">
            <li><i class="pi pi-check text-green-500 mr-3"></i>External ID único para cada conexão</li>
            <li><i class="pi pi-check text-green-500 mr-3"></i>Permissões mínimas necessárias</li>
            <li><i class="pi pi-check text-green-500 mr-3"></i>Template CloudFormation validado</li>
          </ul>
        </div>
      </div>

      <!-- Etapa 2: CloudFormation e Finalização -->
      <div v-if="onboardingStep === 2" class="onboarding-step-2">
        <div class="step-header">
          <i class="pi pi-cloud text-orange-500 text-2xl mb-3"></i>
          <h3 class="step-title">Criar Recursos na AWS</h3>
          <p class="step-description">
            Execute o template CloudFormation na sua conta AWS e cole o ARN da Role criada.
          </p>
        </div>

        <div class="cloudformation-section">
          <div class="instruction-step">
            <div class="step-number">1</div>
            <div class="step-content">
              <h4>Abrir Console AWS</h4>
              <p>Clique no botão abaixo para abrir o CloudFormation com os parâmetros pré-preenchidos:</p>
              <Button 
                label="Abrir Console AWS"
                icon="pi pi-external-link"
                class="p-button-lg p-button-warning mt-2"
                @click="openCloudFormation"
              />
            </div>
          </div>

          <div class="instruction-step">
            <div class="step-number">2</div>
            <div class="step-content">
              <h4>Executar Template</h4>
              <p>No console AWS:</p>
              <ul class="instruction-list">
                <li>Revise os parâmetros (já preenchidos)</li>
                <li>Clique em "Create Stack"</li>
                <li>Aguarde a criação (2-3 minutos)</li>
              </ul>
            </div>
          </div>

          <div class="instruction-step">
            <div class="step-number">3</div>
            <div class="step-content">
              <h4>Copiar Role ARN</h4>
              <p>Após a criação bem-sucedida:</p>
              <ul class="instruction-list">
                <li>Vá para a aba "Outputs"</li>
                <li>Copie o valor de "CostsHubRoleArn"</li>
                <li>Cole no campo abaixo</li>
              </ul>
            </div>
          </div>
        </div>

        <Message v-if="onboardingError" severity="error" :closable="true" class="mb-4" @close="onboardingError = null">
          {{ onboardingError }}
        </Message>

        <div class="field mb-4">
          <label for="role-arn" class="font-semibold mb-2 block">ARN da Role IAM</label>
          <Textarea 
            id="role-arn" 
            v-model="onboardingForm.roleArn" 
            placeholder="arn:aws:iam::123456789012:role/CostsHubRole-123456789012"
            rows="5"
            required
            class="role-arn-input"
            :class="{ 'p-invalid': onboardingForm.roleArnError }"
          />
          <small v-if="onboardingForm.roleArnError" class="p-error">{{ onboardingForm.roleArnError }}</small>
          <small class="text-gray-600 mt-1 block">
            <i class="pi pi-info-circle mr-3"></i>
            Cole aqui o ARN da Role copiado da aba "Outputs" do CloudFormation.
          </small>
        </div>
      </div>

      <template #footer>
        <div class="modal-footer">
          <!-- Etapa 1 -->
          <div v-if="onboardingStep === 1" class="footer-content">
            <Button 
              label="Cancelar" 
              icon="pi pi-times" 
              severity="secondary"
              @click="closeOnboardingModal" 
              :disabled="isSubmitting"
            />
            <Button 
              label="Próximo" 
              icon="pi pi-arrow-right"
              iconPos="right"
              :loading="isSubmitting"
              @click="handleInitiateConnection" 
            />
          </div>

          <!-- Etapa 2 -->
          <div v-if="onboardingStep === 2" class="footer-content">
            <Button 
              label="Voltar" 
              icon="pi pi-arrow-left"
              severity="secondary"
              @click="onboardingStep = 1" 
              :disabled="isSubmitting"
            />
            <div class="footer-right">
              <Button 
                label="Cancelar" 
                icon="pi pi-times" 
                severity="secondary"
                @click="closeOnboardingModal" 
                :disabled="isSubmitting"
              />
              <Button 
                label="Finalizar Conexão" 
                icon="pi pi-check"
                :loading="isSubmitting"
                @click="handleFinalizeConnection" 
              />
            </div>
          </div>
        </div>
      </template>
    </Dialog>

    <!-- Modal de Edição -->
    <Dialog 
      v-model:visible="isEditModalVisible" 
      modal 
      header="Editar Conta AWS"
      :style="{ width: '500px' }"
      :breakpoints="{ '960px': '80vw', '641px': '95vw' }"
    >
      <div v-if="selectedAccount" class="p-fluid">
        <div class="field mb-4">
          <label for="edit-account-name" class="font-semibold mb-2 block">Nome da Conta</label>
          <InputText 
            id="edit-account-name" 
            v-model="selectedAccount.account_name" 
            placeholder="Nome descritivo da conta"
            required
          />
        </div>

        <div class="field mb-4">
          <label for="edit-monthly-budget" class="font-semibold mb-2 block">Orçamento Mensal (USD)</label>
          <InputNumber 
            id="edit-monthly-budget" 
            v-model="selectedAccount.monthly_budget" 
            mode="currency" 
            currency="USD" 
            locale="en-US"
            placeholder="0.00"
          />
          <small class="text-gray-600 mt-1 block">
            <i class="pi pi-info-circle mr-3"></i>
            Orçamento mensal para alertas de custo.
          </small>
        </div>

        <!-- Informações da Conexão (apenas para conexões) -->
        <div v-if="!selectedAccount.aws_account_id" class="field mb-4">
          <label class="font-semibold mb-2 block">Informações da Conexão</label>
          <div class="connection-info">
            <div class="info-item">
              <strong>Account ID:</strong> {{ selectedAccount.payer_account_id || 'N/A' }}
            </div>
            <div class="info-item">
              <strong>Status:</strong> 
              <Tag 
                :value="selectedAccount.status || 'ACTIVE'" 
                :severity="getStatusSeverity(selectedAccount.status)"
                class="ml-2"
              />
            </div>
            <div class="info-item">
              <strong>S3 Bucket:</strong> {{ selectedAccount.focus_s3_bucket_path || 'N/A' }}
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="modal-footer">
          <div class="footer-content">
            <Button 
              label="Cancelar" 
              icon="pi pi-times" 
              severity="secondary"
              @click="isEditModalVisible = false" 
              :disabled="isSubmitting"
            />
            <Button 
              label="Salvar" 
              icon="pi pi-check"
              :loading="isSubmitting"
              @click="handleUpdateAccount" 
            />
          </div>
        </div>
      </template>
    </Dialog>

    <!-- Modal de Confirmação de Exclusão -->
    <Dialog 
      v-model:visible="isDeleteModalVisible" 
      modal 
      header="Confirmar Exclusão"
      :style="{ width: '450px' }"
      :breakpoints="{ '960px': '80vw', '641px': '95vw' }"
    >
      <div v-if="selectedAccount" class="confirmation-content">
        <i class="pi pi-exclamation-triangle text-orange-500 text-4xl mb-4"></i>
        <h3 class="confirmation-title">Tem certeza?</h3>
        <p class="confirmation-message">
          Você está prestes a excluir a conta <strong>{{ selectedAccount.account_name }}</strong>.
        </p>
        <div class="warning-box">
          <i class="pi pi-exclamation-circle text-red-500 mr-3"></i>
          <div>
            <strong>Esta ação não pode ser desfeita!</strong>
            <ul class="warning-list">
              <li>Todos os dados de custo serão perdidos</li>
              <li>Histórico de importações será removido</li>
              <li>Alarmes configurados serão excluídos</li>
            </ul>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="modal-footer">
          <div class="footer-content">
            <Button 
              label="Cancelar" 
              icon="pi pi-times" 
              severity="secondary"
              @click="isDeleteModalVisible = false" 
              :disabled="isSubmitting"
            />
            <Button 
              label="Excluir" 
              icon="pi pi-trash"
              severity="danger"
              :loading="isSubmitting"
              @click="handleDeleteAccount" 
            />
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.connections-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 3rem;
  text-align: center;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 1rem 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-description {
  color: #6c757d;
  font-size: 1.2rem;
  margin: 0;
}

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
}

.add-account-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border: 2px dashed #007bff;
  border-radius: 1rem;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 2rem;
}

.add-account-card:hover {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-color: #0056b3;
  transform: translateY(-2px);
}

.add-account-card h3 {
  color: #2c3e50;
  font-size: 1.3rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
}

.add-account-description {
  color: #6c757d;
  font-size: 0.9rem;
  margin: 0;
}

/* Estilos para Onboarding */
.onboarding-step-1,
.onboarding-step-2 {
  padding: 1rem 0;
}

.step-header {
  text-align: center;
  margin-bottom: 2rem;
}

.step-title {
  color: #2c3e50;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 1rem 0;
}

.step-description {
  color: #6c757d;
  font-size: 1rem;
  line-height: 1.5;
  margin: 0;
}

.security-notice {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 0.5rem;
  padding: 1.5rem;
  margin-top: 1.5rem;
}

.security-header {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
  color: #2c3e50;
  font-size: 1rem;
}

.security-features {
  list-style: none;
  padding: 0;
  margin: 0;
}

.security-features li {
  display: flex;
  align-items: center;
  padding: 0.25rem 0;
  color: #495057;
  font-size: 0.9rem;
}

.cloudformation-section {
  margin: 1.5rem 0;
}

.instruction-step {
  display: flex;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 0.5rem;
  border-left: 4px solid #007bff;
}

.step-number {
  background: #007bff;
  color: white;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.9rem;
  margin-right: 1rem;
  flex-shrink: 0;
}

.step-content h4 {
  color: #2c3e50;
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
}

.step-content p {
  color: #6c757d;
  margin: 0 0 0.5rem 0;
  line-height: 1.5;
}

.instruction-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0 0;
}

.instruction-list li {
  color: #495057;
  padding: 0.25rem 0;
  position: relative;
  padding-left: 1.5rem;
}

.instruction-list li:before {
  content: '•';
  color: #007bff;
  font-weight: bold;
  position: absolute;
  left: 0;
}

.field {
  margin-bottom: 1rem;
}

.p-invalid {
  border-color: #e24c4c;
}

.p-error {
  color: #e24c4c;
  font-size: 0.875rem;
}

/* Modal Footer */
.modal-footer {
  padding: 0;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 1rem;
}

.footer-right {
  display: flex;
  gap: 0.5rem;
}

/* Textarea para Role ARN */
.role-arn-input {
  width: 100% !important;
  min-height: 120px !important;
  height: 120px !important;
  resize: vertical !important;
  font-family: 'Courier New', monospace !important;
  font-size: 0.9rem !important;
  line-height: 1.4 !important;
  padding: 1rem !important;
  box-sizing: border-box !important;
  border: 1px solid #ced4da !important;
  border-radius: 0.375rem !important;
  word-break: break-all !important;
}

.role-arn-input:focus {
  border-color: #007bff !important;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25) !important;
  outline: none !important;
}

.role-arn-input.p-invalid {
  border-color: #e24c4c !important;
}

/* Garantir que todos os textareas tenham tamanho adequado */
.connections-page .p-inputtextarea {
  min-height: 100px !important;
  resize: vertical !important;
  width: 100% !important;
}

/* Específico para o modal de onboarding */
.onboarding-step-2 .role-arn-input {
  min-height: 140px !important;
  height: 140px !important;
}

/* Modal de Edição */
.connection-info {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 0.5rem;
  padding: 1rem;
}

.info-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e9ecef;
}

.info-item:last-child {
  border-bottom: none;
}

/* Modal de Confirmação */
.confirmation-content {
  text-align: center;
  padding: 1rem;
}

.confirmation-title {
  color: #2c3e50;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 1rem 0;
}

.confirmation-message {
  color: #6c757d;
  font-size: 1.1rem;
  margin: 0 0 1.5rem 0;
}

.warning-box {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 0.5rem;
  padding: 1rem;
  text-align: left;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.warning-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0 0;
}

.warning-list li {
  color: #856404;
  padding: 0.25rem 0;
  position: relative;
  padding-left: 1rem;
}

.warning-list li:before {
  content: '•';
  color: #dc3545;
  font-weight: bold;
  position: absolute;
  left: 0;
}

/* Responsividade */
@media (max-width: 768px) {
  .connections-page {
    padding: 1rem;
  }
  
  .page-title {
    font-size: 2rem;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .instruction-step {
    flex-direction: column;
    text-align: center;
  }
  
  .step-number {
    margin: 0 auto 1rem auto;
  }
  
  .step-content {
    width: 100%;
  }
  
  .footer-content {
    flex-direction: column;
    gap: 1rem;
  }
  
  .footer-right {
    width: 100%;
    justify-content: center;
  }
}
</style>
