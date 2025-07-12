<div style="text-align: center;">
    <img src="https://mojie.tos-cn-guangzhou.volces.com/nodes/gitlogo.svg" alt="Logo" style="width: 300px;">
</div>

***
  由魔诘AI开发的Comfyui自定义节点，为了避免在comfyui中调用外部API时难以管理的情况，mjapi-party将许多优秀常用的API节点做整合，只需要一个API-key即可以调用全网的API接口能力。极大的拓展了comfyui的易用性。更多API节点正逐步添加中。

## 安装步骤
1. 确保你已经安装了ComfyUI。
2. 在comfyui-manager中搜索mojieapi_party直接安装本项目
3. 或者在comfyui/custom_nodes目录下
```plaintext
git clone https://github.com/MoJIeAIGC/comfyui-MJAPI-party.git
```
4. 运行requirements安装依赖：
```bash
pip install -r requirements.txt
```
6. 在mojieaigc.com网站上注册一个账户
7. 登录后获取自己的API-KEY
8. 创建`config.ini`文件，放在项目根目录下，内容示例如下：
```ini
[API]
KEY = your_api_key
BASE_URL = https://www.mojieaigc.com/v1/completions
```
请求地址不要动，填入KEY就行了。

## 使用说明

