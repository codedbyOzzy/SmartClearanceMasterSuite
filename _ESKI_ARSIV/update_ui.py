import sys
import re
import shutil

fpath = r'C:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Belgeler\V1SmartClearance_Gumruk\tools\dogruer_master_suite\master_suite.py'
with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Sidebar Category Spacing and Background
content = content.replace('f_grp.pack(fill=tk.X, padx=6, pady=(8, 3))', 'f_grp.pack(fill=tk.X, padx=6, pady=(15, 6))')
content = content.replace('bg="#0c4a6e"', 'bg="#0f172a"')

# 2. Sidebar Item Cleanup (Remove Subtitle)
content = content.replace('f_text = tk.Frame(btn_frame, bg="#0f172a", cursor="hand2", padx=2, pady=3)', 'f_text = tk.Frame(btn_frame, bg="#0f172a", cursor="hand2", padx=2, pady=6)')
content = re.sub(r'(lbl_d\s*=\s*tk\.Label\([\s\S]*?lbl_d\.pack\(fill=tk\.X\))', r'# \1', content)
content = content.replace('for w in (btn_frame, bar, lbl_icon, f_text, lbl_t, lbl_d):', 'for w in (btn_frame, bar, lbl_icon, f_text, lbl_t):')
content = content.replace('_make_hover(btn_frame, lbl_icon, f_text, lbl_t, lbl_d, code)', '_make_hover(btn_frame, lbl_icon, f_text, lbl_t, None, code)')

# 3. Table Zebra Striping & Selection Color
content = content.replace('self.tree_cockpit.tag_configure("kirmizi_hat", background="#fee2e2", foreground="#991b1b")', 'self.tree_cockpit.tag_configure("kirmizi_hat", background="#ffffff")')
content = content.replace('self.tree_cockpit.tag_configure("tescil_ok", background="#f0fdf4", foreground="#166534")', 'self.tree_cockpit.tag_configure("tescil_ok", background="#ffffff")')
content = content.replace('self.tree_cockpit.tag_configure("mail_ok", background="#ecfdf5", foreground="#047857")', 'self.tree_cockpit.tag_configure("mail_ok", background="#ffffff")')
content = content.replace('self.tree_cockpit.tag_configure("mail_warning", background="#fef2f2", foreground="#b91c1c")', 'self.tree_cockpit.tag_configure("mail_warning", background="#ffffff")')
content = content.replace('self.tree_cockpit.tag_configure("closed", background="#f8fafc", foreground="#94a3b8")', 'self.tree_cockpit.tag_configure("closed", background="#ffffff")')

# We can simulate zebra by modifying how rows are inserted, but standard treeview without custom logic doesn't do it automatically.
# Instead of doing complex logic for zebra, I will just make them all white to eliminate the patchy look. The emojis will carry the status.
content = content.replace('self.tree_cockpit.tag_configure("normal", background="#ffffff", foreground="#0f172a")', 'self.tree_cockpit.tag_configure("normal", background="#ffffff", foreground="#334155")')

# 4. Right Button Colors (Standardize to Slate/Blue)
content = content.replace('bg="#16a34a"', 'bg="#334155"')  
content = content.replace('activebackground="#15803d"', 'activebackground="#475569"')
content = content.replace('bg="#4f46e5"', 'bg="#3b82f6"')  
content = content.replace('activebackground="#4338ca"', 'activebackground="#2563eb"')
content = content.replace('bg="#0d9488"', 'bg="#1e293b"')  
content = content.replace('activebackground="#0f766e"', 'activebackground="#334155"')

# 5. Top KPI Card borders and background
content = content.replace('left_f = tk.Frame(box, bg="#ffffff")', 'left_f = tk.Frame(box, bg="#f8fafc")')
content = content.replace('box = tk.Frame(f_cards, bg="#ffffff",', 'box = tk.Frame(f_cards, bg="#f8fafc",')
content = content.replace('relief=tk.SOLID, bd=1', 'relief=tk.FLAT, bd=0') # Flatten borders for cards if any
content = content.replace('highlightbackground="#e2e8f0", highlightthickness=1', 'highlightbackground="#e2e8f0", highlightthickness=1, bg="#f8fafc"') # Adjust border color

with open(fpath, 'w', encoding='utf-8') as f:
    f.write(content)

shutil.copy2(fpath, r'C:\Users\ozan.gemici\Desktop\Dogruer_MasterSuite_Workspace\tools\dogruer_master_suite\master_suite.py')
shutil.copy2(fpath, r'C:\Users\ozan.gemici\Desktop\DogruerMasterSuite_Portable\tools\dogruer_master_suite\master_suite.py')
print('Done!')
