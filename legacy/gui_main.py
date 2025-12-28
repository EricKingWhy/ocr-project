import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import requests
import base64
import re
import threading # 用于防止界面卡死

# ================= 配置区域 =================
# 请务必填入你的 Key
API_KEY = "GyqyRcadrpJqptsANO7SE86g"
SECRET_KEY = "vTQK91cPqJXMzmzWlxxWzF1UHYtMakCN"

# 接口地址
TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'
OCR_URL = 'https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic'

class InvoiceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智能发票识别系统 (实训版)")
        self.root.geometry("800x600")
        
        # 变量存储
        self.file_path = None
        self.token = None

        self.setup_ui()

    def setup_ui(self):
        # 1. 顶部操作区
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack()

        btn_select = tk.Button(top_frame, text="1. 选择发票图片", command=self.select_image, width=15, bg="#e1f5fe")
        btn_select.pack(side=tk.LEFT, padx=10)

        btn_run = tk.Button(top_frame, text="2. 开始识别", command=self.start_thread, width=15, bg="#c8e6c9")
        btn_run.pack(side=tk.LEFT, padx=10)

        # 2. 中间图片展示区
        self.img_label = tk.Label(self.root, text="请先选择图片", bg="#f0f0f0", height=15)
        self.img_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 3. 底部结果展示区
        result_frame = tk.Frame(self.root)
        result_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # 定义结果显示的组件
        self.results = {}
        fields = ["发票代码", "发票号码", "开票日期", "合计金额"]
        
        for idx, field in enumerate(fields):
            row = tk.Frame(result_frame)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"{field}:", width=10, anchor='e', font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
            val_label = tk.Label(row, text="等待识别...", font=('Arial', 12), fg="blue")
            val_label.pack(side=tk.LEFT, padx=10)
            self.results[field] = val_label

        # 状态栏
        self.status_label = tk.Label(self.root, text="系统就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.png;*.jpeg")])
        if path:
            self.file_path = path
            self.show_image(path)
            self.status_label.config(text=f"已选中文件: {path}")

    def show_image(self, path):
        # 读取并缩放图片以适应窗口
        img = Image.open(path)
        img.thumbnail((700, 300)) # 限制最大显示尺寸
        photo = ImageTk.PhotoImage(img)
        self.img_label.config(image=photo, text="", height=0)
        self.img_label.image = photo # 保持引用防止被垃圾回收

    def log(self, message):
        self.status_label.config(text=message)
        self.root.update()

    def start_thread(self):
        # 使用线程运行识别，防止界面卡死
        if not self.file_path:
            messagebox.showwarning("提示", "请先选择一张图片！")
            return
        threading.Thread(target=self.run_recognition, daemon=True).start()

    def run_recognition(self):
        # === 这里严格执行之前的5步逻辑 ===
        
        try:
            # 1. 获取Token
            self.log("[1/5] 正在获取 Access Token...")
            params = {'grant_type': 'client_credentials', 'client_id': API_KEY, 'client_secret': SECRET_KEY}
            resp = requests.post(TOKEN_URL, params=params)
            token_data = resp.json()
            if 'access_token' not in token_data:
                messagebox.showerror("错误", "Token获取失败，请检查Key")
                return
            token = token_data['access_token']

            # 2. 图片编码
            self.log("[2/5] 正在读取并编码图片...")
            with open(self.file_path, 'rb') as f:
                img_b64 = base64.b64encode(f.read())

            # 3. 接口调用
            self.log("[3/5] 正在调用百度 OCR 接口...")
            ocr_url = f"{OCR_URL}?access_token={token}"
            headers = {'content-type': 'application/x-www-form-urlencoded'}
            resp_ocr = requests.post(ocr_url, data={"image": img_b64}, headers=headers)
            result_json = resp_ocr.json()

            # 4. 数据解析
            self.log("[4/5] 正在解析返回数据...")
            if 'words_result' not in result_json:
                messagebox.showerror("识别失败", str(result_json))
                return
            
            full_text = "\n".join([item['words'] for item in result_json['words_result']])

            # 5. 正则提取
            self.log("[5/5] 正在提取关键信息...")
            data = {}
            
            # 代码
            code = re.search(r'(?<!\d)(\d{10}|\d{12})(?!\d)', full_text)
            data["发票代码"] = code.group(1) if code else "未识别"
            
            # 号码
            num = re.search(r'(?<!\d)(\d{8})(?!\d)', full_text)
            data["发票号码"] = num.group(1) if num else "未识别"
            
            # 日期
            date = re.search(r'(\d{4}[年-]\d{1,2}[月-]\d{1,2})', full_text)
            data["开票日期"] = date.group(1) if date else "未识别"
            
            # 金额
            amts = re.findall(r'(?:￥|¥)?(\d+\.\d{2})', full_text)
            data["合计金额"] = amts[-1] if amts else "未识别"

            # 更新界面 (回到主线程)
            self.root.after(0, self.update_results, data)
            self.root.after(0, lambda: messagebox.showinfo("成功", "识别完成！"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("系统错误", str(e)))
        finally:
            self.log("就绪")

    def update_results(self, data):
        for key, value in data.items():
            self.results[key].config(text=value, fg="green" if value != "未识别" else "red")

if __name__ == "__main__":
    root = tk.Tk()
    app = InvoiceApp(root)
    root.mainloop()