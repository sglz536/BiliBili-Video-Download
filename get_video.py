import json
import os
import queue
import random
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

import requests
from moviepy import VideoFileClip, AudioFileClip

from config import project_path, get_save_path, set_save_path


# 爬取代码保持不变
class GetBilibili:
    def __init__(self, data, save_path=None):
        self.url = self.get_url(data)
        self.headers = {'User-Agent': self.generate_user_agent()}
        self.response = self.get_info(self.url)
        self.save_path = save_path  # 保存用户自定义的路径
        self.use_gpu = self._check_gpu_support()  # 初始化时检查 GPU 支持

    @staticmethod
    def get_url(data):
        pattern_url = [r'https://b23.tv/[a-zA-Z0-9]*', r'https://www.bilibili.com/video/[a-zA-Z0-9]*']
        res = ""
        for i in pattern_url:
            x = re.findall(i, data)
            if x:
                res = x[0]
                break
        return res

    def get_info(self, url):
        """获取信息"""
        if not url:
            raise Exception("请输入正确的链接")
        response = requests.get(url, headers=self.headers)
        return response

    def get_audio_video_info(self):
        """获取音视频链接"""
        info = json.loads(
            re.findall(r'<script>\s*window.__playinfo__\s*=(.*?)</script>', self.response.text, re.DOTALL)[0])
        video_url = info["data"]["dash"]["video"][0]["baseUrl"]
        audio_url = info["data"]["dash"]["audio"][0]["baseUrl"]
        return audio_url, video_url

    def get_title_content_info(self):
        """获取视频标题和简介"""
        title_info = re.findall(r'<h1 data-title="(.*?)"', self.response.text, re.DOTALL)[0]
        content_info = re.findall(r'<span class="desc-info-text"\s*\S*?>(.*?)</span>', self.response.text, re.DOTALL)
        if content_info:
            content_info = content_info[0]
        else:
            content_info = ""
        return title_info, content_info

    def save_audio_video(self, video_title):
        """保存音视频文件"""
        audio_url, video_url = self.get_audio_video_info()
        self.headers['Referer'] = self.response.url
        audio_content = self.get_info(audio_url).content
        video_content = self.get_info(video_url).content
        with open(f"{project_path}/file/" + video_title + '.mp4', 'wb') as video:
            video.seek(0)
            video.truncate()
            video.write(video_content)
        with open(f"{project_path}/file/" + video_title + '.mp3', 'wb') as audio:
            audio.seek(0)
            audio.truncate()
            audio.write(audio_content)

    def merge_audio_video(self, video_title):
        """将视频文件和音频文件合成一个新的视频文件"""
        video_clip = VideoFileClip(f"{project_path}/file/" + video_title + '.mp4')
        audio_clip = AudioFileClip(f'{project_path}/file/' + video_title + '.mp3')

        # 将音频设置到视频中
        final_clip = video_clip.with_audio(audio_clip)

        # 使用用户自定义的保存路径，如果没有则使用默认路径
        save_dir = self.save_path if self.save_path else get_save_path()

        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)

        # 输出文件路径
        output_file = f"{save_dir}/{video_title}.mp4"

        # 根据 GPU 支持选择编码方式
        if self.use_gpu:
            # 使用 GPU 加速编码 (NVIDIA NVENC)
            try:
                final_clip.write_videofile(
                    output_file,
                    codec='h264_nvenc',  # NVIDIA GPU 编码器
                    audio_codec='aac',
                    fps=video_clip.fps,
                    threads=0,  # 自动选择线程数
                    ffmpeg_params=[
                        '-preset', 'p4',  # NVIDIA 预设 (p1-p7, p1最快但文件最大)
                        '-rc', 'vbr',  # 可变比特率
                        '-cq', '23',  # 恒定质量模式
                        '-movflags', '+faststart'  # 优化网络播放
                    ],
                    logger=None
                )
            except Exception as e:
                print(f"GPU 编码失败，回退到 CPU 编码: {e}")
                self.use_gpu = False  # 标记 GPU 不可用
                # 回退到 CPU 编码
                self._cpu_encode(final_clip, output_file, video_clip.fps)
        else:
            # 使用 CPU 多线程编码
            self._cpu_encode(final_clip, output_file, video_clip.fps)

        # 关闭剪辑对象释放资源
        video_clip.close()
        audio_clip.close()
        final_clip.close()

        return True

    def _check_gpu_support(self):
        """检查系统是否支持 GPU 加速编码"""
        try:
            # 检查 NVIDIA GPU 支持
            import subprocess
            result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
            return 'nvenc' in result.stdout or 'cuvid' in result.stdout
        except:
            return False

    def _cpu_encode(self, clip, output_file, fps):
        """使用 CPU 进行高效编码"""
        # 获取可用 CPU 核心数，留一个核心给系统
        threads = max(1, (os.cpu_count() or 4) - 1)

        clip.write_videofile(
            output_file,
            codec='libx264',
            audio_codec='aac',
            fps=fps,
            threads=threads,  # 使用多线程
            ffmpeg_params=[
                '-preset', 'fast',
                # 编码速度预设 (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
                '-crf', '23',  # 控制视频质量 (0-51, 23是默认值)
                '-movflags', '+faststart',  # 优化网络播放
                '-pix_fmt', 'yuv420p'  # 确保兼容性
            ],
            logger=None
        )

    @staticmethod
    def generate_user_agent():
        # 浏览器类型和版本
        browsers = [
            {
                'name': 'Chrome',
                'versions': ['90.0.4430.212', '91.0.4472.124', '92.0.4515.107', '93.0.4577.63', '94.0.4606.61'],
                'webkit': 'AppleWebKit/537.36',
                'template': 'Mozilla/5.0 ({platform}) {webkit} (KHTML, like Gecko) Chrome/{version} Safari/537.36'
            },
            {
                'name': 'Firefox',
                'versions': ['88.0', '89.0', '90.0', '91.0', '92.0', '93.0'],
                'gecko': 'Gecko/20100101',
                'template': 'Mozilla/5.0 ({platform}) {gecko} Firefox/{version}'
            },
            {
                'name': 'Safari',
                'versions': ['14.0.3', '14.1.1', '14.1.2', '15.0'],
                'webkit': 'AppleWebKit/605.1.15',
                'template': 'Mozilla/5.0 ({platform}) {webkit} (KHTML, like Gecko) Version/{version} Safari/605.1.15'
            }
        ]

        # 平台选项
        platforms = [
            'Windows NT 10.0; Win64; x64',
            'Windows NT 6.1; Win64; x64',
            'Macintosh; Intel Mac OS X 10_15_7',
            'Macintosh; Intel Mac OS X 10_14_6',
            'X11; Linux x86_64',
            'X11; Ubuntu; Linux x86_64'
        ]

        # 随机选择浏览器和平台
        browser = random.choice(browsers)
        platform = random.choice(platforms)
        version = random.choice(browser['versions'])

        # 构建 User-Agent
        if browser['name'] == 'Chrome':
            return browser['template'].format(
                platform=platform,
                webkit=browser['webkit'],
                version=version
            )
        elif browser['name'] == 'Firefox':
            return browser['template'].format(
                platform=platform,
                gecko=browser['gecko'],
                version=version
            )
        elif browser['name'] == 'Safari':
            return browser['template'].format(
                platform=platform,
                webkit=browser['webkit'],
                version=version
            )


def main(data, save_path=None):
    try:
        b = GetBilibili(data, save_path)
        title, desc = b.get_title_content_info()
        b.save_audio_video(title)
        if b.merge_audio_video(title):
            os.remove(f"{project_path}/file/" + title + '.mp4')
            os.remove(f"{project_path}/file/" + title + '.mp3')
            return {
                "msg": "视频抓取成功，已保存到对应的目录下",
                "title": title,
                "desc": desc
            }
    except Exception as e:
        return {"msg": "视频抓取发生错误", "error": str(e)}


# GUI部分
class BilibiliDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("B站视频下载器")
        self.root.geometry("700x550")  # 增加高度以容纳新的控件
        self.root.resizable(True, True)

        # 设置默认字体 - 使用更适合中文显示的字体
        self.set_fonts()

        # 创建队列用于线程间通信
        self.queue = queue.Queue()

        # 保存路径变量 - 从配置文件读取上次设置的路径
        self.save_path = tk.StringVar()
        self.save_path.set(get_save_path())  # 从配置文件获取保存路径

        self.setup_ui()

        # 定期检查队列
        self.root.after(100, self.process_queue)

    def set_fonts(self):
        """设置统一的字体"""
        # 尝试使用更适合中文显示的字体
        self.default_font = ("Microsoft YaHei", 9)  # 微软雅黑，适合中文显示
        self.title_font = ("Microsoft YaHei", 16, "bold")  # 标题字体
        self.bold_font = ("Microsoft YaHei", 9, "bold")  # 粗体

        # 设置默认字体
        self.root.option_add("*Font", self.default_font)

        # 为特定平台设置备用字体
        if os.name == 'nt':  # Windows
            self.default_font = ("Microsoft YaHei", 9)
        elif os.name == 'posix':  # macOS 或 Linux
            # 尝试使用文泉驿微米黑或苹果系统字体
            self.default_font = ("WenQuanYi Micro Hei", 10)  # Linux
            if os.uname().sysname == 'Darwin':  # macOS
                self.default_font = ("PingFang SC", 12)

    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 标题和设置按钮框架
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        # 标题 - 使用统一的字体设置
        title_label = ttk.Label(header_frame, text="B站视频下载器", font=self.title_font)
        title_label.pack(side=tk.LEFT)

        # 设置按钮 - 放在右上角
        self.settings_btn = ttk.Button(header_frame, text="设置保存位置", command=self.select_path)
        self.settings_btn.pack(side=tk.RIGHT)

        # 当前路径显示
        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(path_frame, text="当前保存位置:", font=self.default_font).pack(side=tk.LEFT)

        self.path_label = ttk.Label(path_frame, textvariable=self.save_path, foreground="blue", font=self.default_font)
        self.path_label.pack(side=tk.LEFT, padx=(5, 0))

        # 输入标签
        input_label = ttk.Label(main_frame, text="请输入B站视频链接:", font=self.default_font)
        input_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 5))

        # 输入框
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60, font=self.default_font)
        self.url_entry.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 下载按钮
        self.download_btn = ttk.Button(main_frame, text="下载视频", command=self.start_download)
        self.download_btn.grid(row=3, column=1, padx=(10, 0), pady=(0, 10))

        # 进度框架
        self.progress_frame = ttk.LabelFrame(main_frame, text="进度", padding="10")
        self.progress_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        # 进度条
        self.progress = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # 状态标签
        self.status_var = tk.StringVar(value="等待下载...")
        self.status_label = ttk.Label(self.progress_frame, textvariable=self.status_var, font=self.default_font)
        self.status_label.grid(row=1, column=0, pady=(5, 0))

        # 结果框架
        self.result_frame = ttk.LabelFrame(main_frame, text="视频信息", padding="10")
        self.result_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(20, 0))

        # 标题标签
        ttk.Label(self.result_frame, text="标题:", font=self.bold_font).grid(row=0, column=0, sticky=tk.NW, pady=(0, 5))

        # 标题文本框（带滚动条）
        title_frame = ttk.Frame(self.result_frame)
        title_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.title_text = scrolledtext.ScrolledText(
            title_frame,
            wrap=tk.WORD,
            width=70,
            height=2,
            font=self.default_font
        )
        self.title_text.pack(fill=tk.BOTH, expand=True)
        self.title_text.config(state=tk.DISABLED)

        # 简介标签
        ttk.Label(self.result_frame, text="简介:", font=self.bold_font).grid(row=2, column=0, sticky=tk.NW, pady=(0, 5))

        # 简介文本框（带滚动条）
        desc_frame = ttk.Frame(self.result_frame)
        desc_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        self.desc_text = scrolledtext.ScrolledText(
            desc_frame,
            wrap=tk.WORD,
            width=70,
            height=8,
            font=self.default_font
        )
        self.desc_text.pack(fill=tk.BOTH, expand=True)
        self.desc_text.config(state=tk.DISABLED)

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        self.progress_frame.columnconfigure(0, weight=1)
        self.result_frame.columnconfigure(0, weight=1)
        self.result_frame.rowconfigure(3, weight=1)

        # 初始隐藏结果框架
        self.result_frame.grid_remove()

    def select_path(self):
        """选择保存路径"""
        path = filedialog.askdirectory(initialdir=self.save_path.get())
        if path:
            self.save_path.set(path)
            # 保存设置到配置文件
            set_save_path(path)
            messagebox.showinfo("成功", f"保存位置已设置为: {path}")

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入有效的B站视频链接")
            return

        # 禁用下载按钮
        self.download_btn.config(state='disabled')

        # 显示进度条并开始动画
        self.progress_frame.grid()
        self.progress.start(10)
        self.status_var.set("正在下载视频，请稍候...")

        # 隐藏结果框架
        self.result_frame.grid_remove()

        # 在后台线程中运行下载任务
        thread = threading.Thread(target=self.download_task, args=(url, self.save_path.get()))
        thread.daemon = True
        thread.start()

    def download_task(self, url, save_path):
        result = main(url, save_path)
        self.queue.put(result)

    def process_queue(self):
        try:
            result = self.queue.get_nowait()
            self.handle_result(result)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def handle_result(self, result):
        # 停止进度条
        self.progress.stop()

        # 启用下载按钮
        self.download_btn.config(state='normal')

        if "error" in result:
            self.status_var.set(f"下载失败: {result['error']}")
            messagebox.showerror("错误", result["msg"])
        else:
            self.status_var.set(result["msg"])

            # 更新标题文本框
            self.title_text.config(state=tk.NORMAL)
            self.title_text.delete(1.0, tk.END)
            self.title_text.insert(tk.END, result["title"])
            self.title_text.config(state=tk.DISABLED)

            # 更新简介文本框
            self.desc_text.config(state=tk.NORMAL)
            self.desc_text.delete(1.0, tk.END)
            self.desc_text.insert(tk.END, result["desc"])
            self.desc_text.config(state=tk.DISABLED)

            # 显示结果框架
            self.result_frame.grid()

            messagebox.showinfo("成功", result["msg"])


def main_gui():
    root = tk.Tk()
    app = BilibiliDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main_gui()
