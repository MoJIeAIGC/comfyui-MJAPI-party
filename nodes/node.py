import requests
from PIL import Image
from io import BytesIO
import base64
from torchvision import transforms
import numpy as np
import torch
import os  # 导入 os 用于路径处理

# 修改导入语句
from .base import ImageConverter
from .config import ConfigManager

# 初始化配置管理器
config_manager = ConfigManager()

class VolcPicNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset"}),
                "width": ("INT", {"default": 512}),
                "height": ("INT", {"default": 512}),
                "cfg_scale": ("FLOAT", {"default": 2.5}),
                "seed": ("INT", {"default": -1}),
                # "seed": ("INT", {"default": 1234}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "MJapiparty/ImageGenerate"

    def generate(self, prompt, width, height, cfg_scale, seed, batch_size):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

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
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response.status_code)
                error_tensor = ImageConverter.create_error_image(error_msg, width, height)
                return error_tensor

            response.raise_for_status()
            result = response.json()
            img_base64_list = result.get('data', {}).get('binary_data_base64', [])
            if not img_base64_list:
                raise ValueError("Empty image data from API.")
            img_data = img_base64_list[0]
            img_bytes = base64.b64decode(img_data)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            return ImageConverter.pil2tensor(img)

        output_tensors = []

        try:
            for i in range(batch_size):
                # 如果两次请求用同一个seed也行，可改为 seed+i 实现不同seed
                img_tensor = call_api(seed + i)
                if isinstance(img_tensor, torch.Tensor):
                    # 判断是否为错误图像 tensor
                    if img_tensor.shape[1] == height and img_tensor.shape[2] == width and img_tensor[0, 0, 0, 0] == 1:
                        return (img_tensor,)
                output_tensors.append(img_tensor)
                print(f"🔥 VolcPicNode 第 {i+1} 张图片生成成功: {prompt} ({width}x{height})")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f"🔥 VolcPicNode 错误: {str(e)}")
            error_tensor = ImageConverter.create_error_image(str(e), width, height)
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

    def generate(self, image, prompt, width, height, gpen, skin, skin_unifi, gen_mode, seed, batch_size):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        # Convert input tensor to base64
        pil_image = ImageConverter.tensor2pil(image)
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
                "seed": seed+i,  # 避免完全一样
                "batch_size": 1,  
                "image_base64": img_base64
            }

            try:
                response = requests.post(oneapi_url, headers=headers, json=payload, timeout=120)
                # 判断状态码是否为 200
                if response.status_code != 200:
                    error_msg = ImageConverter.get_status_error_msg(response.status_code)
                    error_tensor = ImageConverter.create_error_image(error_msg)
                    output_tensors.append(error_tensor)
                    continue
                response.raise_for_status()
                result = response.json()
                img_base64_list = result.get('data', {}).get('binary_data_base64', [])

                if not img_base64_list:
                    raise ValueError("API返回空图像数据.")

                # 正常情况下每次返回1张
                img_bytes = base64.b64decode(img_base64_list[0])
                img = Image.open(BytesIO(img_bytes)).convert("RGB")
                # 直接调用导入的 pil2tensor 函数
                tensor_img = ImageConverter.pil2tensor(img)
                output_tensors.append(tensor_img)

                print(f"✅ DreaminaI2INode 第{i+1}次调用成功")

            except Exception as e:
                print(f"❌ DreaminaI2INode 错误(第{i+1}次): {str(e)}")
                error_tensor = ImageConverter.create_error_image("运行异常，请稍后重试")
                output_tensors.append(error_tensor)

        return (torch.cat(output_tensors, dim=0),)  # 返回(batch_size, H, W, 3)

class FluxProNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset"}),
                "seed": ("INT", {"default": -1}),
                "is_translation": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
            },
            "optional": {
                "image_input": ("IMAGE", {"default": None}),  # 可选的图像输入
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "MJapiparty/ImageGenerate"

    def generate(self, prompt, seed, batch_size, image_input=None, is_translation=False):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        print(f"Flux API URL: {oneapi_url}")  # 打印API URL

        # 如果提供了图像输入，将其转换为base64
        image_base64 = None
        if image_input is not None:
            try:
                pil_image = ImageConverter.tensor2pil(image_input)
                buffered = BytesIO()
                pil_image.save(buffered, format="JPEG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                image_base64 = img_base64
            except Exception as e:
                print(f"处理图像失败: {e}")
                image_base64 = None

        def call_api(seed_override):
            payload = {
                "model": "flux-context-pro",
                "prompt": prompt,
                "seed": int(seed_override),
                "is_translation": is_translation,  # 传递翻译模式参数
            }
            # 如果有图像输入，加入到payload中
            if image_base64 is not None:
                print("使用图像输入进行生成")
                payload["input_image"] = image_base64
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=1200)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response.status_code)
                error_tensor = ImageConverter.create_error_image(error_msg, width=512, height=512)
                return error_tensor
            response.raise_for_status()
            result = response.json()

            # 从返回的结果中提取图片 URL
            image_url = result['result'].get('sample', None)
            if not image_url:
                raise ValueError("未找到图片 URL")
            # 下载图片
            response = requests.get(image_url)
            response.raise_for_status()
            # 将图片数据转换为 PIL 图像对象
            img = Image.open(BytesIO(response.content)).convert("RGB")
            return ImageConverter.pil2tensor(img)

        output_tensors = []

        try:
            for i in range(batch_size):
                # 如果两次请求用同一个seed也行，可改为 seed+i 实现不同seed
                img = call_api(seed + i)
                # 直接调用导入的 pil2tensor 函数
                # tensor_img = ImageConverter.pil2tensor(img)
                output_tensors.append(img)
                print(f"Flux 第 {i+1} 张图片生成成功: {prompt}")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f"Flux错误: {str(e)}")
            error_tensor = ImageConverter.create_error_image("运行异常，请稍后重试")
            # 返回指定数量错误图
            error_tensors = [error_tensor for _ in range(batch_size)]
            return (torch.cat(error_tensors, dim=0),)

class FluxMaxNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset"}),
                "seed": ("INT", {"default": -1}),
                "is_translation": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
            },
            "optional": {
                "image_input": ("IMAGE", {"default": None}),  # 可选的图像输入
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "MJapiparty/ImageGenerate"

    def generate(self, prompt, seed, batch_size, image_input=None, is_translation=False):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        print(f"Flux API URL: {oneapi_url}")  # 打印API URL

        # 如果提供了图像输入，将其转换为base64
        image_base64 = None
        if image_input is not None:
            try:
                pil_image = ImageConverter.tensor2pil(image_input)
                buffered = BytesIO()
                pil_image.save(buffered, format="JPEG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                image_base64 = img_base64
            except Exception as e:
                print(f"处理图像失败: {e}")
                image_base64 = None

        def call_api(seed_override):
            payload = {
                "model": "flux-context-max",
                "prompt": prompt,
                "seed": int(seed_override),
                "is_translation": is_translation,  # 传递翻译模式参数
            }
            # 如果有图像输入，加入到payload中
            if image_base64 is not None:
                print("使用图像输入进行生成")
                payload["input_image"] = image_base64
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=1200)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response.status_code)
                error_tensor = ImageConverter.create_error_image(error_msg, width=512, height=512)
                return error_tensor
            response.raise_for_status()
            result = response.json()

            # 从返回的结果中提取图片 URL
            image_url = result['result'].get('sample', None)
            if not image_url:
                raise ValueError("未找到图片 URL")
            # 下载图片
            response = requests.get(image_url)
            response.raise_for_status()
            # 将图片数据转换为 PIL 图像对象
            img = Image.open(BytesIO(response.content)).convert("RGB")
            return ImageConverter.pil2tensor(img)

        output_tensors = []

        try:
            for i in range(batch_size):
                # 如果两次请求用同一个seed也行，可改为 seed+i 实现不同seed
                img = call_api(seed + i)
                # 直接调用导入的 pil2tensor 函数
                # tensor_img = ImageConverter.pil2tensor(img)
                output_tensors.append(img)
                print(f"Flux 第 {i+1} 张图片生成成功: {prompt}")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f"Flux错误: {str(e)}")
            error_tensor = ImageConverter.create_error_image("运行异常，请稍后重试")
            # 返回指定数量错误图
            error_tensors = [error_tensor for _ in range(batch_size)]
            return (torch.cat(error_tensors, dim=0),)



class ReplaceNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "Product_image": ("IMAGE",),  # 输入图像
                "migrate_image": ("IMAGE",),  # 输入图像
                "prompt": ("STRING", {"default": ""}),
                "strong": ("FLOAT", {"default": 0.6}),
                "seed": ("INT", {"default": -1}),  # -1表示随机
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output",)
    FUNCTION = "generate"
    CATEGORY = "MJapiparty/ImageGenerate"

    def generate(self, Product_image, prompt, migrate_image, seed, strong ):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        pro_base64 = ImageConverter.tensor_to_base64(Product_image)
        mig_base64 = ImageConverter.tensor_to_base64(migrate_image)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {oneapi_token}"
        }

        output_tensors = []
        prompt = "This is a collage picture，in the left Objects replaces the Objects in the right picture." + prompt

        payload = {
            "model": "Product_migrate_mjAPI",
            "prompt": prompt,
            "strong": strong,
            "seed": seed,  # 避免完全一样
            "image": pro_base64,
            "imagem": mig_base64
        }

        try:
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=300)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response.status_code)
                error_tensor = ImageConverter.create_error_image(error_msg)
                output_tensors.append(error_tensor)
                raise requests.exceptions.HTTPError(f"Request failed with status code {response.status_code}: {error_msg}")
            response.raise_for_status()
            result = response.json()
            result_url = result.get('data')[0].get('fileUrl')

            if not result_url:
                raise ValueError("API返回空图像数据.")

            responseurl = requests.get(result_url)
            if responseurl.status_code != 200:
                raise ValueError("从 URL 获取图片失败。")
            
            img_bytes = responseurl.content
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            # 直接调用导入的 pil2tensor 函数
            tensor_img = ImageConverter.pil2tensor(img)
            output_tensors.append(tensor_img)

            print(f"✅ ReplaceNode 调用成功")

        except Exception as e:
            print(f"❌ ReplaceNode 错误: {str(e)}")
            # error_tensor = ImageConverter.create_error_image("运行异常，请稍后重试")
            # output_tensors.append(error_tensor)
        return (torch.cat(output_tensors, dim=0),)  # 返回(batch_size, H, W, 3)



NODE_CLASS_MAPPINGS = {
    "DreaminaI2INode": DreaminaI2INode,
    "FluxProNode": FluxProNode,
    "FluxMaxNode": FluxMaxNode,
    "Dreamina t2i": VolcPicNode,
    "ReplaceNode": ReplaceNode,

}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DreaminaI2INode": "🎨 Dreamina i2i（梦图生图）",
    "FluxProNode": "Flux-context-pro",
    "FluxMaxNode": "Flux-context-max",
    "VolcPicNode": "Dreamina t2i",
    "ReplaceNode": "Product_migrate_mjAPI",

}
