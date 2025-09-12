#!/usr/bin/env python3
"""
Script para encontrar dados FOCUS no AWS
"""

import boto3
import time

def list_s3_buckets_and_objects():
    """Lista buckets S3 que podem conter dados FOCUS"""
    
    session = boto3.Session(profile_name='4bfast')
    s3 = session.client('s3')
    
    print("=== BUCKETS S3 DISPONÍVEIS ===")
    
    try:
        response = s3.list_buckets()
        
        for bucket in response['Buckets']:
            bucket_name = bucket['Name']
            print(f"\n📦 Bucket: {bucket_name}")
            
            # Verificar se contém dados relacionados a custos/FOCUS
            if any(keyword in bucket_name.lower() for keyword in ['cost', 'focus', 'billing', 'cur']):
                print(f"   ✅ Possível bucket de custos!")
                
                try:
                    # Listar alguns objetos
                    objects = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
                    
                    if 'Contents' in objects:
                        print(f"   📄 Objetos encontrados:")
                        for obj in objects['Contents'][:5]:
                            key = obj['Key']
                            size = obj['Size']
                            print(f"      - {key} ({size} bytes)")
                    else:
                        print(f"   📄 Bucket vazio")
                        
                except Exception as e:
                    print(f"   ❌ Erro ao listar objetos: {e}")
            else:
                print(f"   📄 Bucket genérico")
                
    except Exception as e:
        print(f"❌ Erro ao listar buckets: {e}")

def check_athena_workgroups():
    """Verifica workgroups do Athena"""
    
    session = boto3.Session(profile_name='4bfast')
    athena = session.client('athena')
    
    print("\n=== WORKGROUPS ATHENA ===")
    
    try:
        response = athena.list_work_groups()
        
        for wg in response['WorkGroups']:
            wg_name = wg['Name']
            state = wg['State']
            print(f"📊 Workgroup: {wg_name} ({state})")
            
    except Exception as e:
        print(f"❌ Erro ao listar workgroups: {e}")

def check_glue_databases():
    """Verifica databases no Glue Catalog"""
    
    session = boto3.Session(profile_name='4bfast')
    glue = session.client('glue')
    
    print("\n=== DATABASES GLUE CATALOG ===")
    
    try:
        response = glue.get_databases()
        
        for db in response['DatabaseList']:
            db_name = db['Name']
            print(f"📊 Database: {db_name}")
            
            # Listar tabelas neste database
            try:
                tables_response = glue.get_tables(DatabaseName=db_name)
                
                for table in tables_response['TableList']:
                    table_name = table['Name']
                    location = table.get('StorageDescriptor', {}).get('Location', 'N/A')
                    
                    # Verificar se é tabela de custos
                    if any(keyword in table_name.lower() for keyword in ['cost', 'focus', 'billing', 'cur']):
                        print(f"   ✅ {table_name} (possível tabela FOCUS)")
                        print(f"      📍 Location: {location}")
                        
                        # Mostrar algumas colunas
                        columns = table.get('StorageDescriptor', {}).get('Columns', [])
                        focus_columns = [col['Name'] for col in columns if any(keyword in col['Name'].lower() for keyword in ['resource', 'usage', 'service', 'charge'])]
                        
                        if focus_columns:
                            print(f"      📋 Colunas FOCUS: {', '.join(focus_columns[:5])}...")
                    else:
                        print(f"      {table_name}")
                        
            except Exception as e:
                print(f"   ❌ Erro ao listar tabelas: {e}")
                
    except Exception as e:
        print(f"❌ Erro ao listar databases: {e}")

def main():
    print("=== PROCURANDO DADOS FOCUS NA AWS ===\n")
    
    # 1. Verificar buckets S3
    list_s3_buckets_and_objects()
    
    # 2. Verificar workgroups Athena
    check_athena_workgroups()
    
    # 3. Verificar Glue Catalog
    check_glue_databases()
    
    print(f"\n=== BUSCA CONCLUÍDA ===")
    print("💡 Procure por databases/tabelas que contenham dados FOCUS")
    print("💡 Verifique se há configuração específica de workgroup no Athena")

if __name__ == "__main__":
    main()
