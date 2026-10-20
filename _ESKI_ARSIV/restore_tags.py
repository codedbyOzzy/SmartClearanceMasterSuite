import sys
import shutil

fpath = r'C:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Belgeler\V1SmartClearance_Gumruk\tools\dogruer_master_suite\master_suite.py'
with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('self.tree_cockpit.tag_configure("kirmizi_hat", background="#ffffff")', 'self.tree_cockpit.tag_configure("kirmizi_hat", background="#fef2f2", foreground="#991b1b")')
content = content.replace('self.tree_cockpit.tag_configure("tescil_ok", background="#ffffff")', 'self.tree_cockpit.tag_configure("tescil_ok", background="#f4fffa", foreground="#166534")')
content = content.replace('self.tree_cockpit.tag_configure("mail_ok", background="#ffffff")', 'self.tree_cockpit.tag_configure("mail_ok", background="#f4fffa", foreground="#047857")')
content = content.replace('self.tree_cockpit.tag_configure("mail_warning", background="#ffffff")', 'self.tree_cockpit.tag_configure("mail_warning", background="#fff7ed", foreground="#c2410c")')
content = content.replace('self.tree_cockpit.tag_configure("closed", background="#ffffff")', 'self.tree_cockpit.tag_configure("closed", background="#f8fafc", foreground="#64748b")')

with open(fpath, 'w', encoding='utf-8') as f:
    f.write(content)

shutil.copy2(fpath, r'C:\Users\ozan.gemici\Desktop\Dogruer_MasterSuite_Workspace\tools\dogruer_master_suite\master_suite.py')
shutil.copy2(fpath, r'C:\Users\ozan.gemici\Desktop\DogruerMasterSuite_Portable\tools\dogruer_master_suite\master_suite.py')
print('Tags restored.')
