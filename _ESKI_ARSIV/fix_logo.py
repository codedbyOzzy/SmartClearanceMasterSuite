import sys
import shutil
import re

fpath = r'C:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Belgeler\V1SmartClearance_Gumruk\tools\dogruer_master_suite\master_suite.py'
with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Title securely
content = re.sub(r'self\.root\.title\(.*?\)', 'self.root.title("SmartClearance MasterSuite v4.0")', content)

# 2. Update Console Log securely
content = content.replace('MASTER SUITE v3.0', 'MASTER SUITE v4.0')

# 3. Update Sidebar Labels to remove gap and change badge text
content = content.replace('self.lbl_logo_smart = tk.Label(logo_frame, text="Smart", font=("Segoe UI", 12, "bold"), fg="#f8fafc", bg="#0b1120")', 'self.lbl_logo_smart = tk.Label(logo_frame, text="Smart", font=("Segoe UI", 12, "bold"), fg="#f8fafc", bg="#0b1120", bd=0, padx=0, pady=0)')
content = content.replace('self.lbl_logo_smart.pack(side=tk.LEFT)', 'self.lbl_logo_smart.pack(side=tk.LEFT, padx=0, pady=0, ipadx=0, ipady=0)')

content = content.replace('self.lbl_logo_clearance = tk.Label(logo_frame, text="Clearance", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#0b1120")', 'self.lbl_logo_clearance = tk.Label(logo_frame, text="Clearance", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#0b1120", bd=0, padx=0, pady=0)')
content = content.replace('self.lbl_logo_clearance.pack(side=tk.LEFT)', 'self.lbl_logo_clearance.pack(side=tk.LEFT, padx=0, pady=0, ipadx=0, ipady=0)')

content = content.replace('text="MASTER SUITE v4.0 PRO"', 'text="MASTER SUITE v4.0"')

with open(fpath, 'w', encoding='utf-8') as f:
    f.write(content)

shutil.copy2(fpath, r'C:\Users\ozan.gemici\Desktop\Dogruer_MasterSuite_Workspace\tools\dogruer_master_suite\master_suite.py')
shutil.copy2(fpath, r'C:\Users\ozan.gemici\Desktop\DogruerMasterSuite_Portable\tools\dogruer_master_suite\master_suite.py')
print('Fixed!')
