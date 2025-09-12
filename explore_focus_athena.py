#!/usr/bin/env python3
"""
Script para explorar a estrutura FOCUS no Athena
"""

import boto3
import time
import json
from datetime import datetime, timedelta

def execute_athena_query(query, database='costs'):
    """Executa query no Athena e retorna resultados"""
    
    # Usar profile AWS configurado
    session = boto3.Session(profile_name='4bfast')
    client = session.client('athena', region_name='us-east-1')
    
    # Configuração da query
    query_config = {
        'QueryString': query,
        'QueryExecutionContext': {
            'Database': database
        },
        'ResultConfiguration': {
            'OutputLocation': 's3://aws-athena-query-results-4bfast/'  # Ajustar se necessário
        }
    }
    
    try:
        # Executar query
        print(f"🔍 Executando query: {query[:100]}...")
        response = client.start_query_execution(**query_config)
        query_execution_id = response['QueryExecutionId']
        
        # Aguardar conclusão
        while True:
            result = client.get_query_execution(QueryExecutionId=query_execution_id)
            status = result['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED']:
                break
            elif status in ['FAILED', 'CANCELLED']:
                error = result['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                print(f"❌ Query falhou: {error}")
                return None
            
            print("⏳ Aguardando query...")
            time.sleep(2)
        
        # Obter resultados
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        return results
        
    except Exception as e:
        print(f"❌ Erro na query: {e}")
        return None

def explore_focus_structure():
    """Explora a estrutura dos dados FOCUS no Athena"""
    
    print("=== EXPLORANDO ESTRUTURA FOCUS NO ATHENA ===\n")
    
    # 1. Listar tabelas no database costs
    print("1. 📋 TABELAS DISPONÍVEIS NO DATABASE 'costs':")
    print("=" * 50)
    
    query = "SHOW TABLES"
    results = execute_athena_query(query)
    
    if results:
        tables = []
        for row in results['ResultSet']['Rows'][1:]:  # Skip header
            table_name = row['Data'][0]['VarCharValue']
            tables.append(table_name)
            print(f"   📊 {table_name}")
        
        if not tables:
            print("   ❌ Nenhuma tabela encontrada")
            return
        
        # 2. Explorar estrutura da primeira tabela (provavelmente a principal)
        main_table = tables[0]
        print(f"\n2. 🔍 ESTRUTURA DA TABELA '{main_table}':")
        print("=" * 50)
        
        query = f"DESCRIBE {main_table}"
        results = execute_athena_query(query)
        
        if results:
            focus_columns = []
            for row in results['ResultSet']['Rows'][1:]:  # Skip header
                col_name = row['Data'][0]['VarCharValue']
                col_type = row['Data'][1]['VarCharValue']
                focus_columns.append((col_name, col_type))
                print(f"   {col_name:<30} {col_type}")
            
            # 3. Verificar campos FOCUS específicos
            print(f"\n3. ✅ CAMPOS FOCUS RELEVANTES ENCONTRADOS:")
            print("=" * 50)
            
            focus_fields = {
                'ResourceId': False,
                'ResourceName': False, 
                'ResourceType': False,
                'UsageType': False,
                'UsageUnit': False,
                'ServiceName': False,
                'ServiceCategory': False,
                'ChargeCategory': False,
                'BilledCost': False,
                'EffectiveCost': False
            }
            
            for col_name, col_type in focus_columns:
                for field in focus_fields:
                    if field.lower() in col_name.lower():
                        focus_fields[field] = True
                        print(f"   ✅ {field:<20} → {col_name} ({col_type})")
            
            # Mostrar campos ausentes
            missing_fields = [field for field, found in focus_fields.items() if not found]
            if missing_fields:
                print(f"\n   ❌ CAMPOS FOCUS NÃO ENCONTRADOS:")
                for field in missing_fields:
                    print(f"      - {field}")
            
            # 4. Amostra de dados
            print(f"\n4. 📊 AMOSTRA DE DADOS (últimos 5 registros):")
            print("=" * 50)
            
            # Buscar campos que provavelmente existem
            sample_fields = []
            for col_name, col_type in focus_columns[:10]:  # Primeiros 10 campos
                sample_fields.append(col_name)
            
            fields_str = ", ".join(sample_fields)
            query = f"""
            SELECT {fields_str}
            FROM {main_table}
            WHERE billingperiod >= '2025-08-01'
            ORDER BY billingperiod DESC
            LIMIT 5
            """
            
            results = execute_athena_query(query)
            
            if results and len(results['ResultSet']['Rows']) > 1:
                # Header
                headers = [col['VarCharValue'] for col in results['ResultSet']['Rows'][0]['Data']]
                print(f"   Campos: {' | '.join(headers[:5])}...")
                
                # Dados
                for i, row in enumerate(results['ResultSet']['Rows'][1:], 1):
                    values = []
                    for cell in row['Data'][:5]:  # Primeiros 5 campos
                        value = cell.get('VarCharValue', 'NULL')
                        values.append(value[:20] if value else 'NULL')  # Truncar valores longos
                    print(f"   {i}: {' | '.join(values)}...")
            
            # 5. Verificar se há ResourceId e UsageType específicos
            print(f"\n5. 🎯 VERIFICAÇÃO DE GRANULARIDADE:")
            print("=" * 50)
            
            # Tentar encontrar campos de recurso
            resource_fields = [col for col, _ in focus_columns if 'resource' in col.lower()]
            usage_fields = [col for col, _ in focus_columns if 'usage' in col.lower() and 'type' in col.lower()]
            
            if resource_fields:
                print(f"   📋 Campos de Recurso encontrados:")
                for field in resource_fields:
                    print(f"      - {field}")
                    
                # Amostra de ResourceIds
                resource_field = resource_fields[0]
                query = f"""
                SELECT DISTINCT {resource_field}
                FROM {main_table}
                WHERE {resource_field} IS NOT NULL
                AND billingperiod >= '2025-08-01'
                LIMIT 10
                """
                
                results = execute_athena_query(query)
                if results and len(results['ResultSet']['Rows']) > 1:
                    print(f"      Exemplos de {resource_field}:")
                    for row in results['ResultSet']['Rows'][1:]:
                        value = row['Data'][0].get('VarCharValue', 'NULL')
                        print(f"        - {value}")
            
            if usage_fields:
                print(f"\n   📋 Campos de Tipo de Uso encontrados:")
                for field in usage_fields:
                    print(f"      - {field}")
                    
                # Amostra de UsageTypes
                usage_field = usage_fields[0]
                query = f"""
                SELECT DISTINCT {usage_field}
                FROM {main_table}
                WHERE {usage_field} IS NOT NULL
                AND billingperiod >= '2025-08-01'
                LIMIT 10
                """
                
                results = execute_athena_query(query)
                if results and len(results['ResultSet']['Rows']) > 1:
                    print(f"      Exemplos de {usage_field}:")
                    for row in results['ResultSet']['Rows'][1:]:
                        value = row['Data'][0].get('VarCharValue', 'NULL')
                        print(f"        - {value}")
        
        print(f"\n=== EXPLORAÇÃO CONCLUÍDA ===")
        print("💡 Use essas informações para ajustar o modelo de dados e endpoint de variação")
    
    else:
        print("❌ Não foi possível listar tabelas")

if __name__ == "__main__":
    explore_focus_structure()
