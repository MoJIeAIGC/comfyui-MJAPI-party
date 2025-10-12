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
    CATEGORY = "🎨MJapiparty/ImageCreat"

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
    CATEGORY = "🎨MJapiparty/ImageCreat"

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

# vidu文生视频
class ViduT2VNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "model": (["viduq1", "vidu1.5"], {"default": "viduq1"}),
                "style": (["general", "anime"], {"default": "general"}),
                "duration": ("INT", {"default": 5, "min": 4, "max": 5, "readonly": True}),
                "resolution": (["360P", "720P", "1080p"], {"default": "1080p"}),
                "movement_amplitude": (["auto", "small", "medium", "large"], {"default": "auto"}),
                "Size": (["1:1", "9:16", "16:9"], {"default": "16:9"}),
                "bgm": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("VIDEO",)  # 返回VIDEO类型
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/VideoCreat"

    def generate(self, prompt, model, seed, style="general", duration=5, resolution="1080p", Size="16:9", movement_amplitude="auto", bgm=False):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api(seed_override):
            payload = {
                "model": "vidut2vNode",
                "modelr": model,
                "prompt": prompt,
                "seed": int(seed_override),
                "resolution": resolution,
                "aspect_ratio": Size,
                "duration": duration,
                "movement_amplitude": movement_amplitude,
                "bgm": bgm,
                "style": style,
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=400)

            response.raise_for_status()

            result = response.json()
            print(result)

            video_url = result.get('creations', [])[0].get('url', '')
            if not video_url:
                raise ValueError("Empty video data from API.")
            return video_url

        video_url = call_api(seed)
        print(video_url)
        # 下载视频并提取帧
        video_path = ImageConverter.download_video(video_url)
        # 使用 VideoFromFile 封装视频

        return (VideoFromFile(video_path),)

# vidu首尾帧视频
class ViduI2VNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "first_image": ("IMAGE",),  # 接收多个图片
                "last_image": ("IMAGE",),  # 接收多个图片
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "model": (["viduq1", "vidu1.5", "viduq1-classic", "vidu2.0"], {"default": "viduq1-classic"}),
                "duration": ("INT", {"default": 5, "min": 4, "max": 5, "readonly": True}),
                "resolution": (["360P", "720P", "1080p"], {"default": "1080p"}),
                "movement_amplitude": (["auto", "small", "medium", "large"], {"default": "auto"}),
                "Size": (["1:1", "9:16", "16:9"], {"default": "16:9"}),
                "bgm": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("VIDEO",)  # 返回VIDEO类型
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/VideoCreat"

    def generate(self, prompt, model, seed,duration=5, resolution="1080p", Size="16:9", movement_amplitude="auto", bgm=False, first_image=None, last_image=None):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()
        images = []
        first_image_base64 = ImageConverter.tensor_to_base64(first_image)
        images.append(first_image_base64)
        if last_image is not None:
            last_image_base64 = ImageConverter.tensor_to_base64(last_image)
            images.append(last_image_base64)
        
        def call_api(seed_override):
            payload = {
                "model": "vidui2vNode",
                "modelr": model,
                "prompt": prompt,
                "seed": int(seed_override),
                "resolution": resolution,
                "aspect_ratio": Size,
                "duration": duration,
                "movement_amplitude": movement_amplitude,
                "bgm": bgm,
                "images": images,
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=400)

            response.raise_for_status()

            result = response.json()
            print(result)

            video_url =  result.get('creations', [])[0].get('url', '')
            if not video_url:
                raise ValueError("Empty video data from API.")
            return video_url

        video_url = call_api(seed)
        print(video_url)
        # 下载视频并提取帧
        video_path = ImageConverter.download_video(video_url)
        # 使用 VideoFromFile 封装视频

        return (VideoFromFile(video_path),)


# seedance文生视频
class DreaminaT2VNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "resolution": (["480P", "720P", "1080p"], {"default": "1080p"}),
                "Size": (["1:1", "3:4", "4:3", "9:16", "16:9", "21:9"], {"default": "16:9"}),
                "duration": ("INT", {"default": 10, "min": 3, "max": 12}),  # 新增参数，只能是1或2
                "camerafixed": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("VIDEO",)  # 返回VIDEO类型
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/VideoCreat"

    def generate(self, prompt, seed,  resolution="1080p", Size="16:9", duration=10, camerafixed=False):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api(seed_override):
            payload = {
                "model": "Dreaminat2vNode",
                "prompt": prompt,
                "seed": int(seed_override),
                "resolution": resolution,
                "Size": Size,
                "duration": duration,
                "camerafixed": camerafixed,
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=240)

            response.raise_for_status()

            result = response.json()
            print(result)

            video_url = result.get("content").get("video_url")
            if not video_url:
                raise ValueError("Empty video data from API.")
            return video_url

        video_url = call_api(seed)
        print(video_url)
        # 下载视频并提取帧
        video_path = ImageConverter.download_video(video_url)
        # 使用 VideoFromFile 封装视频

        return (VideoFromFile(video_path),)



# seedance图生视频 + seedance首尾帧视频
class DreaminaI2VNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "first_image": ("IMAGE",),  # 接收多个图片
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "resolution": (["480P", "720P", "1080p"], {"default": "1080p"}),
                "Size": (["1:1", "3:4", "4:3", "9:16", "16:9", "21:9"], {"default": "16:9"}),
                "duration": ("INT", {"default": 10, "min": 3, "max": 12}),  # 新增参数，只能是1或2
                "camerafixed": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "seed": ("INT", {"default": -1}),
            },
            "optional": {
                "last_image": ("IMAGE",),  # 接收多个图片
            }
        }

    RETURN_TYPES = ("VIDEO",)  # 返回VIDEO类型
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/VideoCreat"

    def generate(self, prompt, seed, first_image, resolution="1080p", Size="16:9", duration=10, camerafixed=False, last_image=None):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()
        first_image_base64 = ImageConverter.tensor_to_base64(first_image)
        def call_api(seed_override):
            payload = {
                "model": "DreaminaI2VNode",
                "prompt": prompt,
                "resolution": resolution,
                "Size": Size,
                "duration": duration,
                "camerafixed": camerafixed,
                "seed": int(seed_override),
                "first_image_base64": first_image_base64,
            }
            if last_image is not None:
                last_image_base64 = ImageConverter.tensor_to_base64(last_image)
                payload["last_image_base64"] = last_image_base64
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=240)

            response.raise_for_status()

            result = response.json()
            print(result)

            video_url = result.get("content").get("video_url")
            if not video_url:
                raise ValueError("Empty video data from API.")
            return video_url

        # 调用API
        video_url = call_api(seed)
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
                "prompt_extend": ("BOOLEAN", {"default": True}),  # 是否开启prompt智能改写
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/ImageCreat"

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
    CATEGORY = "🎨MJapiparty/ImageCreat"

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
                "extend_prompt": ([ "默认","全身", "上身", "下身","外套"], {"default": "默认"}),
                "size": ([ "1:1", "3:4", "4:3"], {"default": "1:1"}),
                "seed": ("INT", {"default": -1}),  # -1表示随机
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/clothCreat"

    def generate(self,  image, seed,  extend_prompt,size="1:1"):
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
            "aspect_ratio": size,
            "input_image": mig_base64,
            "watermark": False,
            "extend_prompt": extend_prompt
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
            result_url = result.get("res_url")

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

class ViduNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset", "multiline": True}),
                "model": (["default", "viduq1", "vidu1.5", "vidu2.0"], {"default": "viduq1"}),
                "aspect_ratio": ([ "16:9", "9:16", "1:1"], {"default": "16:9"}),
                "seed": ("INT", {"default": -1}),
                "images": ("IMAGE", {"default": []})  # 接收多个图片
            }
        }

    RETURN_TYPES = ("VIDEO",)  # 返回VIDEO类型
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/VideoCreat"

    def generate(self, prompt, seed,model, aspect_ratio="16:9", images=[]):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        if model == "viduq1":
            duration = 5
        else:
            duration = 5

        def call_api(seed_override, binary_data_base64):
            payload = {
                "model": "vidu_video",
                "modelr": model,
                "aspect_ratio": aspect_ratio,
                "prompt": prompt,
                "duration": duration,
                "seed": 0,
                "images": binary_data_base64  # 添加Base64编码的图片数据
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=240)

            response.raise_for_status()

            result = response.json()
            print(result)

            video_url = result.get('creations', [])[0].get('url', '')
            if not video_url:
                raise ValueError("Empty video data from API.")
            return video_url

        # 将图像转换为Base64编码
        binary_data_base64 = ImageConverter.convert_images_to_base64(images)

        # 调用API
        video_url = call_api(0, binary_data_base64)
        print(video_url)
        # 下载视频并提取帧
        video_path = ImageConverter.download_video(video_url)
        # 使用 VideoFromFile 封装视频

        return (VideoFromFile(video_path),)


class ReplaceClothesNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "cloths_image": ("IMAGE",),  # 输入图像
                "model_image": ("IMAGE",),  # 输入图像
                "seed": ("INT", {"default": -1}),  # -1表示随机
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/clothCreat"

    def generate(self, cloths_image, model_image, seed):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        # 获取model_image的尺寸并计算宽高比
        height, width = model_image.shape[1], model_image.shape[2]  # 获取图像的高度和宽度
        image_ratio = width / height  # 计算图像的宽高比
        print(f"模特图片宽高比例: {image_ratio}")
        # 预定义的宽高比列表及其对应的比值
        aspect_ratios = {
            "21:9": 21/9,
            "16:9": 16/9,
            "4:3": 4/3,
            "3:2": 3/2,
            "1:1": 1/1,
            "5:4": 5/4,
            "4:5": 4/5,
            "3:4": 3/4,
            "2:3": 2/3,
            "9:16": 9/16
        }
        
        # 找出最接近的宽高比
        closest_ratio = min(aspect_ratios, key=lambda x: abs(aspect_ratios[x] - image_ratio))
        print(f"最接近的宽高比: {closest_ratio}")

        merged_base64 = ImageConverter.prepare_and_stitch_images(model_image, cloths_image)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {oneapi_token}"
        }

        output_tensors = []

        payload = {
            "model": "dressV2ing_diffusion",
            "Custom_prompt": False,
            "seed": seed, 
            "aspect_ratio": closest_ratio,
            "input_image": merged_base64,
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
            result_url = result.get("res_url")

            if not result_url:
                raise ValueError("API返回空图像数据.")

            responseurl = requests.get(result_url)
            if responseurl.status_code != 200:
                raise ValueError("从 URL 获取图片失败。")
            
            img_bytes = responseurl.content
            img = Image.open(BytesIO(img_bytes)).convert("RGB")

            # img = ImageConverter.get_right_part_of_image(img)
            # 直接调用导入的 pil2tensor 函数
            tensor_img = ImageConverter.pil2tensor(img)
            output_tensors.append(tensor_img)

            print(f"✅ ReplaceNode 调用成功")

        except Exception as e:
            print(f"❌ ReplaceNode 错误: {str(e)}")
            # error_tensor = ImageConverter.create_error_image("运行异常，请稍后重试")
            # output_tensors.append(error_tensor)
        return (torch.cat(output_tensors, dim=0),)  # 返回(batch_size, H, W, 3)


class GeminiEditNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset", "multiline": True}),
                "is_translation": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "Size": (["1:1", "3:4", "4:3", "9:16", "16:9"], {"default": "3:4"}),
                "seed": ("INT", {"default": -1}),
            },
            "optional": {
                "image_input": ("IMAGE", {"default": None}),  # 可选的图像输入
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/ImageCreat"

    def generate(self, prompt, seed, image_input=None, is_translation=False, Size="3:4"):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api(seed_override):
            payload = {
                "model": "gemini-2.5-flash-image",
                "prompt": prompt,
                "is_translation": is_translation,  # 传递翻译模式参数
                "aspect_ratio": Size,  # 传递尺寸参数
                "seed": int(seed_override),
            }
            # 如果有图像输入，加入到payload中
            if image_input is not None:
                payload["input_image"] = ImageConverter.tensor_to_base64(image_input)

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
            image_url = result.get("res_url")

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
            for i in range(1):
                # 如果两次请求用同一个seed也行，可改为 seed+i 实现不同seed
                img = call_api(seed + i)
                # 直接调用导入的 pil2tensor 函数
                # tensor_img = ImageConverter.pil2tensor(img)
                output_tensors.append(img)
                print(f"Gemini 第 {i+1} 张图片生成成功: {prompt}")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f"Gemini: {str(e)}")
            error_tensor = ImageConverter.create_error_image("运行异常，请稍后重试")
            # 返回指定数量错误图
            error_tensors = [error_tensor for _ in range(1)]
            return (torch.cat(error_tensors, dim=0),)


class DoubaoSeedreamNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset", "multiline": True}),
                "seed": ("INT", {"default": -1}),
                "custom_size": ("BOOLEAN", {"default": False}),  # 自定义尺寸开关
                "size": (["2048x2048", "2304x1728", "1728x2304", "2560x1440", "1440x2560", "2496x1664", "1664x2496", "3024x1296"], {"default": "2048x2048"}),
                "width": ("INT", {"default": 1024, "min": 1024, "max": 4096}),  # 生成张数
                "height": ("INT", {"default": 1024, "min": 1024, "max": 4096}),  # 生成张数
                "max_SetImage": (["off", 'auto'], {"default": "off"}),  
            },
            "optional": {
                "image_input": ("IMAGE", {"default": []}),  # 可选的图像输入
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/ImageCreat"

    def generate(self, prompt, seed, image_input=None,width=1024,height=1024,custom_size=True,size="1024x1024",max_SetImage="off"):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        if custom_size == False:
            resl_size = size
        else:
            resl_size = f"{width}x{height}"

        count = 1 if max_SetImage == 'off' else 15

        payload = {
            "model": "doubao-seedream-4.0",
            "prompt": prompt,
            "size": resl_size, 
            "seed": int(seed+6),
            "watermark": False,
            "max_SetImage": count,
        }
        # 如果有图像输入，加入到payload中
        if image_input is not None:
            binary_data_base64 = ImageConverter.convert_images_to_base64(image_input)
            payload["input_image"] = binary_data_base64

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {oneapi_token}"
        }
        response = requests.post(oneapi_url, headers=headers, json=payload, timeout=1200)
        # 判断状态码是否为 200
        if response.status_code != 200:
            error_msg = ImageConverter.get_status_error_msg(response)
            print("错误信息",error_msg)
            output_tensors = []
            error_tensor = ImageConverter.create_error_image(error_msg)
            output_tensors.append(error_tensor)
            return (torch.cat(output_tensors, dim=0),)
        response.raise_for_status()
        result = response.json()

        # 从返回的结果中提取图片 URL
        res_url = result.get("res_url", "")
        if not res_url:
            raise ValueError("未找到图片 URL")
        image_urls = res_url.split("|") if res_url else []

        api_tensors = []
        print(image_urls)
        for image_url in image_urls:
            if not image_url:
                continue
            try:
                # 下载图片
                response = requests.get(image_url)
                response.raise_for_status()
                # 将图片数据转换为 PIL 图像对象
                img = Image.open(BytesIO(response.content)).convert("RGB")
                api_tensors.append(ImageConverter.pil2tensor(img))
            except Exception as e:
                print(f"下载图片 {image_url} 失败: {str(e)}")
                error_tensor = ImageConverter.create_error_image("下载图片失败")
                api_tensors.append(error_tensor)

        if not api_tensors:
            error_tensor = ImageConverter.create_error_image("未获取到有效图片 URL")
            api_tensors.append(error_tensor)

        return (torch.cat(api_tensors, dim=0),)


class ModelGenNode:
    @classmethod
    def INPUT_TYPES(cls):
        # 发送请求
        url = "https://qihuaimage.com/api/mjapi/styles/"
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        styles = result.get("data", [])
        style_prompt = [item["name"] for item in styles]
        return {
            "required": {
                "cloths_image": ("IMAGE",),  # 输入图像
                "race_class": (["亚裔", "黑人", "白人"], {"default": "亚裔"}),
                "gender_class": (["man", "woman", "little boy","little girl"], {"default": "woman"}),
                "style_prompt": (style_prompt, {"default": "INS自拍风"}),
                "seed": ("INT", {"default": -1}),
            },
            "optional": {
                "face_image": ("IMAGE", {"default": None}),  # 可选的图像输入
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/clothCreat"

    def generate(self , seed, face_image=None, cloths_image=None,race_class="Asia",gender_class="woman",style_prompt="INS自拍风"):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        image_base64 = ImageConverter.process_images(face_image, cloths_image)

        races = {
            "亚裔": "Asia",
            "黑人": "black",
            "白人": "Ukraine"
        }
        race_class = races.get(race_class, "Asia")

        is_face = True if face_image is not None else False

        def call_api(seed_override):
            payload = {
                "model": "mojie-output-moter",
                "gender_class": gender_class,
                "race_class": race_class,
                "seed": int(seed_override),
                "is_face": is_face,
                "style_prompt": style_prompt,
                "input_image": image_base64
            }

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
            image_url = result.get("res_url")

            if not image_url:
                raise ValueError("未找到图片 URL")
            # 下载图片
            response = requests.get(image_url)
            response.raise_for_status()
            # 将图片数据转换为 PIL 图像对象
            img = Image.open(BytesIO(response.content)).convert("RGB")
            # 调用封装的函数裁剪白色边框
            img = ImageConverter.crop_white_borders(img)
            return ImageConverter.pil2tensor(img)

        output_tensors = []

        try:
            for i in range(1):
                # 如果两次请求用同一个seed也行，可改为 seed+i 实现不同seed
                img = call_api(seed + i)
                # 直接调用导入的 pil2tensor 函数
                # tensor_img = ImageConverter.pil2tensor(img)
                output_tensors.append(img)
                print(f"Gemini 第 {i+1} 张图片生成成功")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f"Gemini: {str(e)}")
            error_tensor = ImageConverter.create_error_image("运行异常，请稍后重试")
            # 返回指定数量错误图
            error_tensors = [error_tensor for _ in range(1)]
            return (torch.cat(error_tensors, dim=0),)


class MoterPoseNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_input": ("IMAGE", {"default": None}),  # 可选的图像输入
                "extent_prompt": ("BOOLEAN", {"default": True}),  # 是否是翻译模式
                "out_batch": ("INT", {"default": 1, "min": 1, "max": 2}),  # 生成张数
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/clothCreat"

    def generate(self,  seed, image_input=None, extent_prompt=False,out_batch=1):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api(seed_override):
            payload = {
                "model": "moter-pose-change",
                "extent_prompt": extent_prompt,  # 传递翻译模式参数
                "seed": int(seed_override),
                "watermark": False,
                "input_image": ImageConverter.tensor_to_base64(image_input)
            }

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
            image_url = result.get("res_url")

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
            for i in range(out_batch):
                # 如果两次请求用同一个seed也行，可改为 seed+i 实现不同seed
                img = call_api(seed + i)
                # 直接调用导入的 pil2tensor 函数
                # tensor_img = ImageConverter.pil2tensor(img)
                output_tensors.append(img)
                print(f" 第 {i+1} 张图片生成成功")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f": {str(e)}")
            error_tensor = ImageConverter.create_error_image("运行异常，请稍后重试")
            # 返回指定数量错误图
            error_tensors = [error_tensor for _ in range(1)]
            return (torch.cat(error_tensors, dim=0),)


class ImageTranslateNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_input": ("IMAGE", {"default": []}),  # 可选的图像输入
                "modelid": (["default", "erase" ], {"default": "default"}),
                "SourceLang": (["自动","阿拉伯语", "法语", "英语",  "加泰罗尼亚语", "葡萄牙语", "西班牙语", "荷兰语", "德语", "斯洛文尼亚语", "阿塞拜疆语", "孟加拉语", "俄语", "挪威语", "马来语", "中文", "中文 (繁体)", "捷克语", "斯洛伐克语", "波兰语", "匈牙利语", "越南语", "丹麦语", "芬兰语", "瑞典语", "印尼语", "希伯来语", "意大利语", "日语", "韩语", "泰米尔语", "泰语", "土耳其语"], {"default": "自动"}),
                "TargetLang": (["默认英语","中文", "中文 (繁体)",   "日语", "韩语", "阿拉伯语", "葡萄牙语", "法语", "德语", "西班牙语", "印尼语", "意大利语", "马来语", "俄语", "泰语", "越南语"], {"default": "默认英语"}),
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Tools_api"

    def generate(self, seed, image_input=[], modelid="default", SourceLang="auto", TargetLang="auto"):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()
        
        def call(img):
            binary_data_base64 = ImageConverter.tensor_to_base64(img)

            payload = {
                "model": "image_translate",
                "seed": int(seed+6),
                "input_image": binary_data_base64,
                "modelid": modelid,
                "SourceLang": ImageConverter.get_lang(SourceLang),
                "TargetLang": ImageConverter.get_lang(TargetLang),
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=1200)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response)
                print("错误信息",error_msg)
                output_tensors = []
                error_tensor = ImageConverter.create_error_image(error_msg)
                output_tensors.append(error_tensor)
                return (torch.cat(output_tensors, dim=0),)
            response.raise_for_status()
            result = response.json()

            # 从返回的结果中提取图片 URL
            res_url = result.get("res_url", "")
            if not res_url:
                raise ValueError("未找到图片 URL")
            return res_url

        api_tensors = []
        for img in image_input:
            try:
                # 宽高
                width, height = img.shape[2], img.shape[1]
                print(f"图片宽高: {width}x{height}")

                res_url = call(img)
                response = requests.get(res_url)
                response.raise_for_status()
                # 将图片数据转换为 PIL 图像对象
                img = Image.open(BytesIO(response.content)).convert("RGB")
                api_tensors.append(ImageConverter.pil2tensor(img))
            except Exception as e:
                print(f"下载图片 {res_url} 失败: {str(e)}")
                error_tensor = ImageConverter.create_error_image("下载图片失败")
                api_tensors.append(error_tensor)

        if not api_tensors:
            error_tensor = ImageConverter.create_error_image("未获取到有效图片 URL")
            api_tensors.append(error_tensor)

        return (torch.cat(api_tensors, dim=0),)

class ImageUpscaleNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_input": ("IMAGE", {"default": []}),  # 可选的图像输入
                "seed": ("INT", {"default": -1}),
                "multiple": (["x2", "x4", "x6"], {"default": "x2"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Tools_api"

    def generate(self, seed, image_input=[], multiple="x2"):

            
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        multiple_map = {
            "x2": 2,
            "x4": 4,
            "x6": 6,
            "x8": 8,
        }
        multiple = multiple_map[multiple]

        def call(img):
            binary_data_base64 = ImageConverter.tensor_to_base64(img)

            payload = {
                "model": "image_upscale",
                "seed": int(seed+6),
                "input_image": binary_data_base64,
                "multiple": multiple,
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=1200)
            # 判断状态码是否为 200
            if response.status_code != 200:
                error_msg = ImageConverter.get_status_error_msg(response)
                print("错误信息",error_msg)
                output_tensors = []
                error_tensor = ImageConverter.create_error_image(error_msg)
                output_tensors.append(error_tensor)
                return (torch.cat(output_tensors, dim=0),)
            response.raise_for_status()
            result = response.json()

            # 从返回的结果中提取图片 URL
            res_url = result.get("res_url", "")
            if not res_url:
                raise ValueError("未找到图片 URL")
            return res_url

        api_tensors = []
        for img in image_input:
            try:

                # 获取图片尺寸
                # print("处理图片...",len(img.shape))
                height, width = img.shape[0], img.shape[1]
                print(f"图片宽高: {width}x{height}")

                # print("====== 图像输入调试 ======")
                # print("类型:", type(img))

                # if isinstance(img, torch.Tensor):
                #     print("形状:", img.shape)
                #     print("数据类型:", img.dtype)
                #     print("值范围:", (float(img.min()), float(img.max())))
                #     print("前10个像素值:", img.flatten()[:10])
                # elif isinstance(img, list) or isinstance(img, tuple):
                #     print("列表长度:", len(img))
                #     if len(img) > 0 and isinstance(img[0], torch.Tensor):
                #         print("第一个元素形状:", img[0].shape)
                # else:
                #     print("未知结构:", img)
                # print("=========================")
                
                # 检查图片尺寸是否满足要求
                min_size = 256
                max_size = 2048
                
                # 调整图片尺寸以满足要求
                if width < min_size or height < min_size or width > max_size or height > max_size:
                    # 计算缩放因子
                    scale_factor = 1.0
                    
                    # 处理过小的情况
                    if width < min_size or height < min_size:
                        scale_factor = max(min_size / width, min_size / height)
                    
                    # 处理过大的情况
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)
                    if new_width > max_size or new_height > max_size:
                        scale_factor = min(max_size / width, max_size / height)
                    
                    # 计算新的尺寸
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)
                    print(f"调整图片尺寸至: {new_width}x{new_height}")
                    
                    # 转换并调整尺寸
                    pil_img = ImageConverter.tensor2pil(img)
                    pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    img = ImageConverter.pil2tensor(pil_img)
                else:
                    new_width = width
                    new_height = height

                # 如果宽高*multiple大于10240，就直接原图输出
                if new_width * multiple > 10240 or new_height * multiple > 10240:
                    print(f"图片尺寸 {new_width}x{new_height} 超过最大限制 10240x10240，直接输出原图")
                    api_tensors.append(img)
                    continue


                res_url = call(img)
                response = requests.get(res_url)
                response.raise_for_status()
                # 将图片数据转换为 PIL 图像对象
                img = Image.open(BytesIO(response.content)).convert("RGB")
                api_tensors.append(ImageConverter.pil2tensor(img))
            except Exception as e:
                error_tensor = ImageConverter.create_error_image("下载图片失败")
                api_tensors.append(error_tensor)

        if not api_tensors:
            error_tensor = ImageConverter.create_error_image("未获取到有效图片 URL")
            api_tensors.append(error_tensor)

        return (torch.cat(api_tensors, dim=0),)


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
    "ViduNode": ViduNode,
    "GeminiEditNode": GeminiEditNode,
    "ReplaceClothesNode": ReplaceClothesNode,
    "DoubaoSeedreamNode": DoubaoSeedreamNode,
    "ModelGenNode": ModelGenNode,
    "MoterPoseNode": MoterPoseNode,
    "ViduT2VNode": ViduT2VNode,
    "ViduI2VNode": ViduI2VNode,
    "ImageUpscaleNode": ImageUpscaleNode,
    "ImageTranslateNode": ImageTranslateNode,

}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DreaminaI2INode": "Dreamina参考生图",
    "FluxProNode": "Flux-Kontext-pro",
    "FluxMaxNode": "Flux-Kontext-max",
    "ReplaceNode": "Redux迁移",
    "SeedEdit3": "seededit_v3.0",
    "KouTuNode": "自动抠图",
    "DreaminaT2VNode": "Seedance文生视频",
    "DreaminaI2VNode": "Seedance图生视频",
    "QwenImageNode": "Qwen-image文生图",
    "QwenImageEditNode": "Qwen-image-edit图片编辑",
    "GetDressing": "AI服装提取",
    "ViduNode": "Vidu参考生视频",
    "GeminiEditNode": "Gemini-NanoBanana图片编辑",
    "ReplaceClothesNode": "AI同款服装替换",
    "DoubaoSeedreamNode": "seedream-4.0",
    "ModelGenNode": "服装模特生成",
    "MoterPoseNode": "模特姿势更改",
    "ViduT2VNode": "Vidu文生视频",
    "ViduI2VNode": "Vidu首尾帧视频",
    "ImageUpscaleNode": "高清放大",
    "ImageTranslateNode": "图片翻译",
}
