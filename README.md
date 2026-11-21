# chaoxing_xuexitong_tikuzhizuo
将xuexitong水课题目提取到word文档中，方便复习（就是制作一个题库啦）master里面有文件
建好所需的文件夹 存放之后的word文档
在vscode上打开该文件夹 使用终端创建虚拟环境（打开终端复制粘贴以下代码）
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境 (如果是 Windows)
.venv\Scripts\activate
# (如果是 Mac/Linux，输入 source .venv/bin/activate)
pip install playwright python-docx
playwright install chromium
搞定之后将grab.py文件粘贴进来 修改你需要提取题目的网址（代码中已有注释)网址是当前要刷的课的第一个课程界面
保存之后输入 python grab.py
等待提取完成之后就可以查看你的题库啦
ps：ai辅助完成

