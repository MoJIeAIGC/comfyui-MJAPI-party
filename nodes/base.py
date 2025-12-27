import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
import base64
from io import BytesIO
import os
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
    def process_images(face_image, cloths_image, save_filename="output.jpg"):
        """
        新逻辑：
        - 有脸：832x1248 白色画布，上 1/3 区域放脸，下 2/3 区域放衣服，等比缩放居中
        - 无脸：衣服图单独居中缩放到 832x1248，等比缩放，不强行填满
        - 保存到项目目录并返回 base64
        """
        canvas_width, canvas_height = 832, 1248
        face_area_height = canvas_height // 3        # 416
        cloth_area_height = canvas_height - face_area_height  # 832

        # 创建白色背景
        new_img = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))

        if face_image is not None:
            # 有脸部图
            face_pil = ImageConverter.tensor2pil(face_image)
            cloth_pil = ImageConverter.tensor2pil(cloths_image)

            # --- 处理脸部 (放在上方 1/3 区域，等比缩放) ---
            ratio = min(canvas_width / face_pil.width, face_area_height / face_pil.height, 1.0)
            new_width = int(face_pil.width * ratio)
            new_height = int(face_pil.height * ratio)
            face_pil = face_pil.resize((new_width, new_height), Image.LANCZOS)
            paste_x = (canvas_width - new_width) // 2
            paste_y = (face_area_height - new_height) // 2
            new_img.paste(face_pil, (paste_x, paste_y))

            # --- 处理服装 (放在下方 2/3 区域，等比缩放) ---
            ratio = min(canvas_width / cloth_pil.width, cloth_area_height / cloth_pil.height, 1.0)
            new_width = int(cloth_pil.width * ratio)
            new_height = int(cloth_pil.height * ratio)
            cloth_pil = cloth_pil.resize((new_width, new_height), Image.LANCZOS)
            paste_x = (canvas_width - new_width) // 2
            paste_y = face_area_height + (cloth_area_height - new_height) // 2
            new_img.paste(cloth_pil, (paste_x, paste_y))

        else:
            # 没有脸部图 → 衣服图单独居中缩放到整个画布
            cloth_pil = ImageConverter.tensor2pil(cloths_image)
            ratio = min(canvas_width / cloth_pil.width, canvas_height / cloth_pil.height, 1.0)
            new_width = int(cloth_pil.width * ratio)
            new_height = int(cloth_pil.height * ratio)
            cloth_pil = cloth_pil.resize((new_width, new_height), Image.LANCZOS)
            paste_x = (canvas_width - new_width) // 2
            paste_y = (canvas_height - new_height) // 2
            new_img.paste(cloth_pil, (paste_x, paste_y))

        # 保存到项目目录
        # save_path = os.path.join(os.getcwd(), save_filename)
        # new_img.save(save_path, format="JPEG")

        # 转 base64
        buffered = BytesIO()
        new_img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    @staticmethod
    def tensor_to_base64(image_tensor):
        """
        将图像张量转换为 base64 编码的字符串
        如果图片长边超过4096，则等比压缩

        :param image_tensor: 输入的图像张量
        :return: base64 编码的字符串
        """
        pil_image = ImageConverter.tensor2pil(image_tensor)
        
        # 检查图片长边，如果超过4096则等比压缩
        width, height = pil_image.size
        max_size = max(width, height)
        
        if max_size > 4096:
            # 计算缩放比例
            scale = 4096 / max_size
            new_width = int(width * scale)
            new_height = int(height * scale)
            # 使用高质量的重采样方法进行缩放
            pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
        
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
    def highlight_mask_with_rectangle(image, mask):
        """
        在原图上用红色矩形框出遮罩区域
        
        :param image: 输入图像张量
        :param mask: 输入遮罩张量
        :return: 带有红色矩形框的图像的base64编码
        """
        if mask is None:
            return ImageConverter.tensor_to_base64(image)
            
        # 转换为PIL图像
        image_pil = ImageConverter.tensor2pil(image).convert("RGB")
        mask_pil = ImageConverter.tensor2pil(mask).convert("L")
        
        # 检查图片长边，如果超过4096则等比压缩
        width, height = image_pil.size
        max_size = max(width, height)
        
        if max_size > 4096:
            # 计算缩放比例
            scale = 4096 / max_size
            new_width = int(width * scale)
            new_height = int(height * scale)
            # 使用高质量的重采样方法进行缩放
            image_pil = image_pil.resize((new_width, new_height), Image.LANCZOS)
            # 同时缩放遮罩以保持一致
            mask_pil = mask_pil.resize((new_width, new_height), Image.LANCZOS)
        
        # 确保图像和mask尺寸一致
        if image_pil.size != mask_pil.size:
            mask_pil = mask_pil.resize(image_pil.size, Image.BILINEAR)
        
        # 创建绘图对象
        draw = ImageDraw.Draw(image_pil)
        
        # 找到遮罩区域的边界框
        # 首先找到遮罩中非零像素的坐标
        mask_array = np.array(mask_pil)
        non_zero_indices = np.where(mask_array > 0)
        
        if len(non_zero_indices[0]) == 0:  # 如果没有非零像素，返回原图
            return ImageConverter.tensor_to_base64(image)
            
        # 计算边界框
        min_y, min_x = np.min(non_zero_indices[0], axis=0), np.min(non_zero_indices[1], axis=0)
        max_y, max_x = np.max(non_zero_indices[0], axis=0), np.max(non_zero_indices[1], axis=0)
        
        # 在边界框周围绘制红色矩形
        # 可以添加一些边距使矩形更明显
        margin = 5
        left = max(0, min_x - margin)
        top = max(0, min_y - margin)
        right = min(image_pil.width, max_x + margin + 1)
        bottom = min(image_pil.height, max_y + margin + 1)
        
        # 检查矩形范围，如果小于500px则扩大至500px
        rect_width = right - left
        rect_height = bottom - top
        
        if rect_width < 500 or rect_height < 500:
            # 计算需要扩展的像素数
            expand_x = max(0, (500 - rect_width) // 2)
            expand_y = max(0, (500 - rect_height) // 2)
            
            # 扩展矩形边界，确保不超出图像范围
            left = max(0, left - expand_x)
            top = max(0, top - expand_y)
            right = min(image_pil.width, right + expand_x)
            bottom = min(image_pil.height, bottom + expand_y)
            
            # 如果扩展后仍然小于500px，则从另一侧继续扩展
            new_width = right - left
            new_height = bottom - top
            
            if new_width < 500:
                additional_expand = 500 - new_width
                if left >= additional_expand:
                    left -= additional_expand
                else:
                    right = min(image_pil.width, right + (additional_expand - left))
                    left = 0
                    
            if new_height < 500:
                additional_expand = 500 - new_height
                if top >= additional_expand:
                    top -= additional_expand
                else:
                    bottom = min(image_pil.height, bottom + (additional_expand - top))
                    top = 0
        
        # 绘制红色矩形框
        draw.rectangle([(left, top), (right, bottom)], outline=(255, 0, 0), width=10)
        
        # 转换回base64
        buffered = BytesIO()
        image_pil.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return img_base64


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




    @staticmethod
    def get_lang(lang):
        combined_lang_dict = {
            "阿拉伯语": "ar",
            "法语": "fr",
            "英语": "en",
            "自动": "auto",
            "加泰罗尼亚语": "ca",
            "葡萄牙语": "pt",
            "西班牙语": "es",
            "荷兰语": "nl",
            "德语": "de",
            "斯洛文尼亚语": "sl",
            "阿塞拜疆语": "az",
            "孟加拉语": "bn",
            "俄语": "ru",
            "挪威语": "no",
            "马来语": "ms",
            "中文": "zh",
            "中文 (繁体)": "zh_hant",
            "捷克语": "cs",
            "斯洛伐克语": "sk",
            "波兰语": "pl",
            "匈牙利语": "hu",
            "越南语": "vi",
            "丹麦语": "da",
            "芬兰语": "fi",
            "瑞典语": "sv",
            "印尼语": "id",
            "希伯来语": "he",
            "意大利语": "it",
            "日语": "ja",
            "韩语": "ko",
            "泰米尔语": "ta",
            "泰语": "th",
            "土耳其语": "tr"
        }
        return combined_lang_dict.get(lang, "auto")
