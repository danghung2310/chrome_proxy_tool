import os
import json
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, Listbox
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

PROFILE_FILE = "profiles.json"
PROXY_FILE = "proxies.txt"

def load_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_profiles(profiles):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

def load_proxies_from_file():
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            return proxies
    return []

def launch_chrome(profile_dir, proxy=None):
    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--start-maximized")
    if proxy:
        if len(proxy.split(":")) == 4:
            ip, port, user, password = proxy.split(":")
            chrome_options.add_argument(f'--proxy-server=http://{ip}:{port}')
            print(f"[INFO] Proxy with auth not fully handled in this demo: {proxy}")
        else:
            chrome_options.add_argument(f'--proxy-server=http://{proxy}')

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.google.com")

def add_profile():
    name = simpledialog.askstring("Thêm Profile", "Nhập tên profile:")
    if not name:
        return
    proxy = simpledialog.askstring("Proxy", "Nhập proxy (IP:PORT hoặc IP:PORT:USER:PASS, để trống nếu không dùng):")
    profile_dir = os.path.join("chrome_profiles", name)
    os.makedirs(profile_dir, exist_ok=True)

    profiles = load_profiles()
    profiles.append({"name": name, "profile_dir": profile_dir, "proxy": proxy})
    save_profiles(profiles)
    refresh_listbox()

def delete_profile():
    selection = listbox.curselection()
    if not selection:
        return
    idx = selection[0]
    profiles = load_profiles()
    del profiles[idx]
    save_profiles(profiles)
    refresh_listbox()

def launch_selected():
    selection = listbox.curselection()
    if not selection:
        return
    idx = selection[0]
    profiles = load_profiles()
    profile = profiles[idx]
    launch_chrome(profile["profile_dir"], profile.get("proxy"))

def load_from_proxy_file():
    proxies = load_proxies_from_file()
    if not proxies:
        messagebox.showinfo("Thông báo", "Không tìm thấy proxy trong file proxies.txt")
        return
    for i, proxy in enumerate(proxies, 1):
        profile_dir = os.path.join("chrome_profiles", f"profile_{i}")
        os.makedirs(profile_dir, exist_ok=True)
        profiles = load_profiles()
        profiles.append({"name": f"profile_{i}", "profile_dir": profile_dir, "proxy": proxy})
        save_profiles(profiles)
    refresh_listbox()
    messagebox.showinfo("Xong", "Đã load proxies.txt thành profiles.")

def refresh_listbox():
    listbox.delete(0, tk.END)
    for p in load_profiles():
        listbox.insert(tk.END, f"{p['name']} | Proxy: {p.get('proxy', '')}")

os.makedirs("chrome_profiles", exist_ok=True)

root = tk.Tk()
root.title("Chrome Proxy Manager")
root.geometry("600x400")

frame = tk.Frame(root)
frame.pack(pady=10)

btn_add = tk.Button(frame, text="Thêm Profile", command=add_profile)
btn_add.pack(side=tk.LEFT, padx=5)

btn_del = tk.Button(frame, text="Xóa Profile", command=delete_profile)
btn_del.pack(side=tk.LEFT, padx=5)

btn_launch = tk.Button(frame, text="Mở Chrome", command=launch_selected)
btn_launch.pack(side=tk.LEFT, padx=5)

btn_load_file = tk.Button(frame, text="Load proxies.txt", command=load_from_proxy_file)
btn_load_file.pack(side=tk.LEFT, padx=5)

listbox = Listbox(root, width=80)
listbox.pack(pady=10)

refresh_listbox()
root.mainloop()
