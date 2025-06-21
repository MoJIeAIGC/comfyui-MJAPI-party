import requests
from PIL import Image
from io import BytesIO
import base64
from torchvision import transforms
import numpy as np
import torch
import configparser
import os  # 导入 os 用于路径处理

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

    def pil2tensor(self, image):
        img_array = np.array(image).astype(np.float32) / 255.0  # (H, W, 3)
        img_tensor = torch.from_numpy(img_array)[None,]  # (1, H, W, 3)
        return img_tensor

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
                tensor_img = self.pil2tensor(img)
                output_tensors.append(tensor_img)
                print(f"🔥 VolcPicNode 第 {i+1} 张图片生成成功: {prompt} ({width}x{height})")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f"🔥 VolcPicNode 错误: {str(e)}")
            error_img = Image.new("RGB", (width, height), (255, 0, 0))
            error_tensor = self.pil2tensor(error_img)
            # 返回指定数量错误图
            error_tensors = [error_tensor for _ in range(batch_size)]
            return (torch.cat(error_tensors, dim=0),)

NODE_CLASS_MAPPINGS = {
     "Dreamina t2i": VolcPicNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VolcPicNode": "Dreamina t2i"
}
