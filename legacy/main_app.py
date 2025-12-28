import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import sqlite3
import requests
import base64
import re
import threading
from PIL import Image, ImageTk

# ================= 1. 配置区域 =================
# 必须填入你的百度云 Key
API_KEY = "GyqyRcadrpJqptsANO7SE86g"
SECRET_KEY = "vTQK91cPqJXMzmzWlxxWzF1UHYtMakCN"

# 接口地址
TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'
OCR_URL = 'https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic'

# ================= 2. 数据库操作 =================
DB_NAME = 'invoice_system.db'

def login_check(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    res = c.fetchone()
    conn.close()
    return res is not None

def insert_invoice(code, number, date, amount):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO invoices (code, number, date, amount) VALUES (?, ?, ?, ?)", 
              (code, number, date, amount))
    conn.commit()
    conn.close()

def query_all_invoices():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM invoices")
    res = c.fetchall()
    conn.close()
    return res

def delete_invoice(inv_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM invoices WHERE id=?", (inv_id,))
    conn.commit()
    conn.close()

# ================= 3. 主应用程序框架 =================
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("发票管理系统 (实训版)")
        self.geometry("900x600")
        
        # 容器：用于堆叠所有页面
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)
        
        self.frames = {}
        
        # 初始化所有页面
        for F in (LoginPage, MainMenu, ScanPage, QueryPage, DeletePage):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.show_frame("LoginPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        # 如果是查询页，自动刷新数据
        if page_name == "QueryPage":
            frame.refresh_data()

# ================= 4. 页面定义 =================

# --- 页面1：登录 (Login) ---
class LoginPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        tk.Label(self, text="系统登录", font=("黑体", 24)).pack(pady=50)
        
        frame_form = tk.Frame(self)
        frame_form.pack()
        
        tk.Label(frame_form, text="账号:", font=("微软雅黑", 14)).grid(row=0, column=0, pady=10)
        self.entry_user = tk.Entry(frame_form, font=("微软雅黑", 14))
        self.entry_user.grid(row=0, column=1, pady=10)
        
        tk.Label(frame_form, text="密码:", font=("微软雅黑", 14)).grid(row=1, column=0, pady=10)
        self.entry_pass = tk.Entry(frame_form, font=("微软雅黑", 14), show="*")
        self.entry_pass.grid(row=1, column=1, pady=10)
        
        # 按钮区域：登录 & 重置
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=30)
        
        tk.Button(btn_frame, text="登 录", width=10, bg="#4CAF50", fg="white", 
                  command=self.handle_login).pack(side=tk.LEFT, padx=20)
        tk.Button(btn_frame, text="重 置", width=10, bg="#f44336", fg="white", 
                  command=self.handle_reset).pack(side=tk.LEFT, padx=20)

    def handle_login(self):
        u = self.entry_user.get()
        p = self.entry_pass.get()
        if login_check(u, p):
            self.controller.show_frame("MainMenu")
        else:
            messagebox.showerror("错误", "账号或密码错误 (默认: admin/123456)")

    def handle_reset(self):
        self.entry_user.delete(0, tk.END)
        self.entry_pass.delete(0, tk.END)

# --- 页面2：主菜单 (Main Menu) ---
class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # 2.1 左上角返回 (注销)
        top_bar = tk.Frame(self, bg="#ddd", height=40)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(top_bar, text="< 返回登录", command=lambda: controller.show_frame("LoginPage")).pack(side=tk.LEFT, padx=10, pady=5)
        
        tk.Label(self, text="功能主菜单", font=("黑体", 24)).pack(pady=40)
        
        # 2.2 中间三大模块：扫描、删除、查询
        btn_frame = tk.Frame(self)
        btn_frame.pack(expand=True)
        
        btn_opts = {'width': 15, 'height': 2, 'font': ("微软雅黑", 16)}
        
        tk.Button(btn_frame, text="📸 扫描录入", bg="#2196F3", fg="white", **btn_opts,
                  command=lambda: controller.show_frame("ScanPage")).pack(pady=15)
        
        tk.Button(btn_frame, text="🔍 查询结果", bg="#FF9800", fg="white", **btn_opts,
                  command=lambda: controller.show_frame("QueryPage")).pack(pady=15)
        
        tk.Button(btn_frame, text="🗑️ 删除记录", bg="#9E9E9E", fg="white", **btn_opts,
                  command=lambda: controller.show_frame("DeletePage")).pack(pady=15)

# --- 页面3：扫描录入 (Scan Module) ---
class ScanPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        
        # 返回导航
        tk.Button(self, text="< 返回主菜单", command=lambda: controller.show_frame("MainMenu")).pack(anchor='nw', padx=10, pady=10)
        
        # 左右分栏
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # 左侧图片
        self.left_frame = tk.LabelFrame(paned, text="图片预览", width=400)
        paned.add(self.left_frame)
        self.img_label = tk.Label(self.left_frame, text="暂无图片")
        self.img_label.pack()
        
        # 右侧表单
        self.right_frame = tk.LabelFrame(paned, text="信息录入与修改", width=400)
        paned.add(self.right_frame)
        
        tk.Button(self.right_frame, text="1. 选择图片", command=self.load_image).pack(pady=5)
        tk.Button(self.right_frame, text="2. 百度OCR识别", command=self.start_ocr, bg="#2196F3", fg="white").pack(pady=5)
        
        # 输入修改内容模块
        self.entries = {}
        fields = ['发票代码', '发票号码', '开票日期', '合计金额']
        for f in fields:
            row = tk.Frame(self.right_frame)
            row.pack(fill=tk.X, pady=5, padx=10)
            tk.Label(row, text=f).pack(side=tk.LEFT)
            e = tk.Entry(row)
            e.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            self.entries[f] = e
            
        tk.Button(self.right_frame, text="3. 保存到数据库", command=self.save_db, bg="#4CAF50", fg="white").pack(pady=20)

    def load_image(self):
        self.path = filedialog.askopenfilename()
        if self.path:
            img = Image.open(self.path)
            img.thumbnail((300, 400))
            self.photo = ImageTk.PhotoImage(img)
            self.img_label.config(image=self.photo)

    def start_ocr(self):
        threading.Thread(target=self.run_ocr_thread, daemon=True).start()

    def run_ocr_thread(self):
        try:
            # 1. Token
            tk.messagebox.showinfo("提示", "正在请求百度云...")
            token_resp = requests.post(TOKEN_URL, params={'grant_type': 'client_credentials', 'client_id': API_KEY, 'client_secret': SECRET_KEY})
            token = token_resp.json()['access_token']
            
            # 2. OCR
            with open(self.path, 'rb') as f:
                img_b64 = base64.b64encode(f.read())
            ocr_resp = requests.post(f"{OCR_URL}?access_token={token}", data={"image": img_b64}, headers={'content-type': 'application/x-www-form-urlencoded'})
            words = ocr_resp.json()['words_result']
            text = "\n".join([w['words'] for w in words])
            
            # 3. 正则
            data = {}
            data['发票代码'] = re.search(r'(?<!\d)(\d{10}|\d{12})(?!\d)', text).group(1) if re.search(r'(?<!\d)(\d{10}|\d{12})(?!\d)', text) else ""
            data['发票号码'] = re.search(r'(?<!\d)(\d{8})(?!\d)', text).group(1) if re.search(r'(?<!\d)(\d{8})(?!\d)', text) else ""
            data['开票日期'] = re.search(r'(\d{4}[年-]\d{1,2}[月-]\d{1,2})', text).group(1) if re.search(r'(\d{4}[年-]\d{1,2}[月-]\d{1,2})', text) else ""
            data['合计金额'] = re.findall(r'(?:￥|¥)?(\d+\.\d{2})', text)[-1] if re.findall(r'(?:￥|¥)?(\d+\.\d{2})', text) else ""
            
            # 填入输入框
            for k, v in data.items():
                self.entries[k].delete(0, tk.END)
                self.entries[k].insert(0, v)
                
        except Exception as e:
            messagebox.showerror("OCR失败", str(e))

    def save_db(self):
        vals = [self.entries[k].get() for k in ['发票代码', '发票号码', '开票日期', '合计金额']]
        insert_invoice(*vals)
        messagebox.showinfo("成功", "已保存到数据库")

# --- 页面4：查询结果 (Query Module) ---
class QueryPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        tk.Button(self, text="< 返回主菜单", command=lambda: controller.show_frame("MainMenu")).pack(anchor='nw', padx=10)
        
        tk.Label(self, text="数据库查询结果", font=("黑体", 18)).pack(pady=10)
        
        # 表格
        cols = ("ID", "代码", "号码", "日期", "金额")
        self.tree = ttk.Treeview(self, columns=cols, show='headings')
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    def refresh_data(self):
        # 清空旧数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        # 查库
        rows = query_all_invoices()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

# --- 页面5：删除模块 (Delete Module) ---
class DeletePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        tk.Button(self, text="< 返回主菜单", command=lambda: controller.show_frame("MainMenu")).pack(anchor='nw', padx=10)
        
        tk.Label(self, text="删除记录", font=("黑体", 18)).pack(pady=20)
        
        frame = tk.Frame(self)
        frame.pack()
        tk.Label(frame, text="请输入要删除的 ID:").pack(side=tk.LEFT)
        self.del_entry = tk.Entry(frame)
        self.del_entry.pack(side=tk.LEFT, padx=10)
        tk.Button(frame, text="删除", bg="red", fg="white", command=self.do_delete).pack(side=tk.LEFT)
        
        # 显示简略列表方便查看ID
        self.listbox = tk.Listbox(self, width=80)
        self.listbox.pack(pady=20)
        
        # 每次显示页面时刷新列表
        self.bind('<Visibility>', self.refresh_list)

    def refresh_list(self, event=None):
        self.listbox.delete(0, tk.END)
        rows = query_all_invoices()
        for row in rows:
            self.listbox.insert(tk.END, f"ID: {row[0]} | 号码: {row[2]} | 金额: {row[4]}")

    def do_delete(self):
        try:
            tid = int(self.del_entry.get())
            delete_invoice(tid)
            messagebox.showinfo("成功", "删除成功")
            self.refresh_list()
        except:
            messagebox.showerror("错误", "请输入有效的数字ID")

if __name__ == "__main__":
    app = Application()
    app.mainloop()