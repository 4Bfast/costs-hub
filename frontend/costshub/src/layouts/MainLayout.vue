<script setup>
import { RouterView, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <div class="main-layout">
    <aside class="sidebar">
      <div class="logo">CostsHub</div>
      <nav class="navigation">
        <RouterLink to="/dashboard" class="nav-link">Dashboard</RouterLink>
        <RouterLink to="/analysis" class="nav-link">Análise por Serviço</RouterLink>
        <RouterLink to="/alarms" class="nav-link">
          <i class="pi pi-bell"></i>
          Alarmes
        </RouterLink>
        <RouterLink to="/settings" class="nav-link">Configurações</RouterLink>
      </nav>
      <div class="footer">
        <button @click="authStore.logout()" class="logout-button">Sair</button>
      </div>
    </aside>
    <main class="content-area">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
/* Estilos para o nosso Layout */
.main-layout {
  display: flex;
  height: 100vh;
  background-color: #F8F9FA; /* Cinza Claro */
}
.sidebar {
  width: 250px;
  background-color: #212529; /* Tom Escuro */
  color: white;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
}
.logo {
  font-size: 1.8rem;
  font-weight: bold;
  text-align: center;
  margin-bottom: 2rem;
}
.navigation {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex-grow: 1;
}
.nav-link {
  color: #ccc;
  text-decoration: none;
  padding: 0.8rem 1rem;
  border-radius: 6px;
  transition: background-color 0.2s, color 0.2s;
}
.nav-link:hover {
  background-color: #343a40;
  color: white;
}
.router-link-exact-active {
  background-color: #007BFF; /* Azul Primário */
  color: white;
}
.logout-button {
  width: 100%;
  background: none;
  border: 1px solid #dc3545;
  color: #dc3545;
  padding: 0.7rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
}
.logout-button:hover {
    background-color: #dc3545;
    color: white;
}
.content-area {
  flex-grow: 1;
  padding: 2rem;
  overflow-y: auto; /* Adiciona scroll se o conteúdo for grande */
}
</style>