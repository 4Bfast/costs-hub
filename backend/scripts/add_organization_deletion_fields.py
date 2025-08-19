#!/usr/bin/env python3
"""
Migration para adicionar campos de soft delete na tabela organizations
"""

from app import create_app
from app.models import db
from sqlalchemy import text

def add_organization_deletion_fields():
    """Adiciona campos para soft delete de organizações"""
    
    print("🔧 ADICIONANDO CAMPOS DE SOFT DELETE - ORGANIZATIONS")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            # Executar ALTER TABLE para adicionar os novos campos
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE organizations 
                    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ACTIVE',
                    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL,
                    ADD COLUMN IF NOT EXISTS deletion_reason TEXT NULL,
                    ADD COLUMN IF NOT EXISTS deleted_by_user_id INTEGER NULL
                """))
                conn.commit()
            
            print("✅ Campos adicionados com sucesso:")
            print("   - status: VARCHAR(20) DEFAULT 'ACTIVE'")
            print("   - deleted_at: TIMESTAMP NULL")
            print("   - deletion_reason: TEXT NULL") 
            print("   - deleted_by_user_id: INTEGER NULL")
            
            # Verificar se os campos foram criados
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name, data_type, column_default, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'organizations' 
                    AND column_name IN ('status', 'deleted_at', 'deletion_reason', 'deleted_by_user_id')
                    ORDER BY column_name
                """))
                
                print("\n📋 Verificação dos campos criados:")
                for row in result:
                    print(f"   - {row[0]}: {row[1]} (default: {row[2]}, nullable: {row[3]})")
                
        except Exception as e:
            print(f"❌ Erro ao adicionar campos: {str(e)}")
            raise

if __name__ == "__main__":
    add_organization_deletion_fields()
