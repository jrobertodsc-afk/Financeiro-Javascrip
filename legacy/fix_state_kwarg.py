import glob
import re

files_to_process = glob.glob("d:/ROBO/gui/mixins/*.py") + ["d:/ROBO/robo_comprovantes_v14_interface.py"]

for filepath in files_to_process:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Search for cases where state=... is followed by another state=...
    # The error was `state="normal", ..., state="readonly"`
    # Let's remove the `, state="readonly"` that was added by the script.
    
    # We added: `, state="readonly", fg_color="#141414", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414"`
    # But ONLY if it was a Combobox.
    
    new_content = re.sub(r'state=([^,]+?)(.*?), state="readonly"', r'state=\1\2', content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Fixed syntax in", filepath)
