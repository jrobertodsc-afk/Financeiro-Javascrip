import glob
import re
import os

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # --- 1. Replace tk.Entry with ctk.CTkEntry ---
    # Width adjustment (multiply by 9 approx)
    def repl_entry(match):
        inner = match.group(1)
        # Fix width
        width_match = re.search(r'width=(\d+)', inner)
        if width_match:
            new_width = int(width_match.group(1)) * 9
            inner = re.sub(r'width=\d+', f'width={new_width}', inner)
        
        # Replace tk colors with ctk colors
        inner = re.sub(r'\bbg=', 'fg_color=', inner)
        inner = re.sub(r'\bfg=', 'text_color=', inner)
        
        # Remove unsupported arguments like relief, bd, highlightthickness, selectbackground, selectforeground
        inner = re.sub(r',\s*relief=[\'"]?[a-zA-Z]+[\'"]?', '', inner)
        inner = re.sub(r',\s*bd=\d+', '', inner)
        inner = re.sub(r',\s*highlightthickness=\d+', '', inner)
        inner = re.sub(r',\s*selectcolor=[\'"][^\'"]*[\'"]', '', inner)
        inner = re.sub(r',\s*selectbackground=[\'"][^\'"]*[\'"]', '', inner)
        inner = re.sub(r',\s*selectforeground=[\'"][^\'"]*[\'"]', '', inner)
        
        # Ensure it has a border color for modern look
        if 'border_color' not in inner:
            inner += ', border_color="#27272a", border_width=1'
            
        return f'ctk.CTkEntry({inner})'

    content = re.sub(r'tk\.Entry\((.*?)\)', repl_entry, content, flags=re.DOTALL)

    # --- 2. Replace ttk.Combobox with ctk.CTkComboBox ---
    def repl_combo(match):
        inner = match.group(1)
        # Fix width
        width_match = re.search(r'width=(\d+)', inner)
        if width_match:
            new_width = int(width_match.group(1)) * 9
            inner = re.sub(r'width=\d+', f'width={new_width}', inner)
            
        inner = re.sub(r',\s*state=[\'"]readonly[\'"]', '', inner) # CTkComboBox uses state="readonly" too, but default is fine. Actually, let's keep it but remove if it errors. CTkComboBox supports state="readonly".
        inner += ', fg_color="#141414", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414"'
        return f'ctk.CTkComboBox({inner})'
        
    content = re.sub(r'ttk\.Combobox\((.*?)\)', repl_combo, content, flags=re.DOTALL)

    # --- 3. Replace tk.Button with ctk.CTkButton ---
    # Be careful, tk.Button might be used in some legacy popups, but we'll try to convert most.
    def repl_button(match):
        inner = match.group(1)
        inner = re.sub(r'\bbg=', 'fg_color=', inner)
        inner = re.sub(r'\bfg=', 'text_color=', inner)
        inner = re.sub(r',\s*relief=[\'"]?[a-zA-Z]+[\'"]?', '', inner)
        inner = re.sub(r',\s*bd=\d+', '', inner)
        inner = re.sub(r',\s*activebackground=[\'"][^\'"]*[\'"]', '', inner)
        inner = re.sub(r',\s*activeforeground=[\'"][^\'"]*[\'"]', '', inner)
        
        # default modern look
        inner += ', corner_radius=6'
        return f'ctk.CTkButton({inner})'
        
    content = re.sub(r'tk\.Button\((.*?)\)', repl_button, content, flags=re.DOTALL)

    # --- 4. Replace tk.Text with ctk.CTkTextbox ---
    def repl_text(match):
        inner = match.group(1)
        # Fix width and height
        width_match = re.search(r'width=(\d+)', inner)
        if width_match:
            new_width = int(width_match.group(1)) * 9
            inner = re.sub(r'width=\d+', f'width={new_width}', inner)
        
        height_match = re.search(r'height=(\d+)', inner)
        if height_match:
            new_height = int(height_match.group(1)) * 20
            inner = re.sub(r'height=\d+', f'height={new_height}', inner)
            
        inner = re.sub(r'\bbg=', 'fg_color=', inner)
        inner = re.sub(r'\bfg=', 'text_color=', inner)
        inner = re.sub(r',\s*relief=[\'"]?[a-zA-Z]+[\'"]?', '', inner)
        inner = re.sub(r',\s*bd=\d+', '', inner)
        
        return f'ctk.CTkTextbox({inner}, border_color="#27272a", border_width=1)'
        
    content = re.sub(r'tk\.Text\((.*?)\)', repl_text, content, flags=re.DOTALL)
    
    # --- 5. Fix ctk.CTkTabview fonts if not present ---
    # Although ctk.CTkTabview doesn't take font directly for tabs, segmented_button_font can be passed in newer CTk versions.
    # We will just ignore this and rely on global scaling or custom font logic if needed.

    return content

files_to_process = glob.glob("d:/ROBO/gui/mixins/*.py") + ["d:/ROBO/robo_comprovantes_v14_interface.py"]

updated_files = []
for filepath in files_to_process:
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    new_content = process_file(filepath)
    
    if new_content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        updated_files.append(filepath)

print(f"Updated {len(updated_files)} files to CustomTkinter.")
