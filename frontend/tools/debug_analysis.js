// SCRIPT DE DEBUG PARA ANALYSISVIEW
// Cole este código no console do navegador quando estiver na página de Análise

console.log("🔍 DEBUG: ANALYSISVIEW - CARREGAMENTO DE CONTAS AWS");
console.log("=" * 60);

// 1. Verificar se estamos na página correta
console.log("📍 URL atual:", window.location.href);

// 2. Verificar se o token existe
const token = localStorage.getItem('auth_token');
console.log("🔑 Token existe:", !!token);
if (token) {
  console.log("🔑 Token (primeiros 20 chars):", token.substring(0, 20) + "...");
} else {
  console.error("❌ PROBLEMA: Nenhum token encontrado no localStorage");
  console.log("💡 SOLUÇÃO: Faça login novamente");
}

// 3. Verificar se o store de auth está funcionando
try {
  // Tentar acessar o store Pinia
  const stores = window.__VUE_DEVTOOLS_GLOBAL_HOOK__?.apps?.[0]?.config?.globalProperties?.$pinia?._s;
  if (stores) {
    const authStore = stores.get('auth');
    if (authStore) {
      console.log("✅ Store de auth encontrado");
      console.log("🔐 isAuthenticated:", authStore.isAuthenticated);
      console.log("👤 User:", authStore.user);
    } else {
      console.error("❌ Store de auth não encontrado");
    }
  }
} catch (error) {
  console.log("⚠️ Não foi possível acessar o store via DevTools");
}

// 4. Testar requisição direta para /aws-accounts
console.log("\n📡 TESTANDO REQUISIÇÃO PARA /aws-accounts");
fetch('http://localhost:5000/api/v1/aws-accounts', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  }
})
.then(response => {
  console.log("📊 Status da resposta:", response.status, response.statusText);
  
  if (response.status === 401) {
    console.error("❌ PROBLEMA: Token inválido ou expirado (401)");
    console.log("💡 SOLUÇÃO: Faça logout e login novamente");
  } else if (response.status === 403) {
    console.error("❌ PROBLEMA: Acesso negado (403)");
    console.log("💡 SOLUÇÃO: Verificar permissões do usuário");
  } else if (response.status === 404) {
    console.error("❌ PROBLEMA: Endpoint não encontrado (404)");
    console.log("💡 SOLUÇÃO: Verificar se o backend está rodando");
  }
  
  return response.json();
})
.then(data => {
  console.log("✅ Dados recebidos:", data);
  
  if (Array.isArray(data)) {
    console.log("📈 Número de contas AWS:", data.length);
    
    if (data.length === 0) {
      console.warn("⚠️ PROBLEMA: Nenhuma conta AWS cadastrada");
      console.log("💡 SOLUÇÃO: Vá em Configurações e adicione uma conta AWS");
    } else {
      console.log("📋 Contas encontradas:");
      data.forEach((account, index) => {
        console.log(`   ${index + 1}. ${account.account_name} (ID: ${account.id})`);
      });
    }
  } else {
    console.error("❌ PROBLEMA: Resposta não é um array");
  }
})
.catch(error => {
  console.error("❌ ERRO na requisição:", error);
  
  if (error.message.includes('Failed to fetch')) {
    console.error("❌ PROBLEMA: Não conseguiu conectar com o backend");
    console.log("💡 SOLUÇÃO: Verificar se o backend está rodando na porta 5000");
  } else if (error.message.includes('CORS')) {
    console.error("❌ PROBLEMA: Erro de CORS");
    console.log("💡 SOLUÇÃO: Verificar configuração CORS no backend");
  }
});

// 5. Verificar se há erros no console
console.log("\n🔍 VERIFICANDO ERROS NO CONSOLE");
console.log("Abra a aba Console e procure por erros em vermelho");
console.log("Erros comuns:");
console.log("• 401 Unauthorized - Token inválido");
console.log("• 403 Forbidden - Sem permissão");
console.log("• 404 Not Found - Endpoint não existe");
console.log("• CORS error - Problema de CORS");
console.log("• Network error - Backend não está rodando");

// 6. Verificar Network tab
console.log("\n🌐 VERIFICANDO NETWORK TAB");
console.log("1. Abra DevTools (F12)");
console.log("2. Vá para a aba Network");
console.log("3. Recarregue a página");
console.log("4. Procure por requisições para 'aws-accounts'");
console.log("5. Clique na requisição e veja:");
console.log("   • Status code");
console.log("   • Request headers (Authorization)");
console.log("   • Response body");

console.log("\n🎯 RESUMO DO DEBUG CONCLUÍDO");
console.log("Verifique os resultados acima para identificar o problema");
