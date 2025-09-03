import importlib.util
import importlib
from .nodes.node import ConfigManager
from server import PromptServer
from aiohttp import web
config_manager = ConfigManager()
import os
import subprocess


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