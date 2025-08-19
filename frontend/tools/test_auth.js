// SCRIPT DE TESTE - Cole no console do navegador
console.log("🧪 TESTANDO AUTENTICAÇÃO");

// 1. Verificar se o store existe
try {
  const { useAuthStore } = await import('/src/stores/auth.js');
  const authStore = useAuthStore();
  console.log("✅ Store de auth carregado:", authStore);
  console.log("🔑 Token atual:", authStore.token ? "Existe" : "Não existe");
  console.log("👤 Usuário:", authStore.user);
  console.log("🔐 Autenticado:", authStore.isAuthenticated);
} catch (error) {
  console.error("❌ Erro ao carregar store:", error);
}

// 2. Testar requisição para AWS accounts
try {
  const response = await fetch('http://localhost:5000/api/v1/aws-accounts', {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      'Content-Type': 'application/json'
    }
  });
  
  console.log("📡 Resposta da API:", response.status, response.statusText);
  
  if (response.ok) {
    const data = await response.json();
    console.log("✅ Contas AWS:", data);
  } else {
    const error = await response.text();
    console.error("❌ Erro da API:", error);
  }
} catch (error) {
  console.error("❌ Erro na requisição:", error);
}