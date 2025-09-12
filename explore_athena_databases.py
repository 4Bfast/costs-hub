#!/usr/bin/env python3
"""
Script para explorar databases disponíveis no Athena
"""

import boto3
import time

def execute_athena_query(query, database=None):
    """Executa query no Athena e retorna resultados"""
    
    # Usar profile AWS configurado
    session = boto3.Session(profile_name='4bfast')
    client = session.client('athena', region_name='us-east-1')
    
    # Configuração da query
    query_config = {
        'QueryString': query,
        'ResultConfiguration': {
            'OutputLocation': 's3://aws-athena-query-results-4bfast/'
        }
    }
    
    if database:
        query_config['QueryExecutionContext'] = {'Database': database}
    
    try:
        # Executar query
        print(f"🔍 Executando: {query}")
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
            
            time.sleep(1)
        
        # Obter resultados
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        return results
        
    except Exception as e:
        print(f"❌ Erro na query: {e}")
        return None

def explore_athena():
    """Explora databases e tabelas no Athena"""
    
    print("=== EXPLORANDO ATHENA ===\n")
    
    # 1. Listar databases
    print("1. 📋 DATABASES DISPONÍVEIS:")
    print("=" * 30)
    
    results = execute_athena_query("SHOW DATABASES")
    
    if results:
        databases = []
        for row in results['ResultSet']['Rows'][1:]:  # Skip header
            db_name = row['Data'][0]['VarCharValue']
            databases.append(db_name)
            print(f"   📊 {db_name}")
        
        # 2. Para cada database, listar tabelas
        for db in databases:
            print(f"\n2. 📋 TABELAS NO DATABASE '{db}':")
            print("=" * 40)
            
            results = execute_athena_query("SHOW TABLES", database=db)
            
            if results:
                tables = []
                for row in results['ResultSet']['Rows'][1:]:  # Skip header
                    table_name = row['Data'][0]['VarCharValue']
                    tables.append(table_name)
                    print(f"   📊 {table_name}")
                
                # 3. Para tabelas que parecem ser FOCUS, mostrar estrutura
                focus_tables = [t for t in tables if any(keyword in t.lower() for keyword in ['focus', 'cost', 'billing'])]
                
                for table in focus_tables[:2]:  # Limitar a 2 tabelas
                    print(f"\n3. 🔍 ESTRUTURA DA TABELA '{db}.{table}':")
                    print("=" * 50)
                    
                    results = execute_athena_query(f"DESCRIBE {table}", database=db)
                    
                    if results:
                        focus_fields = []
                        for row in results['ResultSet']['Rows'][1:]:  # Skip header
                            col_name = row['Data'][0]['VarCharValue']
                            col_type = row['Data'][1]['VarCharValue']
                            focus_fields.append((col_name, col_type))
                            
                            # Destacar campos FOCUS importantes
                            if any(keyword in col_name.lower() for keyword in ['resource', 'usage', 'service', 'charge', 'cost']):
                                print(f"   ✅ {col_name:<30} {col_type}")
                            else:
                                print(f"      {col_name:<30} {col_type}")
                        
                        # Verificar campos específicos
                        resource_fields = [col for col, _ in focus_fields if 'resource' in col.lower()]
                        usage_fields = [col for col, _ in focus_fields if 'usage' in col.lower()]
                        
                        if resource_fields or usage_fields:
                            print(f"\n   🎯 CAMPOS RELEVANTES PARA VARIAÇÃO:")
                            if resource_fields:
                                print(f"      📋 Recursos: {', '.join(resource_fields)}")
                            if usage_fields:
                                print(f"      📋 Uso: {', '.join(usage_fields)}")
                
                if not tables:
                    print("   ❌ Nenhuma tabela encontrada")
            else:
                print("   ❌ Erro ao listar tabelas")
    
    print(f"\n=== EXPLORAÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    explore_athena()
