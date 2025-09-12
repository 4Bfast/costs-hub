#!/usr/bin/env python3
"""
Script para consultar dados FOCUS na tabela costs.data
"""

import boto3
import time

def execute_athena_query(query, database='costs'):
    """Executa query no Athena e retorna resultados"""
    
    session = boto3.Session(profile_name='4bfast')
    client = session.client('athena', region_name='us-east-1')
    
    query_config = {
        'QueryString': query,
        'QueryExecutionContext': {'Database': database},
        'ResultConfiguration': {
            'OutputLocation': 's3://aws-athena-query-results-4bfast/'
        }
    }
    
    try:
        print(f"🔍 Executando: {query[:100]}...")
        response = client.start_query_execution(**query_config)
        query_execution_id = response['QueryExecutionId']
        
        while True:
            result = client.get_query_execution(QueryExecutionId=query_execution_id)
            status = result['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'CANCELLED']:
                error = result['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                print(f"❌ Query falhou: {error}")
                return None
            
            time.sleep(1)
        
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        return results
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None

def analyze_focus_structure():
    """Analisa a estrutura da tabela FOCUS"""
    
    print("=== ANALISANDO DADOS FOCUS ===\n")
    
    # 1. Estrutura da tabela
    print("1. 📋 ESTRUTURA DA TABELA costs.data:")
    print("=" * 50)
    
    results = execute_athena_query("DESCRIBE data")
    
    if results:
        focus_columns = []
        resource_fields = []
        usage_fields = []
        
        for row in results['ResultSet']['Rows'][1:]:
            col_name = row['Data'][0]['VarCharValue']
            col_type = row['Data'][1]['VarCharValue']
            focus_columns.append((col_name, col_type))
            
            # Identificar campos importantes
            if 'resource' in col_name.lower():
                resource_fields.append(col_name)
            if 'usage' in col_name.lower() and 'type' in col_name.lower():
                usage_fields.append(col_name)
            
            # Destacar campos FOCUS importantes
            if any(keyword in col_name.lower() for keyword in ['resource', 'usage', 'service', 'charge', 'cost', 'billing']):
                print(f"   ✅ {col_name:<35} {col_type}")
            else:
                print(f"      {col_name:<35} {col_type}")
        
        # 2. Campos específicos para variação
        print(f"\n2. 🎯 CAMPOS RELEVANTES PARA ANÁLISE DE VARIAÇÃO:")
        print("=" * 50)
        
        if resource_fields:
            print(f"   📋 Campos de Recurso:")
            for field in resource_fields:
                print(f"      ✅ {field}")
        
        if usage_fields:
            print(f"   📋 Campos de Tipo de Uso:")
            for field in usage_fields:
                print(f"      ✅ {field}")
        
        # 3. Amostra de dados
        print(f"\n3. 📊 AMOSTRA DE DADOS RECENTES:")
        print("=" * 50)
        
        # Campos essenciais para variação
        essential_fields = []
        for col_name, _ in focus_columns:
            if any(keyword in col_name.lower() for keyword in ['resource', 'usage', 'service', 'charge', 'cost', 'billing']):
                essential_fields.append(col_name)
        
        if essential_fields:
            fields_str = ", ".join(essential_fields[:10])  # Limitar campos
            
            query = f"""
            SELECT {fields_str}
            FROM data
            WHERE billingperiod >= '2025-08-01'
            ORDER BY billingperiod DESC
            LIMIT 5
            """
            
            results = execute_athena_query(query)
            
            if results and len(results['ResultSet']['Rows']) > 1:
                # Headers
                headers = [col['VarCharValue'] for col in results['ResultSet']['Rows'][0]['Data']]
                print(f"   Campos: {' | '.join(headers[:5])}...")
                
                # Dados
                for i, row in enumerate(results['ResultSet']['Rows'][1:], 1):
                    values = []
                    for cell in row['Data'][:5]:
                        value = cell.get('VarCharValue', 'NULL')
                        values.append(value[:25] if value else 'NULL')
                    print(f"   {i}: {' | '.join(values)}...")
        
        # 4. Verificar ResourceId específicos
        if resource_fields:
            print(f"\n4. 🔍 EXEMPLOS DE RESOURCE IDs:")
            print("=" * 50)
            
            resource_field = resource_fields[0]
            query = f"""
            SELECT DISTINCT {resource_field}
            FROM data
            WHERE {resource_field} IS NOT NULL
            AND {resource_field} != ''
            AND billingperiod >= '2025-08-01'
            LIMIT 10
            """
            
            results = execute_athena_query(query)
            
            if results and len(results['ResultSet']['Rows']) > 1:
                print(f"   Exemplos de {resource_field}:")
                for row in results['ResultSet']['Rows'][1:]:
                    value = row['Data'][0].get('VarCharValue', 'NULL')
                    if value and value != 'NULL':
                        print(f"      - {value}")
        
        # 5. Verificar UsageType específicos
        if usage_fields:
            print(f"\n5. 📋 EXEMPLOS DE USAGE TYPES:")
            print("=" * 50)
            
            usage_field = usage_fields[0]
            query = f"""
            SELECT DISTINCT {usage_field}
            FROM data
            WHERE {usage_field} IS NOT NULL
            AND {usage_field} != ''
            AND billingperiod >= '2025-08-01'
            LIMIT 10
            """
            
            results = execute_athena_query(query)
            
            if results and len(results['ResultSet']['Rows']) > 1:
                print(f"   Exemplos de {usage_field}:")
                for row in results['ResultSet']['Rows'][1:]:
                    value = row['Data'][0].get('VarCharValue', 'NULL')
                    if value and value != 'NULL':
                        print(f"      - {value}")
        
        # 6. Contagem de registros
        print(f"\n6. 📊 ESTATÍSTICAS DOS DADOS:")
        print("=" * 50)
        
        query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT billingperiod) as billing_periods,
            MIN(billingperiod) as oldest_period,
            MAX(billingperiod) as newest_period
        FROM data
        """
        
        results = execute_athena_query(query)
        
        if results and len(results['ResultSet']['Rows']) > 1:
            row = results['ResultSet']['Rows'][1]
            total = row['Data'][0].get('VarCharValue', '0')
            periods = row['Data'][1].get('VarCharValue', '0')
            oldest = row['Data'][2].get('VarCharValue', 'N/A')
            newest = row['Data'][3].get('VarCharValue', 'N/A')
            
            print(f"   📊 Total de registros: {total}")
            print(f"   📅 Períodos de billing: {periods}")
            print(f"   📅 Período mais antigo: {oldest}")
            print(f"   📅 Período mais recente: {newest}")
    
    print(f"\n=== ANÁLISE CONCLUÍDA ===")
    print("💡 Use essas informações para implementar ResourceId e UsageType reais")

if __name__ == "__main__":
    analyze_focus_structure()
