import importlib.util
import importlib
from .nodes.node import ConfigManager
from server import PromptServer
from aiohttp import web
config_manager = ConfigManager()
import os
import subprocess
import logging
import requests

routes = PromptServer.instance.routes
@routes.post('/my_node/set_key')
async def set_key(request):
    try:
        data = await request.json()
        key = data.get("api_key", "")
        config_manager.set_api_key(key)
        print(f"收到保存请求，KEY长度: {len(key)}")
    except Exception as e:
        print(f"保存KEY失败: {str(e)}")
        return web.json_response({"msg": f"保存失败: {e}"}, status=500)
    return web.json_response({"msg": "ok"})

@routes.get('/my_node/get_key')
async def get_key(request):
    oneapi_url, oneapi_token = config_manager.get_api_config()
    # 读取pyproject.toml中的version
    import toml
    pyproject_path = os.path.join(os.path.dirname(__file__), "pyproject.toml")
    with open(pyproject_path, "r", encoding="utf-8") as f:
        pyproject_data = toml.load(f)
    version = pyproject_data["project"]["version"]
    
    return web.json_response({
        "msg": oneapi_token,
        "version": version
    })



@routes.get('/my_node/get_user')
async def get_user(request):
    oneapi_url, oneapi_token = config_manager.get_api_config()
    oneapi_token = oneapi_token[3:]
    response = requests.get(f"https://mojieaigc.com/api/userinfoo?oneapi_token={oneapi_token}")
    data = response.json()
    print(f"用户信息响应: {data}")
    username = data.get("username", "未知用户")
    quota = data.get("quota", 0)
    quota = round(quota/100, 2)
    print(f"获取用户信息: {username}, 配额: {quota}")
    
    return web.json_response({
        "msg": oneapi_token,
        "username": username,
        "quota": quota
    })


@routes.post('/my_node/send_message')
async def send_message(request):
    try:
        data = await request.json()
        email = data.get("email", "")
        # 构建请求URL
        url = f"https://mojieaigc.com/api/verification?email={email}&turnstile="
        
        try:
            # 发送GET请求
            resp = requests.get(url)
            
            # 解析JSON响应
            data = resp.json()
            
            # 打印响应数据
            print(f"验证码发送接口返回数据: {data}")
            if data.get("success"):
                return web.json_response({"msg": "验证码发送成功","success": True})
            else:
                return web.json_response({"msg": "验证码发送失败","success": False}, status=400)
        except Exception as e:
            print(f"验证码发送接口请求失败: {str(e)}")
            return web.json_response({"msg": f"验证码发送失败: {e}","success": False}, status=500)

    except Exception as e:
        print(f"保存KEY失败: {str(e)}")
        return web.json_response({"msg": f"保存失败: {e}"}, status=500)


@routes.post('/my_node/register')
async def register(request):
    try:
        oneapi_url, oneapi_token = config_manager.get_api_config()

        data = await request.json()
        account = data.get("email", "")
        verifyCode = data.get("verification_code", "")
        password = data.get("password", "")
        confirmPwd = data.get("confirmPassword", "")

        if not account or not verifyCode or not password or not confirmPwd:
            return web.json_response({"msg": "所有字段不能为空","success": False}, status=400)

        if password != confirmPwd:
            return web.json_response({"msg": "两次密码输入不一致","success": False}, status=400)
        
        try:
            # 调用注册接口
            resp = requests.post("https://mojieaigc.com/api/user/register?turnstile=", json={
                "username": account,
                "email": account,
                "password": password,
                "confirmPassword": confirmPwd,
                "verification_code": verifyCode
            })
            data = resp.json()
            print(f"注册接口返回数据: {data}")
            if data.get("success"):
                # if oneapi_token:
                return web.json_response({"msg": "注册成功","success": True})
                # try:
                #     translate_response = requests.get(f"https://qihuaimage.com/api/mjapi/getcomfyuitoken", params={"userid": 2})
                #     translate_data = translate_response.json()
                #     if translate_data.get("code") != 200:
                #         return web.json_response({"msg": "获取comfyui_token失败"}, status=400)
                #     key = "sk-"+translate_data.get("data").get("key")
                #     config_manager.set_api_key(key)
                #     return web.json_response({"msg": "注册成功","success": True})
                # except Exception as e:
                #     return web.json_response({"msg": f"获取comfyui_token失败: {e}","success": False}, status=500)
            else:
                return web.json_response({"msg": "注册失败","success": False}, status=400)
        except Exception as e:
            return web.json_response({"msg": f"注册失败: {e}","success": False}, status=500)

    except Exception as e:
        print(f"注册失败: {str(e)}")
        return web.json_response({"msg": f"注册失败: {e}","success": False}, status=500)




@routes.post('/my_node/login')
async def login(request):
    try:
        oneapi_url, oneapi_token = config_manager.get_api_config()

        data = await request.json()
        username = data.get("username", "")
        password = data.get("password", "")
        
        # 非空检查
        if not username or not password:
            return web.json_response({"msg": "用户名和密码不能为空"}, status=400)
        
        # 发送登录请求
        login_data = {
            "username": username,
            "password": password
        }
        
        response = requests.post("https://mojieaigc.com/api/user/login", json=login_data)
        response_data = response.json()
        if not response_data.get("success"):
            return web.json_response({"msg": "登录失败"}, status=400)

        if oneapi_token:
            return web.json_response({
                "msg": "login success",
            })
        id = response_data.get("data").get("id")
        
        # 发送GET请求到imagetranslate API
        try:
            translate_response = requests.get(f"https://qihuaimage.com/api/mjapi/getcomfyuitoken", params={"userid": id})
            translate_data = translate_response.json()
            if translate_data.get("code") != 200:
                return web.json_response({"msg": "获取comfyui_token失败"}, status=400)
            key = "sk-"+translate_data.get("data").get("key")
            config_manager.set_api_key(key)
            # print(f"收到保存请求，KEY长度: {len(key)}")
            # print(f"返回数据: {translate_data}")
        except Exception as e:
            return web.json_response({"msg": f"获取comfyui_token失败: {e}"}, status=500)

        return web.json_response({
            "msg": "登录请求已发送",
            "data": response_data
        })
    except Exception as e:
        print(f"登录失败: {str(e)}")
        return web.json_response({"msg": f"登录失败: {e}"}, status=500)

@routes.post('/my_node/update')
async def update(request):
    try:
        repo_dir = os.path.dirname(__file__)
        logging.info(f"[update] 仓库目录: {repo_dir}")
        logging.info("[update] 开始执行更新逻辑")

        def run_ok(cmd):
            try:
                result = subprocess.run(
                    cmd, cwd=repo_dir, text=True, capture_output=True, check=True
                )
                # 成功：仅用于调试的简洁日志；不要用输出内容当成功条件
                logging.info(f"[update] ✔ {' '.join(cmd)}\nstdout: {result.stdout.strip()}\nstderr: {result.stderr.strip()}")
                return True
            except subprocess.CalledProcessError as e:
                logging.error(f"[update] ✖ {' '.join(cmd)}\nstdout: {e.stdout.strip() if e.stdout else ''}\nstderr: {e.stderr.strip() if e.stderr else ''}")
                return False

        def ensure_remote(name, url):
            try:
                remotes = subprocess.check_output(["git", "remote"], cwd=repo_dir, text=True).splitlines()
                if name not in remotes:
                    run_ok(["git", "remote", "add", name, url])
                    logging.info(f"[update] 新增远程: {name} → {url}")
                else:
                    current_url = subprocess.check_output(["git", "remote", "get-url", name], cwd=repo_dir, text=True).strip()
                    if current_url != url:
                        run_ok(["git", "remote", "set-url", name, url])
                        logging.info(f"[update] 更新远程 {name} → {url}")
            except Exception as e:
                logging.error(f"[update] ensure_remote 出错: {e}")

        def get_remote_head_branch(remote):
            # 解析 "git remote show <remote>" 里的 "HEAD branch: xxx"
            try:
                info = subprocess.check_output(["git", "remote", "show", remote], cwd=repo_dir, text=True, errors="ignore")
                for line in info.splitlines():
                    if "HEAD branch" in line:
                        return line.split(":")[-1].strip()
            except Exception as e:
                logging.error(f"[update] 获取 {remote} 默认分支失败: {e}")
            return None

        GITHUB_NAME, GITHUB_URL = "github", "https://github.com/MoJIeAIGC/comfyui-MJAPI-party.git"
        GITEE_NAME,  GITEE_URL  = "gitee",  "https://gitee.com/moja_1/comfyui-MJAPI-party.git"

        ensure_remote(GITHUB_NAME, GITHUB_URL)
        ensure_remote(GITEE_NAME,  GITEE_URL)

        def hard_reset(remote):
            # 自动识别远程默认分支，失败则尝试 main/master
            branch = get_remote_head_branch(remote) or "main"
            logging.info(f"[update] {remote} 默认分支: {branch}")

            # fetch 默认分支；若失败且不是 master，则再尝试 master
            if not run_ok(["git", "fetch", remote, branch]):
                if branch != "master" and run_ok(["git", "fetch", remote, "master"]):
                    branch = "master"
                else:
                    return False

            # 用 checkout -B 强制把本地 <branch> 指向 remote/<branch>
            # -B：存在则重置，不存在则创建；-f 强制切换避免工作区阻塞
            if not run_ok(["git", "checkout", "-f", "-B", branch, f"{remote}/{branch}"]):
                return False

            # 强制把工作区/索引对齐远程
            if not run_ok(["git", "reset", "--hard", f"{remote}/{branch}"]):
                return False

            # （可选）清理未跟踪文件：如需更“干净”，解除注释下一行
            # run_ok(["git", "clean", "-fd"])

            logging.info(f"[update] 已成功同步到 {remote}/{branch}")
            return True

        # 国内网络优先用 Gitee，同步失败再回退 GitHub
        success = hard_reset(GITHUB_NAME) or hard_reset(GITEE_NAME)
        if not success:
            logging.error("[update] GitHub 和 Gitee 同步都失败")
            return web.json_response({"msg": "更新失败"}, status=500)

        logging.info("[update] 更新完成")
        return web.json_response({"msg": "ok"})
    except Exception as e:
        logging.exception("[update] 发生异常")
        return web.json_response({"msg": f"更新失败: {e}"}, status=500)

node_list = [
    "node",
]
WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

for module_name in node_list:
    imported_module = importlib.import_module(f".nodes.{module_name}", __name__)
    NODE_CLASS_MAPPINGS = {**NODE_CLASS_MAPPINGS, **imported_module.NODE_CLASS_MAPPINGS}
    NODE_DISPLAY_NAME_MAPPINGS = {**NODE_DISPLAY_NAME_MAPPINGS, **imported_module.NODE_DISPLAY_NAME_MAPPINGS}


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]