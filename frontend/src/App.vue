<script setup>
import { RouterView } from 'vue-router'
import Toast from 'primevue/toast'
</script>

<template>
  <div class="p-dark">
    <RouterView />
    <Toast />
  </div>
</template>