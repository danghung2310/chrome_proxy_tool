import os

print("Đang build exe...")
os.system("pip install pyinstaller selenium")
os.system('pyinstaller --noconfirm --onefile --windowed --name "Chrome_Proxy_Manager" app.py')
print("Build xong! File exe nằm trong thư mục dist/")
