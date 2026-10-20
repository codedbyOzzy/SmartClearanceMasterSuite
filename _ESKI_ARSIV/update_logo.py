import sys
import shutil
import re

fpath = r'C:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Belgeler\V1SmartClearance_Gumruk\tools\dogruer_master_suite\master_suite.py'
with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Title
content = content.replace('self.root.title("🛡 SmartClearance MasterSuite v3.0")', 'self.root.title("SmartClearance MasterSuite v4.0 PRO")')

# 2. Add Icon Generation Logic in __init__
icon_logic = """
        # Otomatik Ikon Olusturma (PIL ile)
        icon_path = os.path.join(os.path.dirname(__file__), "sc_logo.ico")
        if not os.path.exists(icon_path):
            try:
                from PIL import Image, ImageDraw
                img = Image.new('RGB', (64, 64), color=(15, 23, 42))
                d = ImageDraw.Draw(img)
                d.polygon([(32, 8), (56, 32), (32, 56), (8, 32)], fill=(56, 189, 248))
                d.polygon([(20, 20), (44, 20), (44, 44), (20, 44)], outline=(255, 255, 255), width=2)
                img.save(icon_path, format='ICO')
            except Exception as e:
                print("Ikon olusturulamadi:", e)
        
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass
"""

if "icon_path = os.path.join(os.path.dirname(__file__), \"sc_logo.ico\")" not in content:
    content = content.replace('self.root.title("SmartClearance MasterSuite v4.0 PRO")', 'self.root.title("SmartClearance MasterSuite v4.0 PRO")\n' + icon_logic)

# 3. Modify Sidebar Logo
old_logo_block = """        self.lbl_logo = tk.Label(
            self.brand_box, text="🛡 SmartClearance", font=("Segoe UI", 11, "bold"), fg="#f8fafc", bg="#0b1120", anchor="w"
        )
        self.lbl_logo.pack(fill=tk.X)

        self.lbl_sub_badge = tk.Label(
            self.brand_box, text="⚡ MASTER SUITE v4.0", font=("Segoe UI", 7, "bold"),
            fg="#38bdf8", bg="#082f49", padx=6, pady=2, relief=tk.FLAT
        )
        self.lbl_sub_badge.pack(anchor="w", pady=(3, 0))"""

new_logo_block = """        logo_frame = tk.Frame(self.brand_box, bg="#0b1120")
        logo_frame.pack(fill=tk.X)

        self.lbl_logo_icon = tk.Label(logo_frame, text="⚡", font=("Segoe UI", 14), fg="#38bdf8", bg="#0b1120")
        self.lbl_logo_icon.pack(side=tk.LEFT, padx=(0, 4))

        self.lbl_logo_smart = tk.Label(logo_frame, text="Smart", font=("Segoe UI", 12, "bold"), fg="#f8fafc", bg="#0b1120")
        self.lbl_logo_smart.pack(side=tk.LEFT)

        self.lbl_logo_clearance = tk.Label(logo_frame, text="Clearance", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#0b1120")
        self.lbl_logo_clearance.pack(side=tk.LEFT)

        self.lbl_sub_badge = tk.Label(
            self.brand_box, text="MASTER SUITE v4.0 PRO", font=("Segoe UI", 7, "bold"),
            fg="#e0f2fe", bg="#0284c7", padx=8, pady=3, relief=tk.FLAT
        )
        self.lbl_sub_badge.pack(anchor="w", pady=(6, 0))"""

content = content.replace(old_logo_block, new_logo_block)

# Just in case they had slightly different spaces/characters:
if 'lbl_logo_smart = tk.Label' not in content:
    # Use regex
    content = re.sub(
        r'self\.lbl_logo\s*=\s*tk\.Label\([\s\S]*?self\.lbl_sub_badge\.pack\(anchor="w", pady=\(3, 0\)\)',
        new_logo_block,
        content
    )

with open(fpath, 'w', encoding='utf-8') as f:
    f.write(content)

shutil.copy2(fpath, r'C:\Users\ozan.gemici\Desktop\Dogruer_MasterSuite_Workspace\tools\dogruer_master_suite\master_suite.py')
shutil.copy2(fpath, r'C:\Users\ozan.gemici\Desktop\DogruerMasterSuite_Portable\tools\dogruer_master_suite\master_suite.py')
print('UI Logo Updated')
