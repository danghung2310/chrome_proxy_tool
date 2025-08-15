import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

PROFILE_FILE = "profiles.json"
CHROMEDRIVER_PATH = os.path.join("driver", "chromedriver.exe")

# Tải danh sách profile
def load_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Lưu danh sách profile
def save_profiles(data):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Mở Chrome với proxy
def open_chrome(profile_name, proxy=None):
    profile_path = os.path.join("profiles", profile_name)
    os.makedirs(profile_path, exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={os.path.abspath(profile_path)}")

    if proxy:
        chrome_options.add_argument(f'--proxy-server={proxy}')

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://whatismyipaddress.com/")

# GUI
def main():
    root = tk.Tk()
    root.title("Chrome Proxy Tool")

    profiles = load_profiles()

    # Giao diện
    tk.Label(root, text="Tên Profile:").grid(row=0, column=0)
    profile_entry = tk.Entry(root)
    profile_entry.grid(row=0, column=1)

    tk.Label(root, text="Proxy (IP:PORT hoặc IP:PORT:USER:PASS):").grid(row=1, column=0)
    proxy_entry = tk.Entry(root)
    proxy_entry.grid(row=1, column=1)

    def create_profile():
        name = profile_entry.get().strip()
        proxy = proxy_entry.get().strip()
        if not name:
            messagebox.showerror("Lỗi", "Nhập tên profile")
            return
        profiles[name] = {"proxy": proxy}
        save_profiles(profiles)
        messagebox.showinfo("Thành công", f"Đã tạo profile {name}")

    def open_profile():
        name = profile_entry.get().strip()
        if name not in profiles:
            messagebox.showerror("Lỗi", "Profile không tồn tại")
            return
        open_chrome(name, profiles[name]["proxy"])

    tk.Button(root, text="Tạo Profile", command=create_profile).grid(row=2, column=0)
    tk.Button(root, text="Mở Chrome", command=open_profile).grid(row=2, column=1)

    root.mainloop()

if __name__ == "__main__":
    main()
