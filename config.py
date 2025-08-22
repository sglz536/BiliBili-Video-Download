from pathlib import Path
import json
import os

# 项目根目录
project_path = str(Path(__file__).parent.absolute())

# 创建必要的目录
os.makedirs(f"{project_path}/file", exist_ok=True)

# 获取系统默认下载目录
def get_default_download_path():
    """获取系统默认下载目录"""
    # Windows
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                downloads_path = winreg.QueryValueEx(key, downloads_guid)[0]
                return downloads_path
        except:
            pass

    # macOS
    elif os.name == 'posix' and os.uname().sysname == 'Darwin':
        return os.path.join(os.path.expanduser('~'), 'Downloads')

    # Linux 和其他 Unix 系统
    else:
        # 尝试获取 XDG_DOWNLOAD_DIR
        xdg_download_dir = os.environ.get('XDG_DOWNLOAD_DIR')
        if xdg_download_dir and os.path.isdir(xdg_download_dir):
            return xdg_download_dir

        # 尝试获取用户主目录下的 Downloads 目录
        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        if os.path.isdir(downloads_path):
            return downloads_path

        # 如果都不存在，使用用户主目录
        return os.path.expanduser('~')

# 默认输出路径 - 使用系统默认下载目录
default_output_path = get_default_download_path()

# 配置文件路径
config_file = f"{project_path}/config.json"

def get_save_path():
    """从配置文件获取保存路径，如果没有则返回默认下载路径"""
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('save_path', default_output_path)
    except Exception:
        pass
    return default_output_path

def set_save_path(path):
    """保存路径到配置文件"""
    try:
        config = {'save_path': path}
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False