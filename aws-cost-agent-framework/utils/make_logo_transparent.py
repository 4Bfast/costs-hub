#!/usr/bin/env python3
"""
Make CostHub Logo Transparent
Converts logo background to transparent for better integration
"""

import sys
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description='Make CostHub logo background transparent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s assets/images/costhub_logo.png
  %(prog)s logo.jpg --output transparent_logo.png
  %(prog)s logo.png --threshold 240 --output logo_transparent.png
        """
    )
    
    parser.add_argument('input_file', 
                       help='Input logo file (PNG, JPG, etc.)')
    parser.add_argument('--output', '-o',
                       help='Output file (default: adds _transparent suffix)')
    parser.add_argument('--threshold', type=int, default=240,
                       help='White threshold for transparency (0-255, default: 240)')
    parser.add_argument('--preview', action='store_true',
                       help='Show preview of changes (requires display)')
    
    return parser

def make_transparent_pil(input_path: Path, output_path: Path, threshold: int = 240):
    """Make logo transparent using PIL/Pillow"""
    
    print(f"📂 Opening: {input_path}")
    
    # Open image
    img = Image.open(input_path)
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        print(f"🔄 Converting from {img.mode} to RGBA")
        img = img.convert('RGBA')
    
    # Get image data
    data = img.getdata()
    
    # Create new data with transparency
    new_data = []
    pixels_changed = 0
    
    print(f"🎨 Processing {len(data)} pixels...")
    
    for item in data:
        # Check if pixel is close to white
        r, g, b = item[:3]
        
        # If pixel is close to white (above threshold), make it transparent
        if r >= threshold and g >= threshold and b >= threshold:
            new_data.append((r, g, b, 0))  # Transparent
            pixels_changed += 1
        else:
            # Keep original pixel with full opacity
            if len(item) == 4:
                new_data.append(item)  # Keep original alpha
            else:
                new_data.append((r, g, b, 255))  # Add full opacity
    
    # Update image data
    img.putdata(new_data)
    
    # Save as PNG (supports transparency)
    print(f"💾 Saving to: {output_path}")
    img.save(output_path, 'PNG')
    
    print(f"✅ Transparency applied!")
    print(f"📊 Pixels made transparent: {pixels_changed:,} ({pixels_changed/len(data)*100:.1f}%)")
    
    return True

def make_transparent_manual(input_path: Path, output_path: Path, threshold: int = 240):
    """Manual transparency method (fallback without PIL)"""
    
    print("⚠️  PIL not available - using manual method")
    print("💡 For best results, install Pillow: pip install Pillow")
    
    # For now, just copy the file and give instructions
    import shutil
    shutil.copy2(input_path, output_path)
    
    print(f"📂 File copied to: {output_path}")
    print(f"🎨 Manual transparency instructions:")
    print(f"   1. Open {output_path} in an image editor (GIMP, Photoshop, etc.)")
    print(f"   2. Use 'Select by Color' tool to select white background")
    print(f"   3. Delete the selected white areas")
    print(f"   4. Save as PNG with transparency")
    
    return False

def test_logo_integration(logo_path: Path):
    """Test how the logo will look in reports"""
    
    print(f"\n🧪 Testing logo integration...")
    
    try:
        # Test with AssetManager
        sys.path.append(str(Path(__file__).parent))
        from tools.asset_manager import AssetManager
        
        asset_manager = AssetManager()
        
        # Test if logo is detected
        logo_name = logo_path.name
        logo_base64 = asset_manager.get_logo_base64(logo_name)
        
        if logo_base64:
            print(f"✅ Logo detected and converted to base64")
            print(f"📊 Base64 length: {len(logo_base64)} characters")
            
            # Test HTML generation
            html = asset_manager.get_logo_html(logo_name)
            if 'img src=' in html:
                print(f"✅ HTML generation successful")
            else:
                print(f"❌ HTML generation failed")
            
        else:
            print(f"❌ Logo not detected or conversion failed")
            
    except Exception as e:
        print(f"⚠️  Integration test failed: {e}")

def main():
    """Main function"""
    
    if not PIL_AVAILABLE:
        print("⚠️  Warning: PIL/Pillow not installed")
        print("💡 Install with: pip install Pillow")
        print("🔄 Continuing with manual method...")
    
    parser = create_parser()
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        return 1
    
    # Determine output file
    if args.output:
        output_path = Path(args.output)
    else:
        # Add _transparent suffix
        stem = input_path.stem
        suffix = input_path.suffix
        output_path = input_path.parent / f"{stem}_transparent.png"
    
    print(f"🎨 Making Logo Transparent")
    print(f"=" * 50)
    print(f"📂 Input: {input_path}")
    print(f"💾 Output: {output_path}")
    print(f"🎯 Threshold: {args.threshold}")
    print()
    
    try:
        if PIL_AVAILABLE:
            success = make_transparent_pil(input_path, output_path, args.threshold)
        else:
            success = make_transparent_manual(input_path, output_path, args.threshold)
        
        # Test integration
        if success and output_path.exists():
            test_logo_integration(output_path)
        
        print(f"\n🎉 Process completed!")
        
        if success:
            print(f"✅ Transparent logo created: {output_path}")
            print(f"💡 Copy to assets: cp {output_path} assets/images/costhub_logo.png")
        else:
            print(f"⚠️  Manual processing required")
        
        return 0
        
    except Exception as e:
        print(f"💥 Error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)