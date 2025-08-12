<template>
  <div class="verification-container">
    <div class="verification-card">
      <div class="verification-header">
        <i class="pi pi-envelope verification-icon"></i>
        <h1>Verifique seu Email</h1>
        <p v-if="!isVerifying && !verificationResult">
          Enviamos um link de verificação para <strong>{{ email }}</strong>
        </p>
      </div>
      
      <!-- Estado: Aguardando verificação -->
      <div v-if="!isVerifying && !verificationResult" class="verification-content">
        <div class="verification-steps">
          <div class="step">
            <i class="pi pi-check-circle step-icon"></i>
            <span>Email de verificação enviado</span>
          </div>
          <div class="step">
            <i class="pi pi-envelope step-icon"></i>
            <span>Verifique sua caixa de entrada</span>
          </div>
          <div class="step">
            <i class="pi pi-external-link step-icon"></i>
            <span>Clique no link de verificação</span>
          </div>
        </div>
        
        <div class="verification-actions">
          <Button 
            label="Reenviar Email" 
            icon="pi pi-refresh"
            :loading="isResending"
            @click="resendVerification"
            class="p-button-outlined"
          />
          
          <RouterLink to="/login" class="login-link">
            <Button 
              label="Voltar ao Login" 
              icon="pi pi-arrow-left"
              class="p-button-text"
            />
          </RouterLink>
        </div>
      </div>
      
      <!-- Estado: Verificando token -->
      <div v-if="isVerifying" class="verification-loading">
        <ProgressSpinner />
        <p>Verificando seu email...</p>
      </div>
      
      <!-- Estado: Resultado da verificação -->
      <div v-if="verificationResult" class="verification-result">
        <div v-if="verificationResult.success" class="success-result">
          <i class="pi pi-check-circle success-icon"></i>
          <h2>Email Verificado com Sucesso!</h2>
          <p>Sua conta foi ativada. Agora você pode fazer login.</p>
          <Button 
            label="Fazer Login" 
            icon="pi pi-sign-in"
            @click="goToLogin"
            class="login-button"
          />
        </div>
        
        <div v-else class="error-result">
          <i class="pi pi-times-circle error-icon"></i>
          <h2>Erro na Verificação</h2>
          <p>{{ verificationResult.message }}</p>
          <div class="error-actions">
            <Button 
              label="Reenviar Email" 
              icon="pi pi-refresh"
              :loading="isResending"
              @click="resendVerification"
              class="p-button-outlined"
            />
            <RouterLink to="/register">
              <Button 
                label="Criar Nova Conta" 
                icon="pi pi-user-plus"
                class="p-button-text"
              />
            </RouterLink>
          </div>
        </div>
      </div>
      
      <Message v-if="errorMessage" severity="error" :closable="false" class="mt-3">
        {{ errorMessage }}
      </Message>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'

// Router
const route = useRoute()
const router = useRouter()

// Estado reativo
const email = ref(route.query.email || '')
const isVerifying = ref(false)
const isResending = ref(false)
const verificationResult = ref(null)
const errorMessage = ref('')

// Verificar token na montagem do componente
onMounted(() => {
  const token = route.query.token
  if (token) {
    verifyEmailToken(token)
  }
})

// Função para verificar token de email
async function verifyEmailToken(token) {
  isVerifying.value = true
  
  try {
    const response = await fetch('http://127.0.0.1:5000/auth/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    })
    
    const data = await response.json()
    
    verificationResult.value = {
      success: response.ok,
      message: data.message || (response.ok ? 'Email verificado com sucesso!' : 'Erro na verificação')
    }
  } catch (error) {
    verificationResult.value = {
      success: false,
      message: 'Erro de conexão. Tente novamente.'
    }
  } finally {
    isVerifying.value = false
  }
}

// Função para reenviar email de verificação
async function resendVerification() {
  if (!email.value) {
    errorMessage.value = 'Email não informado'
    return
  }
  
  isResending.value = true
  errorMessage.value = ''
  
  try {
    const response = await fetch('http://127.0.0.1:5000/auth/resend-verification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value })
    })
    
    const data = await response.json()
    
    if (response.ok) {
      // Mostrar mensagem de sucesso
      verificationResult.value = null // Reset para mostrar a tela inicial
    } else {
      errorMessage.value = data.error || 'Erro ao reenviar email'
    }
  } catch (error) {
    errorMessage.value = 'Erro de conexão. Tente novamente.'
  } finally {
    isResending.value = false
  }
}

// Função para ir ao login
function goToLogin() {
  router.push('/login')
}
</script>

<style scoped>
.verification-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
}

.verification-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  padding: 3rem;
  width: 100%;
  max-width: 500px;
  text-align: center;
}

.verification-header {
  margin-bottom: 2rem;
}

.verification-icon {
  font-size: 4rem;
  color: #007BFF;
  margin-bottom: 1rem;
}

.verification-header h1 {
  color: #333;
  margin: 0 0 1rem 0;
  font-size: 2rem;
  font-weight: 600;
}

.verification-header p {
  color: #666;
  margin: 0;
  font-size: 1rem;
}

.verification-steps {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
}

.step {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  text-align: left;
}

.step-icon {
  color: #28a745;
  font-size: 1.2rem;
}

.verification-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.verification-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
}

.verification-loading p {
  color: #666;
  font-size: 1.1rem;
}

.success-result {
  color: #28a745;
}

.success-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.error-result {
  color: #dc3545;
}

.error-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.verification-result h2 {
  margin: 0 0 1rem 0;
  font-size: 1.5rem;
}

.verification-result p {
  margin: 0 0 2rem 0;
  font-size: 1rem;
}

.error-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.login-button {
  margin-top: 1rem;
}

.login-link {
  text-decoration: none;
}

.mt-3 {
  margin-top: 1rem;
}

/* Responsividade */
@media (max-width: 768px) {
  .verification-container {
    padding: 1rem;
  }
  
  .verification-card {
    padding: 2rem;
  }
  
  .verification-icon {
    font-size: 3rem;
  }
  
  .verification-header h1 {
    font-size: 1.5rem;
  }
}
</style>
