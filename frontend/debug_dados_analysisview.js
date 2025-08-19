// SCRIPT DE DEBUG ESPECÍFICO - ANALYSISVIEW DADOS
console.log("🔍 DEBUG: Por que os dados não aparecem na AnalysisView?");

// 1. Verificar se há dados no componente Vue
const app = document.querySelector('#app').__vue_app__;
if (app) {
  console.log("✅ App Vue encontrado");
  
  // Tentar acessar dados do componente atual
  const instance = app._instance;
  if (instance && instance.setupState) {
    console.log("📊 Estados do componente:");
    console.log("- costsByService:", instance.setupState.costsByService);
    console.log("- isLoading:", instance.setupState.isLoading);
    console.log("- error:", instance.setupState.error);
    console.log("- selectedAccountId:", instance.setupState.selectedAccountId);
    console.log("- awsAccounts:", instance.setupState.awsAccounts);
  }
}

// 2. Testar requisição direta
const token = localStorage.getItem('token');
const testAccountId = 1; // Ajustar conforme necessário

fetch(`http://localhost:5000/api/v1/costs/by-service?aws_account_id=${testAccountId}&start_date=2024-01-01&end_date=2024-01-31`, {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => r.json())
.then(data => {
  console.log("📡 Response da API:", data);
  console.log("📊 Tipo:", typeof data);
  console.log("📈 É array:", Array.isArray(data));
  console.log("📋 Quantidade:", data.length);
  
  if (data.length > 0) {
    console.log("📝 Primeiro item:", data[0]);
    console.log("🔑 Propriedades:", Object.keys(data[0]));
  }
})
.catch(err => console.error("❌ Erro:", err));

// 3. Verificar elementos DOM
console.log("🔍 Elementos na tela:");
console.log("- KPIs:", document.querySelectorAll('.kpi-card').length);
console.log("- Gráficos:", document.querySelectorAll('.chart-container').length);
console.log("- Tabela:", document.querySelectorAll('.costs-table').length);
console.log("- Loading:", document.querySelectorAll('.loading-state').length);
console.log("- Error:", document.querySelectorAll('.error-state').length);
console.log("- Empty:", document.querySelectorAll('.empty-state').length);
