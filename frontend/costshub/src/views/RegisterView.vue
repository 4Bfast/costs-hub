<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h1>Criar Conta</h1>
        <p>Crie sua organização e comece a usar o CostsHub</p>
      </div>
      
      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label for="orgName">Nome da Organização</label>
          <InputText 
            id="orgName" 
            v-model="orgName" 
            placeholder="Digite o nome da sua organização"
            :disabled="isLoading"
            required 
          />
        </div>
        
        <div class="form-group">
          <label for="email">Email</label>
          <InputText 
            id="email" 
            v-model="email" 
            type="email"
            placeholder="Digite seu email"
            :disabled="isLoading"
            required 
          />
        </div>
        
        <div class="form-group">
          <label for="password">Senha</label>
          <Password 
            id="password" 
            v-model="password" 
            placeholder="Digite sua senha"
            :disabled="isLoading"
            :feedback="true"
            toggleMask
            required 
          />
        </div>
        
        <div class="form-group">
          <label for="confirmPassword">Confirmar Senha</label>
          <Password 
            id="confirmPassword" 
            v-model="confirmPassword" 
            placeholder="Confirme sua senha"
            :disabled="isLoading"
            :feedback="false"
            toggleMask
            required 
          />
        </div>
        
        <Message v-if="errorMessage" severity="error" :closable="false" class="mb-3">
          {{ errorMessage }}
        </Message>
        
        <Message v-if="successMessage" severity="success" :closable="false" class="mb-3">
          {{ successMessage }}
        </Message>
        
        <Button 
          type="submit" 
          label="Criar Conta"
          :loading="isLoading"
          :disabled="isLoading"
          class="register-button"
        />
        
        <div class="login-link">
          <RouterLink to="/login">
            Já tem uma conta? Faça login aqui.
          </RouterLink>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'

// Router e Store
const router = useRouter()
const authStore = useAuthStore()

// Estado reativo
const orgName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

// Função principal de registro
async function handleRegister() {
  // Limpar mensagens anteriores
  errorMessage.value = ''
  successMessage.value = ''
  
  // Validação client-side
  if (password.value !== confirmPassword.value) {
    errorMessage.value = 'As senhas não coincidem. Por favor, verifique e tente novamente.'
    return
  }
  
  if (password.value.length < 6) {
    errorMessage.value = 'A senha deve ter pelo menos 6 caracteres.'
    return
  }
  
  isLoading.value = true
  
  try {
    // Chamada à store
    await authStore.register({
      org_name: orgName.value,
      email: email.value,
      password: password.value
    })
    
    // Sucesso
    successMessage.value = 'Conta criada com sucesso! Redirecionando para verificação de email...'
    
    // Redirecionamento após 2 segundos para página de verificação
    setTimeout(() => {
      router.push({
        name: 'verify-email',
        query: { email: email.value }
      })
    }, 2000)
    
  } catch (error) {
    console.error('Erro no registro:', error)
    // Captura a mensagem de erro corretamente
    if (error.message) {
      errorMessage.value = error.message
    } else if (typeof error === 'string') {
      errorMessage.value = error
    } else {
      errorMessage.value = 'Erro ao criar conta. Tente novamente.'
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
}

.register-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  padding: 3rem;
  width: 100%;
  max-width: 450px;
}

.register-header {
  text-align: center;
  margin-bottom: 2rem;
}

.register-header h1 {
  color: #333;
  margin: 0 0 0.5rem 0;
  font-size: 2rem;
  font-weight: 600;
}

.register-header p {
  color: #666;
  margin: 0;
  font-size: 1rem;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.register-button {
  margin-top: 1rem;
  padding: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
}

.login-link {
  text-align: center;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}

.login-link a {
  color: #007BFF;
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.2s;
}

.login-link a:hover {
  color: #0056b3;
  text-decoration: underline;
}

.mb-3 {
  margin-bottom: 1rem;
}

/* Responsividade */
@media (max-width: 768px) {
  .register-container {
    padding: 1rem;
  }
  
  .register-card {
    padding: 2rem;
  }
  
  .register-header h1 {
    font-size: 1.5rem;
  }
}
</style>
