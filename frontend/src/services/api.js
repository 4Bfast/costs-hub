// src/services/api.js
import { useAuthStore } from '@/stores/auth';

// Configuração da API usando variáveis de ambiente
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5001';
const API_VERSION = import.meta.env.VITE_API_VERSION || 'v1';
const BASE_URL = `${API_BASE_URL}/api/${API_VERSION}`;

console.log('🔧 API Configuration:', { API_BASE_URL, API_VERSION, BASE_URL });

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

    /**
     * Lista todas as contas AWS conectadas
     */
    getAccounts() {
        return authenticatedFetch('/aws-accounts');
    },

    /**
     * Atualiza uma conta AWS
     */
    updateAccount(accountId, data) {
        return authenticatedFetch(`/aws-accounts/${accountId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    /**
     * Remove uma conta AWS
     */
    deleteAccount(accountId) {
        return authenticatedFetch(`/aws-accounts/${accountId}`, {
            method: 'DELETE'
        });
    },

    // --- ENDPOINTS DE GESTÃO DE USUÁRIOS ---

    /**
     * Lista todos os usuários da organização
     */
    getUsers() {
        return authenticatedFetch('/users');
    },

    /**
     * Convida um novo usuário para a organização
     */
    inviteUser(email) {
        return authenticatedFetch('/users/invite', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
    },

    /**
     * Remove um usuário da organização
     */
    removeUser(userId) {
        return authenticatedFetch(`/users/${userId}`, {
            method: 'DELETE'
        });
    },

    /**
     * Verifica um token de convite
     */
    verifyInvitation(token) {
        return fetch(`${BASE_URL}/invitations/verify?token=${token}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        });
    },

    /**
     * Aceita um convite e ativa a conta
     */
    acceptInvitation(token, password) {
        return fetch(`${BASE_URL}/invitations/accept`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ token, password })
        }).then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        });
    },

    // --- ENDPOINTS DE ONBOARDING SEGURO ---

    /**
     * Inicia processo de onboarding seguro
     */
    initiateConnection(payerAccountId, s3Prefix) {
        return authenticatedFetch('/connections/initiate', {
            method: 'POST',
            body: JSON.stringify({
                payer_account_id: payerAccountId,
                s3_prefix: s3Prefix
            })
        });
    },

    /**
     * Finaliza processo de onboarding
     */
    finalizeConnection(connectionId, roleArn) {
        return authenticatedFetch(`/connections/${connectionId}/finalize`, {
            method: 'POST',
            body: JSON.stringify({
                role_arn: roleArn
            })
        });
    },

    // --- Endpoints de Dados ---

    /**
     * Busca as contas-membro descobertas automaticamente.
     */
    getMemberAccounts() {
        return authenticatedFetch('/member-accounts');
    },
    updateMemberAccountBudget(accountId, monthlyBudget) {
        return authenticatedFetch(`/member-accounts/${accountId}`, {
            method: 'PUT',
            body: JSON.stringify({
                monthly_budget: monthlyBudget
            }),
        });
    },

    /**
     * Busca os dados consolidados para o Dashboard Estratégico.
     */
    getDashboardData(startDate, endDate, memberAccountId = null) {
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate
        });
        
        if (memberAccountId) {
            params.append('member_account_id', memberAccountId);
        }
        
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

    /**
     * Busca análise comparativa de custos por serviço (atual vs anterior).
     */
    getCostsByServiceComparative(accountId, startDate, endDate) {
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate
        });

        if (accountId) {
            params.append('aws_account_id', accountId);
        }

        return authenticatedFetch(`/costs/by-service-comparative?${params.toString()}`);
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

    // Análise de Variação por Serviço
    getVariationAnalysis(params) {
        console.log('=== getVariationAnalysis DEBUG ===');
        console.log('Input params:', params);
        
        const searchParams = new URLSearchParams();
        
        // Parâmetros obrigatórios
        searchParams.append('start_date', params.start_date);
        searchParams.append('end_date', params.end_date);
        searchParams.append('service_name', params.service_name);
        
        // Parâmetros opcionais
        if (params.aws_account_id && params.aws_account_id !== '') {
            searchParams.append('aws_account_id', params.aws_account_id);
        }
        
        if (params.min_variation) {
            searchParams.append('min_variation', params.min_variation);
        }
        
        if (params.limit) {
            searchParams.append('limit', params.limit);
        }
        
        const url = `/costs/variation-analysis?${searchParams.toString()}`;
        console.log('Final Variation API URL:', `${BASE_URL}${url}`);
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

    /**
     * Alterar role de um usuário
     */
    updateUserRole(userId, role) {
        return authenticatedFetch(`/users/${userId}/role`, {
            method: 'PUT',
            body: JSON.stringify({ role }),
        });
    },

    /**
     * Reenviar convite para um usuário
     */
    resendInvite(userId) {
        return authenticatedFetch(`/users/${userId}/resend-invite`, {
            method: 'POST'
        });
    },

    /**
     * Deletar organização (soft delete)
     */
    deleteOrganization(password, confirmationText, deletionReason = '') {
        return authenticatedFetch('/organization/delete', {
            method: 'DELETE',
            body: JSON.stringify({ 
                password, 
                confirmation_text: confirmationText,
                deletion_reason: deletionReason 
            }),
        });
    },
};