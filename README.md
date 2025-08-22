# README

使用方法：

```Mermaid
graph LR
A[下载并解压压缩包] --> B[点击运行exe文件]
B --> C[输入b站视频链接]
C --> D[点击下载]
```

```yacas
注：
	1.b站音视频文件分开输出，因此在抓取音视频文件结束后，要合成为一个完整视频，在合成时会默认使用GPU硬件加速，若没有，则会使用CPU所有线程进行合成。
	2.目前支持https://www.bilibili.com/video/ 和 https://b23.tv/ 链接开头的b站视频
	3.exe文件可能会被杀毒软件杀掉，请将该程序添加到 Microsoft Defender 防病毒扫描中排除的项目
```

