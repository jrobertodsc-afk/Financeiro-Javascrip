import glob
import re

files_to_process = glob.glob("d:/ROBO/gui/mixins/*.py") + ["d:/ROBO/robo_comprovantes_v14_interface.py"]

for filepath in files_to_process:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix: font=("Segoe UI", 10, border_color="#27272a", border_width=1)
    # Becomes: font=("Segoe UI", 10), border_color="#27272a", border_width=1)
    # The ending parenthesis of the tk.Entry was also mismatched maybe?
    # Wait, my regex appended `, border_color="..."` before the last `)`.
    # So `tk.Entry(..., font=("Consolas", 8))` matched up to the FIRST `)` which is the font's `)`.
    # It resulted in: `ctk.CTkEntry(..., font=("Consolas", 8, border_color="#27272a", border_width=1))`
    # We should fix it to `ctk.CTkEntry(..., font=("Consolas", 8), border_color="#27272a", border_width=1)`
    # Or maybe it didn't match the closing `)` of the Entry? If it only matched up to the first `)`, then the real `)` of the Entry is still there later on the line?
    # Let's fix `font=([^)]+?)\s*,\s*border_color` -> `font=\1), border_color`
    
    new_content = re.sub(r'font=\(([^)]+?)\s*,\s*border_color', r'font=(\1), border_color', content)
    
    # Check if there are other parameters that suffered the same fate, e.g., tuple for bg? No bg is a string.
    # Check if font was tuple with 3 elements e.g. font=("Arial", 10, "bold")
    # Actually, let's just do `,\s*border_color="#27272a"` and move the `)` before the comma.
    # The regex `font=\(([^)]+?),\s*border_color` might match `font=("Segoe UI", 10, border_color`.
    
    # Let's do a more generic fix: if `border_color=` is inside `font=(...)`, move it out.
    new_content = re.sub(r'font=\(([^)]+?),\s*border_color=([^\)]+)\)', r'font=(\1), border_color=\2)', new_content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Fixed syntax in", filepath)
