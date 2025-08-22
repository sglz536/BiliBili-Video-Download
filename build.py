import PyInstaller.__main__
import os

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    'get_video.py',  # 主程序文件
    '--name=B站视频下载器',  # 生成的exe名称
    '--onedir',  # 打包成为免安装
    '--windowed',  # 不显示控制台窗口
    '--add-data=config.py;.',  # 包含配置文件
    '--icon=favicon.ico',  # 可选：添加图标
    '--clean',  # 清理临时文件
])