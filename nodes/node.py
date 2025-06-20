# comfyui节点定义
import requests
from PIL import Image
from io import BytesIO
import base64
from torchvision import transforms
import numpy as np  # 加这个！
import torch  # 确保导入torch
import configparser  # 导入configparser模块
# 文生图节点
class VolcPicNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset"}),
                "width": ("INT", {"default": 512}),
                "height": ("INT", {"default": 512}),
                # "steps": ("INT", {"default": 30}),
                "cfg_scale": ("FLOAT", {"default": 7.5}),
                "seed": ("INT", {"default": 1234}),
                # "oneapi_url": ("STRING", {"default": "http://118.145.81.83:1024/v1/completions"}),
                # "oneapi_token": ("STRING", {"default": "sk-xxx"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output",)
    FUNCTION = "generate"
    CATEGORY = "VolcPic"

    def pil2tensor(self, image):
        img_array = np.array(image).astype(np.float32) / 255.0  # (H, W, 3)
        img_tensor = torch.from_numpy(img_array)[None,]  # (1, H, W, 3)
        print("✅ Tensor shape in pil2tensor:", img_tensor.shape)  # (1, 512, 512, 3)
        return img_tensor
    

    def generate(self, prompt, width, height,  cfg_scale, seed):
        # 读取配置文件
        # 读取配置文件
        import os  # 导入 os 模块用于路径操作
        config = configparser.ConfigParser()
        # 获取 node.py 文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建项目根目录下 config.ini 的绝对路径
        config_path = os.path.join(os.path.dirname(current_dir), 'config.ini')
        config.read(config_path)
        
        # 从配置文件中获取 oneapi_url 和 oneapi_token
        oneapi_url = config.get('API', 'BASE_URL')
        oneapi_token = config.get('API', 'KEY')

        payload = {
            "model": "volc-pic-3.0",
            "req_key": "high_aes_general_v30l_zt2i",
            "prompt": prompt,
            "width": width,
            "height": height,
            # "steps": steps,
            "cfg_scale": cfg_scale,
            "seed": int(seed)
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {oneapi_token}"
        }

        try:
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            # print("🔥 VolcPicNode API 响应:", result)

            img_base64_list = result.get('data', {}).get('binary_data_base64', [])
            if not img_base64_list:
                raise ValueError("Empty image data from API.")
            

            img_data = img_base64_list[0]
            img_bytes = base64.b64decode(img_data)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            print(img)
            print(f"🔥 VolcPicNode 成功生成图片: {prompt} ({width}x{height})")
            tensor_img = self.pil2tensor(img)
            print("Tensor shape:", tensor_img.shape)  # 必须为 (3, H, W)
            return (tensor_img,)  # 正确tuple

        except Exception as e:
            print(f"🔥 VolcPicNode 错误: {str(e)}")
            error_img = Image.new("RGB", (width, height), (255, 0, 0))  # 红色错误图
            return (self.pil2tensor(error_img),)


NODE_CLASS_MAPPINGS = {
    "VolcPicNode": VolcPicNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VolcPicNode": "🔥 火山文生图（OneAPI）"
}
