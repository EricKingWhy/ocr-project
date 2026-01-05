import re
import sqlite3
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import auth
import ocr_service

DB_NAME = "invoice_system.db"

FONT_TITLE = ("Microsoft YaHei", 20)
FONT_LABEL = ("Microsoft YaHei", 11)
FONT_BTN = ("Microsoft YaHei", 12)

_SCHEMA_READY = False


def get_db_path():
    return Path.cwd() / DB_NAME


def with_db():
    return sqlite3.connect(get_db_path())


def db_exists():
    return get_db_path().exists()


def ensure_schema():
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    conn = with_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users
            (username TEXT PRIMARY KEY, password TEXT)
            """
        )
        cursor.execute("INSERT OR IGNORE INTO users VALUES ('admin', '123456')")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             code TEXT,
             number TEXT,
             date TEXT,
             amount TEXT,
             address TEXT,
             tax_no TEXT,
             bank TEXT)
            """
        )
        cursor.execute("PRAGMA table_info(invoices)")
        existing = {row[1] for row in cursor.fetchall()}
        columns = {
            "address": "TEXT",
            "tax_no": "TEXT",
            "bank": "TEXT",
        }
        for name, col_type in columns.items():
            if name not in existing:
                cursor.execute(f"ALTER TABLE invoices ADD COLUMN {name} {col_type}")
        conn.commit()
        _SCHEMA_READY = True
    finally:
        conn.close()


def login_check(username, password):
    ensure_schema()
    conn = with_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def insert_invoice(code, number, date, amount, address, tax_no, bank):
    ensure_schema()
    conn = with_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO invoices (code, number, date, amount, address, tax_no, bank)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (code, number, date, amount, address, tax_no, bank),
        )
        conn.commit()
    finally:
        conn.close()


def query_all_invoices():
    ensure_schema()
    conn = with_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, code, number, date, amount, address, tax_no, bank FROM invoices"
        )
        return cursor.fetchall()
    finally:
        conn.close()


def query_invoices_by_code_or_number(keyword):
    ensure_schema()
    conn = with_db()
    try:
        cursor = conn.cursor()
        like = f"%{keyword}%"
        cursor.execute(
            """
            SELECT id, code, number, date, amount, address, tax_no, bank
            FROM invoices
            WHERE code LIKE ? OR number LIKE ?
            """,
            (like, like),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def update_invoice(inv_id, code, number, date, amount, address, tax_no, bank):
    ensure_schema()
    conn = with_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE invoices
            SET code = ?, number = ?, date = ?, amount = ?, address = ?, tax_no = ?, bank = ?
            WHERE id = ?
            """,
            (code, number, date, amount, address, tax_no, bank, inv_id),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def delete_invoice(inv_id):
    ensure_schema()
    conn = with_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoices WHERE id = ?", (inv_id,))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def parse_invoice_text(full_text):
    result = {
        "invoice_code": "",
        "invoice_number": "",
        "date": "",
        "amount": "",
        "address": "",
        "tax_no": "",
        "bank": "",
    }

    code = re.search(r"(?<!\d)(\d{10}|\d{12})(?!\d)", full_text)
    if code:
        result["invoice_code"] = code.group(1)

    number = re.search(r"(?<!\d)(\d{8})(?!\d)", full_text)
    if number:
        result["invoice_number"] = number.group(1)

    date = re.search(r"(\d{4}[年/-]\d{1,2}[月/-]\d{1,2})", full_text)
    if date:
        result["date"] = date.group(1)

    amounts = re.findall(r"(\d+\.\d{2})", full_text)
    if amounts:
        result["amount"] = amounts[-1]

    return result


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_schema()
        self.title("票据管理系统")
        self.geometry("980x640")
        self.resizable(False, False)

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for page in (LoginPage, MainMenu, ScanPage, QueryPage, DeletePage):
            frame = page(parent=self.container, controller=self)
            self.frames[page.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()


class LoginPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="系统登录", font=FONT_TITLE).pack(pady=40)

        form = tk.Frame(self)
        form.pack()

        tk.Label(form, text="账号：", font=FONT_LABEL, width=8, anchor="e").grid(
            row=0, column=0, pady=8
        )
        self.entry_user = tk.Entry(form, font=FONT_LABEL, width=20)
        self.entry_user.grid(row=0, column=1, pady=8)

        tk.Label(form, text="密码：", font=FONT_LABEL, width=8, anchor="e").grid(
            row=1, column=0, pady=8
        )
        self.entry_pass = tk.Entry(form, font=FONT_LABEL, width=20, show="*")
        self.entry_pass.grid(row=1, column=1, pady=8)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=30)

        tk.Button(
            btn_frame,
            text="登录",
            width=10,
            font=FONT_BTN,
            bg="#4CAF50",
            fg="white",
            command=self.handle_login,
        ).pack(side=tk.LEFT, padx=20)
        tk.Button(
            btn_frame,
            text="重置",
            width=10,
            font=FONT_BTN,
            bg="#f44336",
            fg="white",
            command=self.handle_reset,
        ).pack(side=tk.LEFT, padx=20)

        self.entry_user.focus_set()

    def handle_login(self):
        if not db_exists():
            messagebox.showerror("错误", "找不到 invoice_system.db，请先运行 db_init.py")
            return
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        if not username or not password:
            messagebox.showwarning("提示", "请输入账号和密码")
            return
        if login_check(username, password):
            self.controller.show_frame("MainMenu")
        else:
            messagebox.showerror("登录失败", "账号或密码错误（默认：admin/123456）")

    def handle_reset(self):
        self.entry_user.delete(0, tk.END)
        self.entry_pass.delete(0, tk.END)


class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        top_bar = tk.Frame(self, height=40)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(
            top_bar,
            text="返回",
            width=8,
            command=lambda: controller.show_frame("LoginPage"),
        ).pack(side=tk.LEFT, padx=10, pady=5)

        tk.Label(self, text="票据管理系统", font=FONT_TITLE).pack(pady=40)

        btn_frame = tk.Frame(self)
        btn_frame.pack(expand=True)

        btn_opts = {"width": 16, "height": 2, "font": FONT_BTN}

        tk.Button(
            btn_frame,
            text="扫描录入",
            bg="#2196F3",
            fg="white",
            command=lambda: controller.show_frame("ScanPage"),
            **btn_opts,
        ).pack(pady=14)
        tk.Button(
            btn_frame,
            text="查询结果",
            bg="#FF9800",
            fg="white",
            command=lambda: controller.show_frame("QueryPage"),
            **btn_opts,
        ).pack(pady=14)
        tk.Button(
            btn_frame,
            text="删除记录",
            bg="#9E9E9E",
            fg="white",
            command=lambda: controller.show_frame("DeletePage"),
            **btn_opts,
        ).pack(pady=14)


class ScanPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.file_path = None
        self.preview_image = None

        tk.Button(
            self, text="返回", width=8, command=lambda: controller.show_frame("MainMenu")
        ).pack(anchor="nw", padx=10, pady=10)

        tk.Label(self, text="发票扫描", font=FONT_TITLE).pack(pady=5)

        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        left_frame = tk.LabelFrame(paned, text="图片预览", width=520)
        paned.add(left_frame)
        self.image_label = tk.Label(left_frame, text="请先选择图片", bg="#f0f0f0")
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        right_frame = tk.LabelFrame(paned, text="输入修改内容", width=360)
        paned.add(right_frame)

        tk.Button(
            right_frame, text="选择图片", width=14, command=self.select_image
        ).pack(pady=6)
        tk.Button(
            right_frame,
            text="OCR识别",
            width=14,
            bg="#2196F3",
            fg="white",
            command=self.start_recognition,
        ).pack(pady=6)

        self.entries = {}
        fields = [
            ("发票代码", "invoice_code"),
            ("发票号码", "invoice_number"),
            ("日期", "date"),
            ("金额", "amount"),
            ("地址", "address"),
            ("税号", "tax_no"),
            ("银行", "bank"),
        ]
        for label, key in fields:
            row = tk.Frame(right_frame)
            row.pack(fill=tk.X, pady=6, padx=10)
            tk.Label(row, text=f"{label}：", font=FONT_LABEL, width=8, anchor="e").pack(
                side=tk.LEFT
            )
            entry = tk.Entry(row, font=FONT_LABEL, width=18)
            entry.pack(side=tk.LEFT, padx=6)
            self.entries[key] = entry

        tk.Button(
            right_frame,
            text="保存",
            width=14,
            bg="#4CAF50",
            fg="white",
            command=self.save_to_db,
        ).pack(pady=16)

        self.status_var = tk.StringVar(value="系统就绪")
        tk.Label(self, textvariable=self.status_var, anchor="w").pack(
            side=tk.BOTTOM, fill=tk.X
        )

    def on_show(self):
        self.status_var.set("系统就绪")

    def select_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp")]
        )
        if not path:
            return
        self.file_path = path
        self._show_image(path)
        self.status_var.set(f"已选择图片: {path}")

    def _show_image(self, path):
        img = Image.open(path)
        img.thumbnail((520, 420))
        self.preview_image = ImageTk.PhotoImage(img)
        self.image_label.configure(image=self.preview_image, text="")

    def start_recognition(self):
        if not self.file_path:
            messagebox.showwarning("提示", "请先选择图片")
            return
        threading.Thread(target=self._run_recognition, daemon=True).start()

    def _run_recognition(self):
        try:
            self._set_status("正在获取 Token...")
            token = auth.get_access_token()
            if not token:
                self._show_error("Token 获取失败，请检查 config.py 的 API_KEY/SECRET_KEY")
                return
            self._set_status("正在调用 OCR 接口...")
            words_result = ocr_service.get_text_from_image(self.file_path, token)
            if not words_result:
                self._show_error("识别失败：未返回文字结果")
                return
            self._set_status("正在解析识别结果...")
            full_text = "\n".join([item.get("words", "") for item in words_result])
            parsed = parse_invoice_text(full_text)
            self.controller.after(0, lambda: self._fill_entries(parsed))
            self.controller.after(0, lambda: messagebox.showinfo("成功", "识别完成"))
        except Exception as exc:
            self._show_error(str(exc))
        finally:
            self._set_status("系统就绪")

    def _fill_entries(self, data):
        for key, entry in self.entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, data.get(key, ""))

    def save_to_db(self):
        try:
            ensure_schema()
        except Exception as exc:
            messagebox.showerror("错误", f"数据库初始化失败: {exc}")
            return
        payload = {
            "invoice_code": self.entries["invoice_code"].get().strip(),
            "invoice_number": self.entries["invoice_number"].get().strip(),
            "date": self.entries["date"].get().strip(),
            "amount": self.entries["amount"].get().strip(),
            "address": self.entries["address"].get().strip(),
            "tax_no": self.entries["tax_no"].get().strip(),
            "bank": self.entries["bank"].get().strip(),
        }
        if not any(payload.values()):
            messagebox.showwarning("提示", "请输入或识别后再保存")
            return
        try:
            insert_invoice(
                payload["invoice_code"],
                payload["invoice_number"],
                payload["date"],
                payload["amount"],
                payload["address"],
                payload["tax_no"],
                payload["bank"],
            )
        except Exception as exc:
            messagebox.showerror("错误", f"保存失败: {exc}")
            return
        messagebox.showinfo("保存成功", "数据已保存到数据库")

    def _set_status(self, text):
        self.controller.after(0, lambda: self.status_var.set(text))

    def _show_error(self, message):
        self.controller.after(0, lambda: messagebox.showerror("错误", message))


class QueryPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.selected_id = None

        tk.Button(
            self, text="返回", width=8, command=lambda: controller.show_frame("MainMenu")
        ).pack(anchor="nw", padx=10, pady=10)

        tk.Label(self, text="查询结果模块", font=FONT_TITLE).pack(pady=5)

        search_frame = tk.Frame(self)
        search_frame.pack(fill=tk.X, padx=16, pady=6)
        tk.Label(search_frame, text="发票代码/号码：", font=FONT_LABEL).pack(
            side=tk.LEFT
        )
        self.search_entry = tk.Entry(search_frame, font=FONT_LABEL, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        tk.Button(
            search_frame,
            text="查询",
            width=8,
            command=self.apply_search,
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            search_frame,
            text="清空",
            width=8,
            command=self.clear_search,
        ).pack(side=tk.LEFT)

        table_frame = tk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=10)

        cols = ("ID", "发票代码", "发票号码", "日期", "金额", "地址", "税号", "银行")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        edit_frame = tk.LabelFrame(self, text="输入修改内容")
        edit_frame.pack(fill=tk.X, padx=16, pady=10)

        self.edit_entries = {}
        fields = [
            ("ID", "id"),
            ("发票代码", "code"),
            ("发票号码", "number"),
            ("日期", "date"),
            ("金额", "amount"),
            ("地址", "address"),
            ("税号", "tax_no"),
            ("银行", "bank"),
        ]

        for idx, (label, key) in enumerate(fields):
            row = tk.Frame(edit_frame)
            row.grid(row=idx // 4, column=idx % 4, padx=6, pady=6, sticky="w")
            tk.Label(row, text=label, font=FONT_LABEL).pack()
            entry = tk.Entry(row, font=FONT_LABEL, width=16)
            entry.pack()
            if key == "id":
                entry.configure(state="readonly")
            self.edit_entries[key] = entry

        tk.Button(
            edit_frame,
            text="修改",
            width=10,
            font=FONT_BTN,
            bg="#4CAF50",
            fg="white",
            command=self.update_selected,
        ).grid(row=2, column=0, columnspan=4, pady=8)

    def on_show(self):
        self.refresh_data()

    def refresh_data(self):
        try:
            rows = query_all_invoices()
        except Exception as exc:
            messagebox.showerror("错误", f"读取数据库失败: {exc}")
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def apply_search(self):
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.refresh_data()
            return
        try:
            rows = query_invoices_by_code_or_number(keyword)
        except Exception as exc:
            messagebox.showerror("错误", f"查询失败: {exc}")
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.refresh_data()

    def _on_select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            self.selected_id = None
            return
        values = self.tree.item(selection[0], "values")
        self.selected_id = values[0]
        mapping = {
            "id": values[0],
            "code": values[1],
            "number": values[2],
            "date": values[3],
            "amount": values[4],
            "address": values[5],
            "tax_no": values[6],
            "bank": values[7],
        }
        for key, entry in self.edit_entries.items():
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, mapping[key])
            if key == "id":
                entry.configure(state="readonly")

    def update_selected(self):
        inv_id = self.edit_entries["id"].get().strip()
        if not inv_id:
            selection = self.tree.selection()
            if selection:
                values = self.tree.item(selection[0], "values")
                inv_id = str(values[0])
            elif self.selected_id:
                inv_id = str(self.selected_id)
            else:
                messagebox.showwarning("提示", "请选择要修改的记录")
                return
        try:
            inv_id_int = int(inv_id)
        except ValueError:
            messagebox.showerror("错误", "ID 必须是数字")
            return
        code = self.edit_entries["code"].get().strip()
        number = self.edit_entries["number"].get().strip()
        date = self.edit_entries["date"].get().strip()
        amount = self.edit_entries["amount"].get().strip()
        address = self.edit_entries["address"].get().strip()
        tax_no = self.edit_entries["tax_no"].get().strip()
        bank = self.edit_entries["bank"].get().strip()
        changed = update_invoice(
            inv_id_int, code, number, date, amount, address, tax_no, bank
        )
        if changed:
            messagebox.showinfo("成功", "修改完成")
            self.refresh_data()
        else:
            messagebox.showwarning("提示", "未找到对应记录")


class DeletePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.selected_id = None

        tk.Button(
            self, text="返回", width=8, command=lambda: controller.show_frame("MainMenu")
        ).pack(anchor="nw", padx=10, pady=10)

        tk.Label(self, text="删除记录", font=FONT_TITLE).pack(pady=5)

        form = tk.Frame(self)
        form.pack(pady=10)
        tk.Label(form, text="输入要删除的 ID：", font=FONT_LABEL).pack(side=tk.LEFT)
        self.entry_id = tk.Entry(form, font=FONT_LABEL, width=12)
        self.entry_id.pack(side=tk.LEFT, padx=8)
        tk.Button(
            form,
            text="删除",
            bg="#f44336",
            fg="white",
            width=8,
            command=self.do_delete,
        ).pack(side=tk.LEFT, padx=6)

        self.list_tree = ttk.Treeview(
            self,
            columns=("ID", "发票号码", "日期", "金额", "地址", "税号", "银行"),
            show="headings",
            height=12,
        )
        for col in ("ID", "发票号码", "日期", "金额", "地址", "税号", "银行"):
            self.list_tree.heading(col, text=col)
            self.list_tree.column(col, width=120, anchor="center")
        self.list_tree.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
        self.list_tree.bind("<<TreeviewSelect>>", self._on_select)

    def on_show(self):
        self.refresh_list()

    def refresh_list(self):
        try:
            rows = query_all_invoices()
        except Exception as exc:
            messagebox.showerror("错误", f"读取数据库失败: {exc}")
            return
        for item in self.list_tree.get_children():
            self.list_tree.delete(item)
        for row in rows:
            self.list_tree.insert(
                "",
                tk.END,
                values=(row[0], row[2], row[3], row[4], row[5], row[6], row[7]),
            )

    def _on_select(self, event=None):
        selection = self.list_tree.selection()
        if not selection:
            self.selected_id = None
            return
        values = self.list_tree.item(selection[0], "values")
        self.selected_id = values[0]
        self.entry_id.delete(0, tk.END)
        self.entry_id.insert(0, str(values[0]))

    def do_delete(self):
        inv_id = self.entry_id.get().strip()
        if not inv_id:
            selection = self.list_tree.selection()
            if selection:
                values = self.list_tree.item(selection[0], "values")
                inv_id = str(values[0])
            elif self.selected_id:
                inv_id = str(self.selected_id)
            else:
                messagebox.showwarning("提示", "请输入要删除的 ID")
                return
        try:
            inv_id_int = int(inv_id)
        except ValueError:
            messagebox.showerror("错误", "ID 必须是数字，请从列表选择记录")
            return
        deleted = delete_invoice(inv_id_int)
        if deleted:
            messagebox.showinfo("成功", "删除成功")
            self.entry_id.delete(0, tk.END)
            self.refresh_list()
        else:
            messagebox.showwarning("提示", "未找到对应记录")


if __name__ == "__main__":
    app = Application()
    app.mainloop()
