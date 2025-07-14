<div align="center">
    <img src="https://mojie.tos-cn-guangzhou.volces.com/nodes/gitlogo.svg" alt="Logo" style="width: 300px;">
</div>

<div align="center">
    <a href="https://space.bilibili.com/483532108" target="_blank">
        <img src="https://img.shields.io/badge/Bilibili-B站-blue?logo=bilibili" alt="Bilibili">
    </a>
    <a href="#" target="_blank">
        <img src="https://img.shields.io/badge/YouTube-油管-red?logo=youtube" alt="YouTube">
    </a>
    <a href="/README_EN.md" target="_blank">
        <img src="https://img.shields.io/badge/Docs-文档-green?logo=readme" alt="Documentation">
    </a>
</div>
  

***
  MojieAI开发的Comfyui自定义节点工具。为了避免在comfyui中调用外部API时密钥和地址难以统一管理，以及许多更优秀模型本地算力难以支撑，本地部署耗时耗力，因此mjapi-party将许多优秀常用的API节点做整合，只需要一个API-key即可以调用全网的API接口能力，也能够通过comfyui节点式操作，保留极大的灵活性，极大的拓展了comfyui的易用性。更多API节点正逐步添加中,后续也会逐步增加对扣子和n8n的支持。


### 目前已支持的节点
- [seededit3.0](/doc/node_list.md#seededit30)
- [Dreamina(即梦)](/doc/node_list.md#Dreamina(即梦)) 
- [Redux万物迁移](/doc/node_list.md#redux万物迁移)

### 节点使用说明
所有的节点说明文档在：
> doc目录下[node_list.md](doc/node_list.md)

所有的节点示例工作流在：
> workflow目录下

在comfyui节点列表中找到mjapiparty
![alt text](doc/assets/node.png)

- 250714-新增节点：
seededit3.0
SeedEdit 3.0 是字节跳动开发的图片编辑工具，能通过文字描述修改图片。比如你说 “把背景换成海边”。支持使用中文提示词，支持输出中文，对比kontext一致性保持更好，支持中文提示词输入和中文文本输出。效果相当不错。
![alt text](doc/assets/seed.png)
![alt text](doc/assets/seed2.png)

### 安装步骤
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
填入密钥key后记得重启comfyui

### 联系我们
wechat:mojie_AIGC
扫描下方二维码
<img src="doc/assets/qr.jpg" alt="QR Code" style="width: 300px;">
### star
<div align="center">
    <a href="https://star-history.com/#MoJIeAIGC/comfyui-MJAPI-party&Date">
        <img src="https://api.star-history.com/svg?repos=MoJIeAIGC/comfyui-MJAPI-party&type=Date" alt="Star History Chart">
    </a>
</div>
