"""
Lambda Asset Manager for S3-based Asset Management

Handles client logos, branding assets, and image optimization for email compatibility.
Optimized for Lambda environment with S3 integration.
"""

import boto3
import base64
import io
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image
from botocore.exceptions import ClientError

try:
    from ..models.config_models import ClientConfig
    from ..utils.logging import create_logger as get_logger
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.config_models import ClientConfig
    from utils.logging import create_logger
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class LambdaAssetManager:
    """S3-based asset management for client logos and branding"""
    
    def __init__(self, s3_bucket: str, s3_prefix: str = "assets"):
        """
        Initialize Lambda Asset Manager
        
        Args:
            s3_bucket: S3 bucket name for storing assets
            s3_prefix: S3 prefix for asset storage
        """
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.s3_client = boto3.client('s3')
        
        # Email-safe image constraints
        self.email_max_width = 600
        self.email_max_height = 200
        self.email_max_size_kb = 100  # 100KB max for email images
        
    def get_client_logo_url(self, client_id: str, expiration: int = 3600) -> Optional[str]:
        """
        Get presigned URL for client logo
        
        Args:
            client_id: Client identifier
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL for the logo or None if not found
        """
        try:
            # Try different logo file extensions
            logo_extensions = ['png', 'jpg', 'jpeg', 'svg', 'gif']
            
            for ext in logo_extensions:
                s3_key = f"{self.s3_prefix}/{client_id}/logo.{ext}"
                
                if self._object_exists(s3_key):
                    url = self._generate_presigned_url(s3_key, expiration)
                    logger.info(f"Generated presigned URL for client {client_id} logo")
                    return url
            
            logger.warning(f"No logo found for client {client_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting logo URL for client {client_id}: {e}")
            return None
    
    def upload_client_asset(self, client_id: str, asset_data: bytes, 
                           asset_type: str, filename: str = None) -> str:
        """
        Upload client asset to S3
        
        Args:
            client_id: Client identifier
            asset_data: Asset binary data
            asset_type: Type of asset (logo, favicon, etc.)
            filename: Optional filename (auto-generated if not provided)
            
        Returns:
            S3 key of uploaded asset
        """
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                extension = self._detect_image_format(asset_data)
                filename = f"{asset_type}_{timestamp}.{extension}"
            
            s3_key = f"{self.s3_prefix}/{client_id}/{filename}"
            
            # Determine content type
            content_type = self._get_content_type(filename)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=asset_data,
                ContentType=content_type,
                Metadata={
                    'client_id': client_id,
                    'asset_type': asset_type,
                    'uploaded_at': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Asset uploaded successfully: s3://{self.s3_bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error uploading asset for client {client_id}: {e}")
            raise
    
    def optimize_logo_for_email(self, logo_data: bytes) -> bytes:
        """
        Optimize logo for email compatibility
        
        Args:
            logo_data: Original logo binary data
            
        Returns:
            Optimized logo binary data
        """
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(logo_data))
            
            # Convert to RGB if necessary (for JPEG output)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Resize if too large
            if image.width > self.email_max_width or image.height > self.email_max_height:
                image.thumbnail((self.email_max_width, self.email_max_height), Image.Resampling.LANCZOS)
                logger.info(f"Resized image to {image.width}x{image.height}")
            
            # Save optimized image
            output = io.BytesIO()
            
            # Try PNG first (better for logos with transparency)
            image.save(output, format='PNG', optimize=True)
            png_size = len(output.getvalue())
            
            # If PNG is too large, try JPEG
            if png_size > self.email_max_size_kb * 1024:
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=85, optimize=True)
                jpeg_size = len(output.getvalue())
                
                # If JPEG is still too large, reduce quality
                if jpeg_size > self.email_max_size_kb * 1024:
                    output = io.BytesIO()
                    image.save(output, format='JPEG', quality=70, optimize=True)
                    logger.info("Reduced JPEG quality to 70% for email compatibility")
            
            optimized_data = output.getvalue()
            logger.info(f"Optimized logo: {len(logo_data)} -> {len(optimized_data)} bytes")
            
            return optimized_data
            
        except Exception as e:
            logger.error(f"Error optimizing logo for email: {e}")
            # Return original data if optimization fails
            return logo_data
    
    def get_logo_base64(self, client_id: str, optimize_for_email: bool = False) -> Optional[str]:
        """
        Get logo as base64 string for embedding in HTML/email
        
        Args:
            client_id: Client identifier
            optimize_for_email: Whether to optimize for email compatibility
            
        Returns:
            Base64 encoded logo data URI or None if not found
        """
        try:
            # Get logo data from S3
            logo_data = self._get_logo_data(client_id)
            
            if not logo_data:
                return None
            
            # Optimize for email if requested
            if optimize_for_email:
                logo_data = self.optimize_logo_for_email(logo_data)
            
            # Determine MIME type
            image_format = self._detect_image_format(logo_data)
            mime_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'svg': 'image/svg+xml'
            }
            
            mime_type = mime_types.get(image_format.lower(), 'image/png')
            
            # Encode to base64
            base64_data = base64.b64encode(logo_data).decode('utf-8')
            
            return f"data:{mime_type};base64,{base64_data}"
            
        except Exception as e:
            logger.error(f"Error getting base64 logo for client {client_id}: {e}")
            return None
    
    def get_logo_html(self, client_id: str, max_width: str = "280px", 
                     max_height: str = "auto", alt_text: str = None,
                     optimize_for_email: bool = False) -> str:
        """
        Get HTML img tag for client logo
        
        Args:
            client_id: Client identifier
            max_width: Maximum width CSS value
            max_height: Maximum height CSS value
            alt_text: Alt text for image
            optimize_for_email: Whether to optimize for email
            
        Returns:
            HTML img tag or fallback text
        """
        try:
            # Get base64 logo
            logo_base64 = self.get_logo_base64(client_id, optimize_for_email)
            
            if logo_base64:
                if not alt_text:
                    alt_text = f"Client {client_id} Logo"
                
                style = f"max-width: {max_width}; max-height: {max_height}; height: auto;"
                if optimize_for_email:
                    style += " display: block; margin: 0 auto;"
                
                return f'<img src="{logo_base64}" alt="{alt_text}" style="{style}">'
            
            # Fallback to text
            return f'<div style="font-size: 28px; font-weight: bold; color: #1e40af;">Client {client_id}</div>'
            
        except Exception as e:
            logger.error(f"Error generating logo HTML for client {client_id}: {e}")
            return f'<div style="font-size: 28px; font-weight: bold; color: #1e40af;">Client {client_id}</div>'
    
    def delete_client_assets(self, client_id: str) -> bool:
        """
        Delete all assets for a client
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if deletion successful
        """
        try:
            # List all objects with client prefix
            prefix = f"{self.s3_prefix}/{client_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                logger.info(f"No assets found for client {client_id}")
                return True
            
            # Delete all objects
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            
            self.s3_client.delete_objects(
                Bucket=self.s3_bucket,
                Delete={'Objects': objects_to_delete}
            )
            
            logger.info(f"Deleted {len(objects_to_delete)} assets for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting assets for client {client_id}: {e}")
            return False
    
    def list_client_assets(self, client_id: str) -> List[Dict[str, Any]]:
        """
        List all assets for a client
        
        Args:
            client_id: Client identifier
            
        Returns:
            List of asset information dictionaries
        """
        try:
            prefix = f"{self.s3_prefix}/{client_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            assets = []
            for obj in response['Contents']:
                # Get object metadata
                try:
                    head_response = self.s3_client.head_object(
                        Bucket=self.s3_bucket,
                        Key=obj['Key']
                    )
                    
                    assets.append({
                        'key': obj['Key'],
                        'filename': obj['Key'].split('/')[-1],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'content_type': head_response.get('ContentType'),
                        'metadata': head_response.get('Metadata', {})
                    })
                    
                except Exception as e:
                    logger.warning(f"Error getting metadata for {obj['Key']}: {e}")
                    assets.append({
                        'key': obj['Key'],
                        'filename': obj['Key'].split('/')[-1],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
            
            return assets
            
        except Exception as e:
            logger.error(f"Error listing assets for client {client_id}: {e}")
            return []
    
    def _object_exists(self, s3_key: str) -> bool:
        """Check if S3 object exists"""
        try:
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def _generate_presigned_url(self, s3_key: str, expiration: int) -> str:
        """Generate presigned URL for S3 object"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.s3_bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL for {s3_key}: {e}")
            raise
    
    def _get_logo_data(self, client_id: str) -> Optional[bytes]:
        """Get logo binary data from S3"""
        try:
            # Try different logo file extensions
            logo_extensions = ['png', 'jpg', 'jpeg', 'svg', 'gif']
            
            for ext in logo_extensions:
                s3_key = f"{self.s3_prefix}/{client_id}/logo.{ext}"
                
                if self._object_exists(s3_key):
                    response = self.s3_client.get_object(
                        Bucket=self.s3_bucket,
                        Key=s3_key
                    )
                    return response['Body'].read()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting logo data for client {client_id}: {e}")
            return None
    
    def _detect_image_format(self, image_data: bytes) -> str:
        """Detect image format from binary data"""
        try:
            # Check magic bytes
            if image_data.startswith(b'\x89PNG'):
                return 'png'
            elif image_data.startswith(b'\xff\xd8\xff'):
                return 'jpg'
            elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
                return 'gif'
            elif image_data.startswith(b'<svg') or b'<svg' in image_data[:100]:
                return 'svg'
            else:
                # Default to PNG
                return 'png'
                
        except Exception:
            return 'png'
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename"""
        extension = filename.lower().split('.')[-1]
        
        content_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'ico': 'image/x-icon'
        }
        
        return content_types.get(extension, 'application/octet-stream')
    
    def create_default_logo(self, client_id: str, company_name: str) -> str:
        """
        Create a default SVG logo for a client
        
        Args:
            client_id: Client identifier
            company_name: Company name to display in logo
            
        Returns:
            S3 key of created logo
        """
        try:
            # Create simple SVG logo
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="280" height="80" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#1e40af;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#3b82f6;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="280" height="80" fill="url(#grad1)" rx="12"/>
  <text x="140" y="45" font-family="Arial, sans-serif" font-size="24" font-weight="bold" 
        text-anchor="middle" fill="white">{company_name[:20]}</text>
  <circle cx="35" cy="40" r="12" fill="#fbbf24"/>
</svg>'''
            
            # Upload SVG logo
            s3_key = self.upload_client_asset(
                client_id=client_id,
                asset_data=svg_content.encode('utf-8'),
                asset_type='logo',
                filename='logo.svg'
            )
            
            logger.info(f"Created default logo for client {client_id}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error creating default logo for client {client_id}: {e}")
            raise
    
    def validate_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        Validate image data and return information
        
        Args:
            image_data: Image binary data
            
        Returns:
            Dictionary with validation results and image info
        """
        try:
            # Try to open with PIL
            image = Image.open(io.BytesIO(image_data))
            
            return {
                'valid': True,
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'width': image.width,
                'height': image.height,
                'file_size': len(image_data),
                'has_transparency': image.mode in ('RGBA', 'LA', 'P'),
                'email_compatible': (
                    image.width <= self.email_max_width and 
                    image.height <= self.email_max_height and 
                    len(image_data) <= self.email_max_size_kb * 1024
                )
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'file_size': len(image_data)
            }
    
    def get_asset_info(self, client_id: str) -> Dict[str, Any]:
        """
        Get comprehensive asset information for a client
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dictionary with asset information
        """
        try:
            assets = self.list_client_assets(client_id)
            
            info = {
                'client_id': client_id,
                'total_assets': len(assets),
                'total_size': sum(asset.get('size', 0) for asset in assets),
                'has_logo': False,
                'logo_info': None,
                'assets': assets
            }
            
            # Check for logo
            for asset in assets:
                if 'logo' in asset['filename'].lower():
                    info['has_logo'] = True
                    info['logo_info'] = asset
                    break
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting asset info for client {client_id}: {e}")
            return {
                'client_id': client_id,
                'error': str(e)
            }


# Legacy compatibility functions
def get_default_asset_manager(s3_bucket: str) -> LambdaAssetManager:
    """Get default asset manager instance"""
    return LambdaAssetManager(s3_bucket)