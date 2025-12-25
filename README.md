# 题库工具使用

## 方式一：直接运行打包程序
- 下载 dist/main.exe，并与题库目录放在同一层级。
- 双击 main.exe 即可启动练习窗口。
- 首次打开选择 题库/ 下的 Excel 文件即可开始练习。

## 方式二：使用源码运行
1. 准备 Python 3.10+ 环境并安装依赖：`pip install pyqt5 pandas python-docx`
2. 将题库 Excel 文件放在仓库根目录的 题库/ 下。
3. 在仓库根目录执行：`python main.py`
4. 启动后选择题库文件，按照界面提示进行练习。