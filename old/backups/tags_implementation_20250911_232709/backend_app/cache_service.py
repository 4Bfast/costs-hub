# app/cache_service.py

import time
from typing import Optional, Dict, Any
import threading

class SimpleMemoryCache:
    """Cache simples em memória com TTL para o MVP"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[str]:
        """
        Recupera valor do cache se ainda válido
        
        Args:
            key: Chave do cache
            
        Returns:
            Valor armazenado ou None se expirado/inexistente
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            current_time = time.time()
            
            # Verificar se expirou
            if current_time > entry['expires_at']:
                del self._cache[key]
                return None
            
            return entry['value']
    
    def set(self, key: str, value: str, ttl_seconds: int = 21600) -> None:
        """
        Armazena valor no cache com TTL
        
        Args:
            key: Chave do cache
            value: Valor a ser armazenado
            ttl_seconds: Tempo de vida em segundos (padrão: 6 horas)
        """
        with self._lock:
            expires_at = time.time() + ttl_seconds
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
    
    def clear_expired(self) -> int:
        """
        Remove entradas expiradas do cache
        
        Returns:
            Número de entradas removidas
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time > entry['expires_at']
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)
    
    def size(self) -> int:
        """Retorna número de entradas no cache"""
        with self._lock:
            return len(self._cache)


# Instância global do cache
ai_summary_cache = SimpleMemoryCache()
ai_explanation_cache = SimpleMemoryCache()

def generate_cache_key(organization_id: int, start_date: str, end_date: str) -> str:
    """
    Gera chave única para o cache baseada nos parâmetros
    
    Args:
        organization_id: ID da organização
        start_date: Data de início (YYYY-MM-DD)
        end_date: Data de fim (YYYY-MM-DD)
        
    Returns:
        Chave única para o cache
    """
    return f"ai_summary:{organization_id}:{start_date}:{end_date}"

def is_cache_available(organization_id: int, start_date: str, end_date: str) -> bool:
    """
    Verifica se há cache disponível para evitar chamadas desnecessárias ao Bedrock
    """
    cache_key = generate_cache_key(organization_id, start_date, end_date)
    return ai_summary_cache.get(cache_key) is not None

def generate_explanation_cache_key(term: str, context: str) -> str:
    """
    Gera chave única para cache de explicações
    
    Args:
        term: Termo técnico
        context: Contexto do termo
        
    Returns:
        Chave única para o cache
    """
    return f"ai_explanation:{term}:{context}"
