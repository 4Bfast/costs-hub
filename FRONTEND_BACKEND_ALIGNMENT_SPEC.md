# Frontend-Backend Alignment Specification

## 📋 DISCREPÂNCIAS IDENTIFICADAS - 2025-11-03T23:43:00

### 🎯 **OBJETIVO:**
Alinhar completamente o frontend com o backend implementado, garantindo que todas as funcionalidades funcionem corretamente.

---

## 🔧 **TASKS DE IMPLEMENTAÇÃO NECESSÁRIAS**

### 🚨 **ALTA PRIORIDADE - ENDPOINTS FALTANDO NO BACKEND**

#### 1. **COSTS ENDPOINTS - 3 tasks**

##### ❌ **TASK 1.1: Implementar GET /costs/records**
**Frontend espera:** `GET /costs/records?page=1&limit=20&sort=date&order=desc`
**Backend tem:** `GET /costs` (genérico)
**Ação:** Modificar `/costs` para aceitar paginação ou criar `/costs/records`

```typescript
// Frontend usa:
return await apiClient.getPaginated<CostRecord>(`/costs/records?${searchParams.toString()}`);

// Parâmetros esperados:
- page, limit (paginação)
- sort, order (ordenação)  
- search (busca)
- start_date, end_date (filtros)
- providers, services, accounts (filtros)
- min_cost, max_cost (range de custo)
```

##### ❌ **TASK 1.2: Implementar POST /costs/export**
**Frontend espera:** `POST /costs/export` com body de configuração
**Backend não tem:** Endpoint de exportação
**Ação:** Criar endpoint para exportar dados de custo

```typescript
// Frontend usa:
const response = await apiClient.post<{ job_id: string; download_url?: string }>('/costs/export', exportRequest);

// Body esperado:
{
  format: 'csv' | 'excel' | 'pdf',
  filters: CostFilters,
  columns: string[],
  date_range: { start: string, end: string }
}
```

##### ❌ **TASK 1.3: Ajustar endpoints de breakdown**
**Frontend espera:** Estrutura específica de resposta
**Backend tem:** Implementação básica
**Ação:** Verificar se resposta está no formato correto

---

#### 2. **ACCOUNTS ENDPOINTS - 2 tasks**

##### ❌ **TASK 2.1: Implementar POST /accounts/{id}/test**
**Frontend espera:** `POST /accounts/{id}/test` para testar conexão
**Backend não tem:** Endpoint de teste de conexão
**Ação:** Criar endpoint para testar credenciais da conta

```typescript
// Frontend usa:
const response = await apiClient.post<ConnectionTestResponse>(`/accounts/${id}/test`);

// Resposta esperada:
{
  success: boolean,
  message: string,
  details?: {
    latency: number,
    permissions: string[],
    last_sync: string
  }
}
```

##### ❌ **TASK 2.2: Implementar POST /accounts/{id}/refresh**
**Frontend espera:** `POST /accounts/{id}/refresh` para atualizar dados
**Backend não tem:** Endpoint de refresh
**Ação:** Criar endpoint para forçar sincronização

```typescript
// Frontend usa:
await apiClient.post(`/accounts/${id}/refresh`);

// Resposta esperada:
{
  success: boolean,
  message: string,
  sync_status: 'started' | 'completed' | 'failed'
}
```

---

#### 3. **ALARMS ENDPOINTS - 1 task**

##### ❌ **TASK 3.1: Implementar POST /alarms/{id}/test**
**Frontend espera:** `POST /alarms/{id}/test` para testar alarme
**Backend não tem:** Endpoint de teste de alarme
**Ação:** Criar endpoint para simular disparo do alarme

```typescript
// Frontend usa:
const response = await apiClient.post<{ success: boolean; message: string }>(`/alarms/${id}/test`);

// Resposta esperada:
{
  success: boolean,
  message: string,
  test_result: {
    would_trigger: boolean,
    current_value: number,
    threshold: number,
    notification_sent: boolean
  }
}
```

---

#### 4. **DASHBOARD ENDPOINTS - 2 tasks**

##### ❌ **TASK 4.1: Ajustar GET /dashboard/metrics**
**Frontend espera:** `GET /dashboard/metrics`
**Backend tem:** `GET /dashboard/summary`
**Ação:** Criar alias ou renomear endpoint

```typescript
// Frontend usa:
const response = await apiClient.get<{
  total_monthly_cost: number;
  month_over_month_change: number;
  connected_accounts: number;
  active_alarms: number;
  unread_insights: number;
  cost_trend_7d: Array<{ date: string; cost: number }>;
  top_service: { service_name: string; cost: number; percentage: number } | null;
  provider_distribution: Array<{
    provider: string;
    cost: number;
    percentage: number;
    account_count: number;
  }>;
  recent_activity: Array<{
    type: 'cost_spike' | 'new_insight' | 'alarm_triggered' | 'account_added';
    title: string;
    description: string;
    timestamp: string;
    severity?: 'low' | 'medium' | 'high' | 'critical';
  }>;
}>('/dashboard/metrics');
```

##### ❌ **TASK 4.2: Verificar outros endpoints dashboard**
**Frontend pode usar:** Outros endpoints específicos
**Ação:** Verificar se todos os endpoints dashboard estão alinhados

---

#### 5. **INSIGHTS ENDPOINTS - 1 task**

##### ❌ **TASK 5.1: Implementar GET /insights/by-service/{service}**
**Frontend espera:** `GET /insights/by-service/{service}?limit=5`
**Backend não tem:** Endpoint específico por serviço
**Ação:** Criar endpoint para insights filtrados por serviço

```typescript
// Frontend usa:
const response = await apiClient.get<AIInsight[]>(`/insights/by-service/${service}?limit=${limit}`);

// Resposta esperada:
Array<{
  id: string,
  type: string,
  severity: string,
  title: string,
  description: string,
  service: string,
  potential_savings: number,
  created_at: string
}>
```

---

### 🔄 **MÉDIA PRIORIDADE - ENDPOINTS EXTRAS NO BACKEND**

#### 6. **USERS ENDPOINTS - Frontend não usa**
**Backend tem:** 3 endpoints de usuários implementados
**Frontend não usa:** Nenhum endpoint de usuários
**Ação:** Decidir se implementar no frontend ou manter apenas no backend

- ✅ GET /users (implementado, não usado)
- ✅ GET /users/profile (implementado, não usado)  
- ✅ PUT /users/profile (implementado, não usado)

#### 7. **INSIGHTS GENERATE - Frontend não usa**
**Backend tem:** POST /insights/generate
**Frontend não usa:** Geração manual de insights
**Ação:** Implementar no frontend se necessário

---

## 📊 **RESUMO DAS TASKS**

### 🚨 **CRÍTICAS (Quebram funcionalidades):**
- **TASK 1.1:** GET /costs/records (paginação de custos)
- **TASK 1.2:** POST /costs/export (exportação de dados)
- **TASK 2.1:** POST /accounts/{id}/test (teste de conexão)
- **TASK 2.2:** POST /accounts/{id}/refresh (sincronização)
- **TASK 3.1:** POST /alarms/{id}/test (teste de alarmes)

### 🔧 **IMPORTANTES (Melhoram UX):**
- **TASK 4.1:** GET /dashboard/metrics (métricas dashboard)
- **TASK 5.1:** GET /insights/by-service/{service} (insights por serviço)

### 📈 **OPCIONAIS (Features extras):**
- Implementar endpoints de usuários no frontend
- Implementar geração manual de insights

---

## 🎯 **PLANO DE IMPLEMENTAÇÃO**

### **FASE 1: Endpoints Críticos (1-2 horas)**
1. Implementar GET /costs/records com paginação
2. Implementar POST /costs/export
3. Implementar POST /accounts/{id}/test
4. Implementar POST /accounts/{id}/refresh
5. Implementar POST /alarms/{id}/test

### **FASE 2: Endpoints Importantes (30min)**
1. Ajustar GET /dashboard/metrics
2. Implementar GET /insights/by-service/{service}

### **FASE 3: Testes e Validação (30min)**
1. Testar todos os endpoints no frontend
2. Verificar se todas as funcionalidades funcionam
3. Validar fluxos completos

---

## 🚀 **RESULTADO ESPERADO**

Após implementar todas as tasks:
- ✅ **100% compatibilidade** entre frontend e backend
- ✅ **Todas as funcionalidades** do frontend funcionando
- ✅ **Zero erros** de endpoints não encontrados
- ✅ **UX completa** para usuários finais

**Tempo estimado total: 2-3 horas de desenvolvimento**

---

## 🔧 **PRÓXIMOS PASSOS**

1. **Implementar FASE 1** (endpoints críticos)
2. **Testar cada endpoint** conforme implementado
3. **Implementar FASE 2** (endpoints importantes)
4. **Validação final** com frontend

**Pronto para começar a implementação?** 🚀
