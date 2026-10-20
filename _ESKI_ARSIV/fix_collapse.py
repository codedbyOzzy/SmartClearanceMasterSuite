import sys
import shutil

fpath = r'C:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Belgeler\V1SmartClearance_Gumruk\tools\dogruer_master_suite\master_suite.py'
with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """    def toggle_sidebar_collapse(self):
        self.sidebar_is_collapsed = not self.sidebar_is_collapsed
        if self.sidebar_is_collapsed:
            self.sidebar_frame.config(width=52)
            self.lbl_logo.config(text="🛡", anchor="center")
            self.lbl_sub_badge.pack_forget()
            self.btn_toggle_sidebar.config(text="▶", font=("Segoe UI", 9, "bold"))
            for grp in self.category_headers:
                grp.pack_forget()
            for code, btn in self.nav_buttons.items():
                btn["text_frame"].pack_forget()
                btn["icon_lbl"].config(font=("Segoe UI", 11), width=2)
            self.lbl_side_sync.config(text="⚡", anchor="center")
        else:
            self.sidebar_frame.config(width=240)
            for child in self.sidebar_frame.winfo_children():
                child.destroy()
            self.setup_sidebar()
            self.switch_tab(self.current_tab)"""

new_logic = """    def toggle_sidebar_collapse(self):
        self.sidebar_is_collapsed = not self.sidebar_is_collapsed
        if self.sidebar_is_collapsed:
            self.sidebar_frame.config(width=52)
            if hasattr(self, 'lbl_logo_smart'): self.lbl_logo_smart.pack_forget()
            if hasattr(self, 'lbl_logo_clearance'): self.lbl_logo_clearance.pack_forget()
            self.lbl_sub_badge.pack_forget()
            self.btn_toggle_sidebar.config(text="▶", font=("Segoe UI", 9, "bold"))
            for grp in self.category_headers:
                grp.pack_forget()
            for code, btn in self.nav_buttons.items():
                btn["text_frame"].pack_forget()
                btn["icon_lbl"].config(font=("Segoe UI", 11), width=2)
            if hasattr(self, 'bottom_box'): self.bottom_box.pack_forget()
        else:
            self.sidebar_frame.config(width=240)
            for child in self.sidebar_frame.winfo_children():
                child.destroy()
            self.setup_sidebar()
            self.switch_tab(self.current_tab)"""

import re
content = re.sub(
    r'    def toggle_sidebar_collapse\(self\):[\s\S]*?self\.switch_tab\(self\.current_tab\)',
    new_logic,
    content
)

with open(fpath, 'w', encoding='utf-8') as f:
    f.write(content)

shutil.copy2(fpath, r'C:\Users\ozan.gemici\Desktop\Dogruer_MasterSuite_Workspace\tools\dogruer_master_suite\master_suite.py')
shutil.copy2(fpath, r'C:\Users\ozan.gemici\Desktop\DogruerMasterSuite_Portable\tools\dogruer_master_suite\master_suite.py')
print('Collapse logic updated!')
