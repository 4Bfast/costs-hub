"""
AWS SES Email Sender for CostHub Reports
"""

import boto3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SESEmailSender:
    """Send CostHub reports via AWS SES"""
    
    def __init__(self, aws_config, ses_config: Dict[str, Any] = None):
        self.aws_config = aws_config
        self.ses_config = ses_config or {}
        
        # Initialize SES client
        self.session = boto3.Session(
            profile_name=aws_config.profile_name,
            region_name=self.ses_config.get('region', 'us-east-1')  # SES regions
        )
        self.ses_client = self.session.client('ses')
        
        # Default configuration
        self.from_email = self.ses_config.get('from_email', 'costhub@yourdomain.com')
        self.reply_to = self.ses_config.get('reply_to', self.from_email)
        
    def send_cost_report_email(self, 
                              email_report: Dict[str, str],
                              recipients: List[str],
                              cc_recipients: List[str] = None,
                              bcc_recipients: List[str] = None) -> Dict[str, Any]:
        """Send cost report email via SES"""
        
        try:
            # Prepare destination
            destination = {
                'ToAddresses': recipients
            }
            
            if cc_recipients:
                destination['CcAddresses'] = cc_recipients
            
            if bcc_recipients:
                destination['BccAddresses'] = bcc_recipients
            
            # Send email
            response = self.ses_client.send_email(
                Source=self.from_email,
                Destination=destination,
                Message={
                    'Subject': {
                        'Data': email_report['subject'],
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': email_report['html_body'],
                            'Charset': 'UTF-8'
                        },
                        'Text': {
                            'Data': email_report['text_body'],
                            'Charset': 'UTF-8'
                        }
                    }
                },
                ReplyToAddresses=[self.reply_to]
            )
            
            logger.info(f"Email sent successfully. MessageId: {response['MessageId']}")
            
            return {
                'success': True,
                'message_id': response['MessageId'],
                'recipients': recipients,
                'sent_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                'success': False,
                'error': str(e),
                'recipients': recipients,
                'attempted_at': datetime.now().isoformat()
            }
    
    def create_ses_template(self, template_name: str, email_report: Dict[str, str]) -> Dict[str, Any]:
        """Create SES email template"""
        
        try:
            # Create template
            response = self.ses_client.create_template(
                Template={
                    'TemplateName': template_name,
                    'SubjectPart': email_report['subject'],
                    'HtmlPart': email_report['html_body'],
                    'TextPart': email_report['text_body']
                }
            )
            
            logger.info(f"SES template created: {template_name}")
            
            return {
                'success': True,
                'template_name': template_name,
                'created_at': datetime.now().isoformat()
            }
            
        except self.ses_client.exceptions.AlreadyExistsException:
            logger.warning(f"Template {template_name} already exists, updating...")
            return self.update_ses_template(template_name, email_report)
            
        except Exception as e:
            logger.error(f"Failed to create SES template: {e}")
            return {
                'success': False,
                'error': str(e),
                'template_name': template_name
            }
    
    def update_ses_template(self, template_name: str, email_report: Dict[str, str]) -> Dict[str, Any]:
        """Update existing SES email template"""
        
        try:
            response = self.ses_client.update_template(
                Template={
                    'TemplateName': template_name,
                    'SubjectPart': email_report['subject'],
                    'HtmlPart': email_report['html_body'],
                    'TextPart': email_report['text_body']
                }
            )
            
            logger.info(f"SES template updated: {template_name}")
            
            return {
                'success': True,
                'template_name': template_name,
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update SES template: {e}")
            return {
                'success': False,
                'error': str(e),
                'template_name': template_name
            }
    
    def send_templated_email(self, 
                           template_name: str,
                           recipients: List[str],
                           template_data: Dict[str, Any] = None,
                           cc_recipients: List[str] = None,
                           bcc_recipients: List[str] = None) -> Dict[str, Any]:
        """Send email using SES template"""
        
        try:
            # Prepare destination
            destination = {
                'ToAddresses': recipients
            }
            
            if cc_recipients:
                destination['CcAddresses'] = cc_recipients
            
            if bcc_recipients:
                destination['BccAddresses'] = bcc_recipients
            
            # Send templated email
            response = self.ses_client.send_templated_email(
                Source=self.from_email,
                Destination=destination,
                Template=template_name,
                TemplateData=json.dumps(template_data or {}),
                ReplyToAddresses=[self.reply_to]
            )
            
            logger.info(f"Templated email sent successfully. MessageId: {response['MessageId']}")
            
            return {
                'success': True,
                'message_id': response['MessageId'],
                'template_name': template_name,
                'recipients': recipients,
                'sent_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send templated email: {e}")
            return {
                'success': False,
                'error': str(e),
                'template_name': template_name,
                'recipients': recipients,
                'attempted_at': datetime.now().isoformat()
            }
    
    def send_bulk_templated_email(self, 
                                template_name: str,
                                destinations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send bulk emails using SES template"""
        
        try:
            # Prepare destinations for bulk send
            bulk_destinations = []
            
            for dest in destinations:
                bulk_dest = {
                    'Destination': {
                        'ToAddresses': dest['recipients']
                    },
                    'ReplacementTemplateData': json.dumps(dest.get('template_data', {}))
                }
                
                if dest.get('cc_recipients'):
                    bulk_dest['Destination']['CcAddresses'] = dest['cc_recipients']
                
                if dest.get('bcc_recipients'):
                    bulk_dest['Destination']['BccAddresses'] = dest['bcc_recipients']
                
                bulk_destinations.append(bulk_dest)
            
            # Send bulk email
            response = self.ses_client.send_bulk_templated_email(
                Source=self.from_email,
                Template=template_name,
                DefaultTemplateData=json.dumps({}),
                Destinations=bulk_destinations,
                ReplyToAddresses=[self.reply_to]
            )
            
            logger.info(f"Bulk email sent successfully. MessageIds: {len(response['MessageId'])}")
            
            return {
                'success': True,
                'message_ids': response['MessageId'],
                'template_name': template_name,
                'total_recipients': len(destinations),
                'sent_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send bulk email: {e}")
            return {
                'success': False,
                'error': str(e),
                'template_name': template_name,
                'total_recipients': len(destinations),
                'attempted_at': datetime.now().isoformat()
            }
    
    def verify_email_address(self, email: str) -> Dict[str, Any]:
        """Verify email address for SES"""
        
        try:
            response = self.ses_client.verify_email_identity(
                EmailAddress=email
            )
            
            logger.info(f"Verification email sent to: {email}")
            
            return {
                'success': True,
                'email': email,
                'verification_sent_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to verify email {email}: {e}")
            return {
                'success': False,
                'error': str(e),
                'email': email
            }
    
    def get_send_quota(self) -> Dict[str, Any]:
        """Get SES sending quota and rate"""
        
        try:
            response = self.ses_client.get_send_quota()
            
            return {
                'success': True,
                'max_24_hour': response['Max24HourSend'],
                'max_send_rate': response['MaxSendRate'],
                'sent_last_24_hours': response['SentLast24Hours']
            }
            
        except Exception as e:
            logger.error(f"Failed to get send quota: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_verified_emails(self) -> Dict[str, Any]:
        """List verified email addresses"""
        
        try:
            response = self.ses_client.list_verified_email_addresses()
            
            return {
                'success': True,
                'verified_emails': response['VerifiedEmailAddresses']
            }
            
        except Exception as e:
            logger.error(f"Failed to list verified emails: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class CostHubEmailService:
    """High-level service for sending CostHub reports"""
    
    def __init__(self, aws_config, ses_config: Dict[str, Any] = None):
        self.ses_sender = SESEmailSender(aws_config, ses_config)
        self.ses_config = ses_config or {}
    
    def send_cost_analysis_report(self, 
                                email_report: Dict[str, str],
                                recipient_groups: Dict[str, List[str]]) -> Dict[str, Any]:
        """Send cost analysis report to different recipient groups"""
        
        results = []
        
        # Send to executives (TO)
        if recipient_groups.get('executives'):
            result = self.ses_sender.send_cost_report_email(
                email_report=email_report,
                recipients=recipient_groups['executives']
            )
            results.append({
                'group': 'executives',
                'result': result
            })
        
        # Send to finance team (TO) with devops in CC
        if recipient_groups.get('finance'):
            result = self.ses_sender.send_cost_report_email(
                email_report=email_report,
                recipients=recipient_groups['finance'],
                cc_recipients=recipient_groups.get('devops', [])
            )
            results.append({
                'group': 'finance',
                'result': result
            })
        
        # Send alerts if cost increase is significant
        metadata = email_report.get('metadata', {})
        cost_change_percent = metadata.get('cost_change_percent', 0)
        
        if abs(cost_change_percent) > 10 and recipient_groups.get('alerts'):
            result = self.ses_sender.send_cost_report_email(
                email_report=email_report,
                recipients=recipient_groups['alerts']
            )
            results.append({
                'group': 'alerts',
                'result': result
            })
        
        return {
            'total_groups': len(results),
            'results': results,
            'sent_at': datetime.now().isoformat()
        }
    
    def setup_automated_reporting(self, 
                                template_name: str,
                                email_report: Dict[str, str]) -> Dict[str, Any]:
        """Setup SES template for automated reporting"""
        
        # Create or update template
        template_result = self.ses_sender.create_ses_template(template_name, email_report)
        
        if template_result['success']:
            logger.info(f"Automated reporting template ready: {template_name}")
        
        return template_result