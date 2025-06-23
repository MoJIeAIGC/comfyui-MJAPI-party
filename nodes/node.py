import requests
from PIL import Image
from io import BytesIO
import base64
from torchvision import transforms
import numpy as np
import torch
import configparser
import os  # 导入 os 用于路径处理

# 从 base.py 导入 pil2tensor 函数
from .base import pil2tensor

class VolcPicNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset"}),
                "width": ("INT", {"default": 512}),
                "height": ("INT", {"default": 512}),
                "cfg_scale": ("FLOAT", {"default": 2.5}),
                "seed": ("INT", {"default": 1234}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🔥 MJapiparty/ImageGenerate"

    def generate(self, prompt, width, height, cfg_scale, seed, batch_size):
        # 读取配置文件
        config = configparser.ConfigParser()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(current_dir), 'config.ini')
        config.read(config_path)
        
        oneapi_url = config.get('API', 'BASE_URL')
        oneapi_token = config.get('API', 'KEY')

        use_pre_llm = False
        if len(prompt) > 500:
            use_pre_llm = True

        def call_api(seed_override):
            payload = {
                "model": "volc-pic-3.0",
                "req_key": "high_aes_general_v30l_zt2i",
                "prompt": prompt,
                "width": width,
                "use_pre_llm": use_pre_llm,
                "height": height,
                "cfg_scale": cfg_scale,
                "seed": int(seed_override)
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            img_base64_list = result.get('data', {}).get('binary_data_base64', [])
            if not img_base64_list:
                raise ValueError("Empty image data from API.")
            img_data = img_base64_list[0]
            img_bytes = base64.b64decode(img_data)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            return img

        output_tensors = []

        try:
            for i in range(batch_size):
                # 如果两次请求用同一个seed也行，可改为 seed+i 实现不同seed
                img = call_api(seed + i)
                # 直接调用导入的 pil2tensor 函数
                tensor_img = pil2tensor(img)
                output_tensors.append(tensor_img)
                print(f"🔥 VolcPicNode 第 {i+1} 张图片生成成功: {prompt} ({width}x{height})")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f"🔥 VolcPicNode 错误: {str(e)}")
            error_img = Image.new("RGB", (width, height), (255, 0, 0))
            # 直接调用导入的 pil2tensor 函数
            error_tensor = pil2tensor(error_img)
            # 返回指定数量错误图
            error_tensors = [error_tensor for _ in range(batch_size)]
            return (torch.cat(error_tensors, dim=0),)

class DreaminaI2INode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),  # 输入图像
                # "image": ("STRING", {"default": "https://pic.52112.com/180320/180320_17/Bl3t6ivHKZ_small.jpg"}),
                "prompt": ("STRING", {"default": ""}),
                "width": ("INT", {"default": 1024}),
                "height": ("INT", {"default": 1024}),
                "gpen": ("FLOAT", {"default": 0.4}),
                "skin": ("FLOAT", {"default": 0.3}),
                "skin_unifi": ("FLOAT", {"default": 0.0}),
                "gen_mode": (["creative", "reference", "reference_char"], {"default": "reference"}),
                "seed": ("INT", {"default": -1}),  # -1表示随机
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 2}),  # 生成张数
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output",)
    FUNCTION = "generate"
    CATEGORY = "Dreamina"

    def tensor2pil(self, tensor):
        # Tensor (1, H, W, 3) to PIL
        image = tensor.squeeze().numpy() * 255.0
        return Image.fromarray(image.astype(np.uint8))

    def generate(self, image, prompt, width, height, gpen, skin, skin_unifi, gen_mode, seed, batch_size):
        # 读取配置文件
        config = configparser.ConfigParser()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(current_dir), 'config.ini')
        config.read(config_path)
        
        oneapi_url = config.get('API', 'BASE_URL')
        oneapi_token = config.get('API', 'KEY')

        # Convert input tensor to base64
        pil_image = self.tensor2pil(image)
        buffered = BytesIO()
        pil_image.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {oneapi_token}"
        }

        output_tensors = []

        for i in range(batch_size):  # batch_size=2 时调用两次
            payload = {
                "model": "volc-pic-3.0",
                "req_key": "i2i_portrait_photo",
                "prompt": prompt,
                "width": width,
                "height": height,
                "gpen": gpen,
                "skin": skin,
                "skin_unifi": skin_unifi,
                "gen_mode": gen_mode,
                "seed": None if seed == -1 else seed + i,  # 避免完全一样
                "batch_size": 1,  
                "image_base64": img_base64
            }

            try:
                response = requests.post(oneapi_url, headers=headers, json=payload, timeout=120)
                response.raise_for_status()
                result = response.json()
                img_base64_list = result.get('data', {}).get('binary_data_base64', [])

                if not img_base64_list:
                    raise ValueError("API返回空图像数据.")

                # 正常情况下每次返回1张
                img_bytes = base64.b64decode(img_base64_list[0])
                img = Image.open(BytesIO(img_bytes)).convert("RGB")
                # 直接调用导入的 pil2tensor 函数
                tensor_img = pil2tensor(img)
                output_tensors.append(tensor_img)

                print(f"✅ DreaminaI2INode 第{i+1}次调用成功")

            except Exception as e:
                print(f"❌ DreaminaI2INode 错误(第{i+1}次): {str(e)}")
                error_img = Image.new("RGB", (width, height), (255, 0, 0))
                # 直接调用导入的 pil2tensor 函数
                error_tensor = pil2tensor(error_img)
                output_tensors.append(error_tensor)

        return (torch.cat(output_tensors, dim=0),)  # 返回(batch_size, H, W, 3)



NODE_CLASS_MAPPINGS = {
    "DreaminaI2INode": DreaminaI2INode,
     "Dreamina t2i": VolcPicNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DreaminaI2INode": "🎨 Dreamina i2i（梦图生图）",
    "VolcPicNode": "Dreamina t2i"
}
