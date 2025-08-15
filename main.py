import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import threading

# Load profiles
if os.path.exists("profiles.json"):
    with open("profiles.json", "r", encoding="utf-8") as f:
        profiles = json.load(f)
else:
    profiles = {}

# Hàm lưu profiles
def save_profiles():
    with open("profiles.json", "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=4)

# Hàm mở Chrome với proxy
def open_chrome(profile_name, proxy):
    profile_path = os.path.join("profiles", profile_name)
    os.makedirs(profile_path, exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={os.path.abspath(profile_path)}")

    if proxy:
        proxy_parts = proxy.split(":")
        if len(proxy_parts) == 4:
            ip, port, user, password = proxy_parts
            manifest_json = """
            {
                "version": "1.0.0",
                "manifest_version": 2,
                "name": "Chrome Proxy",
                "permissions": ["proxy","tabs","unlimitedStorage","storage","<all_urls>","webRequest","webRequestBlocking"],
                "background": {"scripts": ["background.js"]},
                "minimum_chrome_version":"22.0.0"
            }
            """
            background_js = f"""
            var config = {{
                mode: "fixed_servers",
                rules: {{
                    singleProxy: {{
                        scheme: "http",
                        host: "{ip}",
                        port: parseInt({port})
                    }},
                    bypassList: ["localhost"]
                }}
            }};
            chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
            function callbackFn(details) {{
                return {{
                    authCredentials: {{
                        username: "{user}",
                        password: "{password}"
                    }}
                }};
            }}
            chrome.webRequest.onAuthRequired.addListener(callbackFn, {{urls: ["<all_urls>"]}}, ['blocking']);
            """
            plugin_path = os.path.join(profile_path, "proxy_auth_plugin")
            os.makedirs(plugin_path, exist_ok=True)
            with open(os.path.join(plugin_path, "manifest.json"), "w") as f:
                f.write(manifest_json)
            with open(os.path.join(plugin_path, "background.js"), "w") as f:
                f.write(background_js)
            chrome_options.add_argument(f"--load-extension={plugin_path}")
        else:
            chrome_options.add_argument(f"--proxy-server=http://{proxy}")

    driver_path = os.path.join("driver", "chromedriver.exe")
    driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
    driver.get("https://www.google.com")

# GUI
root = tk.Tk()
root.title("Chrome Proxy Tool")

profile_name_var = tk.StringVar()
proxy_var = tk.StringVar()
selected_profiles = []

def add_profile():
    name = profile_name_var.get().strip()
    proxy = proxy_var.get().strip()
    if name:
        profiles[name] = proxy
        save_profiles()
        refresh_list()
        profile_name_var.set("")
        proxy_var.set("")
    else:
        messagebox.showwarning("Lỗi", "Nhập tên profile!")

def refresh_list():
    listbox.delete(0, tk.END)
    for name, proxy in profiles.items():
        listbox.insert(tk.END, f"{name} | {proxy}")

def delete_profile():
    sel = listbox.curselection()
    if sel:
        name = list(listbox.get(i).split(" | ")[0] for i in sel)
        for n in name:
            profiles.pop(n, None)
        save_profiles()
        refresh_list()

def run_selected():
    sel = listbox.curselection()
    threads = []
    for i in sel:
        name, proxy = listbox.get(i).split(" | ")
        t = threading.Thread(target=open_chrome, args=(name, proxy))
        t.start()
        threads.append(t)

tk.Label(root, text="Tên profile").grid(row=0, column=0)
tk.Entry(root, textvariable=profile_name_var).grid(row=0, column=1)
tk.Label(root, text="Proxy (IP:PORT:USER:PASS hoặc IP:PORT)").grid(row=1, column=0)
tk.Entry(root, textvariable=proxy_var).grid(row=1, column=1)
tk.Button(root, text="Thêm", command=add_profile).grid(row=2, column=0)
tk.Button(root, text="Xóa", command=delete_profile).grid(row=2, column=1)
tk.Button(root, text="Mở profile đã chọn", command=run_selected).grid(row=2, column=2)

listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, width=60)
listbox.grid(row=3, column=0, columnspan=3)

refresh_list()
root.mainloop()
