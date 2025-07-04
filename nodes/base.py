import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO
class ImageConverter:
    @staticmethod
    def pil2tensor(image):
        img_array = np.array(image).astype(np.float32) / 255.0  # (H, W, 3)
        img_tensor = torch.from_numpy(img_array)[None,]  # (1, H, W, 3)
        return img_tensor

    @staticmethod
    def tensor2pil(tensor):
        # Tensor (1, H, W, 3) to PIL
        image = tensor.squeeze().numpy() * 255.0
        return Image.fromarray(image.astype(np.uint8))

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
    def get_status_error_msg(status_code):
        """
        根据状态码返回对应的错误信息

        :param status_code: HTTP 状态码
        :return: 对应的错误信息字符串
        """
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
        return error_msg_map.get(status_code, f"请求失败，状态码: {status_code}")

    @staticmethod
    def create_error_image(text, width=512, height=512, font_size=20):
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