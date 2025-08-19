<template>
  <div class="accept-invite-page">
    <div class="invite-container">
      <!-- Loading -->
      <div v-if="isLoading" class="loading-section">
        <ProgressSpinner size="50" />
        <h2 class="loading-title">Verificando convite...</h2>
        <p class="loading-description">Aguarde enquanto validamos seu convite.</p>
      </div>

      <!-- Erro -->
      <div v-else-if="error" class="error-section">
        <i class="pi pi-exclamation-triangle error-icon"></i>
        <h2 class="error-title">Convite Inválido</h2>
        <p class="error-description">{{ error }}</p>
        <div class="error-actions">
          <Button 
            label="Ir para Login" 
            icon="pi pi-sign-in"
            @click="goToLogin"
          />
        </div>
      </div>

      <!-- Formulário de Aceite -->
      <div v-else class="invite-form-section">
        <div class="welcome-header">
          <i class="pi pi-user-plus welcome-icon"></i>
          <h1 class="welcome-title">Bem-vindo ao CostsHub!</h1>
          <p class="welcome-description">
            Você foi convidado para fazer parte da organização 
            <strong>{{ invitationData.organization_name }}</strong>
          </p>
          <div class="invited-email">
            <i class="pi pi-envelope mr-2"></i>
            {{ invitationData.email }}
          </div>
        </div>

        <Card class="password-card">
          <template #title>
            <i class="pi pi-key mr-2"></i>
            Crie sua senha
          </template>
          
          <template #content>
            <form @submit.prevent="handleAcceptInvite" class="p-fluid">
              <Message v-if="formError" severity="error" :closable="true" class="mb-4" @close="formError = null">
                {{ formError }}
              </Message>

              <div class="field mb-4">
                <label for="password" class="font-semibold mb-2 block">Nova Senha</label>
                <Password 
                  id="password"
                  v-model="form.password" 
                  placeholder="Digite sua senha"
                  :feedback="true"
                  toggleMask
                  required
                  :class="{ 'p-invalid': form.passwordError }"
                />
                <small v-if="form.passwordError" class="p-error">{{ form.passwordError }}</small>
                <small class="text-gray-600 mt-1 block">
                  <i class="pi pi-info-circle mr-1"></i>
                  A senha deve ter pelo menos 6 caracteres.
                </small>
              </div>

              <div class="field mb-4">
                <label for="confirmPassword" class="font-semibold mb-2 block">Confirmar Senha</label>
                <Password 
                  id="confirmPassword"
                  v-model="form.confirmPassword" 
                  placeholder="Confirme sua senha"
                  :feedback="false"
                  toggleMask
                  required
                  :class="{ 'p-invalid': form.confirmPasswordError }"
                />
                <small v-if="form.confirmPasswordError" class="p-error">{{ form.confirmPasswordError }}</small>
              </div>

              <div class="form-actions">
                <Button 
                  type="submit"
                  label="Ativar Conta" 
                  icon="pi pi-check"
                  :loading="isSubmitting"
                  class="w-full"
                  size="large"
                />
              </div>
            </form>
          </template>
        </Card>

        <div class="help-section">
          <p class="help-text">
            <i class="pi pi-question-circle mr-2"></i>
            Precisa de ajuda? Entre em contato com o administrador da sua organização.
          </p>
        </div>
      </div>

      <!-- Sucesso -->
      <div v-if="isSuccess" class="success-section">
        <i class="pi pi-check-circle success-icon"></i>
        <h2 class="success-title">Conta Ativada com Sucesso!</h2>
        <p class="success-description">
          Sua conta foi ativada e você já pode acessar o CostsHub.
        </p>
        <div class="success-actions">
          <Button 
            label="Fazer Login" 
            icon="pi pi-sign-in"
            @click="goToLogin"
            size="large"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { apiService } from '@/services/api';

// Componentes PrimeVue
import Card from 'primevue/card';
import Button from 'primevue/button';
import Password from 'primevue/password';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';
import { useToast } from 'primevue/usetoast';

// Estado
const route = useRoute();
const router = useRouter();
const toast = useToast();

const isLoading = ref(true);
const error = ref(null);
const invitationData = ref(null);
const isSubmitting = ref(false);
const isSuccess = ref(false);
const formError = ref(null);

const form = ref({
  password: '',
  confirmPassword: '',
  passwordError: null,
  confirmPasswordError: null
});

// Funções
async function verifyInvitation() {
  try {
    const token = route.query.token;
    
    if (!token) {
      error.value = 'Token de convite não encontrado na URL.';
      return;
    }
    
    const response = await apiService.verifyInvitation(token);
    invitationData.value = response;
    
  } catch (err) {
    console.error('Erro ao verificar convite:', err);
    error.value = err.error || 'Token inválido ou expirado.';
  } finally {
    isLoading.value = false;
  }
}

async function handleAcceptInvite() {
  try {
    // Reset errors
    form.value.passwordError = null;
    form.value.confirmPasswordError = null;
    formError.value = null;
    
    // Validações
    if (!form.value.password) {
      form.value.passwordError = 'Senha é obrigatória';
      return;
    }
    
    if (form.value.password.length < 6) {
      form.value.passwordError = 'Senha deve ter pelo menos 6 caracteres';
      return;
    }
    
    if (!form.value.confirmPassword) {
      form.value.confirmPasswordError = 'Confirmação de senha é obrigatória';
      return;
    }
    
    if (form.value.password !== form.value.confirmPassword) {
      form.value.confirmPasswordError = 'Senhas não coincidem';
      return;
    }
    
    isSubmitting.value = true;
    
    const token = route.query.token;
    await apiService.acceptInvitation(token, form.value.password);
    
    isSuccess.value = true;
    
    toast.add({
      severity: 'success',
      summary: 'Conta Ativada',
      detail: 'Sua conta foi ativada com sucesso!',
      life: 5000
    });
    
    // Redirecionar para login após 3 segundos
    setTimeout(() => {
      goToLogin();
    }, 3000);
    
  } catch (err) {
    console.error('Erro ao aceitar convite:', err);
    formError.value = err.error || 'Erro ao ativar conta. Tente novamente.';
  } finally {
    isSubmitting.value = false;
  }
}

function goToLogin() {
  router.push('/login');
}

// Lifecycle
onMounted(() => {
  verifyInvitation();
});
</script>

<style scoped>
.accept-invite-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.invite-container {
  width: 100%;
  max-width: 500px;
}

/* Loading */
.loading-section {
  background: white;
  border-radius: 1rem;
  padding: 3rem;
  text-align: center;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.loading-title {
  color: #2c3e50;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 1rem 0 0.5rem 0;
}

.loading-description {
  color: #6c757d;
  margin: 0;
}

/* Error */
.error-section {
  background: white;
  border-radius: 1rem;
  padding: 3rem;
  text-align: center;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.error-icon {
  font-size: 4rem;
  color: #dc3545;
  margin-bottom: 1rem;
}

.error-title {
  color: #2c3e50;
  font-size: 1.8rem;
  font-weight: 600;
  margin: 0 0 1rem 0;
}

.error-description {
  color: #6c757d;
  font-size: 1.1rem;
  margin: 0 0 2rem 0;
}

.error-actions {
  display: flex;
  justify-content: center;
}

/* Success */
.success-section {
  background: white;
  border-radius: 1rem;
  padding: 3rem;
  text-align: center;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.success-icon {
  font-size: 4rem;
  color: #28a745;
  margin-bottom: 1rem;
}

.success-title {
  color: #2c3e50;
  font-size: 1.8rem;
  font-weight: 600;
  margin: 0 0 1rem 0;
}

.success-description {
  color: #6c757d;
  font-size: 1.1rem;
  margin: 0 0 2rem 0;
}

.success-actions {
  display: flex;
  justify-content: center;
}

/* Form */
.invite-form-section {
  background: white;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.welcome-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2.5rem;
  text-align: center;
}

.welcome-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.welcome-title {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
}

.welcome-description {
  font-size: 1.1rem;
  margin: 0 0 1.5rem 0;
  opacity: 0.9;
}

.invited-email {
  background: rgba(255, 255, 255, 0.2);
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
}

.password-card {
  margin: 0;
  border-radius: 0;
  box-shadow: none;
}

.form-actions {
  margin-top: 1.5rem;
}

.help-section {
  padding: 1.5rem 2.5rem;
  background: #f8f9fa;
  text-align: center;
}

.help-text {
  color: #6c757d;
  font-size: 0.9rem;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Responsividade */
@media (max-width: 768px) {
  .accept-invite-page {
    padding: 1rem;
  }
  
  .welcome-header {
    padding: 2rem 1.5rem;
  }
  
  .welcome-title {
    font-size: 1.5rem;
  }
  
  .welcome-description {
    font-size: 1rem;
  }
  
  .help-text {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>
