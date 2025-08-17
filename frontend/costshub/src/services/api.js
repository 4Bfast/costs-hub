// src/services/api.js
import { useAuthStore } from '@/stores/auth';

const BASE_URL = 'http://127.0.0.1:5000/api/v1';

// Função auxiliar para fazer requisições autenticadas
async function authenticatedFetch(url, options = {}) {
    const authStore = useAuthStore();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (authStore.isAuthenticated) {
        headers['Authorization'] = `Bearer ${authStore.token}`;
    }

    const fullUrl = `${BASE_URL}${url}`;
    console.log('=== AUTHENTICATED FETCH DEBUG ===');
    console.log('Full URL:', fullUrl);
    console.log('Headers:', headers);
    console.log('Options:', options);
    console.log('================================');

    const response = await fetch(fullUrl, { ...options, headers });

    console.log('=== RESPONSE DEBUG ===');
    console.log('Response status:', response.status);
    console.log('Response ok:', response.ok);
    console.log('Response headers:', Object.fromEntries(response.headers.entries()));
    console.log('=====================');

    if (response.status === 401) {
        // Se o token for inválido ou expirar, desloga o usuário
        authStore.logout();
        throw new Error('Sessão expirada. Por favor, faça login novamente.');
    }

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Erro desconhecido' }));
        console.error('=== ERROR RESPONSE ===');
        console.error('Error data:', errorData);
        console.error('=====================');
        throw new Error(errorData.error || errorData.message || 'Ocorreu um erro na API');
    }

    return response.json();
}

// Exporta funções específicas para cada endpoint
// src/services/api.js

// A função authenticatedFetch e a const BASE_URL permanecem como estão.
// A mudança é apenas DENTRO do objeto apiService.

export const apiService = {
    // --- Autenticação e Gestão de Contas ---
    getAwsAccounts() {
        return authenticatedFetch('/aws-accounts');
    },
    addAwsAccount(accountData) {
        return authenticatedFetch('/aws-accounts', {
            method: 'POST',
            body: JSON.stringify(accountData),
        });
    },
    updateAwsAccount(accountId, accountData) {
        return authenticatedFetch(`/aws-accounts/${accountId}`, {
            method: 'PUT',
            body: JSON.stringify(accountData),
        });
    },
    deleteAwsAccount(accountId) {
        return authenticatedFetch(`/aws-accounts/${accountId}`, {
            method: 'DELETE',
        });
    },
    importHistory(accountId) {
        return authenticatedFetch(`/aws-accounts/${accountId}/import-history`, {
            method: 'POST',
        });
    },

    // --- Endpoints de Dados ---

    /**
     * Busca os dados consolidados para o Dashboard Estratégico.
     */
    getDashboardData(startDate, endDate) {
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate
        });
        return authenticatedFetch(`/dashboards/main?${params.toString()}`);
    },

    /**
     * [VERSÃO CORRIGIDA E ÚNICA]
     * Busca os custos agregados por serviço.
     * O parâmetro accountId é opcional.
     */
    getCostsByService(accountId, startDate, endDate) {
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate
        });

        // Adiciona o aws_account_id à query APENAS se ele for fornecido
        if (accountId) {
            params.append('aws_account_id', accountId);
        }

        return authenticatedFetch(`/costs/by-service?${params.toString()}`);
    },

    // NOVO: Série Temporal por Serviço
    getTimeSeriesByService(params) {
        console.log('=== getTimeSeriesByService DEBUG ===');
        console.log('Input params:', params);
        
        const searchParams = new URLSearchParams();
        
        // Validação detalhada dos parâmetros obrigatórios
        if (!params.start_date) {
            console.error('Missing start_date parameter');
            throw new Error('start_date é obrigatório');
        }
        if (!params.end_date) {
            console.error('Missing end_date parameter');
            throw new Error('end_date é obrigatório');
        }
        if (!params.service_name) {
            console.error('Missing service_name parameter');
            throw new Error('service_name é obrigatório');
        }
        
        searchParams.append('start_date', params.start_date);
        searchParams.append('end_date', params.end_date);
        searchParams.append('service_name', params.service_name);
        
        // aws_account_id é opcional
        if (params.aws_account_id && params.aws_account_id !== '') {
            console.log('Adding aws_account_id:', params.aws_account_id);
            searchParams.append('aws_account_id', params.aws_account_id);
        } else {
            console.log('Skipping aws_account_id (optional)');
        }
        
        const url = `/costs/time-series-by-service?${searchParams.toString()}`;
        console.log('Final API URL:', `${BASE_URL}${url}`);
        console.log('====================================');
        
        return authenticatedFetch(url);
    },

    // --- Módulo de Alarmes ---
    
    /**
     * Lista todos os serviços AWS disponíveis para criar alarmes
     */
    getServices() {
        return authenticatedFetch('/services');
    },

    /**
     * Lista todas as regras de alarme da organização
     */
    getAlarms() {
        return authenticatedFetch('/alarms');
    },

    /**
     * Cria uma nova regra de alarme
     */
    createAlarm(alarmData) {
        return authenticatedFetch('/alarms', {
            method: 'POST',
            body: JSON.stringify(alarmData),
        });
    },

    /**
     * Atualiza uma regra de alarme existente
     */
    updateAlarm(alarmId, alarmData) {
        return authenticatedFetch(`/alarms/${alarmId}`, {
            method: 'PUT',
            body: JSON.stringify(alarmData),
        });
    },

    /**
     * Deleta uma regra de alarme
     */
    deleteAlarm(alarmId) {
        return authenticatedFetch(`/alarms/${alarmId}`, {
            method: 'DELETE',
        });
    },

    /**
     * Lista todos os eventos de alarme com filtros opcionais
     */
    getAlarmEvents(filters = {}) {
        const params = new URLSearchParams();
        
        if (filters.status) {
            params.append('status', filters.status);
        }
        if (filters.severity) {
            params.append('severity', filters.severity);
        }
        if (filters.page) {
            params.append('page', filters.page);
        }
        if (filters.per_page) {
            params.append('per_page', filters.per_page);
        }

        const queryString = params.toString();
        const url = queryString ? `/alarm-events?${queryString}` : '/alarm-events';
        
        return authenticatedFetch(url);
    },

    /**
     * Atualiza o status de um evento de alarme
     */
    updateAlarmEventStatus(eventId, statusData) {
        return authenticatedFetch(`/alarm-events/${eventId}/status`, {
            method: 'PUT',
            body: JSON.stringify(statusData),
        });
    },

    /**
     * Obtém o histórico de ações de um evento de alarme
     */
    getAlarmEventHistory(eventId) {
        return authenticatedFetch(`/alarm-events/${eventId}/history`);
    },

    // --- Métodos auxiliares ---
    
    /**
     * Método genérico para GET
     */
    get(endpoint) {
        return authenticatedFetch(endpoint);
    },

    /**
     * Método genérico para POST
     */
    post(endpoint, data) {
        return authenticatedFetch(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * Método genérico para PUT
     */
    put(endpoint, data) {
        return authenticatedFetch(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },

    /**
     * Método genérico para DELETE
     */
    delete(endpoint) {
        return authenticatedFetch(endpoint, {
            method: 'DELETE',
        });
    },
};