import glob
import re

files_to_process = glob.glob("d:/ROBO/gui/mixins/*.py") + ["d:/ROBO/robo_comprovantes_v14_interface.py"]

for filepath in files_to_process:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Search for repeated state= args across newlines too
    new_content = re.sub(r'state=([^,]+?)(.*?), state="readonly"', r'state=\1\2', content, flags=re.DOTALL)
    
    # Also if the first state was on the same line but we missed it
    new_content = re.sub(r'state=([^,\)]+)(.*?), state="readonly"', r'state=\1\2', new_content, flags=re.DOTALL)
    
    # Let's also check for repeated `border_width=1` or `border_color="#27272a"`
    new_content = re.sub(r'border_width=1(.*?),\s*border_width=1', r'border_width=1\1', new_content, flags=re.DOTALL)
    new_content = re.sub(r'border_color="#27272a"(.*?),\s*border_color="#27272a"', r'border_color="#27272a"\1', new_content, flags=re.DOTALL)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Fixed syntax in", filepath)
