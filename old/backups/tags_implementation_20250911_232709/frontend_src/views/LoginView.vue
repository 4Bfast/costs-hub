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
  <div class="tw-flex tw-justify-center tw-items-center tw-min-h-screen tw-bg-gray-100">
    <div class="tw-bg-white tw-p-10 tw-rounded-lg tw-shadow-lg tw-w-full tw-max-w-md tw-text-center">
      <h1 class="tw-text-3xl tw-font-bold tw-text-gray-900 tw-mb-3 tw-font-inter">
        CostsHub
      </h1>
      <p class="tw-text-gray-600 tw-mb-8 tw-text-base">
        Acesse sua conta
      </p>
      
      <form @submit.prevent="handleLogin" class="tw-space-y-6">
        <div class="tw-text-left">
          <label for="email" class="tw-block tw-mb-2 tw-font-semibold tw-text-gray-700">
            Email
          </label>
          <input 
            type="email" 
            id="email" 
            v-model="email" 
            required
            class="tw-w-full tw-px-4 tw-py-3 tw-border tw-border-gray-300 tw-rounded-md tw-box-border tw-text-gray-900 tw-bg-white focus:tw-outline-none focus:tw-ring-2 focus:tw-ring-blue-500 focus:tw-border-blue-500 tw-transition-colors"
            placeholder="seu@email.com"
          >
        </div>
        
        <div class="tw-text-left">
          <label for="password" class="tw-block tw-mb-2 tw-font-semibold tw-text-gray-700">
            Senha
          </label>
          <input 
            type="password" 
            id="password" 
            v-model="password" 
            required
            class="tw-w-full tw-px-4 tw-py-3 tw-border tw-border-gray-300 tw-rounded-md tw-box-border tw-text-gray-900 tw-bg-white focus:tw-outline-none focus:tw-ring-2 focus:tw-ring-blue-500 focus:tw-border-blue-500 tw-transition-colors"
            placeholder="••••••••"
          >
        </div>
        
        <div v-if="errorMessage" class="tw-bg-red-50 tw-border tw-border-red-200 tw-rounded-md tw-p-3">
          <p class="tw-text-red-700 tw-text-sm tw-font-medium">
            {{ errorMessage }}
          </p>
        </div>
        
        <button 
          type="submit" 
          :disabled="isLoading"
          class="tw-w-full tw-py-3 tw-px-4 tw-bg-blue-600 tw-text-white tw-border-none tw-rounded-md tw-cursor-pointer tw-text-base tw-font-semibold tw-transition-colors hover:tw-bg-blue-700 focus:tw-outline-none focus:tw-ring-2 focus:tw-ring-blue-500 focus:tw-ring-offset-2 disabled:tw-bg-blue-300 disabled:tw-cursor-not-allowed"
        >
          <span v-if="isLoading" class="tw-flex tw-items-center tw-justify-center">
            <svg class="tw-animate-spin tw--ml-1 tw-mr-3 tw-h-5 tw-w-5 tw-text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="tw-opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="tw-opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Entrando...
          </span>
          <span v-else>Entrar</span>
        </button>
        
        <div class="tw-text-center tw-mt-6 tw-pt-4 tw-border-t tw-border-gray-200">
          <RouterLink 
            to="/register"
            class="tw-text-blue-600 tw-no-underline tw-text-sm tw-transition-colors hover:tw-text-blue-800 hover:tw-underline"
          >
            Não tem uma conta? Crie uma agora.
          </RouterLink>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
/* 
 * FASE 2: LoginView refatorado com Tailwind CSS
 * Todo o CSS customizado foi substituído por classes utilitárias Tailwind com prefixo tw-
 * Mantendo a mesma aparência visual, mas com melhor consistência e manutenibilidade
 */
</style>