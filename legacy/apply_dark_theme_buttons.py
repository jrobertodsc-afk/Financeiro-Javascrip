import glob
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Vibrant colors to be converted to White (#ffffff)
    vibrant_to_white = [
        '#7c3aed', '#6d28d9', '#8b5cf6', '#a78bfa', # purples
        '#10b981', '#059669', '#166534', '#22c55e', '#4ade80', '#a3e635', '#1A6B3A', # greens
        '#3b82f6', '#0ea5e9', '#0284c7', '#38bdf8', # blues
        '#f59e0b', '#fbbf24', '#fb923c', '#eab308'  # oranges/yellows
    ]
    for c in vibrant_to_white:
        content = re.sub(c, '#ffffff', content, flags=re.IGNORECASE)

    # 2. Fix White-on-White buttons (bg="#ffffff", fg="#ffffff")
    # Using regex to find Tkinter configurations where both bg and fg ended up white,
    # or just replace known patterns
    content = re.sub(r'bg=[\'"]#ffffff[\'"]\s*,\s*fg=[\'"]#(?:ffffff|f8fafc|F8FAFC)[\'"]', 'bg="#ffffff", fg="#000000"', content, flags=re.IGNORECASE)
    content = re.sub(r'fg=[\'"]#(?:ffffff|f8fafc|F8FAFC)[\'"]\s*,\s*bg=[\'"]#ffffff[\'"]', 'fg="#000000", bg="#ffffff"', content, flags=re.IGNORECASE)
    content = re.sub(r'bg=[\'"]#ffffff[\'"]\s*,\s*fg=text', 'bg="#ffffff", fg="#000000"', content, flags=re.IGNORECASE)

    # 3. Old grays to #141414 (Dark card / secondary button bg)
    old_grays = [
        '#333333', '#222222', '#555555', '#666666', '#777777', '#888888', '#999999',
        '#AAAAAA', '#CCCCCC', '#DDDDDD', '#3A3A3A', '#1A1A1A'
    ]
    for g in old_grays:
        content = re.sub(g, '#141414', content, flags=re.IGNORECASE)

    # 4. Vibrant texts (like reds for errors) to #a1a1aa (muted) or #ffffff
    vibrant_to_muted = [
        '#ef4444', '#dc2626', '#f87171', '#fca5a5', '#7f1d1d', '#450a0a', '#f472b6', '#9d174d', '#fee2e2', '#8B1A2B', '#C41E3A', '#2d1515' # reds
    ]
    for c in vibrant_to_muted:
        content = re.sub(c, '#a1a1aa', content, flags=re.IGNORECASE)
        
    return content

updated_files = []
for filepath in glob.glob("d:/ROBO/gui/mixins/*.py"):
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    new_content = process_file(filepath)
    
    if new_content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        updated_files.append(filepath)

print(f"Updated {len(updated_files)} files.")
