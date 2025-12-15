FROM python:3.12-slim
#https://github.com/fengmuxi/p123dav
WORKDIR /app

# 复制requirements.txt文件
COPY requirements.txt .

# 使用国内PyPI镜像源安装所有依赖项
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt

# 复制主程序和配置文件
COPY p123-webdav.py .
COPY config/ ./config/

# 复制整个p123client和p123dav目录到site-packages目录
COPY p123client/ /usr/local/lib/python3.12/site-packages/p123client/
COPY p123dav/ /usr/local/lib/python3.12/site-packages/p123dav/

# 编译所有Python文件为.pyc
RUN python -m compileall -b . /usr/local/lib/python3.12/site-packages/

# 删除当前目录下的原始.py文件
RUN find . -name "*.py" -type f -delete

# 删除site-packages目录下的原始.py文件，只保留.pyc文件
RUN find /usr/local/lib/python3.12/site-packages/ -name "*.py" -type f -delete

EXPOSE 18881

# 使用编译后的.pyc文件运行程序
CMD ["python", "p123-webdav.pyc"]
