import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
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
    def prepare_and_stitch_images(model_image, cloth_image):
        """
        准备并拼接模特图和服装图
        1. 模特图(右图)单边超过1280则等比缩小至1280
        2. 服装图(左图)保持原尺寸
        3. 合并左右图，保持等高，短边图等比拉伸
        """
        # 转换模特图为PIL
        model_pil = ImageConverter.tensor2pil(model_image)
        # 转换服装图为PIL
        cloth_pil = ImageConverter.tensor2pil(cloth_image)
        
        # 1. 处理模特图 - 如果单边超过1280则等比缩小
        max_size = 1280
        if max(model_pil.size) > max_size:
            ratio = max_size / max(model_pil.size)
            new_width = int(model_pil.width * ratio)
            new_height = int(model_pil.height * ratio)
            model_pil = model_pil.resize((new_width, new_height), Image.LANCZOS)
        
        # 2. 处理服装图 - 保持原尺寸
        
        # 3. 合并图片 - 保持等高
        # 确定目标高度(取两者中较大的高度)
        target_height = max(model_pil.height, cloth_pil.height)
        
        # 调整模特图高度
        if model_pil.height != target_height:
            ratio = target_height / model_pil.height
            new_width = int(model_pil.width * ratio)
            model_pil = model_pil.resize((new_width, target_height), Image.LANCZOS)
        
        # 调整服装图高度
        if cloth_pil.height != target_height:
            ratio = target_height / cloth_pil.height
            new_width = int(cloth_pil.width * ratio)
            cloth_pil = cloth_pil.resize((new_width, target_height), Image.LANCZOS)
        
        # 创建新图片(宽度为两者之和)
        new_img = Image.new('RGB', (cloth_pil.width + model_pil.width, target_height))
        new_img.paste(cloth_pil, (0, 0))  # 左图
        new_img.paste(model_pil, (cloth_pil.width, 0))  # 右图
        
        # 转换为base64
        buffered = BytesIO()
        new_img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")



    @staticmethod
    def process_images(face_image, cloths_image):
        """
        处理服装图片和脸部图片，根据脸部图片是否存在执行不同的处理逻辑，最后返回 base64 数据。
        :param face_image: 脸部图片
        :param cloths_image: 服装图片
        :return: 处理后图片的 base64 数据
        """
        if face_image is None:
            # 将服装图片转换为 PIL 图像
            cloth_pil = ImageConverter.tensor2pil(cloths_image)
            # 如果单边超过1536则等比缩小至1536
            if max(cloth_pil.size) > 1536:
                ratio = 1536 / max(cloth_pil.size)
                new_width = int(cloth_pil.width * ratio)
                new_height = int(cloth_pil.height * ratio)
                cloth_pil = cloth_pil.resize((new_width, new_height), Image.LANCZOS)

            # 如果是1:1正方形或横向长方形，则上下填充黑色，使高度达到1536
            if cloth_pil.width >= cloth_pil.height:
                if cloth_pil.height < 1536:
                    new_img = Image.new('RGB', (cloth_pil.width, 1536), (0, 0, 0))
                    paste_y = (1536 - cloth_pil.height) // 2
                    new_img.paste(cloth_pil, (0, paste_y))
                    cloth_pil = new_img

            # 转换为 base64
            buffered = BytesIO()
            cloth_pil.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        else:
            # 将人脸和服装图片转换为 PIL 图像
            face_pil = ImageConverter.tensor2pil(face_image)
            cloth_pil = ImageConverter.tensor2pil(cloths_image)

            # 上下合并图片
            new_width = max(face_pil.width, cloth_pil.width)
            new_height = face_pil.height + cloth_pil.height
            new_img = Image.new('RGB', (new_width, new_height), (0, 0, 0))
            new_img.paste(face_pil, ((new_width - face_pil.width) // 2, 0))
            new_img.paste(cloth_pil, ((new_width - cloth_pil.width) // 2, face_pil.height))

            # 再次缩小图片尺寸最大不超过1536，长宽比不超过4:1
            if max(new_img.size) > 1536:
                ratio = 1536 / max(new_img.size)
                new_width = int(new_img.width * ratio)
                new_height = int(new_img.height * ratio)
                new_img = new_img.resize((new_width, new_height), Image.LANCZOS)

            width, height = new_img.size
            if width / height > 4:
                new_width = int(height * 4)
                new_img = new_img.resize((new_width, height), Image.LANCZOS)
            elif height / width > 4:
                new_height = int(width * 4)
                new_img = new_img.resize((width, new_height), Image.LANCZOS)

            # 转换为 base64
            buffered = BytesIO()
            new_img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")

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
            400: "请求参数错误，请检查输入 (Bad request, check input)",
            401: "未授权，请检查 API Token (Unauthorized, check API Token)",
            403: "权限不足，请检查余额或令牌权限 (Forbidden, check balance or permissions)",
            404: "请求资源不存在 (Resource not found)",
            500: "服务器繁忙，请稍后再试 (Server busy, try later)",
            502: "网关错误 (Bad gateway)",
            503: "服务不可用 (Service unavailable)",
            504: "网关超时 (Gateway timeout)"
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
        
        error_data = response.json()
        print("Error data:", error_data)  # 调试输出
        print("Error type:", type(error_data.get("error")))  # 调试输出
        if error_data.get("error") and type(error_data.get("error")) is not dict:
            error_msg = error_data.get("error")
        
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

            # 根据图片宽度和字体大小计算每行最大字符数
            max_chars_per_line = width // (font_size // 2)  # 根据字体大小动态计算
            max_chars_per_line = max(20, min(max_chars_per_line, 50))  # 限制在20-50字符之间
            
            # 将错误信息分行，避免单行过长
            lines = []
            words = text.split()
            current_line = ""
            
            for word in words:
                if len(current_line + word) <= max_chars_per_line:
                    current_line += word + " "
                else:
                    lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())

            # 在图像上逐行绘制错误信息
            y_text = 10
            line_height = font_size + 4
            max_lines = (height - 20) // line_height  # 计算图片能容纳的最大行数
            
            for line in lines[:max_lines]:  # 只显示能容纳的行数
                draw.text((10, y_text), line, font=font, fill=(255, 255, 255))
                y_text += line_height

        except Exception as font_error:
            print(f"在错误图片上绘制文字时出错: {font_error}")

        return ImageConverter.pil2tensor(error_img)


    @staticmethod
    def merge_image(image, mask):
        imageres = ImageConverter.tensor_to_base64(image)
        if mask is None:
            return imageres

        # 转 PIL
        image = ImageConverter.tensor2pil(image).convert("RGB")  # 保留原图
        mask = ImageConverter.tensor2pil(mask).convert("L")

        # 确保图像和mask尺寸一致
        if image.size != mask.size:
            # 调整mask尺寸以匹配图像
            mask = mask.resize(image.size, Image.BILINEAR)

        # alpha 通道 = 255 - mask（保持透明显示）
        alpha = Image.eval(mask, lambda px: 255 - px)

        # 合成 RGBA（但不清理 RGB 内容！）
        rgba_image = image.copy()
        rgba_image.putalpha(alpha)

        # ---关键：额外保存一份原始 RGB 和 mask 到 PNG metadata---
        meta = PngImagePlugin.PngInfo()

        # 原始 RGB
        buf_rgb = BytesIO()
        image.save(buf_rgb, format="PNG")
        meta.add_text("raw_rgb_base64", base64.b64encode(buf_rgb.getvalue()).decode("utf-8"))

        # 原始 Mask
        buf_mask = BytesIO()
        mask.save(buf_mask, format="PNG")
        meta.add_text("raw_mask_base64", base64.b64encode(buf_mask.getvalue()).decode("utf-8"))

        # 保存 PNG
        buffered = BytesIO()
        rgba_image.save(buffered, format="PNG", pnginfo=meta)

        return base64.b64encode(buffered.getvalue()).decode("utf-8")


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

    @staticmethod
    def get_right_part_of_image(img):
        """
        从输入图片中找到分割线并仅保留右边部分
        
        :param img: PIL 图像对象
        :return: 仅包含右边部分的 PIL 图像对象
        """
        # 简单的边缘检测找分割线，计算每列的像素差异
        width, height = img.size
        diff_values = []
        for x in range(1, width):
            diff = 0
            for y in range(height):
                left_pixel = img.getpixel((x - 1, y))
                right_pixel = img.getpixel((x, y))
                diff += sum(abs(a - b) for a, b in zip(left_pixel, right_pixel))
            diff_values.append(diff)

        # 找到差异最大的位置作为分割线
        split_x = diff_values.index(max(diff_values)) + 1

        # 只保留右边部分图片
        return img.crop((split_x, 0, width, height))


    @staticmethod
    def crop_white_borders(img, tolerance=30):
        """
        判断并裁剪图片上下的白色部分

        :param img: PIL 图像对象
        :param tolerance: 颜色容差，值越大允许的色差范围越广，默认为 30
        :return: 裁剪后的 PIL 图像对象
        """
        width, height = img.size
        top = 0
        bottom = height

        def is_white(pixel, tolerance):
            """
            判断像素是否接近白色，考虑颜色容差

            :param pixel: 像素值
            :param tolerance: 颜色容差
            :return: 如果接近白色返回 True，否则返回 False
            """
            if len(pixel) == 4:  # 处理带透明度的图像
                r, g, b, a = pixel
            else:
                r, g, b = pixel
            return all(255 - x <= tolerance for x in (r, g, b))

        # 查找顶部白色区域结束位置
        for y in range(height):
            # 检查每行的第一个和最后一个像素
            if not is_white(img.getpixel((0, y)), tolerance) or not is_white(img.getpixel((width - 1, y)), tolerance):
                top = y
                break

        # 查找底部白色区域开始位置
        for y in range(height - 1, -1, -1):
            # 检查每行的第一个和最后一个像素
            if not is_white(img.getpixel((0, y)), tolerance) or not is_white(img.getpixel((width - 1, y)), tolerance):
                bottom = y + 1
                break

        # 执行裁剪
        return img.crop((0, top, width, bottom))

