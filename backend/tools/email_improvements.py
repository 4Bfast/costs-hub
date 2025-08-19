"""
Melhorias para o sistema de envio de emails
- Logs detalhados
- Endpoint de reenvio de convite
- Melhor tratamento de erros
"""

# Código para substituir no routes.py

# 1. Melhorar o endpoint de convite existente
@api_bp.route('/users/invite', methods=['POST'])
@token_required
def invite_user(current_user):
    """Convida um novo usuário para a organização (apenas ADMIN)."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem convidar usuários.'}), 403
        
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email é obrigatório'}), 400
        
        logging.info(f"🔄 Iniciando processo de convite para {email} pela organização {current_user.organization_id}")
        
        # Verificar se já existe um usuário com este email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.organization_id == current_user.organization_id:
                return jsonify({'error': 'Este usuário já faz parte da organização'}), 400
            else:
                return jsonify({'error': 'Este email já está em uso por outra organização'}), 400
        
        # Gerar token de convite
        invitation_token = generate_invitation_token()
        invitation_expires_at = datetime.utcnow() + timedelta(hours=48)  # 48 horas
        
        # Criar novo usuário com status PENDING_INVITE
        new_user = User(
            email=email,
            organization_id=current_user.organization_id,
            status='PENDING_INVITE',
            role='MEMBER',
            invitation_token=invitation_token,
            invitation_expires_at=invitation_expires_at,
            password_hash=None  # Será definido quando aceitar o convite
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        logging.info(f"✅ Usuário {email} criado com status PENDING_INVITE (ID: {new_user.id})")
        
        # Enviar email de convite com logs detalhados
        email_sent = False
        email_error = None
        
        try:
            logging.info(f"📧 Tentando enviar email de convite para {email}...")
            from .notifications import send_invitation_email
            email_sent = send_invitation_email(new_user, current_user.organization)
            
            if email_sent:
                logging.info(f"✅ Email de convite enviado com sucesso para {email}")
            else:
                logging.error(f"❌ Falha ao enviar email de convite para {email}")
                email_error = "Falha no envio do email"
                
        except Exception as e:
            email_error = str(e)
            logging.error(f"❌ Erro ao enviar email de convite para {email}: {email_error}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
        
        # Retornar resposta com status do email
        response_data = {
            'message': 'Usuário convidado com sucesso',
            'user_id': new_user.id,
            'email': new_user.email,
            'email_sent': email_sent
        }
        
        if email_error:
            response_data['email_error'] = email_error
            response_data['message'] = 'Usuário criado, mas houve problema no envio do email'
        
        return jsonify(response_data), 201
        
    except Exception as e:
        logging.error(f"❌ Erro geral no convite de usuário: {str(e)}")
        return jsonify({'error': str(e)}), 500


# 2. Novo endpoint para reenviar convite
@api_bp.route('/users/<int:user_id>/resend-invite', methods=['POST'])
@token_required
def resend_invitation(current_user, user_id):
    """Reenvia convite para um usuário pendente (apenas ADMIN)."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem reenviar convites.'}), 403
        
        # Buscar o usuário
        user = User.query.filter_by(
            id=user_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Verificar se o usuário está com convite pendente
        if user.status != 'PENDING_INVITE':
            return jsonify({'error': 'Este usuário não possui convite pendente'}), 400
        
        logging.info(f"🔄 Reenviando convite para {user.email} (ID: {user.id})")
        
        # Gerar novo token e estender prazo
        user.invitation_token = generate_invitation_token()
        user.invitation_expires_at = datetime.utcnow() + timedelta(hours=48)
        db.session.commit()
        
        logging.info(f"🔄 Token de convite renovado para {user.email}")
        
        # Tentar reenviar email
        email_sent = False
        email_error = None
        
        try:
            logging.info(f"📧 Reenviando email de convite para {user.email}...")
            from .notifications import send_invitation_email
            email_sent = send_invitation_email(user, current_user.organization)
            
            if email_sent:
                logging.info(f"✅ Email de convite reenviado com sucesso para {user.email}")
            else:
                logging.error(f"❌ Falha ao reenviar email de convite para {user.email}")
                email_error = "Falha no envio do email"
                
        except Exception as e:
            email_error = str(e)
            logging.error(f"❌ Erro ao reenviar email de convite para {user.email}: {email_error}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
        
        # Retornar resposta
        response_data = {
            'message': 'Convite reenviado com sucesso' if email_sent else 'Token renovado, mas houve problema no envio do email',
            'user_id': user.id,
            'email': user.email,
            'email_sent': email_sent,
            'new_expiration': user.invitation_expires_at.isoformat()
        }
        
        if email_error:
            response_data['email_error'] = email_error
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logging.error(f"❌ Erro ao reenviar convite: {str(e)}")
        return jsonify({'error': str(e)}), 500


# 3. Endpoint para testar configuração de email (apenas ADMIN)
@api_bp.route('/admin/test-email', methods=['POST'])
@token_required
def test_email_config(current_user):
    """Testa a configuração de email (apenas ADMIN)."""
    try:
        # Verificar se o usuário atual é ADMIN
        if not current_user.is_admin():
            return jsonify({'error': 'Acesso negado. Apenas administradores podem testar email.'}), 403
        
        data = request.get_json()
        test_email = data.get('email', current_user.email)
        
        logging.info(f"🧪 Testando configuração de email para {test_email}")
        
        # Testar configuração
        from .notifications import test_email_configuration, send_test_email
        
        config_result = test_email_configuration()
        
        # Tentar enviar email de teste
        email_sent = False
        if config_result['test_successful']:
            try:
                email_sent = send_test_email(test_email)
            except Exception as e:
                logging.error(f"Erro ao enviar email de teste: {str(e)}")
        
        return jsonify({
            'configuration': config_result,
            'test_email_sent': email_sent,
            'test_email_address': test_email
        }), 200
        
    except Exception as e:
        logging.error(f"❌ Erro no teste de email: {str(e)}")
        return jsonify({'error': str(e)}), 500
