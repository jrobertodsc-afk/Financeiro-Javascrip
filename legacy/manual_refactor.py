import re

filepath = "d:/ROBO/gui/mixins/aba_contas_pagar.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update 'ent' in _cap_build_adiantamentos
# original:
#         def ent(w=20):
#             return tk.Entry(frm, font=("Segoe UI",12), bg="#0a0a0a", fg="#ffffff",
#                          insertbackground=accent, relief="flat", bd=2, width=w)
replacement_ad_ent = """        def ent(w=20):
            return ctk.CTkEntry(frm, font=("Segoe UI",12), fg_color="#0a0a0a", text_color="#ffffff",
                         border_color="#27272a", border_width=1, corner_radius=6, width=w*9, height=32)"""
content = re.sub(r'def ent\(w=20\):\s+return tk\.Entry\(frm, font=\("Segoe UI",12\), bg="#0a0a0a", fg="#ffffff",\s+insertbackground=accent, relief="flat", bd=2, width=w\)', replacement_ad_ent, content, count=1)

# 2. Update _ad_tipo in _cap_build_adiantamentos
replacement_ad_tipo = """self._ad_tipo = ctk.CTkComboBox(frm,
            values=["FUNCIONARIO","FORNECEDOR"],
            state="readonly", width=162, height=32, font=("Segoe UI",12), fg_color="#0a0a0a", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414")"""
content = re.sub(r'self\._ad_tipo = ttk\.Combobox\(frm,\s+values=\["FUNCIONARIO","FORNECEDOR"\],\s+state="readonly", width=18, font=\("Segoe UI",12\)\)', replacement_ad_tipo, content, count=1)

# 3. Update _ad_emp in _cap_build_adiantamentos
replacement_ad_emp = """self._ad_emp = ctk.CTkComboBox(frm,
            values=["LALUA","SOLAR"],
            state="readonly", width=108, height=32, font=("Segoe UI",12), fg_color="#0a0a0a", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414")"""
content = re.sub(r'self\._ad_emp = ttk\.Combobox\(frm,\s+values=\["LALUA","SOLAR"\],\s+state="readonly", width=12, font=\("Segoe UI",12\)\)', replacement_ad_emp, content, count=1)

# 4. Update 'ent' in _cap_build_prestacao
# original:
#         def ent(w=20):
#             return tk.Entry(frm, font=("Segoe UI",9), bg="#0a0a0a", fg="#ffffff",
#                          insertbackground=accent, relief="flat", bd=2, width=w)
replacement_pr_ent = """        def ent(w=20):
            return ctk.CTkEntry(frm, font=("Segoe UI",12), fg_color="#0a0a0a", text_color="#ffffff",
                         border_color="#27272a", border_width=1, corner_radius=6, width=w*9, height=32)"""
content = re.sub(r'def ent\(w=20\):\s+return tk\.Entry\(frm, font=\("Segoe UI",9\), bg="#0a0a0a", fg="#ffffff",\s+insertbackground=accent, relief="flat", bd=2, width=w\)', replacement_pr_ent, content, count=1)

# 5. Update _pr_ad_cb in _cap_build_prestacao
replacement_pr_ad = """ttk.Combobox(frm, textvariable=self._pr_ad_var,
                     values=opts or [""], state="readonly",
                     width=405, font=("Segoe UI",12))"""
content = re.sub(r'ttk\.Combobox\(frm, textvariable=self\._pr_ad_var,\s+values=opts, state="readonly",\s+width=45, font=\("Segoe UI",8\)\)', replacement_pr_ad, content, count=1)
# now to ctk
content = content.replace('ttk.Combobox(frm, textvariable=self._pr_ad_var,\n                     values=opts or [""], state="readonly",\n                     width=405, font=("Segoe UI",12))', 
'ctk.CTkComboBox(frm, variable=self._pr_ad_var, values=opts or [""], state="readonly", width=405, height=32, font=("Segoe UI",12), fg_color="#0a0a0a", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414")')

# 6. Update _pr_nota_cb in _cap_build_prestacao
replacement_pr_nota = """ctk.CTkComboBox(frm, variable=self._pr_nota_var,
                     values=[f"{n['numero_tx']} - {n['fornecedor']}"
                             for n in listar_notas(status="PENDENTE")] or [""],
                     state="normal", width=198, height=32, font=("Segoe UI",12),
                     fg_color="#0a0a0a", border_color="#27272a", border_width=1, button_color="#27272a", dropdown_fg_color="#141414")"""
content = re.sub(r'ttk\.Combobox\(frm, textvariable=self\._pr_nota_var,\s+values=\[f"\{n\[\'numero_tx\'\]\} - \{n\[\'fornecedor\'\]\}"\s+for n in listar_notas\(status="PENDENTE"\)\],\s+state="normal", width=22, font=\("Segoe UI",8\)\)', replacement_pr_nota, content, count=1)


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated manual CTK replacements in", filepath)
