"""
全自动安装脚本：Python 3.11 + 所有依赖 + 项目运行测试
"""
import os
import sys
import subprocess
import urllib.request
import ssl
import time

PROJECT_DIR = r"C:\Users\22617\Documents\kimi\workspace\overwatch-assistant"
INSTALLER_PATH = r"C:\Users\22617\AppData\Local\Temp\python-3.11.9.exe"
PYTHON_311 = r"C:\Program Files\Python311\python.exe"

def log(msg):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print(f"{'='*50}")

def download():
    log("Step 1/5: 下载 Python 3.11 安装包")
    url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    
    if os.path.exists(INSTALLER_PATH) and os.path.getsize(INSTALLER_PATH) > 20_000_000:
        print("  安装包已存在，跳过下载")
        return True
    
    print("  正在从 python.org 下载...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=300) as r:
            data = r.read()
            with open(INSTALLER_PATH, 'wb') as f:
                f.write(data)
        size_mb = os.path.getsize(INSTALLER_PATH) / (1024*1024)
        print(f"  下载完成: {size_mb:.1f} MB")
        return True
    except Exception as e:
        print(f"  下载失败: {e}")
        return False

def install_python():
    log("Step 2/5: 安装 Python 3.11")
    
    # 检查是否已经安装
    if os.path.exists(PYTHON_311):
        print("  Python 3.11 已安装，跳过")
        return True
    
    if not os.path.exists(INSTALLER_PATH):
        print("  安装包不存在，无法安装")
        return False
    
    print("  正在静默安装 Python 3.11...")
    print("  (包含 tkinter + pip + PATH，无需操作)")
    
    # 静默安装参数
    cmd = [
        INSTALLER_PATH,
        "/quiet",           # 静默模式
        "InstallAllUsers=1", # 为所有用户安装
        "PrependPath=1",     # 添加到 PATH
        "Include_test=0",    # 不安装测试
        "Include_tcltk=1",   # 包含 tkinter（关键！）
        "Include_launcher=1",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  安装失败: {result.stderr}")
        return False
    
    # 等待安装完成
    for i in range(30):
        if os.path.exists(PYTHON_311):
            print("  Python 3.11 安装成功！")
            return True
        time.sleep(1)
    
    print("  等待超时，可能安装失败")
    return False

def install_deps():
    log("Step 3/5: 安装项目依赖")
    
    if not os.path.exists(PYTHON_311):
        print("  Python 3.11 未找到")
        return False
    
    deps = [
        "Pillow", "numpy", "opencv-python-headless",
        "translators", "keyboard", "pytesseract",
    ]
    
    for dep in deps:
        print(f"  安装 {dep}...")
        result = subprocess.run(
            [PYTHON_311, "-m", "pip", "install", "--user", dep],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"    ✓ {dep}")
        else:
            print(f"    ✗ {dep}: {result.stderr[:100]}")
    
    # 安装 easyocr（可能需要更长时间）
    print("  安装 easyocr（韩文识别更好，可选）...")
    result = subprocess.run(
        [PYTHON_311, "-m", "pip", "install", "--user", "easyocr"],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode == 0:
        print("    ✓ easyocr")
    else:
        print("    ✗ easyocr (将使用 tesseract 作为备选)")
    
    return True

def run_test():
    log("Step 4/5: 运行测试")
    
    test_script = os.path.join(PROJECT_DIR, "test_init.py")
    if not os.path.exists(test_script):
        print("  测试脚本不存在")
        return False
    
    result = subprocess.run(
        [PYTHON_311, test_script],
        capture_output=True, text=True, timeout=30
    )
    
    print(result.stdout)
    if result.returncode != 0:
        print(f"  测试错误: {result.stderr}")
    
    return "PASS" in result.stdout

def run_main():
    log("Step 5/5: 启动守望先锋辅助插件")
    
    main_script = os.path.join(PROJECT_DIR, "main.py")
    
    print("  程序将启动，按 Ctrl+C 退出")
    print("  热键: F11=选区域 F10=翻译 F9=显示/隐藏 Ctrl+Shift+Q=退出")
    
    # 使用 Popen 启动程序（不阻塞）
    process = subprocess.Popen(
        [PYTHON_311, main_script],
        cwd=PROJECT_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    print(f"  程序已启动 (PID: {process.pid})")
    return True

def main():
    print("\n" + "="*50)
    print("  守望先锋辅助插件 - 全自动安装")
    print("="*50)
    
    if not download():
        print("\n下载失败，请检查网络连接")
        return 1
    
    if not install_python():
        print("\nPython 安装失败")
        return 1
    
    if not install_deps():
        print("\n依赖安装失败")
        return 1
    
    if not run_test():
        print("\n测试未完全通过，但仍尝试启动...")
    
    run_main()
    return 0

if __name__ == "__main__":
    sys.exit(main())
