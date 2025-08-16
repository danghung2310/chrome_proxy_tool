import os, shutil
import PyInstaller.__main__

# dọn build cũ
for p in ["dist", "build", "main.spec"]:
    if os.path.isdir(p):
        shutil.rmtree(p, ignore_errors=True)
    elif os.path.isfile(p):
        os.remove(p)

PyInstaller.__main__.run([
    "main.py",
    "--onefile",
    "--noconsole",
    "--add-data=profiles.json;.",
    "--add-data=proxies.txt;.",
])

print("✅ Build xong! File .exe ở thư mục dist/")
