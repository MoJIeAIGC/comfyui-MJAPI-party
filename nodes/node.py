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
    CATEGORY = "🎨MJapiparty/ImageCreat"

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
    CATEGORY = "🎨MJapiparty/ImageCreat"

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
                "duration": ("INT", {"default": 5, "min": 1, "max": 8}),
                "resolution": ([ "720p", "1080p"], {"default": "1080p"}),
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

    def generate(self, prompt, seed, duration=5, resolution="1080p", Size="16:9", movement_amplitude="auto", bgm=False):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api(seed_override):
            payload = {
                "model": "vidut2vNode",
                "modelr": "viduq2",
                "prompt": prompt,
                "seed": int(seed_override),
                "resolution": resolution,
                "aspect_ratio": Size,
                "duration": duration,
                "movement_amplitude": movement_amplitude,
                "bgm": bgm,
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
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "duration": ("INT", {"default": 5, "min": 2, "max": 8}),
                "resolution": (["720p", "1080p"], {"default": "1080p"}),
                "movement_amplitude": (["auto", "small", "medium", "large"], {"default": "auto"}),
                "bgm": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
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

    def generate(self, prompt,  seed,duration=5, resolution="1080p", Size="16:9", movement_amplitude="auto", bgm=False, first_image=None, last_image=None):
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
                "modelr": "viduq2-turbo",
                "prompt": prompt,
                "seed": int(seed_override),
                "resolution": resolution,
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
    CATEGORY = "🎨MJapiparty/Product&tool"

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
                "aspect_ratio": ([ "16:9", "9:16", "1:1"], {"default": "16:9"}),
                "duration": ("INT", {"default": 5, "min": 1, "max": 8}),
                "resolution": (["720p", "1080p"], {"default": "1080p"}),
                "movement_amplitude": (["auto", "small", "medium", "large"], {"default": "auto"}),
                "seed": ("INT", {"default": -1}),
                "images": ("IMAGE", {"default": []})  # 接收多个图片
            }
        }

    RETURN_TYPES = ("VIDEO",)  # 返回VIDEO类型
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/VideoCreat"

    def generate(self, prompt, seed, aspect_ratio="16:9", duration=5, resolution="1080p", movement_amplitude="auto", images=[]):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api(seed_override, binary_data_base64):
            payload = {
                "model": "vidu_video",
                "modelr": "viduq2",
                "aspect_ratio": aspect_ratio,
                "prompt": prompt,
                "duration": duration,
                "seed": 0,
                "images": binary_data_base64,  # 添加Base64编码的图片数据
                "resolution": resolution,
                "movement_amplitude": movement_amplitude,
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
    CATEGORY = "🎨MJapiparty/Product&tool"

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


        imput_image = []
        imput_image.append(ImageConverter.tensor_to_base64(model_image))
        imput_image.append(ImageConverter.tensor_to_base64(cloths_image))

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
            "input_image": imput_image,
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
                "mount": ("INT", {"default": 1, "min": 1, "max": 4}),  # 生成张数
                "seed": ("INT", {"default": -1}),
            },
            "optional": {
                "image_input": ("IMAGE", {"default": []}),  # 可选的图像输入
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/ImageCreat"

    def generate(self, prompt, seed, image_input=[], is_translation=False, Size="3:4", mount=1):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api(seed_override):
            payload = {
                "model": "gemini-2.5-flash-image",
                "prompt": prompt,
                "is_translation": is_translation,  # 传递翻译模式参数
                "aspect_ratio": Size,  # 传递尺寸参数
                "mount": mount,  # 生成张数
                "seed": int(seed_override),
            }
            # 如果有图像输入，加入到payload中
            if len(image_input) > 0:
                binary_data_base64 = ImageConverter.convert_images_to_base64(image_input)
                payload["input_image"] = binary_data_base64

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=1200)
            # 判断状态码是否为 200
            print(f"Gemini API 响应状态码: {response.status_code}")
            if response.status_code != 200:
                raise requests.exceptions.HTTPError(f"Request failed with status code {response.status_code}: {response.text}")
                # error_msg = ImageConverter.get_status_error_msg(response)
                # error_tensor = ImageConverter.create_error_image(error_msg, width=512, height=512)
                # return (torch.cat(error_tensor, dim=0),)
            response.raise_for_status()
            result = response.json()

            # 从返回的结果中提取图片 URL
            image_url = result.get("res_url")

            if not image_url:
                raise ValueError("未找到图片 URL")
            image_urls = image_url.split("|") if image_url else []

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

        try:
            return call_api(seed + 666)

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
            "model": "doubao-seedream-4.5",
            "prompt": prompt,
            "size": resl_size, 
            "seed": int(seed+6),
            "watermark": False,
            "max_SetImage": count,
            "pro": True,
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
                "style_prompt": (style_prompt, {"default": "通用-INS自拍"}),
                "seed": ("INT", {"default": -1}),
                "Size": (["1:1", "3:4", "9:16"], {"default": "3:4"}),
            },
            "optional": {
                "face_image": ("IMAGE", {"default": None}),  # 可选的图像输入
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Product&tool"

    def generate(self , seed, face_image=None, cloths_image=None,race_class="Asia",gender_class="woman",style_prompt="INS自拍风",Size="3:4"):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        cloths_image_base64 = ImageConverter.tensor_to_base64(cloths_image)

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
                "aspect_ratio": Size,  # 传递尺寸参数
                "cloths_image": cloths_image_base64
            }
            if face_image is not None:
                face_image_base64 = ImageConverter.tensor_to_base64(face_image)
                payload["face_image"] = face_image_base64


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
            # img = ImageConverter.crop_white_borders(img)
            return ImageConverter.pil2tensor(img)

        output_tensors = []

        try:
            for i in range(1):
                # 如果两次请求用同一个seed也行，可改为 seed+i 实现不同seed
                img = call_api(seed + i)
                # 直接调用导入的 pil2tensor 函数
                # tensor_img = ImageConverter.pil2tensor(img)
                output_tensors.append(img)
                print(f"MojieClothesAPI 第 {i+1} 张图片生成成功")

            return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)

        except Exception as e:
            print(f"MojieClothesAPI: {str(e)}")
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
                "out_batch": ("INT", {"default": 1, "min": 1, "max": 4}),  # 生成张数
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Product&tool"

    def generate(self,  seed, image_input=None, extent_prompt=False,out_batch=1):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def call_api(seed_override):
            payload = {
                "model": "moter-pose-change",
                "extent_prompt": extent_prompt,  # 传递翻译模式参数
                "seed": int(seed_override),
                "watermark": False,
                "mount": out_batch,
                "input_image": ImageConverter.tensor_to_base64(image_input)
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=1200)
            # 判断状态码是否为 200
            if response.status_code != 200:
                raise requests.exceptions.HTTPError(f"Request failed with status code {response.status_code}: {response.text}")
                # error_msg = ImageConverter.get_status_error_msg(response)
                # error_tensor = ImageConverter.create_error_image(error_msg, width=512, height=512)
                # return error_tensor
            response.raise_for_status()
            result = response.json()

            # 从返回的结果中提取图片 URL
            image_url = result.get("res_url")

            if not image_url:
                raise ValueError("未找到图片 URL")
            image_urls = image_url.split("|") if image_url else []

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

        try:
            return call_api(seed + 666)
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
                "TargetLang": (["英语","中文", "中文 (繁体)",   "日语", "韩语", "阿拉伯语", "葡萄牙语", "法语", "德语", "西班牙语", "印尼语", "意大利语", "马来语", "俄语", "泰语", "越南语"], {"default": "英语"}),
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
                    print(f"图片尺寸 {new_width}x{new_height} 超过最大限制 10240x10240,直接输出原图")
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


class FurniturePhotoNode:
    @classmethod
    def INPUT_TYPES(cls):
        url = "http://admin.qihuaimage.com/items/furniture_style"
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        
        # 处理数据：创建去重的parentname列表和以parentname为键的字典
        data = result.get('data', [])
        
        # 创建去重的parentname列表
        parentname_list = list(set(item['parentname'] for item in data))
        parentname_list.sort()  # 排序
        
        # 创建以parentname为键，typename列表为值的字典
        parentname_dict = {}
        typename_list = []
        for item in data:
            typename = item['typename']
            if typename not in typename_list:
                typename_list.append(typename)
            parentname = item['parentname']
            typename = item['typename']
            if parentname not in parentname_dict:
                parentname_dict[parentname] = []
            parentname_dict[parentname].append(typename)
        
        # print("去重的parentname列表:", parentname_list)
        # print("parentname字典:", parentname_dict)
        
        return {
            "required": {
                "input_image": ("IMAGE",),  # 接收多个图片
                "furniture_types": (parentname_list, {"default": parentname_list[0]}),
                "style_type": (typename_list, {"default": typename_list[0]}),
                # "resolution": (["1K", "2K", "4K"], {"default": "2K"}),
                "aspect_ratio": (["16:9","4:3","1:1", "3:4",  "9:16"], {"default": "4:3"}),
                "num_images": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Product&tool"

    def generate(self, seed, input_image, resolution="1K", aspect_ratio="4:3", num_images=1, furniture_types="", style_type=""):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()
        input_image_base64 = ImageConverter.tensor_to_base64(input_image)
        def call_api(seed_override):
            payload = {
                "model": "furniture-photo",
                "resolution": "2K",
                "aspect_ratio": aspect_ratio,
                "num_images": num_images,
                "furniture_types": furniture_types,
                "style_type": style_type,
                "seed": int(seed_override),
                "input_image": [input_image_base64],
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=240)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print(f"HTTP错误: {e}")
                print(f"响应内容: {response.text}")
                
                # 尝试解析错误信息
                try:
                    response_data = response.json()
                    if "error" in response_data and "message" in response_data["error"]:
                        error_message = response_data["error"]["message"]
                        # 提取JSON部分（去除request id等额外信息）
                        import re
                        json_match = re.search(r'\{.*\}', error_message)
                        if json_match:
                            json_str = json_match.group(0)
                            import json
                            error_json = json.loads(json_str)
                            if "error" in error_json:
                                print(f"具体错误: {error_json['error']}")
                                if error_json["error"]:
                                    error_msg = error_json["error"]
                                else:
                                    error_msg = "server error,please try again laters"
                                error_tensor = ImageConverter.create_error_image(error_msg, 1024, 1024)
                                output_tensors.append(error_tensor)
                                return
                    raise
                except:
                    # 如果解析失败，忽略错误
                    error_msg = "server error,please try again laters"
                    error_tensor = ImageConverter.create_error_image(error_msg, 1024, 1024)
                    output_tensors.append(error_tensor)
                    return

            result = response.json()
            # print(result)
            image_url = result.get("res_url")

            if not image_url:
                raise ValueError("未找到图片 URL")

            image_urls = image_url.split("|") if image_url else []

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
                    output_tensors.append(ImageConverter.pil2tensor(img))
                except Exception as e:
                    print(f"下载图片 {image_url} 失败: {str(e)}")
                    error_tensor = ImageConverter.create_error_image("下载图片失败")
                    output_tensors.append(error_tensor)
            if not output_tensors:
                error_tensor = ImageConverter.create_error_image("未获取到有效图片 URL")
                output_tensors.append(error_tensor)
        output_tensors = []

        # 调用API
        call_api(seed)

        return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)


class DetailPhotoNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_image": ("IMAGE",),  # 接收多个图片
                "mask": ("MASK",),  # 输入遮罩
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Product&tool"

    def generate(self, seed, input_image=None, mask=None, num_images=1):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()
        if input_image is not None:
            # 将张量转换为PIL图像以获取尺寸
            pil_image = ImageConverter.tensor2pil(input_image)
            width, height = pil_image.size
            # print(f"原始图片尺寸: 宽度={width}, 高度={height}")
            
            # 检查并调整图片尺寸，确保宽高在1280到4096之间
            min_size, max_size = 1280, 4096
            needs_resize = False
            scale_factor = 1.0
            
            # 如果宽度或高度小于最小值，需要放大
            if width < min_size or height < min_size:
                # 计算放大比例，取两个方向中较大的比例
                scale_factor = max(min_size / width, min_size / height)
                needs_resize = True
            
            # 如果宽度或高度大于最大值，需要缩小
            elif width > max_size or height > max_size:
                # 计算缩小比例，取两个方向中较小的比例
                scale_factor = min(max_size / width, max_size / height)
                needs_resize = True
            
            # 如果需要调整尺寸
            if needs_resize:
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                #print(f"调整图片尺寸: 宽度={new_width}, 高度={new_height}, 缩放比例={scale_factor:.2f}")
                
                # 使用LANCZOS重采样方法进行高质量缩放
                pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                
                # 将调整后的PIL图像转换回张量
                input_image = ImageConverter.pil2tensor(pil_image)
            
            # 获取最终尺寸用于API请求
            final_width, final_height = pil_image.size
            size = f"{final_width}x{final_height}"
            # print(f"最终图片尺寸: {size}")
        # 合并图像和遮罩
        merged_image = ImageConverter.highlight_mask_with_rectangle(input_image, mask)

        payload = {
            "model": "detail-photo",
            "seed": int(seed+6),
            "watermark": False,
            "max_SetImage": num_images,
            "input_image": [merged_image],
            "DetailPhoto": True,
            "size": size,
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



class DetailJinNode:
    @classmethod
    def INPUT_TYPES(cls):
        url = "http://admin.qihuaimage.com/items/furn_cai"
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        data = result.get('data', [])
        Polished_list = list(set(item['name'] for item in data))
        return {
            "required": {
                "input_image": ("IMAGE",),  # 接收多个图片
                "Polished_type": (Polished_list, {"default": Polished_list[0]}),
                "num_images": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Product&tool"

    def generate(self, seed, input_image=None,Polished_type="金属&木纹",num_images=1):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()
        
        # 获取图片的长宽
        if input_image is not None:
            # 将张量转换为PIL图像以获取尺寸
            pil_image = ImageConverter.tensor2pil(input_image)
            width, height = pil_image.size
            # print(f"原始图片尺寸: 宽度={width}, 高度={height}")
            
            # 检查并调整图片尺寸，确保宽高在1280到4096之间
            min_size, max_size = 1280, 4096
            needs_resize = False
            scale_factor = 1.0
            
            # 如果宽度或高度小于最小值，需要放大
            if width < min_size or height < min_size:
                # 计算放大比例，取两个方向中较大的比例
                scale_factor = max(min_size / width, min_size / height)
                needs_resize = True
            
            # 如果宽度或高度大于最大值，需要缩小
            elif width > max_size or height > max_size:
                # 计算缩小比例，取两个方向中较小的比例
                scale_factor = min(max_size / width, max_size / height)
                needs_resize = True
            
            # 如果需要调整尺寸
            if needs_resize:
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                # print(f"调整图片尺寸: 宽度={new_width}, 高度={new_height}, 缩放比例={scale_factor:.2f}")
                
                # 使用LANCZOS重采样方法进行高质量缩放
                pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                
                # 将调整后的PIL图像转换回张量
                input_image = ImageConverter.pil2tensor(pil_image)
            
            # 获取最终尺寸用于API请求
            final_width, final_height = pil_image.size
            size = f"{final_width}x{final_height}"
            # print(f"最终图片尺寸: {size}")
        
        merged_image = ImageConverter.tensor_to_base64(input_image)

        payload = {
            "model": "detail-jin",
            "seed": int(seed+6),
            "max_SetImage": num_images,
            "input_image": [merged_image],
            "Polished-type": Polished_type,
            "size": size,
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




class FurnitureAngleNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_image": ("IMAGE",),  # 接收多个图片
                "angle_type": (["4k-俯视45度","4K-正视角","4k-顶视图","4K-对角线拍摄","1k-左侧垂直视图","1k-右侧垂直视图"], {"default": "2k-俯视45度"}),
                "seed": ("INT", {"default": -1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/Product&tool"

    def generate(self, seed, input_image=None,angle_type="2k-俯视45度",num_images=1):
        # 初始化默认宽高
        width = 1024
        height = 1024
        
        # 从input_image中获取宽高
        if input_image is not None:
            # 将张量转换为PIL图像
            pil_image = ImageConverter.tensor2pil(input_image)
            if pil_image is not None:
                width = pil_image.width
                height = pil_image.height
        
        min_pixels = 3986400  # 2560x1440
        max_pixels = 16777216  # 4096x4096
        
        # 计算当前总像素数
        current_pixels = width * height
        
        # 1. 首先处理总像素数不满足的情况
        if current_pixels < min_pixels:
            scale_ratio = (min_pixels / current_pixels) ** 0.5
            width = int(width * scale_ratio)
            height = int(height * scale_ratio)
            current_pixels = width * height  # 更新当前像素数

        if current_pixels > max_pixels:
            # 需要缩小，计算缩小比例
            scale_ratio = (max_pixels / current_pixels) ** 0.5
            width = int(width * scale_ratio)
            height = int(height * scale_ratio)
            current_pixels = width * height  # 更新当前像素数
        
        # print("处理后的图片宽高",f"{width}x{height}")
            

                
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()
        # 合并图像和遮罩
        merged_image = ImageConverter.tensor_to_base64(input_image)
        
        def cell(num):
            payload = {
                "model": "furniture-angle",
                "input_image": [merged_image],
                "angle_type": angle_type,
                "seed": int(seed+num),
                "watermark": False,
                "max_SetImage": num_images,
                "pro": True,
                "size": f"{width}x{height}",
            }

            if "1k" in angle_type:
                payload["model"] = "multiple-angles"
                payload["input_image"] = [merged_image]
                payload["rotate_right_left"] = float(-90) if "右侧" in angle_type else float(90)
                payload["num_images"] = num_images

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
        api_tensors = []
        cell(1)
        if "2k" in angle_type and num_images == 2:
            cell(2)
        if not api_tensors:
            error_tensor = ImageConverter.create_error_image("未获取到有效图片 URL")
            api_tensors.append(error_tensor)

        return (torch.cat(api_tensors, dim=0),)




class NanoProNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset", "multiline": True}),
                "is_translation": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                # "limit_generations": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "resolution": (["1K", "2K", "4K"], {"default": "2K"}),
                "aspect_ratio": (["auto","16:9","4:3","2:3","4:5","1:1","3:2","5:4","3:4", "9:16"], {"default": "auto"}),
                "num_images": ("INT", {"default": 1, "min": 1, "max": 2}),  # 新增参数，只能是1或2
                "seed": ("INT", {"default": -1}),
            },
            "optional": {
                "input_images": ("IMAGE",),  # 接收多个图片
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/ImageCreat"

    def generate(self, seed, input_images=None, resolution="1K", aspect_ratio="auto", is_translation=False, limit_generations=False, prompt="", num_images=1):
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()
        def call_api(seed_override):
            payload = {
                "model": "nano-banana-pro",
                "resolution": resolution,
                "aspect_ratio": aspect_ratio,
                "prompt": prompt,
                "is_translation": is_translation,
                "limit_generations": limit_generations,
                "seed": int(seed_override),
                "num_images": int(num_images),
            }
            if input_images is None and aspect_ratio == "auto":
                payload["aspect_ratio"] = "1:1"
            if input_images is not None:
                # 检查图像长边是否大于1280，如果是则等比压缩
                compressed_images = []
                for img in input_images:
                    # 将张量转换为PIL图像
                    pil_image = ImageConverter.tensor2pil(img)
                    if pil_image is not None:
                        # 检查长边
                        width, height = pil_image.size
                        max_size = max(width, height)
                        
                        if max_size > 1280:
                            # 计算缩放比例
                            scale = 1280 / max_size
                            new_width = int(width * scale)
                            new_height = int(height * scale)
                            # 使用高质量的重采样方法进行缩放
                            pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                        
                        # 将处理后的图像转换回张量
                        compressed_tensor = ImageConverter.pil2tensor(pil_image)
                        compressed_images.append(compressed_tensor)
                
                input_image_base64 = ImageConverter.convert_images_to_base64(compressed_images)
                payload["input_image"] = input_image_base64
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=240)

            response.raise_for_status()

            result = response.json()
            image_url = result.get("res_url")

            if not image_url:
                raise ValueError("未找到图片 URL")

            image_urls = image_url.split("|") if image_url else []

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
                    output_tensors.append(ImageConverter.pil2tensor(img))
                except Exception as e:
                    print(f"下载图片 {image_url} 失败: {str(e)}")
                    error_tensor = ImageConverter.create_error_image("下载图片失败")
                    output_tensors.append(error_tensor)
            if not output_tensors:
                error_tensor = ImageConverter.create_error_image("未获取到有效图片 URL")
                output_tensors.append(error_tensor)
        output_tensors = []

        # 调用API
        call_api(seed)

        return (torch.cat(output_tensors, dim=0),)  # 拼接为 (数量, H, W, 3)



class Flux2Node:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "A beautiful sunset", "multiline": True}),
                "is_translation": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "aspect_ratio": (["auto","16:9","4:3","1:1", "3:4",  "9:16"], {"default": "auto"}),
                "custom_size": ("BOOLEAN", {"default": False}),  # 自定义尺寸开关
                "width": ("INT", {"default": 1024, "min": 1024, "max": 2048}),  # 生成张数
                "height": ("INT", {"default": 1024, "min": 1024, "max": 2048}),  # 生成张数
                "seed": ("INT", {"default": -1}),
            },
            "optional": {
                "input_images": ("IMAGE",),  # 接收多个图片
            }
        }

    RETURN_TYPES = ("IMAGE",)  # 返回一个或多个IMAGE
    RETURN_NAMES = ("output",)  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/ImageCreat"

    def generate(self, seed, input_images=None,prompt="",num_images=1,is_translation=False,aspect_ratio="auto",custom_size=False,width=1024,height=1024):
        # 调用配置管理器获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()

        def cell(num):
            payload = {
                "model": "flux2",
                "prompt": prompt,
                "num_images": num_images,
                "is_translation": is_translation,
                "aspect_ratio": aspect_ratio,
                "seed": int(seed+num),
            }
            if custom_size:
                payload["width"] = width
                payload["height"] = height
            if input_images is None and aspect_ratio == "auto":
                payload["aspect_ratio"] = "4:3"
            if input_images is not None:
                input_image_base64 = ImageConverter.convert_images_to_base64(input_images)
                payload["input_image"] = input_image_base64

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
        api_tensors = []
        cell(1)
        if not api_tensors:
            error_tensor = ImageConverter.create_error_image("未获取到有效图片 URL")
            api_tensors.append(error_tensor)

        return (torch.cat(api_tensors, dim=0),)


# 确保ComfyUI的核心模块能被导入
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from typing import Any, Dict, List
# ComfyUI核心节点基类（不同版本路径可能略有差异）
try:
    from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
except ImportError:
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}

# --------------------------
# 基础文件加载节点（解决FILE输入问题）
# --------------------------
class FileLoaderNode:
    """文件加载节点：点击弹出系统文件选择框，支持docx/pdf等文件"""
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "file_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "widget": "string",  # 使用标准string widget，配合JavaScript添加上传按钮
                    "placeholder": "文件路径或点击上传按钮选择文件"
                }),
            }
        }

    RETURN_TYPES = ("FILE",)
    RETURN_NAMES = ("file",)
    FUNCTION = "load_file"
    CATEGORY = "🎨MJapiparty/LLM"
    DISPLAY_NAME = "文件加载器（PDF/Word）"

    def load_file(self, file_path: str) -> tuple:
        if not os.path.exists(file_path):
            raise ValueError(f"文件不存在：{file_path}")
        allowed_extensions = (".docx", ".pdf", ".doc")
        if not file_path.lower().endswith(allowed_extensions):
            raise ValueError(f"仅支持以下文件类型：{allowed_extensions}")
        return (file_path,)




class GeminiLLMNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", ),
                # "limit_generations": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "model": (["Gemini 3 Pro Preview", "Gemini 3 Flash Preview"], {"default": "Gemini 3 Flash Preview"}),  # 值需和后端 MODEL_MAPPING 的 key 完全一致
                "media_resolution": (["Default","Low","Medium","High"], {"default": "Default"}),  # 值需和后端 RESOLUTION_MAPPING 的 key 完全一致
                "thinking_level": (["Minimal","Low","Medium","High"], {"default": "High"}),  # 值需和后端 THINKING_LEVEL_MAPPING 的 key 完全一致
                "System_prompt": ("STRING", {"default": ""}),
                "Web_search": ("BOOLEAN", {"default": True}),  # 是否是翻译模式
                "format": ("BOOLEAN", {"default": False}),  # 是否是翻译模式
                "seed": ("INT", {"default": -1}),
            },
            "optional": {
                "image_input": ("IMAGE",),  # 支持多输入，传递时会转为 base64 列表
                "video": ("VIDEO",),  # 支持多输入，传递时会转为 base64 列表（拆帧后）
                "file": ("FILE",),  # 支持多输入，传递时会转为 base64 列表
                "context": ("ANY",),  # 接收对话历史上下文数据
            }
        }

    # 返回字符串文本
    RETURN_TYPES = ("STRING","ANY")  # 返回一个或多个STRING
    RETURN_NAMES = ("output","context")  # 保持为一个返回名
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/LLM"


    def generate(self, seed, prompt="", model="Gemini 3 Flash Preview Free", media_resolution="Default", thinking_level="High", System_prompt="", Web_search=True, format=False, image_input=None, video=None, file=None, context=None):
        # 输入非空校验 - 更严格地检查prompt是否为空
        prompt_stripped = prompt.strip() if prompt else ""
        if not prompt_stripped and not image_input and not video and not file:
            return ("错误：至少需要输入文本、图片、视频或文件中的一种",)

        if context is not None:
            conversation_history = context.get("llm", [])
        else:
            conversation_history = []

        # 参数值校验
        valid_models = ["Gemini 3 Pro Preview", "Gemini 3 Flash Preview", "Gemini 3 Flash Preview Free"]
        valid_resolutions = ["Default", "Low", "Medium", "High"]
        valid_thinking_levels = ["Minimal", "Low", "Medium", "High"]
        
        if model not in valid_models:
            return (f"错误：无效的模型选择，可选值为：{', '.join(valid_models)}",)
        
        if media_resolution not in valid_resolutions:
            return (f"错误：无效的分辨率选择，可选值为：{', '.join(valid_resolutions)}",)
        
        if thinking_level not in valid_thinking_levels:
            return (f"错误：无效的思维水平选择，可选值为：{', '.join(valid_thinking_levels)}",)
        
        # 获取配置
        oneapi_url, oneapi_token = config_manager.get_api_config()
        # 处理图片输入
        input_image_base64 = None
        if image_input is not None:
            try:
                input_image_base64 = ImageConverter.convert_images_to_base64(image_input)
                if not input_image_base64:
                    return ("错误：图片转换为base64失败",)
            except Exception as e:
                return (f"错误：图片处理失败：{str(e)}",)
        
        # 处理视频输入
        video_base64 = None
        if video is not None:
            try:
                # 确保video是列表形式
                video_list = [video] if not isinstance(video, list) else video
                video_base64 = ImageConverter.video_to_full_base64_list(video_list)
                if not video_base64:
                    return ("错误：视频转帧或base64转换失败",)
            except Exception as e:
                return (f"错误：视频处理失败：{str(e)}",)
        
        # 处理文件输入
        file_base64 = None
        if file is not None:
            try:
                # 确保file是列表形式
                file_list = [file] if not isinstance(file, list) else file
                file_base64 = ImageConverter.files_to_base64_list(file_list)
                if not file_base64:
                    return ("错误：文件转base64失败",)
            except Exception as e:
                return (f"错误：文件处理失败：{str(e)}",)
        
        # 记录处理的媒体文件数量
        print(f"处理媒体文件数量: 图片{len(input_image_base64) if input_image_base64 else 0}张, 视频帧{len(video_base64) if video_base64 else 0}帧, 文件{len(file_base64) if file_base64 else 0}个")
        
        def call_api(seed_override):
            MODEL_MAPPING = {
                "Gemini 3 Pro Preview": "Gemini-3-Pro-Preview",
                "Gemini 3 Flash Preview": "Gemini-3-Flash-Preview",
            }
            modelr = MODEL_MAPPING.get(model, model)
            print("=== 准备调用API ===")
            # 构建payload，包含所有参数
            nonlocal conversation_history  # 允许在内部函数中修改外部变量
            payload = {
                "model": modelr,
                "prompt": prompt,
                "seed": int(seed_override),
                "model_type": model,
                "media_resolution": media_resolution,
                "thinking_level": thinking_level,
                "system_prompt": System_prompt,
                "web_search": Web_search,
                "format": format,
                "conversation_history": conversation_history,
            }
            
            # 添加图片输入（如果有）
            if input_image_base64 is not None:
                payload["input_image"] = input_image_base64
                print(f"API请求包含图片: {len(input_image_base64)}张")
            
            # 添加视频输入（如果有）
            if video_base64 is not None:
                payload["video"] = video_base64
                print(f"API请求包含视频帧: {len(video_base64)}帧")
            
            # 添加文件输入（如果有）
            if file_base64 is not None:
                payload["file"] = file_base64
                print(f"API请求包含文件: {len(file_base64)}个")
            
            # 日志：打印API请求基本信息（不包含大的base64数据）
            payload_info = {
                "model": payload["model"],
                "model_type": payload["model_type"],
                "seed": payload["seed"],
                "has_prompt": bool(payload["prompt"].strip()),
                "has_system_prompt": bool(payload["system_prompt"].strip()),
                "web_search": payload["web_search"],
                "format": payload["format"],
                "media_resolution": payload["media_resolution"],
                "thinking_level": payload["thinking_level"],
                "has_images": "input_image" in payload,
                "has_videos": "video" in payload,
                "has_files": "file" in payload
            }
            print(f"API请求参数: {payload_info}")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oneapi_token}"
            }
            print(f"正在调用API: {oneapi_url}")
            print(f"API调用超时设置: 240秒")
            response = requests.post(oneapi_url, headers=headers, json=payload, timeout=240)
            print(f"API调用完成，状态码: {response.status_code}")

            response.raise_for_status()

            result = response.json()
            print(f"API响应结构: {list(result.keys())}")
            restext = result.get("restext", "")
            conversation_history = result.get("conversation_history", [])  # 提取对话历史
            if conversation_history:
                # print(f"API返回对话历史: {conversation_history}")
                ImageConverter.conversation_context["llm"] = conversation_history
                conversation_history = {
                    "llm": conversation_history
                }
                # print("ContextNode 保存对话历史:", ImageConverter.conversation_context)
            
            if not restext:
                print("警告：API响应中restext字段为空")
                restext = "未找到响应文本"
            else:
                print(f"API返回restext，长度: {len(restext)}字符")
            
            return restext
        try:
            print("=== 执行API调用 ===")
            # 调用API
            restext = call_api(seed)
            print("=== GeminiLLMNode 执行完成 ===")
            return (restext,conversation_history)
        except requests.exceptions.RequestException as e:
            print(f"=== API调用失败 ===")
            print(f"错误类型: 请求异常")
            print(f"错误详情: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误状态码: {e.response.status_code}")
                try:
                    error_response = e.response.json()
                    print(f"错误响应内容: {error_response}")
                except:
                    print(f"错误响应文本: {e.response.text[:500]}...")
            # 返回错误信息作为字符串
            return (f"API调用失败: {str(e)}",)
        except Exception as e:
            print(f"=== GeminiLLMNode 执行失败 ===")
            print(f"错误类型: 其他异常")
            print(f"错误详情: {str(e)}")
            # 返回错误信息作为字符串
            return (f"API调用失败: {str(e)}",)




class Gemini3NanoNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", ),
                "model": (["Gemini 2.5 Flash Image", "Gemini-3-pro-image-preview"], {"default": "Gemini 2.5 Flash Image"}),  # 值需和后端 MODEL_MAPPING 的 key 完全一致
                "media_resolution": (["Default","Low","Medium","High"], {"default": "Default"}),  # 值需和后端 RESOLUTION_MAPPING 的 key 完全一致
                "thinking_level": (["minimal","low","medium","high"], {"default": "high"}),  # 值需和后端 THINKING_LEVEL_MAPPING 的 key 完全一致
                "safe_level": (["high","medium","low"], {"default": "medium"}),  # 值需和后端 THINKING_LEVEL_MAPPING 的 key 完全一致
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "aspect_ratio": (["16:9","4:3","2:3","4:5","1:1","3:2","5:4","3:4", "9:16"], {"default": "1:1"}),
                "System_prompt": ("STRING", {"default": ""}),
                "Web_search": ("BOOLEAN", {"default": True}),  # 是否是翻译模式
                "seed": ("INT", {"default": -1}),
            },
            "optional": {
                "input_images": ("IMAGE",),  # 接收多个图片
                "context": ("ANY",),  # 接收对话历史上下文数据
            }
        }

    RETURN_TYPES = ("IMAGE","STRING", "ANY")  # 返回图片和对话历史（ANY类型兼容conversation_history数组）
    RETURN_NAMES = ("image", "text", "context")  # 输出端口名称
    FUNCTION = "generate"
    CATEGORY = "🎨MJapiparty/LLM"

    def generate(self, seed, input_images=None, resolution="1K", aspect_ratio="1:1",  prompt="", safe_level="medium", thinking_level="High", System_prompt="", Web_search=True, model="Gemini 2.5 Flash Image", context=None, media_resolution="Default"):
        # 获取配置
        from PIL import Image
        oneapi_url, oneapi_token = config_manager.get_api_config()
        # 如果没有提供对话历史，初始化为空列表
        if context is not None:
            conversation_history = context.get("image", [])
        else:
            conversation_history = []
        MODEL_MAPPING = {
            "Gemini 2.5 Flash Image": "Gemini2.5-image-Nanobanana",
            "Gemini-3-pro-image-preview": "Gemini3-image-Nanobanana-pro",
        }
        modelr = MODEL_MAPPING.get(model, model)
        output_tensors = []
        payload = {
            "model": modelr,
            "modelr": model,
            "resolution": resolution,
            "media_resolution": media_resolution,
            "prompt": prompt,
            "seed": 666,
            "safe_level": safe_level,
            "System_prompt": System_prompt,
            "Web_search": Web_search,
            "aspect_ratio": aspect_ratio,
            "conversation_history": conversation_history,  # 发送API请求时带上上下文数据
        }
        if model != "Gemini 2.5 Flash Image":
            payload["thinking_level"] = thinking_level 
        if input_images is not None:
            # 检查图像长边是否大于1280，如果是则等比压缩
            compressed_images = []
            for img in input_images:
                # 将张量转换为PIL图像
                pil_image = ImageConverter.tensor2pil(img)
                if pil_image is not None:
                    # 检查长边
                    width, height = pil_image.size
                    max_size = max(width, height)
                    
                    if max_size > 1280:
                        # 计算缩放比例
                        scale = 1280 / max_size
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        # 使用高质量的重采样方法进行缩放
                        pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                    
                    # 将处理后的图像转换回张量
                    compressed_tensor = ImageConverter.pil2tensor(pil_image)
                    compressed_images.append(compressed_tensor)
            
            input_image_base64 = ImageConverter.convert_images_to_base64(compressed_images)
            payload["input_image"] = input_image_base64
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {oneapi_token}"
        }
        response = requests.post(oneapi_url, headers=headers, json=payload, timeout=240)

        response.raise_for_status()

        result = response.json()
        image_url = result.get("res_url")
        restext = result.get("restext","")

        if not image_url:
            if result.get("restext"):
                # 创建一个纯白色的图片
                from PIL import Image
                white_image = Image.new("RGB", (512, 512), (255, 255, 255))
                white_tensor = ImageConverter.pil2tensor(white_image)
                return (white_tensor, result.get("restext"), conversation_history)
            else:
                raise ValueError("模型未回复")

        image_urls = image_url.split("|") if image_url else []
        conversation_history = result.get("conversation_history", [])  # 提取对话历史
        if conversation_history:
            # print(f"API返回对话历史: {conversation_history}")
            ImageConverter.conversation_context["image"] = conversation_history
            conversation_history = {
                "image": conversation_history
            }
            # print("ContextNode 保存对话历史:", ImageConverter.conversation_context)
        print(image_urls)
        for image_url in image_urls:
            if not image_url:
                continue
            try:
                # 下载图片
                response = requests.get(image_url)
                response.raise_for_status()
                # 将图片数据转换为 PIL 图像对象
                from PIL import Image
                img = Image.open(BytesIO(response.content)).convert("RGB")
                output_tensors.append(ImageConverter.pil2tensor(img))
            except Exception as e:
                print(f"下载图片 {image_url} 失败: {str(e)}")
                error_tensor = ImageConverter.create_error_image("下载图片失败")
                output_tensors.append(error_tensor)
        if not output_tensors:
            error_tensor = ImageConverter.create_error_image("未获取到有效图片 URL")
            output_tensors.append(error_tensor)
        return (torch.cat(output_tensors, dim=0),restext,conversation_history)


class ContextNode:
    # ========== 核心强制执行配置（缺一不可） ==========
    OUTPUT_NODE = True       # 标记为输出节点，优先执行
    FORCE_ATTN = True        # 强制ComfyUI关注该节点，无视输出是否被使用
    CACHEABLE = False        # 禁用结果缓存，绝不复用旧结果
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            # ========== 关键：加一个“可变伪输入”（seed），触发节点重新执行 ==========
            "required": {
                "seed": ("INT", {"default": 1, "min": 1, "max": 0xffffffffffffffff}),
            },
            # 保留原有隐藏参数
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT"
            }
        }

    RETURN_TYPES = ("ANY",)
    RETURN_NAMES = ("context",)
    FUNCTION = "read_global_context"
    CATEGORY = "🎨MJapiparty/LLM"
    DESCRIPTION = "读取全局对话上下文并输出（强制每次执行）"

    def read_global_context(self, seed, unique_id=None, prompt=None):
        # 初始化容错：确保ImageConverter有conversation_context属性
        if not hasattr(ImageConverter, 'conversation_context'):
            ImageConverter.conversation_context = []
        
        # 读取最新全局上下文
        conversation_history = ImageConverter.conversation_context
        log_prefix = f"[ContextNode-{unique_id[:8] if unique_id else '未知'}]"
        # 打印日志（验证每次都执行）
        print(f"{log_prefix} 本次传入Gemini的上下文：{len(conversation_history)}条")
        print(f"{log_prefix} 本次执行seed：{seed}")  # 验证seed变化触发执行
        
        # 确保返回合法列表
        return (conversation_history,)

NODE_CLASS_MAPPINGS = {
    "GeminiEditNode": GeminiEditNode,
    "NanoProNode": NanoProNode,
    "Flux2Node": Flux2Node,
    "FluxProNode": FluxProNode,
    "FluxMaxNode": FluxMaxNode,
    "ReplaceNode": ReplaceNode,
    "SeedEdit3": SeedEdit3,
    "DoubaoSeedreamNode": DoubaoSeedreamNode,
    "QwenImageNode": QwenImageNode,
    "QwenImageEditNode": QwenImageEditNode,
    "KouTuNode": KouTuNode,
    "DreaminaT2VNode": DreaminaT2VNode,
    "DreaminaI2VNode": DreaminaI2VNode,
    "GetDressing": GetDressing,
    "ViduNode": ViduNode,
    "ReplaceClothesNode": ReplaceClothesNode,
    "ModelGenNode": ModelGenNode,
    "MoterPoseNode": MoterPoseNode,
    "ViduT2VNode": ViduT2VNode,
    "ContextNode": ContextNode,
    "ViduI2VNode": ViduI2VNode,
    "ImageUpscaleNode": ImageUpscaleNode,
    "ImageTranslateNode": ImageTranslateNode,
    "FurniturePhotoNode": FurniturePhotoNode,
    "DetailPhotoNode": DetailPhotoNode,
    "DetailJinNode": DetailJinNode,
    "FurnitureAngleNode": FurnitureAngleNode, 
    "DreaminaI2INode": DreaminaI2INode,
    "GeminiLLMNode": GeminiLLMNode,
    "Gemini3NanoNode": Gemini3NanoNode,
    "FileLoaderNode": FileLoaderNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GeminiEditNode": "Gemini-Nano-1图片编辑",
    "NanoProNode": "Gemini-Nano-2-pro图片编辑",
    "Flux2Node": "Flux-2-pro",
    "FluxProNode": "Flux-Kontext-pro",
    "FluxMaxNode": "Flux-Kontext-max",
    "SeedEdit3": "seededit_v3.0",
    "DoubaoSeedreamNode": "seedream-v4.5",
    "QwenImageNode": "Qwen-image文生图",
    "QwenImageEditNode": "Qwen-image-edit图片编辑",
    "ReplaceNode": "Redux迁移",
    "KouTuNode": "自动抠图",
    "DreaminaT2VNode": "Seedance文生视频",
    "DreaminaI2VNode": "Seedance图生视频",
    "GetDressing": "AI服装提取",
    "ViduNode": "Vidu参考生视频",
    "ReplaceClothesNode": "AI同款服装替换",
    "ModelGenNode": "服装模特生成",
    "MoterPoseNode": "模特姿势更改",
    "ViduT2VNode": "Vidu文生视频",
    "ViduI2VNode": "Vidu首尾帧视频",
    "ImageUpscaleNode": "高清放大",
    "ImageTranslateNode": "图片翻译",
    "FurniturePhotoNode": "AI家具摄影图",
    "DetailPhotoNode": "局部细节呈现",
    "DetailJinNode": "细节精修",
    "FurnitureAngleNode": "家具角度图",
    "DreaminaI2INode": "Dreamina参考生图",
    "GeminiLLMNode": "Gemini3-LLM",
    "Gemini3NanoNode": "Gemini3-image-Nano",
    "ContextNode": "对话上下文管理",
    "FileLoaderNode": "文件加载器",
}
