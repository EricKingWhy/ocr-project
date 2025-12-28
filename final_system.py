import re
import sqlite3
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

import auth
import ocr_service

DB_NAME = "invoice_system.db"


def get_db_path():
    return Path.cwd() / DB_NAME


def parse_invoice_text(full_text):
    result = {
        "invoice_code": "",
        "invoice_number": "",
        "date": "",
        "amount": "",
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


class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("登录")
        self.root.geometry("320x200")
        self.root.resizable(False, False)

        tk.Label(root, text="用户名").pack(pady=(20, 5))
        self.username_entry = tk.Entry(root, width=28)
        self.username_entry.pack()

        tk.Label(root, text="密码").pack(pady=(10, 5))
        self.password_entry = tk.Entry(root, width=28, show="*")
        self.password_entry.pack()

        tk.Button(root, text="登录", width=12, command=self.login).pack(pady=15)

        self.username_entry.focus_set()

    def login(self):
        db_path = get_db_path()
        if not db_path.exists():
            messagebox.showerror("错误", "找不到 invoice_system.db，请先运行 db_init.py")
            return

        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("提示", "请输入用户名和密码")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username FROM users WHERE username = ? AND password = ?",
                (username, password),
            )
            row = cursor.fetchone()
        finally:
            conn.close()

        if row:
            self.root.destroy()
            main_root = tk.Tk()
            SystemWindow(main_root)
            main_root.mainloop()
        else:
            messagebox.showwarning("登录失败", "用户名或密码错误")


class SystemWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("发票识别系统")
        self.root.geometry("980x620")

        self.file_path = None
        self.preview_image = None

        self._build_ui()

    def _build_ui(self):
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X)

        tk.Button(top_frame, text="选择图片", width=12, command=self.select_image).pack(
            side=tk.LEFT, padx=8
        )
        tk.Button(top_frame, text="开始识别", width=12, command=self.start_recognition).pack(
            side=tk.LEFT, padx=8
        )
        tk.Button(top_frame, text="保存到数据库", width=12, command=self.save_to_db).pack(
            side=tk.LEFT, padx=8
        )

        body_frame = tk.Frame(self.root)
        body_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        left_frame = tk.LabelFrame(body_frame, text="图片预览区")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.image_label = tk.Label(left_frame, text="请先选择图片", bg="#f0f0f0")
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        right_frame = tk.LabelFrame(body_frame, text="识别结果录入区", width=320)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.entries = {}
        fields = [
            ("发票代码", "invoice_code"),
            ("发票号码", "invoice_number"),
            ("日期", "date"),
            ("金额", "amount"),
        ]

        for label, key in fields:
            row = tk.Frame(right_frame)
            row.pack(fill=tk.X, pady=8, padx=10)
            tk.Label(row, text=label, width=10, anchor="e").pack(side=tk.LEFT)
            entry = tk.Entry(row, width=22)
            entry.pack(side=tk.LEFT, padx=6)
            self.entries[key] = entry

        self.status_var = tk.StringVar(value="系统就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, anchor="w")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

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
        img.thumbnail((600, 420))
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

            self.root.after(0, lambda: self._fill_entries(parsed))
            self.root.after(0, lambda: messagebox.showinfo("成功", "识别完成"))
        except Exception as exc:
            self._show_error(str(exc))
        finally:
            self._set_status("系统就绪")

    def _fill_entries(self, data):
        for key, entry in self.entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, data.get(key, ""))

    def save_to_db(self):
        db_path = get_db_path()
        if not db_path.exists():
            messagebox.showerror("错误", "找不到 invoice_system.db，请先运行 db_init.py")
            return

        payload = {
            "invoice_code": self.entries["invoice_code"].get().strip(),
            "invoice_number": self.entries["invoice_number"].get().strip(),
            "date": self.entries["date"].get().strip(),
            "amount": self.entries["amount"].get().strip(),
        }

        if not any(payload.values()):
            messagebox.showwarning("提示", "请输入或识别后再保存")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO invoices (code, number, date, amount)
                VALUES (?, ?, ?, ?)
                """,
                (
                    payload["invoice_code"],
                    payload["invoice_number"],
                    payload["date"],
                    payload["amount"],
                ),
            )
            conn.commit()
        finally:
            conn.close()

        messagebox.showinfo("保存成功", "数据已保存到数据库")

    def _set_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def _show_error(self, message):
        self.root.after(0, lambda: messagebox.showerror("错误", message))


if __name__ == "__main__":
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()
