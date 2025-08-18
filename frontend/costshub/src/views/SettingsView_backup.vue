<template>
  <div class="settings-page p-6 max-w-7xl mx-auto">
    <!-- Cabeçalho da página com melhor espaçamento -->
    <div class="page-header mb-8">
      <h1 class="page-title text-3xl font-bold text-gray-900 mb-2">
        <i class="pi pi-cog mr-4"></i>
        Configurações da Organização
      </h1>
      <p class="page-description text-gray-600">
        Gerencie usuários, permissões e configurações da sua organização
      </p>
    </div>

    <!-- Mensagem de Erro/Sucesso -->
    <Message v-if="message" :severity="message.type" :closable="true" class="mb-6" @close="message = null">
      {{ message.text }}
    </Message>

    <!-- Card de Gestão de Usuários -->
    <Card class="mb-8">
      <template #title>
        <div class="flex items-center text-blue-600">
          <i class="pi pi-users mr-4 text-xl"></i>
          <span class="text-xl font-semibold">Membros da Organização</span>
        </div>
      </template>
      
      <template #content>
        <div class="space-y-6">
          <p class="text-gray-600">
            Gerencie os membros da sua organização. Convide novos usuários e controle o acesso aos dados de custos AWS.
          </p>
          
          <!-- Botão Convidar com espaçamento adequado -->
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-semibold text-gray-800 m-0">Usuários Ativos</h3>
            <Button 
              label="Convidar Novo Membro" 
              icon="pi pi-user-plus" 
              class="p-button-primary"
              @click="openInviteModal"
            />
          </div>
          <!-- Container da tabela com melhor espaçamento -->
          <div class="border border-gray-200 rounded-lg overflow-hidden bg-white">
            <!-- Loading -->
            <div v-if="isLoadingUsers" class="text-center py-8">
              <ProgressSpinner size="50" />
              <p class="mt-4 text-gray-600">Carregando usuários...</p>
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
          
          <Column field="role" header="Papel" style="min-width: 120px">
            <template #body="slotProps">
              <Tag 
                :value="getRoleLabel(slotProps.data.role)" 
                :severity="getRoleSeverity(slotProps.data.role)"
              />
            </template>
          </Column>
          
          <Column field="status" header="Status" style="min-width: 120px">
            <template #body="slotProps">
              <Tag 
                v-if="slotProps.data.status === 'ACTIVE'" 
                value="Ativo" 
                severity="success" 
                class="text-xs"
              />
              <Tag 
                v-else-if="slotProps.data.status === 'PENDING_INVITE'" 
                value="Convite Pendente" 
                severity="warning" 
                class="text-xs"
              />
              <Tag 
                v-else 
                :value="slotProps.data.status" 
                severity="info" 
                class="text-xs"
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
          
          <Column header="Ações" style="min-width: 200px">
            <template #body="slotProps">
              <div class="flex gap-2">
                <!-- Botão de alterar role (não para o próprio usuário e apenas para usuários ativos) -->
                <Button 
                  v-if="slotProps.data.id !== currentUserId && slotProps.data.status === 'ACTIVE'"
                  :icon="slotProps.data.role === 'ADMIN' ? 'pi pi-user-minus' : 'pi pi-user-plus'" 
                  :class="slotProps.data.role === 'ADMIN' ? 'p-button-sm p-button-text p-button-warning' : 'p-button-sm p-button-text p-button-success'"
                  :loading="isChangingRole === slotProps.data.id"
                  @click="confirmChangeRole(slotProps.data)"
                  :v-tooltip="slotProps.data.role === 'ADMIN' ? 'Remover admin' : 'Tornar admin'"
                />
                
                <!-- Botão de reenvio para usuários pendentes -->
                <Button 
                  v-if="slotProps.data.status === 'PENDING_INVITE'"
                  icon="pi pi-send" 
                  class="p-button-sm p-button-text p-button-info"
                  :loading="isResendingInvite === slotProps.data.id"
                  @click="resendInvite(slotProps.data)"
                  v-tooltip="'Reenviar convite'"
                />
                
                <!-- Botão de remoção (não para o próprio usuário) -->
                <Button 
                  v-if="slotProps.data.id !== currentUserId"
                  icon="pi pi-trash" 
                  class="p-button-sm p-button-text p-button-danger"
                  @click="confirmRemoveUser(slotProps.data)"
                  v-tooltip="'Remover usuário'"
                />
                <span v-else-if="slotProps.data.status === 'ACTIVE'" class="text-gray-400 text-sm">-</span>
              </div>
            </template>
          </Column>
        </DataTable>
          </div>
        </div>
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

    <!-- Modal de Alteração de Role -->
    <Dialog 
      v-model:visible="isRoleModalVisible" 
      modal 
      header="Alterar Permissões"
      :style="{ width: '450px' }"
    >
      <div class="confirmation-content">
        <i class="pi pi-user-edit text-blue-500 text-3xl mb-3"></i>
        <p class="mb-3">
          Alterar permissões de <strong>{{ userToChangeRole?.email }}</strong>?
        </p>
        <p class="text-sm text-gray-600 mb-3">
          <span v-if="userToChangeRole?.role === 'ADMIN'">
            O usuário será <strong>rebaixado para Membro</strong> e perderá acesso às configurações administrativas.
          </span>
          <span v-else>
            O usuário será <strong>promovido para Administrador</strong> e terá acesso total às configurações da organização.
          </span>
        </p>
        <div class="role-change-summary p-3 bg-gray-50 rounded">
          <div class="flex justify-between items-center">
            <span>Role atual:</span>
            <Tag 
              :value="getRoleLabel(userToChangeRole?.role)" 
              :severity="getRoleSeverity(userToChangeRole?.role)"
              class="text-xs"
            />
          </div>
          <div class="flex justify-between items-center mt-2">
            <span>Nova role:</span>
            <Tag 
              :value="getRoleLabel(userToChangeRole?.role === 'ADMIN' ? 'MEMBER' : 'ADMIN')" 
              :severity="getRoleSeverity(userToChangeRole?.role === 'ADMIN' ? 'MEMBER' : 'ADMIN')"
              class="text-xs"
            />
          </div>
        </div>
      </div>
      
      <template #footer>
        <Button 
          label="Cancelar" 
          icon="pi pi-times" 
          severity="secondary"
          @click="closeRoleModal" 
        />
        <Button 
          :label="userToChangeRole?.role === 'ADMIN' ? 'Rebaixar' : 'Promover'"
          :icon="userToChangeRole?.role === 'ADMIN' ? 'pi pi-user-minus' : 'pi pi-user-plus'"
          :severity="userToChangeRole?.role === 'ADMIN' ? 'warning' : 'success'"
          :loading="isSubmitting"
          @click="handleChangeRole" 
        />
      </template>
    </Dialog>

    <!-- Seção Zona de Perigo com melhor espaçamento -->
    <Card class="border-red-200">
      <template #header>
        <div class="flex items-center p-6 pb-0 text-red-600">
          <i class="pi pi-exclamation-triangle mr-4 text-xl"></i>
          <h2 class="text-xl font-semibold">Zona de Perigo</h2>
        </div>
      </template>
      
      <template #content>
        <div class="px-6 pb-6 space-y-6">
          <Message severity="warn" :closable="false">
            <div>
              <p class="font-semibold mb-1">Atenção: Ações irreversíveis</p>
              <p class="text-sm">As ações nesta seção podem afetar permanentemente sua organização e dados.</p>
            </div>
          </Message>
          
          <div class="border border-red-200 rounded-lg p-6 bg-red-50">
            <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
              <div class="flex-1">
                <h3 class="text-lg font-semibold text-red-800 mb-3 flex items-center">
                  <i class="pi pi-trash mr-3"></i>
                  Deletar Organização
                </h3>
                <p class="text-sm text-red-700 mb-4">
                  Remove permanentemente sua organização da plataforma. Esta ação irá:
                </p>
                <ul class="text-sm text-red-700 space-y-2 mb-6">
                  <li class="flex items-center">
                    <i class="pi pi-times-circle mr-3 text-red-500"></i>
                    Desativar todos os usuários imediatamente
                  </li>
                  <li class="flex items-center">
                    <i class="pi pi-times-circle mr-3 text-red-500"></i>
                    Parar o processamento de custos
                  </li>
                  <li class="flex items-center">
                    <i class="pi pi-times-circle mr-3 text-red-500"></i>
                    Desabilitar conexões AWS
                  </li>
                  <li class="flex items-center">
                    <i class="pi pi-times-circle mr-3 text-red-500"></i>
                    Suspender alarmes e notificações
                  </li>
                  <li class="flex items-center">
                    <i class="pi pi-clock mr-3 text-orange-500"></i>
                    Manter dados por 30 dias para recuperação
                  </li>
                </ul>
                <div class="bg-red-100 border border-red-300 rounded-lg p-3">
                  <p class="text-xs text-red-800 font-medium flex items-center">
                    <i class="pi pi-info-circle mr-3"></i>
                    Apenas o suporte pode recuperar a organização nos primeiros 30 dias
                  </p>
                </div>
              </div>
              <div class="flex-shrink-0">
                <Button 
                  label="Deletar Organização" 
                  icon="pi pi-trash"
                  severity="danger"
                  size="large"
                  class="w-full lg:w-auto"
                  @click="openDeleteOrganizationModal"
                />
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Modais de Exclusão de Organização -->
    
    <!-- Modal 1: Aviso Inicial -->
    <Dialog 
      v-model:visible="isDeleteStep1Visible" 
      modal 
      header="⚠️ ATENÇÃO: Deletar Organização"
      :style="{ width: '500px' }"
    >
      <div class="space-y-4">
        <Message severity="error" :closable="false">
          <p class="font-semibold">Esta ação irá:</p>
        </Message>
        
        <ul class="space-y-2 text-sm">
          <li class="flex items-center">
            <i class="pi pi-times-circle text-red-500 mr-2"></i>
            Desativar todos os usuários
          </li>
          <li class="flex items-center">
            <i class="pi pi-times-circle text-red-500 mr-2"></i>
            Parar processamento de custos
          </li>
          <li class="flex items-center">
            <i class="pi pi-times-circle text-red-500 mr-2"></i>
            Desabilitar conexões AWS
          </li>
          <li class="flex items-center">
            <i class="pi pi-times-circle text-red-500 mr-2"></i>
            Suspender alarmes e notificações
          </li>
        </ul>
        
        <Message severity="info" :closable="false">
          <p class="text-sm">
            <strong>Os dados serão mantidos por 30 dias para recuperação.</strong><br>
            Apenas o suporte pode reativar a organização neste período.
          </p>
        </Message>
      </div>
      
      <template #footer>
        <Button 
          label="Cancelar" 
          icon="pi pi-times" 
          severity="secondary"
          @click="closeDeleteModals" 
        />
        <Button 
          label="Continuar" 
          icon="pi pi-arrow-right"
          severity="danger"
          @click="goToDeleteStep2" 
        />
      </template>
    </Dialog>

    <!-- Modal 2: Confirmação com Senha -->
    <Dialog 
      v-model:visible="isDeleteStep2Visible" 
      modal 
      header="🔐 Confirme sua Identidade"
      :style="{ width: '450px' }"
    >
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-2">
            Para continuar, digite sua senha:
          </label>
          <InputText 
            v-model="deleteForm.password"
            type="password"
            placeholder="Sua senha"
            class="w-full"
            :class="{ 'p-invalid': deleteForm.errors.password }"
          />
          <small v-if="deleteForm.errors.password" class="p-error">
            {{ deleteForm.errors.password }}
          </small>
        </div>
        
        <div>
          <label class="block text-sm font-medium mb-2">
            Digite "DELETAR" para confirmar:
          </label>
          <InputText 
            v-model="deleteForm.confirmationText"
            placeholder="DELETAR"
            class="w-full"
            :class="{ 'p-invalid': deleteForm.errors.confirmationText }"
          />
          <small v-if="deleteForm.errors.confirmationText" class="p-error">
            {{ deleteForm.errors.confirmationText }}
          </small>
        </div>
        
        <div>
          <label class="block text-sm font-medium mb-2">
            Motivo da exclusão (opcional):
          </label>
          <InputText 
            v-model="deleteForm.reason"
            placeholder="Ex: Não precisamos mais da plataforma"
            class="w-full"
          />
        </div>
      </div>
      
      <template #footer>
        <Button 
          label="Voltar" 
          icon="pi pi-arrow-left" 
          severity="secondary"
          @click="goBackToDeleteStep1" 
        />
        <Button 
          label="Confirmar Exclusão" 
          icon="pi pi-exclamation-triangle"
          severity="danger"
          :disabled="!canProceedToStep3"
          @click="goToDeleteStep3" 
        />
      </template>
    </Dialog>

    <!-- Modal 3: Confirmação Final -->
    <Dialog 
      v-model:visible="isDeleteStep3Visible" 
      modal 
      header="🚨 ÚLTIMA CONFIRMAÇÃO"
      :style="{ width: '500px' }"
    >
      <div class="space-y-4">
        <Message severity="error" :closable="false">
          <p class="font-semibold">Você está prestes a deletar a organização:</p>
        </Message>
        
        <div class="bg-gray-50 p-4 rounded border">
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="font-medium">Nome:</span>
              <span>{{ authStore.user?.organization?.name || 'N/A' }}</span>
            </div>
            <div class="flex justify-between">
              <span class="font-medium">Usuários:</span>
              <span>{{ users.length }} usuários serão desativados</span>
            </div>
            <div class="flex justify-between">
              <span class="font-medium">Dados:</span>
              <span>Mantidos por 30 dias</span>
            </div>
          </div>
        </div>
        
        <Message severity="warn" :closable="false">
          <p class="text-sm">
            <strong>Esta ação não pode ser desfeita pelo usuário.</strong><br>
            Apenas o suporte pode recuperar nos próximos 30 dias.
          </p>
        </Message>
      </div>
      
      <template #footer>
        <Button 
          label="Cancelar" 
          icon="pi pi-times" 
          severity="secondary"
          @click="closeDeleteModals" 
        />
        <Button 
          label="DELETAR ORGANIZAÇÃO" 
          icon="pi pi-trash"
          severity="danger"
          :loading="isSubmitting"
          @click="handleDeleteOrganization" 
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
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

// Modal de alteração de role
const isRoleModalVisible = ref(false);
const userToChangeRole = ref(null);
const isChangingRole = ref(null); // ID do usuário para quem está alterando role

// Modais de exclusão de organização
const isDeleteStep1Visible = ref(false);
const isDeleteStep2Visible = ref(false);
const isDeleteStep3Visible = ref(false);
const deleteForm = ref({
  password: '',
  confirmationText: '',
  reason: '',
  errors: {}
});

const isSubmitting = ref(false);
const isResendingInvite = ref(null); // ID do usuário para quem está reenviando

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

// Funções para alteração de role
function confirmChangeRole(user) {
  userToChangeRole.value = user;
  isRoleModalVisible.value = true;
}

function closeRoleModal() {
  isRoleModalVisible.value = false;
  userToChangeRole.value = null;
}

async function handleChangeRole() {
  try {
    isSubmitting.value = true;
    
    const newRole = userToChangeRole.value.role === 'ADMIN' ? 'MEMBER' : 'ADMIN';
    
    await apiService.updateUserRole(userToChangeRole.value.id, newRole);
    
    toast.add({
      severity: 'success',
      summary: 'Role Alterada',
      detail: `${userToChangeRole.value.email} agora é ${newRole === 'ADMIN' ? 'Administrador' : 'Membro'}`,
      life: 5000
    });
    
    closeRoleModal();
    await fetchUsers(); // Recarregar lista
    
  } catch (error) {
    console.error('Erro ao alterar role:', error);
    
    toast.add({
      severity: 'error',
      summary: 'Erro',
      detail: error.response?.data?.error || 'Não foi possível alterar a role do usuário',
      life: 5000
    });
  } finally {
    isSubmitting.value = false;
  }
}

// Funções para exclusão de organização
function openDeleteOrganizationModal() {
  // Resetar formulário
  deleteForm.value = {
    password: '',
    confirmationText: '',
    reason: '',
    errors: {}
  };
  
  isDeleteStep1Visible.value = true;
}

function closeDeleteModals() {
  isDeleteStep1Visible.value = false;
  isDeleteStep2Visible.value = false;
  isDeleteStep3Visible.value = false;
  
  // Resetar formulário
  deleteForm.value = {
    password: '',
    confirmationText: '',
    reason: '',
    errors: {}
  };
}

function goToDeleteStep2() {
  isDeleteStep1Visible.value = false;
  isDeleteStep2Visible.value = true;
}

function goBackToDeleteStep1() {
  isDeleteStep2Visible.value = false;
  isDeleteStep1Visible.value = true;
}

function goToDeleteStep3() {
  // Validar campos
  const errors = {};
  
  if (!deleteForm.value.password) {
    errors.password = 'Senha é obrigatória';
  }
  
  if (deleteForm.value.confirmationText !== 'DELETAR') {
    errors.confirmationText = 'Digite "DELETAR" para confirmar';
  }
  
  deleteForm.value.errors = errors;
  
  if (Object.keys(errors).length === 0) {
    isDeleteStep2Visible.value = false;
    isDeleteStep3Visible.value = true;
  }
}

// Computed para habilitar botão do step 2
const canProceedToStep3 = computed(() => {
  return deleteForm.value.password && 
         deleteForm.value.confirmationText === 'DELETAR';
});

async function handleDeleteOrganization() {
  try {
    isSubmitting.value = true;
    
    const response = await apiService.deleteOrganization(
      deleteForm.value.password,
      deleteForm.value.confirmationText,
      deleteForm.value.reason
    );
    
    const result = await response.json();
    
    toast.add({
      severity: 'success',
      summary: 'Organização Deletada',
      detail: 'Sua organização foi marcada para exclusão. Dados mantidos por 30 dias.',
      life: 10000
    });
    
    closeDeleteModals();
    
    // Redirecionar para página de confirmação ou logout
    setTimeout(() => {
      authStore.logout();
      window.location.href = '/';
    }, 3000);
    
  } catch (error) {
    console.error('Erro ao deletar organização:', error);
    
    const errorData = await error.response?.json();
    
    toast.add({
      severity: 'error',
      summary: 'Erro',
      detail: errorData?.error || 'Não foi possível deletar a organização',
      life: 5000
    });
  } finally {
    isSubmitting.value = false;
  }
}

// Função para reenviar convite
async function resendInvite(user) {
  try {
    isResendingInvite.value = user.id;
    
    await apiService.post(`/users/${user.id}/resend-invite`);
    
    toast.add({
      severity: 'success',
      summary: 'Convite Reenviado',
      detail: `Novo convite enviado para ${user.email}`,
      life: 5000
    });
    
  } catch (error) {
    console.error('Erro ao reenviar convite:', error);
    
    toast.add({
      severity: 'error',
      summary: 'Erro',
      detail: error.response?.data?.error || 'Não foi possível reenviar o convite',
      life: 5000
    });
  } finally {
    isResendingInvite.value = null;
  }
}

// Funções de utilidade
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
