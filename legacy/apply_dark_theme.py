import glob
import re

mapping = {
    # Fundos super escuros (passam a ser o bg #0a0a0a - Preto absoluto)
    "#0a0f1e": "#0a0a0a",
    "#0F172A": "#0a0a0a",
    "#0f172a": "#0a0a0a",
    "#020617": "#0a0a0a",
    "#111827": "#0a0a0a",
    "#0A101C": "#0a0a0a",
    "#0d1526": "#0a0a0a",
    "#111d35": "#0a0a0a",
    "#0a1a2a": "#0a0a0a",
    "#0a2a3a": "#0a0a0a",
    "#1a1a2e": "#0a0a0a",
    "#1a1200": "#0a0a0a",
    "#1a1510": "#0a0a0a",
    "#1e1b4b": "#0a0a0a",

    # Fundos de Cards / Entradas (passam a ser #141414 - Cinza ultra escuro)
    "#1e293b": "#141414",
    "#1E293B": "#141414",
    "#1e3050": "#141414",
    "#1e2a3a": "#141414",
    "#1e3a2f": "#141414",
    "#1A3A6B": "#141414",

    # Bordas e hover (passam a ser #27272a - Zinc 800)
    "#334155": "#27272a",
    "#475569": "#27272a",
    
    # Textos Principais
    "#f8fafc": "#ffffff",
    "#F8FAFC": "#ffffff",
    "#f1f5f9": "#ffffff",
    "#F1F5F9": "#ffffff",
    "#F5F0E8": "#ffffff",
    "#F0ECE4": "#ffffff",
    "#e2e8f0": "#e5e5e5",
    "#E2E8F0": "#e5e5e5",
    
    # Textos Secundários / Muted
    "#94a3b8": "#a1a1aa",
    "#64748b": "#71717a",
    "#64748B": "#71717a",
}

updated_files = []
for filepath in glob.glob("d:/ROBO/gui/mixins/*.py"):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for old_color, new_color in mapping.items():
        new_content = new_content.replace(old_color, new_color)
        
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        updated_files.append(filepath)

print(f"Updated {len(updated_files)} files.")
