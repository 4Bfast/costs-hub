# 🗺️ Endpoint Mapping - Frontend vs Backend

## 📋 Mapeamento Completo

### 🔐 Autenticação
| Frontend Espera | Backend Atual | Nova API Gateway | Transformação |
|----------------|---------------|------------------|---------------|
| `POST /api/v1/auth/login` | ❌ Não existe | `POST /api/v1/auth/login` | JWT Mock → Real JWT |
| `GET /api/v1/auth/me` | ❌ Não existe | `GET /api/v1/auth/me` | JWT Decode |
| `POST /api/v1/auth/logout` | ❌ Não existe | `POST /api/v1/auth/logout` | Token Invalidation |

### 📊 Dashboard
| Frontend Espera | Backend Atual | Nova API Gateway | Transformação |
|----------------|---------------|------------------|---------------|
| `GET /api/v1/dashboard/metrics` | `GET /costs` | `GET /api/v1/dashboard/metrics` | Mapear campos |
| `GET /api/v1/dashboard/cost-overview` | `GET /costs` | `GET /api/v1/dashboard/cost-overview` | Extrair overview |
| `GET /api/v1/dashboard/service-breakdown` | `GET /costs` | `GET /api/v1/dashboard/service-breakdown` | Extrair services |
| `GET /api/v1/dashboard/recent-alarms` | ❌ Mock | `GET /api/v1/dashboard/recent-alarms` | Mock estruturado |
| `GET /api/v1/dashboard/insights-summary` | `GET /insights` | `GET /api/v1/dashboard/insights-summary` | Transformar formato |

### 💰 Custos
| Frontend Espera | Backend Atual | Nova API Gateway | Transformação |
|----------------|---------------|------------------|---------------|
| `GET /api/v1/costs` | `GET /costs` | `GET /api/v1/costs` | Padronizar response |
| `GET /api/v1/cost-data` | `GET /costs` | `GET /api/v1/cost-data` | Alias para /costs |
| `GET /api/v1/cost-data/summary` | `GET /costs/total` | `GET /api/v1/cost-data/summary` | Direto |
| `GET /api/v1/cost-data/trends` | ❌ Calcular | `GET /api/v1/cost-data/trends` | Processar histórico |

### 🔍 Insights
| Frontend Espera | Backend Atual | Nova API Gateway | Transformação |
|----------------|---------------|------------------|---------------|
| `GET /api/v1/insights` | `GET /insights` | `GET /api/v1/insights` | Padronizar response |
| `GET /api/v1/insights/summary` | `GET /insights` | `GET /api/v1/insights/summary` | Resumir dados |
| `GET /api/v1/insights/anomalies` | `GET /anomalies` | `GET /api/v1/insights/anomalies` | Direto |
| `GET /api/v1/insights/recommendations` | `GET /recommendations` | `GET /api/v1/insights/recommendations` | Direto |

### 🏢 Contas
| Frontend Espera | Backend Atual | Nova API Gateway | Transformação |
|----------------|---------------|------------------|---------------|
| `GET /api/v1/accounts` | `GET /accounts` | `GET /api/v1/accounts` | Padronizar response |
| `POST /api/v1/accounts` | ❌ Não existe | `POST /api/v1/accounts` | Implementar |
| `DELETE /api/v1/accounts/{id}` | ❌ Não existe | `DELETE /api/v1/accounts/{id}` | Implementar |

## 🔄 Formato de Transformação

### Entrada (Backend Atual)
```json
{
  "totalCost": 25.47,
  "serviceBreakdown": [...]
}
```

### Saída (Padronizada)
```json
{
  "success": true,
  "data": {
    "total_monthly_cost": 25.47,
    "service_breakdown": [...]
  }
}
```

## 🎯 Prioridades de Implementação

### P0 - Crítico (Dashboard Funcional)
1. ✅ Auth endpoints (mock JWT)
2. ✅ Dashboard metrics
3. ✅ Cost overview
4. ✅ Service breakdown

### P1 - Importante
1. ✅ Insights summary
2. ✅ Accounts list
3. ✅ Cost data endpoints

### P2 - Desejável
1. ⏳ Account management (CRUD)
2. ⏳ Alarms (quando backend implementar)
3. ⏳ Advanced filtering
