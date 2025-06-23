# 请求函数
import numpy as np
import torch

def pil2tensor(image):
    img_array = np.array(image).astype(np.float32) / 255.0  # (H, W, 3)
    img_tensor = torch.from_numpy(img_array)[None,]  # (1, H, W, 3)
    return img_tensor