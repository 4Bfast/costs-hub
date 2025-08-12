<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/stores/auth'; // 1. Importa nossa store

const email = ref('');
const password = ref('');
const errorMessage = ref('');
const isLoading = ref(false);

const authStore = useAuthStore(); // 2. Pega uma instância da store

async function handleLogin() {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    // 3. Chama a ação de login da store. A store agora cuida de tudo!
    await authStore.login(email.value, password.value);
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-box">
      <h1>CostsHub</h1>
      <p class="subtitle">Acesse sua conta</p>
      <form @submit.prevent="handleLogin">
        <div class="input-group">
          <label for="email">Email</label>
          <input type="email" id="email" v-model="email" required>
        </div>
        <div class="input-group">
          <label for="password">Senha</label>
          <input type="password" id="password" v-model="password" required>
        </div>
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
        <button type="submit" :disabled="isLoading">
          {{ isLoading ? 'Entrando...' : 'Entrar' }}
        </button>
        
        <div class="register-link">
          <RouterLink to="/register">
            Não tem uma conta? Crie uma agora.
          </RouterLink>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}
.login-box {
  background: white;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
  text-align: center;
}
h1 {
  margin-bottom: 10px;
}
.subtitle {
  margin-bottom: 30px;
  color: #666;
}
.input-group {
  margin-bottom: 20px;
  text-align: left;
}
.input-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}
.input-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}
.error-message {
  color: red;
  margin-bottom: 15px;
}

.register-link {
  text-align: center;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}

.register-link a {
  color: #007BFF;
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.2s;
}

.register-link a:hover {
  color: #0056b3;
  text-decoration: underline;
}
button {
  width: 100%;
  padding: 12px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
}
button:disabled {
  background-color: #a0c7e4;
  cursor: not-allowed;
}
</style>