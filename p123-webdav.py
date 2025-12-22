import os
import sys
import json
import time

# 添加当前目录到Python路径，确保优先引用本地库
sys.path.insert(0, '.')

from p123client import P123Client

# 配置常量：使用基于脚本目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
TOKEN_PATH = os.path.join(CONFIG_DIR, "config.txt")
MAX_RETRIES = 5


def load_config():
    """加载配置文件"""
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        default_config = {"username": "", "password": ""}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        print("请修改 config 后重启容器")
        exit()
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_token():
    """从文件加载token"""
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, "r", encoding="utf-8") as f:
                token = f.read().strip()
            print("已加载持久化token")
            return token
        except Exception as e:
            print(f"读取token文件失败：{e}，将重新获取")
    return None


def save_token(token):
    """将token保存到文件"""
    try:
        # 确保配置目录存在
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(token)
    except Exception as e:
        print(f"保存token失败：{e}")


def validate_token(token):
    """验证token有效性"""
    try:
        client = P123Client(token=token)
        res = client.user_info()  # 验证token有效性
        if res.get('code') == 0 and res.get('message') == "ok":
            print("123客户端初始化成功（使用持久化token）")
            return client
        print(f"检测到token无效：{res.get('message')}，将重新获取")
        return None
    except Exception as e:
        error_msg = str(e).lower()
        if "token is expired" in error_msg:
            print("检测到token过期，将重新获取")
        else:
            print(f"验证token失败：{e}，将重新获取")
        return None


def get_new_token(username, password):
    """使用用户名密码获取新token"""
    print("123客户端初始化（重新获取token）")
    for i in range(1, MAX_RETRIES + 1):
        try:
            client = P123Client(username, password)
            save_token(client.token)
            print(f"123客户端初始化成功（使用新获取的token）")
            return client
        except Exception as e:
            if i < MAX_RETRIES:
                print(f"获取token失败（第{i}/{MAX_RETRIES}次）：{e}，尝试重试...")
                time.sleep(10)  # 短时间重试，避免频繁请求
            else:
                print(f"获取token失败（已重试{MAX_RETRIES}次）：{e}")
                return None


def init_client():
    """初始化123客户端"""
    # 加载配置
    cfg = load_config()
    username = cfg.get("username")
    password = cfg.get("password")
    
    if not username or not password:
        print("123客户端初始化：缺少用户名和密码")
        exit()
    
    # 加载并验证token
    token = load_token()
    client = validate_token(token) if token else None
    
    # 如果token无效，重新获取
    if not client:
        client = get_new_token(username, password)
        if not client:
            print("无法获取有效token，程序将退出")
            exit()
    
    return client, username, password


def main():
    """主函数"""
    client, username, password = init_client()
    token = client.token
    
    # 导入WebDAV相关模块
    from p123dav import P123FileSystemProvider
    from wsgidav.wsgidav_app import WsgiDAVApp
    from wsgidav.server.server_cli import SUPPORTED_SERVERS
    
    # WebDAV配置
    config = {
        "server": "cheroot",
        "host": "0.0.0.0",
        "port": 18881,
        "mount_path": "",
        "simple_dc": {"user_mapping": {"*": True}},
        "provider_mapping": {"/": P123FileSystemProvider(
            username=username,
            password=password,
            token=token,
            ttl=10,
            refresh=False,
            token_path=TOKEN_PATH
        )},
    }
    
    # 启动WebDAV服务
    app = WsgiDAVApp(config)
    server = config["server"]
    handler = SUPPORTED_SERVERS.get(server)
    if not handler:
        raise RuntimeError(f"不支持的服务器类型 {server!r}（支持的类型：{', '.join(SUPPORTED_SERVERS.keys())!r}")
    
    # 运行WebDAV服务
    handler(app, config, server)


if __name__ == "__main__":
    main()
