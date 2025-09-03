#### 所有API节点列表
所有的节点示例工作流都可以在workflow目录下找到
- [Gemini-NanoBanana](#gemini-nanobanana使用说明)
- [Qwen-image](#qwen-image-使用说明)
- [Qwen-edit-image](#qwen-edit-image-使用说明)
- [seededit3.0](#seededit30)
- [Redux万物迁移](#redux万物迁移)
- [Kontext-pro&max](#Kontext-pro&max)
- [自动抠图](#自动抠图)
- [Dreamina(即梦参考生图)](#dreamina即梦参考生图)
- [即梦视频生成](#即梦视频生成)(即将下线换成Seedance)
***

#### Gemini-NanoBanana使用说明
NanoBanana又名Gemini 2.5 Flash Image Preview,是google旗下的图片编辑工具。提示词遵循强度很高。基本不需要特别的提示词格式，支持中英文输入，但是不支持中文输出，可输出英文字体。
is_translation是翻译开关，如果中文输入效果不理想，可以把翻译开关打开，翻译过后再试。
![alt text](assets/NanoBanana.png)
![alt text](assets/NanoBanana2.png)

#### Qwen-image 使用说明
Qwen-image是阿里开源的AI绘画工具，对中文的支持非常友好，能够准确的画出细节的小字和排版，支持中文输入，中文输出。
prompt_extend是提示词扩写参数，默认开启，仅需简单提示词就可以出来非常不错的画面效果。
#### Qwen-edit-image 使用说明
和seededit功能一样能通过文字描述修改图片。各有千秋，价格便宜，支持使用中文提示词，支持输出中文。具体使用方法和标准提示词可以参考seededit

![alt text](assets/Qwen-image.png)

#### seededit3.0 使用说明
SeedEdit 3.0 是字节跳动开发的图片编辑工具，
能通过文字描述修改图片。比如你说 “把背景换成海边”。支持使用中文提示词，支持输出中文。
![alt text](assets/seed.png)
![alt text](assets/seed2.png)

用于编辑图像的提示词 ,建议：
- 建议长度 <= 120字符，prompt过长有概率出图异常或不生效
- 编辑指令使用自然语言即可
- 每次编辑使用单指令会更好
- 局部编辑时指令描述尽量精准，尤其是画面有多个实体的时候，描述清楚对谁做什么，能获取更精准的编辑效果
- 发现编辑效果不明显的时候，可以调整一下编辑强度cfg_scale，数值越大越贴近指令执行
尽量使用清晰的，分辨率高的底片.
##### 提示词参考示例：
- 添加/删除实体：添加/删除xxx（删除图上的女孩/添加一道彩虹）
- 修改实体：把xxx改成xxx（把手里的鸡腿变成汉堡）
- 修改风格：改成xxx风格（改成漫画风格）
- 修改色彩：把xxx改成xx颜色（把衣服改成粉色的）
- 修改动作：修改表情动作（让他哭/笑/生气）
- 修改环境背景：背景换成xxx，在xxx（背景换成海边/在星空下）
***
#### Redux万物迁移
这是flux-redux的迁移整合节点，一切都配置好了，无需下载模型，只需直接使用即可。
![alt text](assets/redux.png)
- migrate_image和migrate_mask是必选项上传需要被迁移的图片和迁移区域的遮罩。
- Product_image和Product_mask是上传迁移产品图，遮罩不是必须的。
- 但是可以给Product_mask细节处添加遮罩，可以让细节还原更加准确。
- 提示词可以不填，有默认提示词。或者简单形容一下这个是什么物品。
- 强度在0.6-0.9即可
#### Kontext-pro&max
![alt text](assets/kontext.png)
Kontext 是一个基于大模型的 AI 绘画工具，它可以通过文字描述生成图像。
- 加入了翻译开关is_translation,在每个节点中都有，默认是关闭的。打开可以输入中文。
- aspect_ratio是尺寸控制，默认是default，由kontext自己控制输出图片的尺寸。也可以开启根据自己的需要选择尺寸。
- max效果更好，pro性价比更高。视频教程可以查看：
> [Kontext-pro&max详细测评教程](https://www.bilibili.com/video/BV19931zAE4c/?vd_source=25d3add966daa64cbb811354319ec18d#reply268510289936)
- 使用前请确保你的账户中有足够的余额

#### Dreamina(即梦参考生图)
加入Qwen-image后，即梦文身图就没有太多存在的意义了，完全可以平替即梦。但是即梦的参考生图还是非常不错的，在人像还原上也非常准确。

![alt text](assets/Dreamina.png)

即梦图生图有多种参考模式gen_mode选下下
第一种 creative 是创意模式，可以理解为全图参考
第二种 reference 人脸参考
第三种 reference_char 人物参考
cfg默认2.5请勿修改

##### 自动抠图
图片上传最大不超过10M
用就行了，没啥参数。
带了遮罩就按遮罩范围抠图


