import os
import json
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import sys

CONFIG_FILE = "profiles.json"

# Lấy đường dẫn ChromeDriver bên trong exe hoặc khi chạy code
if getattr(sys, 'frozen', False):  # Khi chạy file exe
    DRIVER_PATH = os.path.join(sys._MEIPASS, "driver", "chromedriver.exe")
else:
    DRIVER_PATH = os.path.join("driver", "chromedriver.exe")

def load_profiles():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_profiles(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def launch_chrome(profile_name, proxy):
    try:
        if not os.path.exists(DRIVER_PATH):
            messagebox.showerror("Lỗi", f"Không tìm thấy ChromeDriver tại {DRIVER_PATH}")
            return

        chrome_options = Options()
        profile_path = os.path.join("profiles", profile_name)
        os.makedirs(profile_path, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={os.path.abspath(profile_path)}")

        if proxy:
            proxy_parts = proxy.strip().split(":")
            if len(proxy_parts) == 4:
                ip, port, user, password = proxy_parts
                chrome_options.add_argument(f"--proxy-server=http://{ip}:{port}")
            elif len(proxy_parts) == 2:
                chrome_options.add_argument(f"--proxy-server=http://{proxy_parts[0]}:{proxy_parts[1]}")

        service = Service(DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://whatismyipaddress.com")
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể mở Chrome: {str(e)}")

# GUI
profiles = load_profiles()

def add_profile():
    name = simpledialog.askstring("Profile Name", "Nhập tên profile:")
    if not name:
        return
    proxy = simpledialog.askstring("Proxy", "Nhập proxy (IP:PORT:USER:PASS hoặc IP:PORT):")
    profiles[name] = proxy
    save_profiles(profiles)
    refresh_list()

def load_proxy_file():
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if file_path:
        with open(file_path, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            profiles[f"profile_{i}"] = line.strip()
        save_profiles(profiles)
        refresh_list()

def delete_profile():
    selected = listbox.curselection()
    if selected:
        name = listbox.get(selected[0])
        if name in profiles:
            del profiles[name]
            save_profiles(profiles)
            refresh_list()

def open_profile():
    selected = listbox.curselection()
    if selected:
        name = listbox.get(selected[0])
        proxy = profiles.get(name, None)
        launch_chrome(name, proxy)

def refresh_list():
    listbox.delete(0, tk.END)
    for name in profiles:
        listbox.insert(tk.END, name)

root = tk.Tk()
root.title("Chrome Proxy Manager")

frame = tk.Frame(root)
frame.pack(pady=10)

listbox = tk.Listbox(frame, width=50, height=10)
listbox.pack(side=tk.LEFT, padx=10)

scrollbar = tk.Scrollbar(frame, orient="vertical")
scrollbar.config(command=listbox.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
listbox.config(yscrollcommand=scrollbar.set)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="Thêm profile", command=add_profile).grid(row=0, column=0, padx=5)
tk.Button(btn_frame, text="Xóa profile", command=delete_profile).grid(row=0, column=1, padx=5)
tk.Button(btn_frame, text="Mở profile", command=open_profile).grid(row=0, column=2, padx=5)
tk.Button(btn_frame, text="Load proxy từ file", command=load_proxy_file).grid(row=0, column=3, padx=5)

refresh_list()
root.mainloop()
