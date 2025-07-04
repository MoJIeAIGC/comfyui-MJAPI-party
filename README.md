# ComfyUI MJAPI Party

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
BASE_URL = your_api_base_url
KEY = your_api_key
```

## 使用说明
### 即梦3.0节点
#### 文本生成图像 (`VolcPicNode`)
- **类别**：`🎨MJapiparty/Dreamina(即梦)`
- **输入参数**：
  - `prompt`：图像描述文本，默认值为 `A beautiful sunset`。
  - `width`：图像宽度，默认值为 `512`。
  - `height`：图像高度，默认值为 `512`。
  - `cfg_scale`：配置比例，默认值为 `2.5`。
  - `seed`：随机种子，默认值为 `-1`。
  - `batch_size`：生成图像数量，范围为 `1-2`，默认值为 `1`。

#### 图像转图像 (`DreaminaI2INode`)
- **类别**：`🎨MJapiparty/Dreamina(即梦)`
- **输入参数**：
  - `image`：输入图像。
  - `prompt`：图像描述文本，默认值为 `A beautiful sunset`。
  - `width`：图像宽度，默认值为 `512`。
  - `height`：图像高度，默认值为 `512`。
  - `cfg_scale`：配置比例，默认值为 `2.5`。
  - `prompt`：图像描述文本，默认值为 `
