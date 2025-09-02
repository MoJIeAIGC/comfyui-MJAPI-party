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
    return web.json_response({"msg": oneapi_token})

@routes.post('/my_node/update')
async def update(request):
    try:
        repo_dir = os.path.dirname(__file__)
        
        # 捕获标准错误输出
        result = subprocess.check_output(
            ["git", "pull"],
            cwd=repo_dir,
            stderr=subprocess.STDOUT,
            text=True
        )
        return web.json_response({"msg": result})
    except subprocess.CalledProcessError as e:
        return web.json_response({"msg": f"更新失败: {e.output}"}, status=500)
    except Exception as e:
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