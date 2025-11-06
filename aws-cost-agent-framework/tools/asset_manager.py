"""
Asset Manager for CostHub Reports
Handles logos, images, and other static assets
"""

import base64
from pathlib import Path
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class AssetManager:
    """Manage static assets for reports"""
    
    def __init__(self, assets_dir: Path = None):
        self.assets_dir = assets_dir or Path(__file__).parent.parent / "assets"
        self.images_dir = self.assets_dir / "images"
        
        # Ensure directories exist
        self.assets_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
    
    def get_logo_base64(self, logo_name: str = "costhub_logo.svg") -> Optional[str]:
        """Get logo as base64 string for embedding in HTML/email"""
        
        logo_path = self.images_dir / logo_name
        
        if not logo_path.exists():
            logger.warning(f"Logo not found: {logo_path}")
            return None
        
        try:
            with open(logo_path, 'rb') as f:
                logo_data = f.read()
            
            # Determine MIME type based on extension
            extension = logo_path.suffix.lower()
            mime_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml'
            }
            
            mime_type = mime_types.get(extension, 'image/png')
            
            # Encode to base64
            base64_data = base64.b64encode(logo_data).decode('utf-8')
            
            return f"data:{mime_type};base64,{base64_data}"
            
        except Exception as e:
            logger.error(f"Error reading logo {logo_path}: {e}")
            return None
    
    def _find_logo_file(self) -> Optional[str]:
        """Find the first available logo file"""
        
        # Priority order for logo files
        logo_candidates = [
            'costhub_logo.png',
            'costhub_logo.svg', 
            'costhub_logo.jpg',
            'costhub_logo.jpeg',
            'logo.png',
            'logo.svg',
            'logo.jpg',
            'logo.jpeg'
        ]
        
        for candidate in logo_candidates:
            logo_path = self.images_dir / candidate
            if logo_path.exists():
                return candidate
        
        return None
    
    def get_logo_html(self, logo_name: str = None, 
                     width: str = "280px", height: str = "auto",
                     alt_text: str = "CostHub Logo") -> str:
        """Get HTML img tag for logo"""
        
        # Auto-detect logo if not specified
        if logo_name is None:
            logo_name = self._find_logo_file()
        
        if logo_name:
            logo_base64 = self.get_logo_base64(logo_name)
            
            if logo_base64:
                return f'''<img src="{logo_base64}" alt="{alt_text}" style="width: {width}; height: {height}; max-width: 100%;">'''
        
        # Fallback to text logo
        return f'''<div style="font-size: 32px; font-weight: bold; color: #1e40af;">{alt_text}</div>'''
    
    def get_favicon_base64(self, favicon_name: str = "costhub_favicon.png") -> Optional[str]:
        """Get favicon as base64 for HTML head"""
        
        return self.get_logo_base64(favicon_name)
    
    def save_logo_placeholder(self, logo_name: str = "costhub_logo.png"):
        """Create a placeholder logo file with instructions"""
        
        logo_path = self.images_dir / logo_name
        
        if logo_path.exists():
            logger.info(f"Logo already exists: {logo_path}")
            return
        
        # Create a simple SVG placeholder
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="60" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#1e40af;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#3b82f6;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="200" height="60" fill="url(#grad1)" rx="8"/>
  <text x="100" y="35" font-family="Arial, sans-serif" font-size="24" font-weight="bold" 
        text-anchor="middle" fill="white">CostHub</text>
  <circle cx="25" cy="30" r="8" fill="#fbbf24"/>
</svg>'''
        
        # Save as SVG placeholder
        placeholder_path = self.images_dir / "costhub_logo_placeholder.svg"
        with open(placeholder_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        logger.info(f"Placeholder logo created: {placeholder_path}")
        
        # Create instructions file
        instructions_path = self.images_dir / "README.md"
        instructions = f"""# CostHub Assets

## Logo Setup

1. **Add your CostHub logo** to this directory:
   - Recommended name: `costhub_logo.png`
   - Recommended size: 200x60px (or similar aspect ratio)
   - Supported formats: PNG, JPG, SVG

2. **Optional files**:
   - `costhub_favicon.png` - For browser favicon (16x16 or 32x32px)
   - `costhub_logo_dark.png` - Dark theme version
   - `costhub_logo_email.png` - Email-optimized version (max 600px width)

## Current Files

- `costhub_logo_placeholder.svg` - Placeholder logo (replace with your actual logo)

## Usage

The AssetManager will automatically use your logo in:
- HTML reports
- Email reports  
- PDF exports (future)

If no logo is found, it will fallback to text-based branding.
"""
        
        with open(instructions_path, 'w', encoding='utf-8') as f:
            f.write(instructions)
        
        logger.info(f"Instructions created: {instructions_path}")
    
    def get_email_logo_html(self, logo_name: str = None,
                           max_width: str = "240px") -> str:
        """Get email-optimized logo HTML"""
        
        # Auto-detect logo if not specified
        if logo_name is None:
            logo_name = self._find_logo_file()
        
        if logo_name:
            logo_base64 = self.get_logo_base64(logo_name)
            
            if logo_base64:
                return f'''<img src="{logo_base64}" alt="CostHub" style="max-width: {max_width}; height: auto; display: block; margin: 0 auto;">'''
        
        # Email-safe fallback
        return '''<div style="font-size: 28px; font-weight: bold; color: #ffffff; text-align: center; margin: 10px 0;">CostHub</div>'''
    
    def get_assets_info(self) -> Dict:
        """Get information about available assets"""
        
        info = {
            'assets_dir': str(self.assets_dir),
            'images_dir': str(self.images_dir),
            'available_logos': [],
            'logo_exists': False,
            'favicon_exists': False
        }
        
        # Check for logo files
        logo_patterns = ['costhub_logo.*', 'logo.*', 'costhub.*']
        
        for pattern in logo_patterns:
            for logo_file in self.images_dir.glob(pattern):
                if logo_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.svg', '.gif']:
                    info['available_logos'].append(logo_file.name)
                    if 'logo' in logo_file.name.lower():
                        info['logo_exists'] = True
                    if 'favicon' in logo_file.name.lower():
                        info['favicon_exists'] = True
        
        return info


def get_default_asset_manager() -> AssetManager:
    """Get default asset manager instance"""
    return AssetManager()