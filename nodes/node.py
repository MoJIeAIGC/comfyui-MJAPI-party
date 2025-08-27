import requests
from PIL import Image
from io import BytesIO
import base64
from torchvision import transforms
import numpy as np
import torch
import os
from comfy_api.input_impl.video_types import VideoFromFile

from .base import ImageConverter
from .config import ConfigManager
import random
# 初始化配置管理器
config_manager = ConfigManager()


class DreaminaI2INode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),  # 输入图像
                # "image": ("STRING", {"default": "https://pic.52112.com/180320/180320_17/Bl3t6ivHKZ_small.jpg"}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
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
    CATEGORY = "🎨MJapiparty/Dreamina(即梦)"

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
                    error_msg = ImageConverter.get_status_error_msg(response,1)
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
                "prompt": ("STRING", {"default": "A beautiful sunset", "multiline": True}),
                "seed": ("INT", {"default": -1}),
                "is_translation": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "aspect_ratio": (["default", "1:1", "3:4", "4:3", "9:16", "16:9"], {"default": "default"}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
            },
            "optional": {
                "image_input": ("IMAGE", {"default": None}),  # 可选的图像输入
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Flux"

    def generate(self, prompt, seed, batch_size, image_input=None, is_translation=False, aspect_ratio="default"):
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
                "safety_tolerance":6,
                "prompt": prompt,
                "seed": int(seed_override),
                "is_translation": is_translation,  # 传递翻译模式参数
            }
            # 如果有图像输入，加入到payload中
            if image_base64 is not None:
                payload["input_image"] = image_base64
            if aspect_ratio != "default":
                payload["aspect_ratio"] = aspect_ratio
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=1200)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response)
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
                "prompt": ("STRING", {"default": "A beautiful sunset", "multiline": True}),
                "seed": ("INT", {"default": -1}),
                "is_translation": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "aspect_ratio": (["default", "1:1", "3:4", "4:3", "9:16", "16:9"], {"default": "default"}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
            },
            "optional": {
                "image_input": ("IMAGE", {"default": None}),  # 可选的图像输入
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Flux"

    def generate(self, prompt, seed, batch_size, image_input=None, is_translation=False, aspect_ratio="default"):
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
                "safety_tolerance":6,
                "prompt": prompt,
                "seed": int(seed_override),
                "is_translation": is_translation,  # 传递翻译模式参数
            }
            # 如果有图像输入，加入到payload中
            if image_base64 is not None:
                payload["input_image"] = image_base64
            if aspect_ratio != "default":
                payload["aspect_ratio"] = aspect_ratio
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=1200)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response)
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
                "migrate_image": ("IMAGE",),  # 输入图像
                "migrate_mask": ("MASK",),  # 输入遮罩
                "Product_image": ("IMAGE",),  # 输入图像
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "strong": ("FLOAT", {"default": 0.6}),
                "seed": ("INT", {"default": -1}),  # -1表示随机
            },
            "optional": {
                "Product_mask": ("MASK",),  # 可选的图像输入
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Tools_api"

    def generate(self, Product_image, prompt, migrate_image, seed, strong , Product_mask=None, migrate_mask=None):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        pro_base64 = ImageConverter.merge_image(Product_image, Product_mask)
        mig_base64 = ImageConverter.merge_image(migrate_image, migrate_mask)

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
            "seed": seed, 
            "image": pro_base64,
            "imagem": mig_base64
        }

        try:
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=300)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response)
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


class SeedEdit3:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),  # 输入图像
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "cfg_scale": ("FLOAT", {"default": 0.5}),
                "seed": ("INT", {"default": -1}),  # -1表示随机
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 2}),  # 生成张数
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/seededit_v3.0"

    def generate(self, image, prompt, cfg_scale, seed, batch_size):
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
                "model": "seededit_v3.0",
                "req_key": "seededit_v3.0",
                "prompt": prompt,
                "scale": cfg_scale,
                "seed": seed+i,  # 避免完全一样
                "batch_size": 1,  
                "image_base64": img_base64
            }

            try:
                response = requests.post(oneapi_url, headers=headers, json=payload, timeout=120)
                # 判断状态码是否为 200
                if response.status_code != 200:
                    error_msg = ImageConverter.get_status_error_msg(response,1)
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

                print(f"✅ seededit_v3.0 第{i+1}次调用成功")

            except Exception as e:
                print(f"❌ seededit_v3.0 错误(第{i+1}次): {str(e)}")
                error_tensor = ImageConverter.create_error_image("运行异常，请稍后重试")
                output_tensors.append(error_tensor)

        return (torch.cat(output_tensors, dim=0),)  # 返回(batch_size, H, W, 3)


class KouTuNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),  # 输入图像
                "seed": ("INT", {"default": -1}),  # -1表示随机
            },
            "optional": {
                "mask": ("MASK",),  # 可选的图像输入
            }

        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Tools_api"

    def generate(self,  image, seed,  mask=None):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        mig_base64 = ImageConverter.merge_image(image, mask)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {oneapi_token}"
        }

        output_tensors = []

        payload = {
            "model": "auto_koutu_1.0",
            "seed": seed, 
            "imagem": mig_base64
        }

        try:
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=300)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response)
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
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            # 直接调用导入的 pil2tensor 函数
            tensor_img = ImageConverter.pil2tensor(img)
            output_tensors.append(tensor_img)

            print(f"✅ KouTuNode 调用成功")

        except Exception as e:
            print(f"❌ KouTuNode 错误: {str(e)}")
        return (torch.cat(output_tensors, dim=0),)  # 返回(batch_size, H, W, 3)


class DreaminaT2VNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset", "multiline": True}),
                "aspect_ratio": (["default", "1:1", "3:4", "4:3", "9:16", "16:9", "21:9"], {"default": "default"}),
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("VIDEO",)  # 返回VIDEO类型
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Dreamina(即梦)"

    def generate(self, prompt, seed, aspect_ratio="default"):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api(seed_override):
            payload = {
                "model": "Dreaminat2vNode",
                "req_key": "jimeng_vgfm_t2v_l20",
                "prompt": prompt,
                "seed": int(seed_override)
            }
            if aspect_ratio != "default":
                payload["aspect_ratio"] = aspect_ratio
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=240)

            response.raise_for_status()

            result = response.json()
            print(result)

            video_url = result.get('data', {}).get('video_url', [])
            if not video_url:
                raise ValueError("Empty video data from API.")
            return video_url

        video_url = call_api(seed)
        print(video_url)
        # 下载视频并提取帧
        video_path = ImageConverter.download_video(video_url)
        # 使用 VideoFromFile 封装视频

        return (VideoFromFile(video_path),)


class DreaminaI2VNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset", "multiline": True}),
                "aspect_ratio": (["default", "1:1", "3:4", "4:3", "9:16", "16:9", "21:9"], {"default": "default"}),
                "seed": ("INT", {"default": -1}),
                "images": ("IMAGE", {"default": []})  # 接收多个图片
            }
        }

    RETURN_TYPES = ("VIDEO",)  # 返回VIDEO类型
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Dreamina(即梦)"

    def generate(self, prompt, seed, aspect_ratio="default", images=[]):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api(seed_override, binary_data_base64):
            payload = {
                "model": "DreaminaI2VNode",
                "req_key": "jimeng_vgfm_i2v_l20",
                "prompt": prompt,
                "seed": int(seed_override),
                "binary_data_base64": binary_data_base64  # 添加Base64编码的图片数据
            }
            if aspect_ratio != "default":
                payload["aspect_ratio"] = aspect_ratio
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=240)

            response.raise_for_status()

            result = response.json()
            print(result)

            video_url = result.get('data', {}).get('video_url', [])
            if not video_url:
                raise ValueError("Empty video data from API.")
            return video_url

        # 将图像转换为Base64编码
        binary_data_base64 = ImageConverter.convert_images_to_base64(images)

        # 调用API
        video_url = call_api(seed, binary_data_base64)
        print(video_url)
        # 下载视频并提取帧
        video_path = ImageConverter.download_video(video_url)
        # 使用 VideoFromFile 封装视频

        return (VideoFromFile(video_path),)


class QwenImageNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset", "multiline": True}),
                "size": (["1328*1328", "1664*928", "1472*1140", "1140*1472", "928*1664"], {"default": "1328*1328"}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
                "prompt_extend": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/qwen-image"

    def generate(self, prompt, size, batch_size,seed,prompt_extend):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api():
            payload = {
                "model": "qwen-image",
                "modelr": "qwen-image",
                "prompt": prompt,
                "prompt_extend": prompt_extend,
                "size": size,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=60)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response,1)
                error_tensor = ImageConverter.create_error_image(error_msg, 512, 512)
                return error_tensor

            response.raise_for_status()
            result = response.json()
            # 处理URL列表获取图片数据
            img_bytes_list = []
            url = result.get('output').get('results', [])[0].get('url', None)
            response = requests.get(url)
            response.raise_for_status()
            img_bytes_list.append(response.content)
            
            # 转换为Base64格式
            img_base64_list = [base64.b64encode(img_bytes).decode('utf-8') for img_bytes in img_bytes_list]
            img_data = img_base64_list[0]  # 取第一张图片
            img_bytes = base64.b64decode(img_data)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            return ImageConverter.pil2tensor(img)

        output_tensors = []

        try:
            for i in range(batch_size):
                img_tensor = call_api()
                if isinstance(img_tensor, torch.Tensor):
                    # 判断是否为错误图像 tensor
                    if img_tensor.shape[1] == 512 and img_tensor.shape[2] == 512 and img_tensor[0, 0, 0, 0] == 1:
                        return (img_tensor,)
                output_tensors.append(img_tensor)
                print(f"QwenImageNode 第 {i+1} 张图片生成成功: {prompt} ()")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f"QwenImageNode 错误: {str(e)}")
            error_tensor = ImageConverter.create_error_image(str(e))
            error_tensors = [error_tensor for _ in range(batch_size)]
            return (torch.cat(error_tensors, dim=0),)


class QwenImageEditNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "image": ("IMAGE",),  # 输入图像
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/qwen-image-edit"

    def generate(self, prompt,image, batch_size,seed):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        image_base64 = ImageConverter.tensor_to_base64(image)

        def call_api():
            payload = {
                "model": "qwen-image-edit",
                "prompt": prompt,
                "image": image_base64,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=60)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response,1)
                error_tensor = ImageConverter.create_error_image(error_msg, 512, 512)
                return error_tensor

            response.raise_for_status()
            result = response.json()
            # 处理URL列表获取图片数据
            img_bytes_list = []
            url = result.get('output', {}).get('choices', [{}])[0].get('message', {}).get('content', [{}])[0].get('image', None)
            response = requests.get(url)
            response.raise_for_status()
            img_bytes_list.append(response.content)
            
            # 转换为Base64格式
            img_base64_list = [base64.b64encode(img_bytes).decode('utf-8') for img_bytes in img_bytes_list]
            img_data = img_base64_list[0]  # 取第一张图片
            img_bytes = base64.b64decode(img_data)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            return ImageConverter.pil2tensor(img)

        output_tensors = []

        try:
            for i in range(batch_size):
                img_tensor = call_api()
                if isinstance(img_tensor, torch.Tensor):
                    # 判断是否为错误图像 tensor
                    if img_tensor.shape[1] == 512 and img_tensor.shape[2] == 512 and img_tensor[0, 0, 0, 0] == 1:
                        return (img_tensor,)
                output_tensors.append(img_tensor)
                print(f"QwenImageNode 第 {i+1} 张图片生成成功: {prompt} ()")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f"QwenImageNode 错误: {str(e)}")
            error_tensor = ImageConverter.create_error_image(str(e))
            error_tensors = [error_tensor for _ in range(batch_size)]
            return (torch.cat(error_tensors, dim=0),)


class GetDressing:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),  # 输入图像
                "prompt": ("STRING", {"default": "Extract the clothes", "multiline": True}),
                "seed": ("INT", {"default": -1}),  # -1表示随机
                "prompt_extend": ("BOOLEAN", {"default": True}), 
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Tools_api"

    def generate(self,  image, seed,  prompt, prompt_extend):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        mig_base64 = ImageConverter.tensor_to_base64(image)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {oneapi_token}"
        }

        output_tensors = []
        if seed == -1:
            seed = random.randint(0, 999999)


        payload = {
            "model": "mojie_get_dressing",
            "seed": seed, 
            "image": mig_base64,
        }
        
        if not prompt_extend:
            payload["prompt"] = prompt
        

        try:
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=300)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response)
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
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            # 直接调用导入的 pil2tensor 函数
            tensor_img = ImageConverter.pil2tensor(img)
            output_tensors.append(tensor_img)

            print(f"✅ GetDressing 调用成功")

        except Exception as e:
            print(f"❌ GetDressing 错误: {str(e)}")
        return (torch.cat(output_tensors, dim=0),)  # 返回(batch_size, H, W, 3)


NODE_CLASS_MAPPINGS = {
    "DreaminaI2INode": DreaminaI2INode,
    "FluxProNode": FluxProNode,
    "FluxMaxNode": FluxMaxNode,
    "ReplaceNode": ReplaceNode,
    "SeedEdit3": SeedEdit3,
    "KouTuNode": KouTuNode,
    "DreaminaT2VNode": DreaminaT2VNode,
    "DreaminaI2VNode": DreaminaI2VNode,
    "QwenImageNode": QwenImageNode,
    "QwenImageEditNode": QwenImageEditNode,
    "GetDressing": GetDressing,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DreaminaI2INode": "Dreamina_I2i(即梦)",
    "FluxProNode": "Flux-Kontext-pro",
    "FluxMaxNode": "Flux-Kontext-max",
    "ReplaceNode": "Redux迁移",
    "SeedEdit3": "seededit_v3.0",
    "KouTuNode": "自动抠图",
    "DreaminaT2VNode": "即梦文生视频",
    "DreaminaI2VNode": "即梦图生视频",
    "QwenImageNode": "qwen-image文生图",
    "QwenImageEditNode": "qwen-image-edit图片编辑",
    "GetDressing": "AI服装提取",
}
