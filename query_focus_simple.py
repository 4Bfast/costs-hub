#!/usr/bin/env python3
"""
Script simples para consultar dados FOCUS
"""

import boto3
import time

def execute_athena_query(query, database='costs'):
    """Executa query no Athena"""
    
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
        print(f"🔍 Query: {query}")
        response = client.start_query_execution(**query_config)
        query_execution_id = response['QueryExecutionId']
        
        while True:
            result = client.get_query_execution(QueryExecutionId=query_execution_id)
            status = result['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'CANCELLED']:
                error = result['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
                print(f"❌ Falhou: {error}")
                return None
            
            time.sleep(1)
        
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Processar resultados
        if results['ResultSet']['Rows']:
            print(f"✅ {len(results['ResultSet']['Rows'])} linhas retornadas")
            
            for i, row in enumerate(results['ResultSet']['Rows'][:10]):  # Primeiras 10 linhas
                values = []
                for cell in row['Data']:
                    value = cell.get('VarCharValue', 'NULL')
                    values.append(value[:30] if value else 'NULL')
                print(f"   {i}: {' | '.join(values)}")
        
        return results
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None

def main():
    print("=== CONSULTA SIMPLES FOCUS ===\n")
    
    # 1. Verificar se tabela existe
    print("1. Verificando tabela...")
    execute_athena_query("SELECT COUNT(*) FROM data LIMIT 1")
    
    # 2. Mostrar estrutura
    print("\n2. Estrutura da tabela...")
    execute_athena_query("DESCRIBE data")
    
    # 3. Amostra de dados
    print("\n3. Amostra de dados...")
    execute_athena_query("SELECT * FROM data LIMIT 3")

if __name__ == "__main__":
    main()
