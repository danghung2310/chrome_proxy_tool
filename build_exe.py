import os
import shutil
import PyInstaller.__main__

# Xóa thư mục build cũ nếu có
if os.path.exists("dist"):
    shutil.rmtree("dist")
if os.path.exists("build"):
    shutil.rmtree("build")
if os.path.exists("app.spec"):
    os.remove("app.spec")

# Build exe
PyInstaller.__main__.run([
    "app.py",
    "--onefile",
    "--noconsole",
    "--add-data=driver/chromedriver.exe;driver",
    "--add-data=profiles.json;.",
    "--add-data=proxies.txt;.",
    "--icon=None"
])

print("✅ Build xong! File exe nằm trong thư mục dist/")
