import os, sys, json, math, threading, shutil, tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, END, MULTIPLE
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# ===== Optional: helper proxy có auth nếu cài được =====
try:
    from selenium_authenticated_proxy import SeleniumAuthenticatedProxy
    HAS_PROXY_HELPER = True
except Exception:
    HAS_PROXY_HELPER = False

# ===== Tự tải ChromeDriver đúng version Chrome =====
from webdriver_manager.chrome import ChromeDriverManager

CONFIG_FILE = "profiles.json"

# ---------- Utils ----------
def load_profiles():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_profiles(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def detect_chrome_binary():
    """
    Cố gắng tìm chrome.exe/google-chrome tự động trên mọi OS.
    Không bắt buộc: nếu không tìm thấy, Selenium vẫn dùng mặc định của hệ thống.
    """
    # 1) which/path
    candidates = [
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chrome.exe"),
        shutil.which("google-chrome-stable"),
    ]
    # 2) Windows registry
    if os.name == "nt":
        try:
            import winreg
            for key_path in [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
            ]:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
                        p, _ = winreg.QueryValueEx(k, "")
                        candidates.append(p)
                except OSError:
                    pass
        except Exception:
            pass
        # phổ biến
        candidates += [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    else:
        # macOS + Linux phổ biến
        candidates += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/usr/bin/google-chrome",
            "/usr/local/bin/google-chrome",
        ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def get_screen_size():
    # Thử lấy từ Tkinter (ổn định)
    try:
        _root = tk.Tk()
        _root.withdraw()
        w = _root.winfo_screenwidth()
        h = _root.winfo_screenheight()
        _root.destroy()
        if w and h:
            return w, h
    except Exception:
        pass
    # Fallback Windows
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            pass
    # Mặc định
    return 1920, 1080

def parse_proxy(proxy_str):
    """
    Hỗ trợ:
      - ip:port
      - user:pass@ip:port
      - ip:port:user:pass
    Trả về dict: {"host":..., "port":..., "user":..., "pass":...} (có thể None).
    """
    if not proxy_str:
        return {}
    s = proxy_str.strip()
    if "@" in s:
        # user:pass@ip:port
        cred, host = s.split("@", 1)
        user, pwd = cred.split(":", 1)
        ip, port = host.split(":", 1)
        return {"host": ip, "port": port, "user": user, "pass": pwd}
    parts = s.split(":")
    if len(parts) == 2:
        ip, port = parts
        return {"host": ip, "port": port}
    if len(parts) == 4:
        ip, port, user, pwd = parts
        return {"host": ip, "port": port, "user": user, "pass": pwd}
    # không đúng định dạng -> trả về chuỗi thô
    return {"raw": s}

def make_auth_extension(profile_dir, host, port, user, pwd):
    """
    Tạo extension tạm để điền proxy + auth cho trường hợp không có selenium_authenticated_proxy.
    """
    ext_dir = os.path.join(profile_dir, "_proxy_ext")
    os.makedirs(ext_dir, exist_ok=True)
    manifest = r"""
    {
      "version": "1.0.0",
      "manifest_version": 2,
      "name": "AuthProxy",
      "permissions": ["proxy","tabs","unlimitedStorage","storage","<all_urls>","webRequest","webRequestBlocking"],
      "background": {"scripts": ["background.js"]},
      "minimum_chrome_version":"22.0.0"
    }
    """
    background = f"""
    var config = {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: "http",
                host: "{host}",
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
                password: "{pwd}"
            }}
        }};
    }}
    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {{urls: ["<all_urls>"]}},
        ['blocking']
    );
    """
    with open(os.path.join(ext_dir, "manifest.json"), "w", encoding="utf-8") as f:
        f.write(manifest.strip())
    with open(os.path.join(ext_dir, "background.js"), "w", encoding="utf-8") as f:
        f.write(background.strip())
    return ext_dir

def open_chrome(profile_name, proxy_str, position=None, size=None):
    chrome_binary = detect_chrome_binary()

    # Chuẩn bị profile dir để lưu dữ liệu đăng nhập
    profile_dir = os.path.abspath(os.path.join("profiles", profile_name))
    os.makedirs(profile_dir, exist_ok=True)

    # Cấu hình Chrome
    opts = Options()
    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_argument("--disable-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)

    if chrome_binary and os.path.exists(chrome_binary):
        opts.binary_location = chrome_binary

    # Proxy
    pinfo = parse_proxy(proxy_str)
    if pinfo:
        if "host" in pinfo and "port" in pinfo:
            if pinfo.get("user") and pinfo.get("pass"):
                # Có user/pass
                if HAS_PROXY_HELPER:
                    helper = SeleniumAuthenticatedProxy(
                        proxy_url=f"http://{pinfo['user']}:{pinfo['pass']}@{pinfo['host']}:{pinfo['port']}"
                    )
                    helper.enrich_chrome_options(opts)
                else:
                    # Dùng extension tự tạo
                    ext_path = make_auth_extension(profile_dir, pinfo["host"], pinfo["port"], pinfo["user"], pinfo["pass"])
                    opts.add_argument(f"--load-extension={ext_path}")
            else:
                # Không auth
                opts.add_argument(f"--proxy-server=http://{pinfo['host']}:{pinfo['port']}")
        elif "raw" in pinfo:
            # Chuỗi thô fallback
            opts.add_argument(f"--proxy-server=http://{pinfo['raw']}")

    # Vị trí/kích thước
    if position:
        opts.add_argument(f"--window-position={position[0]},{position[1]}")
    if size:
        opts.add_argument(f"--window-size={size[0]},{size[1]}")

    # Khởi tạo driver (tự tải bản phù hợp)
    driver_path = ChromeDriverManager().install()
    driver = webdriver.Chrome(service=Service(driver_path), options=opts)
    driver.get("https://whatismyipaddress.com/")
    # bạn có thể chỉnh URL đích theo nhu cầu

# ---------- GUI ----------
profiles = load_profiles()

root = tk.Tk()
root.title("Chrome Proxy Tool — Multi Profile (Auto Chrome/Driver)")

# Controls
tk.Label(root, text="Tên profile").grid(row=0, column=0, sticky="w")
e_name = tk.Entry(root, width=28)
e_name.grid(row=0, column=1, sticky="we", padx=4)

tk.Label(root, text="Proxy (ip:port | user:pass@ip:port | ip:port:user:pass)").grid(row=1, column=0, sticky="w")
e_proxy = tk.Entry(root, width=28)
e_proxy.grid(row=1, column=1, sticky="we", padx=4)

def add_profile():
    name = e_name.get().strip()
    proxy = e_proxy.get().strip()
    if not name:
        messagebox.showerror("Lỗi", "Tên profile không được để trống")
        return
    profiles[name] = proxy
    save_profiles(profiles)
    refresh_list()
    e_name.delete(0, END)
    e_proxy.delete(0, END)

def edit_profile():
    sel = lb.curselection()
    if len(sel) != 1:
        messagebox.showerror("Lỗi", "Hãy chọn đúng 1 profile để sửa")
        return
    item = lb.get(sel[0])
    name = item.split(" | ")[0]
    new_proxy = e_proxy.get().strip()
    profiles[name] = new_proxy
    save_profiles(profiles)
    refresh_list()

def delete_selected():
    sel = list(lb.curselection())
    if not sel:
        return
    for i in reversed(sel):
        item = lb.get(i)
        name = item.split(" | ")[0]
        profiles.pop(name, None)
    save_profiles(profiles)
    refresh_list()

def import_from_txt():
    path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if not path:
        return
    added = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            name = f"profile_{len(profiles)+1}"
            profiles[name] = line
            added += 1
    save_profiles(profiles)
    refresh_list()
    messagebox.showinfo("OK", f"Đã thêm {added} proxy từ file.")

def refresh_list():
    lb.delete(0, END)
    for name, proxy in profiles.items():
        lb.insert(END, f"{name} | {proxy}")

def run_selected():
    sel = list(lb.curselection())
    if not sel:
        return
    n = len(sel)
    sw, sh = get_screen_size()
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    win_w = max(600, sw // cols)
    win_h = max(500, sh // rows)

    for idx, i in enumerate(sel):
        item = lb.get(i)
        name, proxy = item.split(" | ", 1) if " | " in item else (item, "")
        col = idx % cols
        row = idx // cols
        x = col * win_w
        y = row * win_h
        threading.Thread(
            target=open_chrome,
            args=(name, proxy, (x, y), (win_w, win_h)),
            daemon=True
        ).start()

btn_frame = tk.Frame(root)
btn_frame.grid(row=0, column=2, rowspan=2, padx=6, pady=2, sticky="ns")
tk.Button(btn_frame, text="Thêm", width=12, command=add_profile).pack(pady=2)
tk.Button(btn_frame, text="Sửa proxy", width=12, command=edit_profile).pack(pady=2)
tk.Button(btn_frame, text="Xoá", width=12, command=delete_selected).pack(pady=2)
tk.Button(btn_frame, text="Nhập từ .txt", width=12, command=import_from_txt).pack(pady=2)
tk.Button(btn_frame, text="Mở (song song)", width=12, command=run_selected).pack(pady=10)

lb = tk.Listbox(root, selectmode=MULTIPLE, width=60, height=16)
lb.grid(row=2, column=0, columnspan=3, padx=4, pady=6, sticky="we")

refresh_list()
root.mainloop()
