import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO
import requests
import logging
from comfy_api.input_impl.video_types import VideoFromFile
class ImageConverter:
    @staticmethod
    def pil2tensor(image):
        img_array = np.array(image).astype(np.float32) / 255.0  # (H, W, 3)
        img_tensor = torch.from_numpy(img_array)[None,]  # (1, H, W, 3)
        return img_tensor

    @staticmethod
    def tensor2pil(tensor):
        try:
            # Tensor (1, H, W, 3) to PIL
            image = tensor.squeeze().numpy() * 255.0
            return Image.fromarray(image.astype(np.uint8))
        except Exception as e:
            return None

    @staticmethod
    def tensor_to_base64(image_tensor):
        """
        将图像张量转换为 base64 编码的字符串

        :param image_tensor: 输入的图像张量
        :return: base64 编码的字符串
        """
        pil_image = ImageConverter.tensor2pil(image_tensor)
        buffered = BytesIO()
        pil_image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    @staticmethod
    def get_status_error_msg(response,cate=0):
        """
        根据响应对象返回对应的错误信息

        :param response: requests.Response对象
        :return: 对应的错误信息字符串
        """
        status_code = response.status_code
        error_msg_map = {
            400: "请求参数错误，请检查输入",
            401: "未授权，请检查 API Token",
            403: "余额不足",
            404: "请求资源不存在",
            500: "服务器繁忙，请稍后再试",
            502: "网关错误",
            503: "服务不可用",
            504: "网关超时"
        }
        error_msg = error_msg_map.get(status_code, f"请求失败，状态码: {status_code}")
        # return error_msg_map.get(status_code, f"请求失败，状态码: {status_code}")

        if cate == 1:
            try:
                error_data = response.json()
                error_msg1 = error_data.get("error", {}).get("message", "")
                # 尝试解析嵌套的JSON字符串
                import json
                import re
                try:
                    match = re.search(r'^\{.*\}', error_msg1)
                    if match:
                        json_part = match.group(0)
                        outer = json.loads(json_part)
                        inner_str = outer['error'][2:-1]  # 去掉 b' 和最后的 '
                        inner_json = json.loads(inner_str)
                        error_msg = inner_json['message']
                except:
                    return error_msg
            except:
                pass
        
        return error_msg

    @staticmethod
    def create_error_image(text, width=512, height=512, font_size=40):
        """
        创建一个红色背景的错误图片，并在上面绘制指定的文字。

        :param text: 要显示的错误文字
        :param width: 图片宽度，默认为 512
        :param height: 图片高度，默认为 512
        :param font_size: 字体大小，默认为 20
        :return: 包含错误文字的图片对应的 tensor
        """
        error_img = Image.new("RGB", (width, height), (255, 0, 0))
        try:
            draw = ImageDraw.Draw(error_img)
            try:
                # 尝试加载常见支持中文的字体
                # Windows 系统
                font = ImageFont.truetype("simhei.ttf", font_size)  # 黑体
            except:
                try:
                    # macOS 系统
                    font = ImageFont.truetype("PingFang.ttc", font_size)  # 苹方
                except:
                    try:
                        # Linux 系统
                        font = ImageFont.truetype("WenQuanYi Zen Hei.ttf", font_size)  # 文泉驿正黑
                    except:
                        # 若都失败，使用默认字体
                        font = ImageFont.load_default()

            # 将错误信息分行，避免单行过长
            max_chars_per_line = 30
            lines = []
            for i in range(0, len(text), max_chars_per_line):
                lines.append(text[i:i+max_chars_per_line])

            # 在图像上逐行绘制错误信息
            y_text = 10
            line_height = font_size + 4
            for line in lines:
                draw.text((10, y_text), line, font=font, fill=(255, 255, 255))
                y_text += line_height

        except Exception as font_error:
            print(f"在错误图片上绘制文字时出错: {font_error}")

        return ImageConverter.pil2tensor(error_img)


    @staticmethod
    def merge_image(image,mask):
        imageres = ImageConverter.tensor_to_base64(image)
        if mask is None:
            return imageres
        # 转为 PIL 图像
        image = ImageConverter.tensor2pil(image).convert("RGB")
        mask = ImageConverter.tensor2pil(mask).convert("L")
        if mask is None:
            return ImageConverter.tensor_to_base64(image)

        # 生成 Alpha 通道
        alpha = Image.eval(mask, lambda px: 255 - px)

        # 合并为 RGBA 图像
        try:
            rgba_image = image.convert("RGBA")
            rgba_image.putalpha(alpha)
        except Exception as e:
            return imageres
        # rgba_image.save("E:\\merged_result.png", format="PNG")

        # 将 RGBA 图像转换为 Base64
        buffered = BytesIO()
        rgba_image.save(buffered, format="PNG")  # 保存为 PNG 格式到内存中
        mig_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")  # 转换为 Base64 字符串

        return mig_base64

    @staticmethod
    def download_video(video_url: str, save_path: str = "temp_video.mp4") -> str:
        """
        下载视频文件到本地
        :param video_url: 视频URL
        :param save_path: 本地保存路径
        :return: 本地视频文件路径
        """
        try:
            response = requests.get(video_url, stream=True)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        f.write(chunk)
                logging.info(f"视频下载完成: {save_path}")
                return save_path
            else:
                raise ValueError(f"下载视频失败: {response.status_code}")
        except Exception as e:
            logging.error(f"视频下载出错: {str(e)}")
            raise

    @staticmethod
    def convert_images_to_base64(image_list):
        # 转换图像为Base64编码的字符串数组
        base64_images = []
        for img in image_list:
            img_base64 = ImageConverter.tensor_to_base64(img)
            base64_images.append(img_base64)
        return base64_images
