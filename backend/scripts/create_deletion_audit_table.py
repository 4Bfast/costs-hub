#!/usr/bin/env python3
"""
Script para criar tabela de auditoria de exclusão de organizações
"""

from app import create_app
from app.models import db, OrganizationDeletionLog

def create_deletion_audit_table():
    """Cria a tabela de auditoria de exclusão"""
    
    print("🔧 CRIANDO TABELA DE AUDITORIA - ORGANIZATION_DELETION_LOGS")
    print("=" * 70)
    
    app = create_app()
    with app.app_context():
        try:
            # Criar a tabela
            db.create_all()
            
            print("✅ Tabela de auditoria criada com sucesso:")
            print("   - organization_deletion_logs")
            
            # Verificar se a tabela foi criada
            from sqlalchemy import text
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'organization_deletion_logs'
                    ORDER BY ordinal_position
                """))
                
                print("\n📋 Colunas da tabela criada:")
                for row in result:
                    print(f"   - {row[0]}: {row[1]} (nullable: {row[2]})")
                
        except Exception as e:
            print(f"❌ Erro ao criar tabela: {str(e)}")
            raise

if __name__ == "__main__":
    create_deletion_audit_table()
