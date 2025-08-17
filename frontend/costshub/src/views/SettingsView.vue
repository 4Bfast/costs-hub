<template>
  <div class="settings-page">
    <div class="page-header">
      <h1 class="page-title">
        <i class="pi pi-cog mr-3"></i>
        Configurações da Organização
      </h1>
      <p class="page-description">
        Gerencie usuários, permissões e configurações da sua organização
      </p>
    </div>

    <!-- Mensagem de Erro/Sucesso -->
    <Message v-if="message" :severity="message.type" :closable="true" class="mb-4" @close="message = null">
      {{ message.text }}
    </Message>

    <!-- Card de Gestão de Usuários -->
    <Card class="mb-4">
      <template #title>
        <i class="pi pi-users mr-2"></i>
        Membros da Organização
      </template>
      
      <template #content>
        <p class="text-gray-600 mb-4">
          Gerencie os membros da sua organização. Convide novos usuários e controle o acesso aos dados de custos AWS.
        </p>
        
        <div class="flex justify-content-between align-items-center mb-4">
          <h3 class="m-0">Usuários Ativos</h3>
          <Button 
            label="Convidar Novo Membro" 
            icon="pi pi-user-plus" 
            class="p-button-sm"
            @click="openInviteModal"
          />
        </div>
        
        <!-- Loading -->
        <div v-if="isLoadingUsers" class="text-center py-4">
          <ProgressSpinner size="50" />
          <p class="mt-2 text-gray-600">Carregando usuários...</p>
        </div>
        
        <!-- Tabela de Usuários -->
        <DataTable 
          v-else
          :value="users" 
          responsiveLayout="scroll" 
          class="p-datatable-sm"
          :emptyMessage="users.length === 0 ? 'Nenhum usuário encontrado' : ''"
        >
          <Column field="email" header="Email" style="min-width: 200px">
            <template #body="slotProps">
              <div class="flex align-items-center gap-2">
                <i class="pi pi-user text-blue-500"></i>
                <span class="font-medium">{{ slotProps.data.email }}</span>
                <Tag v-if="slotProps.data.id === currentUserId" value="Você" severity="info" class="text-xs" />
              </div>
            </template>
          </Column>
          
          <Column field="status" header="Status" style="min-width: 120px">
            <template #body="slotProps">
              <Tag 
                :value="getStatusLabel(slotProps.data.status)" 
                :severity="getStatusSeverity(slotProps.data.status)"
              />
            </template>
          </Column>
          
          <Column field="role" header="Papel" style="min-width: 120px">
            <template #body="slotProps">
              <Tag 
                :value="getRoleLabel(slotProps.data.role)" 
                :severity="getRoleSeverity(slotProps.data.role)"
              />
            </template>
          </Column>
          
          <Column field="created_at" header="Membro desde" style="min-width: 150px">
            <template #body="slotProps">
              <span class="text-sm text-gray-600">
                {{ formatDate(slotProps.data.created_at) }}
              </span>
            </template>
          </Column>
          
          <Column header="Ações" style="min-width: 100px">
            <template #body="slotProps">
              <div class="flex gap-2">
                <Button 
                  v-if="slotProps.data.id !== currentUserId"
                  icon="pi pi-trash" 
                  class="p-button-sm p-button-text p-button-danger"
                  @click="confirmRemoveUser(slotProps.data)"
                  v-tooltip="'Remover usuário'"
                />
                <span v-else class="text-gray-400 text-sm">-</span>
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Modal de Convite -->
    <Dialog 
      v-model:visible="isInviteModalVisible" 
      modal 
      header="Convidar Novo Membro"
      :style="{ width: '450px' }"
      :breakpoints="{ '960px': '75vw', '641px': '90vw' }"
    >
      <form @submit.prevent="handleSendInvite" class="p-fluid">
        <div class="field mb-4">
          <label for="invite-email" class="font-semibold mb-2 block">Email do novo membro</label>
          <InputText 
            id="invite-email" 
            v-model="inviteForm.email" 
            placeholder="exemplo@empresa.com"
            type="email"
            required 
            :class="{ 'p-invalid': inviteForm.emailError }"
          />
          <small v-if="inviteForm.emailError" class="p-error">{{ inviteForm.emailError }}</small>
          <small class="text-gray-600 mt-1 block">
            <i class="pi pi-info-circle mr-1"></i>
            O novo membro receberá um email com instruções para ativar a conta.
          </small>
        </div>
      </form>
      
      <template #footer>
        <Button 
          label="Cancelar" 
          icon="pi pi-times" 
          severity="secondary"
          @click="closeInviteModal" 
        />
        <Button 
          label="Enviar Convite" 
          icon="pi pi-send"
          :loading="isSubmitting"
          @click="handleSendInvite" 
        />
      </template>
    </Dialog>

    <!-- Dialog de Confirmação de Remoção -->
    <Dialog 
      v-model:visible="isRemoveModalVisible" 
      modal 
      header="Confirmar Remoção"
      :style="{ width: '450px' }"
    >
      <div class="confirmation-content">
        <i class="pi pi-exclamation-triangle text-orange-500 text-3xl mb-3"></i>
        <p class="mb-3">
          Tem certeza que deseja remover <strong>{{ userToRemove?.email }}</strong> da organização?
        </p>
        <p class="text-sm text-gray-600">
          Esta ação não pode ser desfeita. O usuário perderá acesso imediato a todos os dados da organização.
        </p>
      </div>
      
      <template #footer>
        <Button 
          label="Cancelar" 
          icon="pi pi-times" 
          severity="secondary"
          @click="closeRemoveModal" 
        />
        <Button 
          label="Remover" 
          icon="pi pi-trash"
          severity="danger"
          :loading="isSubmitting"
          @click="handleRemoveUser" 
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { apiService } from '@/services/api';

// Componentes PrimeVue
import Card from 'primevue/card';
import Button from 'primevue/button';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Tag from 'primevue/tag';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';
import { useToast } from 'primevue/usetoast';

// Estado
const authStore = useAuthStore();
const toast = useToast();

const users = ref([]);
const isLoadingUsers = ref(true);
const message = ref(null);
const currentUserId = ref(null);

// Modal de convite
const isInviteModalVisible = ref(false);
const inviteForm = ref({
  email: '',
  emailError: null
});

// Modal de remoção
const isRemoveModalVisible = ref(false);
const userToRemove = ref(null);

const isSubmitting = ref(false);

// Funções
async function fetchUsers() {
  try {
    isLoadingUsers.value = true;
    const response = await apiService.get('/users');
    users.value = response;
    
    // Obter ID do usuário atual
    const currentUser = authStore.user;
    if (currentUser) {
      currentUserId.value = currentUser.id;
    }
  } catch (error) {
    console.error('Erro ao buscar usuários:', error);
    message.value = {
      type: 'error',
      text: 'Erro ao carregar usuários da organização'
    };
  } finally {
    isLoadingUsers.value = false;
  }
}

function openInviteModal() {
  inviteForm.value = {
    email: '',
    emailError: null
  };
  isInviteModalVisible.value = true;
}

function closeInviteModal() {
  isInviteModalVisible.value = false;
  inviteForm.value = {
    email: '',
    emailError: null
  };
}

async function handleSendInvite() {
  try {
    // Validação
    inviteForm.value.emailError = null;
    
    if (!inviteForm.value.email) {
      inviteForm.value.emailError = 'Email é obrigatório';
      return;
    }
    
    if (!isValidEmail(inviteForm.value.email)) {
      inviteForm.value.emailError = 'Email inválido';
      return;
    }
    
    isSubmitting.value = true;
    
    await apiService.post('/users/invite', {
      email: inviteForm.value.email.toLowerCase().trim()
    });
    
    toast.add({
      severity: 'success',
      summary: 'Convite Enviado',
      detail: `Convite enviado para ${inviteForm.value.email}`,
      life: 5000
    });
    
    closeInviteModal();
    await fetchUsers(); // Recarregar lista
    
  } catch (error) {
    console.error('Erro ao enviar convite:', error);
    
    if (error.response?.data?.error) {
      inviteForm.value.emailError = error.response.data.error;
    } else {
      toast.add({
        severity: 'error',
        summary: 'Erro',
        detail: 'Não foi possível enviar o convite',
        life: 5000
      });
    }
  } finally {
    isSubmitting.value = false;
  }
}

function confirmRemoveUser(user) {
  userToRemove.value = user;
  isRemoveModalVisible.value = true;
}

function closeRemoveModal() {
  isRemoveModalVisible.value = false;
  userToRemove.value = null;
}

async function handleRemoveUser() {
  try {
    isSubmitting.value = true;
    
    await apiService.delete(`/users/${userToRemove.value.id}`);
    
    toast.add({
      severity: 'success',
      summary: 'Usuário Removido',
      detail: `${userToRemove.value.email} foi removido da organização`,
      life: 5000
    });
    
    closeRemoveModal();
    await fetchUsers(); // Recarregar lista
    
  } catch (error) {
    console.error('Erro ao remover usuário:', error);
    
    toast.add({
      severity: 'error',
      summary: 'Erro',
      detail: error.response?.data?.error || 'Não foi possível remover o usuário',
      life: 5000
    });
  } finally {
    isSubmitting.value = false;
  }
}

// Funções de utilidade
function getStatusLabel(status) {
  const labels = {
    'ACTIVE': 'Ativo',
    'PENDING_INVITE': 'Convite Pendente'
  };
  return labels[status] || status;
}

function getStatusSeverity(status) {
  const severities = {
    'ACTIVE': 'success',
    'PENDING_INVITE': 'warning'
  };
  return severities[status] || 'info';
}

function getRoleLabel(role) {
  const labels = {
    'ADMIN': 'Administrador',
    'MEMBER': 'Membro'
  };
  return labels[role] || role;
}

function getRoleSeverity(role) {
  const severities = {
    'ADMIN': 'danger',
    'MEMBER': 'info'
  };
  return severities[role] || 'info';
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('pt-BR');
}

function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// Lifecycle
onMounted(() => {
  fetchUsers();
});
</script>

<style scoped>
.settings-page {
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

.confirmation-content {
  text-align: center;
  padding: 1rem;
}

/* Responsividade */
@media (max-width: 768px) {
  .settings-page {
    padding: 1rem;
  }
  
  .page-title {
    font-size: 2rem;
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>
