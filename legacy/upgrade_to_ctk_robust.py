import glob
import re
import os

def find_matching_paren(s, start):
    count = 0
    for i in range(start, len(s)):
        if s[i] == '(': count += 1
        elif s[i] == ')':
            count -= 1
            if count == 0:
                return i
    return -1

def process_widget(content, widget_name, new_widget_name, modifier_func):
    while True:
        idx = content.find(widget_name + '(')
        if idx == -1:
            break
            
        start_paren = idx + len(widget_name)
        end_paren = find_matching_paren(content, start_paren)
        
        if end_paren == -1:
            break # Malformed file?
            
        inner = content[start_paren+1:end_paren]
        
        new_inner = modifier_func(inner)
        
        content = content[:idx] + new_widget_name + '(' + new_inner + ')' + content[end_paren+1:]
        
    return content

def mod_entry(inner):
    # Fix width
    width_match = re.search(r'\bwidth=(\d+)', inner)
    if width_match:
        new_width = int(width_match.group(1)) * 9
        inner = re.sub(r'\bwidth=\d+', f'width={new_width}', inner)
    
    # Replace tk colors with ctk colors
    inner = re.sub(r'\bbg=', 'fg_color=', inner)
    inner = re.sub(r'\bfg=', 'text_color=', inner)
    
    # Remove unsupported arguments
    inner = re.sub(r',\s*relief=[\'"]?[a-zA-Z]+[\'"]?', '', inner)
    inner = re.sub(r',\s*bd=\d+', '', inner)
    inner = re.sub(r',\s*highlightthickness=\d+', '', inner)
    inner = re.sub(r',\s*selectcolor=[\'"][^\'"]*[\'"]', '', inner)
    inner = re.sub(r',\s*selectbackground=[\'"][^\'"]*[\'"]', '', inner)
    inner = re.sub(r',\s*selectforeground=[\'"][^\'"]*[\'"]', '', inner)
    inner = re.sub(r',\s*insertbackground=[^,\)]+', '', inner)
    inner = re.sub(r',\s*cursor=[\'"][^\'"]*[\'"]', '', inner)
    
    if 'border_color' not in inner:
        inner += ', border_color="#27272a", border_width=1'
        
    return inner

def mod_combo(inner):
    width_match = re.search(r'\bwidth=(\d+)', inner)
    if width_match:
        new_width = int(width_match.group(1)) * 9
        inner = re.sub(r'\bwidth=\d+', f'width={new_width}', inner)
        
    inner = re.sub(r',\s*state=[\'"]readonly[\'"]', '', inner)
    inner += ', state="readonly", fg_color="#141414", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414"'
    return inner

def mod_button(inner):
    inner = re.sub(r'\bbg=', 'fg_color=', inner)
    inner = re.sub(r'\bfg=', 'text_color=', inner)
    inner = re.sub(r',\s*relief=[\'"]?[a-zA-Z]+[\'"]?', '', inner)
    inner = re.sub(r',\s*bd=\d+', '', inner)
    inner = re.sub(r',\s*activebackground=[^,\)]+', '', inner)
    inner = re.sub(r',\s*activeforeground=[^,\)]+', '', inner)
    inner = re.sub(r',\s*highlightthickness=\d+', '', inner)
    inner += ', corner_radius=6'
    return inner

def mod_text(inner):
    width_match = re.search(r'\bwidth=(\d+)', inner)
    if width_match:
        new_width = int(width_match.group(1)) * 9
        inner = re.sub(r'\bwidth=\d+', f'width={new_width}', inner)
    
    height_match = re.search(r'\bheight=(\d+)', inner)
    if height_match:
        new_height = int(height_match.group(1)) * 20
        inner = re.sub(r'\bheight=\d+', f'height={new_height}', inner)
        
    inner = re.sub(r'\bbg=', 'fg_color=', inner)
    inner = re.sub(r'\bfg=', 'text_color=', inner)
    inner = re.sub(r',\s*relief=[\'"]?[a-zA-Z]+[\'"]?', '', inner)
    inner = re.sub(r',\s*bd=\d+', '', inner)
    inner = re.sub(r',\s*insertbackground=[^,\)]+', '', inner)
    inner = re.sub(r',\s*highlightthickness=\d+', '', inner)
    
    inner += ', border_color="#27272a", border_width=1'
    return inner


files_to_process = glob.glob("d:/ROBO/gui/mixins/*.py") + ["d:/ROBO/robo_comprovantes_v14_interface.py"]

updated_files = []
for filepath in files_to_process:
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    # Needs a hack for the `while True:` logic since it replaces instances and updates the string.
    # To avoid infinite loops, we can temporarily replace the string with a placeholder or just process them correctly.
    # Actually `content.find(widget_name + '(')` will keep finding the replaced ones if new_widget_name contains widget_name.
    # ctk.CTkEntry contains tk.Entry? No. ctk.CTkEntry does NOT contain "tk.Entry" (it has "CTkEntry").
    # Wait, "tk.Entry" is 8 chars. If I search for "tk.Entry(" it won't match "ctk.CTkEntry(".
    # Let's be careful about imports like `import tkinter as tk`.
    
    content = original
    content = process_widget(content, 'tk.Entry', 'ctk.CTkEntry', mod_entry)
    content = process_widget(content, 'ttk.Combobox', 'ctk.CTkComboBox', mod_combo)
    content = process_widget(content, 'tk.Button', 'ctk.CTkButton', mod_button)
    content = process_widget(content, 'tk.Text', 'ctk.CTkTextbox', mod_text)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        updated_files.append(filepath)

print(f"Updated {len(updated_files)} files to CustomTkinter safely.")
