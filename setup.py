#!/usr/bin/env python3
import os
import sys
import subprocess
import pkg_resources

def install_package(package):
    try:
        pkg_resources.require(package)
        print(f"{package} đã được cài đặt")
    except pkg_resources.DistributionNotFound:
        print(f"Đang cài đặt {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def setup_project():
    print("Bắt đầu cài đặt môi trường cho dự án CCTV Viewer...")
    
    # Tạo và kích hoạt môi trường ảo
    if not os.path.exists("venv"):
        print("Tạo môi trường ảo Python...")
        subprocess.check_call([sys.executable, "-m", "venv", "venv"])
    
    # Xác định interpreter của venv
    if sys.platform == "win32":
        python_path = os.path.join("venv", "Scripts", "python")
        pip_path = os.path.join("venv", "Scripts", "pip")
    else:
        python_path = os.path.join("venv", "bin", "python")
        pip_path = os.path.join("venv", "bin", "pip")
    
    # Nâng cấp pip
    print("Nâng cấp pip...")
    subprocess.check_call([python_path, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Cài đặt các thư viện cần thiết
    required_packages = [
        "PyQt6>=6.0.0",
        "opencv-python>=4.5.0",
        "numpy>=1.20.0"
    ]
    
    print("Cài đặt các thư viện Python cần thiết...")
    for package in required_packages:
        subprocess.check_call([python_path, "-m", "pip", "install", package])
    
    # Cài đặt các thư viện system cho X11/XCB
    if sys.platform.startswith('linux'):
        print("Cài đặt các thư viện hệ thống cho Linux...")
        try:
            subprocess.check_call([
                "sudo", "apt-get", "install", "-y",
                "libxcb-cursor0",
                "libxcb-xinerama0",
                "libxcb-randr0",
                "libxcb-xfixes0",
                "libxcb-shape0",
                "libxcb-sync1",
                "libxcb-shm0",
                "libxcb-icccm4",
                "libxcb-keysyms1",
                "libxcb-image0"
            ])
        except subprocess.CalledProcessError:
            print("Cảnh báo: Không thể cài đặt một số thư viện hệ thống. Có thể cần quyền sudo.")
    
    print("\nHoàn tất cài đặt!")
    print("\nĐể chạy chương trình:")
    print("1. Kích hoạt môi trường ảo:")
    if sys.platform == "win32":
        print("   .\\venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("2. Chạy chương trình:")
    print("   QT_QPA_PLATFORM=xcb python main.py")

if __name__ == "__main__":
    setup_project()
