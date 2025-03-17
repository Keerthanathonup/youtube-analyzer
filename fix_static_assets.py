# fix_static_assets.py

import os
import base64
from pathlib import Path

def ensure_directory(directory):
    """Create directory if it doesn't exist."""
    Path(directory).mkdir(parents=True, exist_ok=True)
    print(f"Ensured directory exists: {directory}")

def create_placeholder_svg(width=100, height=100):
    """Create a simple placeholder SVG."""
    svg = f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#e0e0e0"/>
    <text x="50%" y="50%" font-family="Arial" font-size="14" fill="#666" 
          text-anchor="middle" dominant-baseline="middle">Placeholder</text>
</svg>'''
    return svg

def save_file(filepath, content):
    """Save content to a file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created: {filepath}")

def main():
    """Create missing static directories and assets."""
    # Create directory structure
    dirs = [
        'static/css',
        'static/js',
        'static/img',
    ]
    
    for directory in dirs:
        ensure_directory(directory)
    
    # Create placeholder image
    placeholder_svg = create_placeholder_svg(400, 225)
    save_file('static/img/placeholder.png.svg', placeholder_svg)  # Fallback for PNG
    
    # Create analysis.svg (placeholder for analysis UI components)
    analysis_svg = create_placeholder_svg(800, 400)
    save_file('static/img/analysis.svg', analysis_svg)
    
    # Create any missing CSS files (styles.css already exists)
    if not os.path.exists('static/css/styles.css'):
        print("Warning: styles.css doesn't exist. Not overwriting.")
    
    # Ensure the custom-red-theme.css is in the right location
    if not os.path.exists('static/css/custom-red-theme.css'):
        if os.path.exists('custom-red-theme.css'):
            with open('custom-red-theme.css', 'r', encoding='utf-8') as f:
                red_theme_css = f.read()
            save_file('static/css/custom-red-theme.css', red_theme_css)
        else:
            print("Could not find custom-red-theme.css to copy to static/css/")
    
    # Ensure network.css is in the right location
    if not os.path.exists('static/css/network.css'):
        if os.path.exists('network.css'):
            with open('network.css', 'r', encoding='utf-8') as f:
                network_css = f.read()
            save_file('static/css/network.css', network_css)
        else:
            print("Could not find network.css to copy to static/css/")
    
    # Ensure JS files are in the right location
    if not os.path.exists('static/js/network_visualization.js'):
        if os.path.exists('network_visualization.js'):
            with open('network_visualization.js', 'r', encoding='utf-8') as f:
                network_js = f.read()
            save_file('static/js/network_visualization.js', network_js)
        else:
            print("Could not find network_visualization.js to copy to static/js/")
    
    if not os.path.exists('static/js/main.js'):
        if os.path.exists('main.js'):
            with open('main.js', 'r', encoding='utf-8') as f:
                main_js = f.read()
            save_file('static/js/main.js', main_js)
        else:
            print("Could not find main.js to copy to static/js/")
    
    if not os.path.exists('static/js/video.js'):
        if os.path.exists('video.js'):
            with open('video.js', 'r', encoding='utf-8') as f:
                video_js = f.read()
            save_file('static/js/video.js', video_js)
        else:
            print("Could not find video.js to copy to static/js/")
    
    print("\nStatic asset fixing complete!")

if __name__ == "__main__":
    main()