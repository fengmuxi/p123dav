import os
import json

from p123client import P123Client
import time

CONFIG_PATH = "./config/config.json"

token_path = "./config/config.txt"
token = None

# 尝试加载持久化的token
if os.path.exists(token_path):
    try:
        with open(token_path, "r", encoding="utf-8") as f:
            token = f.read().strip()
        print("已加载持久化token")
    except Exception as e:
        print(f"读取token文件失败：{e}，将重新获取")

# 尝试使用token初始化客户端
if token:
    try:
        client = P123Client(token=token)
        res = client.user_info()  # 验证token有效性

        # 检查API返回结果是否表示token过期
        if res.get('code') != 0 or res.get('message') != "ok":
            print("检测到token过期，将重新获取")
            if os.path.exists(token_path):
                os.remove(token_path)
            token = None
        else:
            print("123客户端初始化成功（使用持久化token）")
    except Exception as e:
        if "token is expired" in str(e).lower() or (
                hasattr(e, 'args') and "token is expired" in str(e.args).lower()):
            print("检测到token过期，将重新获取")
            if os.path.exists(token_path):
                os.remove(token_path)
        token = None

if not os.path.exists(CONFIG_PATH):
    os.makedirs("./config", exist_ok=True)
    default_config = {"username": "", "password": ""}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=4)
    print("请修改 config 后重启容器")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

username = cfg.get("username")
password = cfg.get("password")

if token is None:
    if not username or not password:
        print("123客户端初始化username and password为空")
        exit()
    print("123客户端初始化（重新获取token）")
    i = 1
    while True:
        # 通过API接口获取新token
        try:

            # 使用新token初始化客户端
            client = P123Client(username, password)
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(client.token)
            token = client.token

            print("123客户端初始化成功（使用新获取的token）")
            break
        except Exception as e:
            if i < 5:
                print(f"获取token失败：{e}，尝试重试...")
            else:
                time.sleep(60)
                print(f"获取token失败（已重试）：{e}")
                break
        finally:
            i += 1

from p123dav import P123FileSystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.server.server_cli import SUPPORTED_SERVERS

config = {
    "server": "cheroot",
    "host": "0.0.0.0",
    "port": 18881,
    "mount_path": "",
    "simple_dc": {"user_mapping": {"*": True}},
    "provider_mapping": {"/": P123FileSystemProvider(token=token, ttl=10, refresh=False)},
}

app = WsgiDAVApp(config)
server = config["server"]
handler = SUPPORTED_SERVERS.get(server)
if not handler:
    raise RuntimeError(f"Unsupported server type {server!r} (expected {', '.join(SUPPORTED_SERVERS.keys())!r})")

# 运行 WebDAV 服务
handler(app, config, server)
