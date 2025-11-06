import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

export const useAuthStore = defineStore('auth', () => {
  // --- STATE ---
  // O token é pego do localStorage para que o login persista após recarregar a página
  const token = ref(localStorage.getItem('token'))
  const router = useRouter()

  // --- GETTERS ---
  // Um 'getter' é como uma propriedade computada do nosso estado.
  const isAuthenticated = computed(() => !!token.value)

  // --- ACTIONS ---
  // Actions são as funções que mudam o estado.

  function setToken(newToken) {
    localStorage.setItem('token', newToken)
    token.value = newToken
  }

  function clearToken() {
    localStorage.removeItem('token')
    token.value = null
  }

  async function login(email, password) {
    try {
      const response = await fetch('http://127.0.0.1:5001/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.message || 'Falha no login')
      }
      // Sucesso! Salva o token no estado e no localStorage
      setToken(data.access_token)
      // Redireciona para o dashboard
      router.push('/dashboard')
    } catch (error) {
      // Propaga o erro para que o componente possa exibi-lo
      throw error
    }
  }

  async function register(payload) {
    try {
      const response = await fetch('http://127.0.0.1:5001/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await response.json()
      if (!response.ok) {
        // A API retorna {"error": "mensagem"} então vamos capturar corretamente
        throw new Error(data.error || data.message || 'Falha no registro')
      }
      // Não salva token nem autentica - apenas retorna sucesso
      return data
    } catch (error) {
      // Propaga o erro para que o componente possa exibi-lo
      throw error
    }
  }

  function logout() {
    clearToken()
    router.push('/login')
  }

  // Expõe o estado e as ações para serem usados nos componentes
  return { token, isAuthenticated, login, register, logout }
})
