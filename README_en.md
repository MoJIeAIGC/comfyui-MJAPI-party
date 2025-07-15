<div align="center">
    <img src="https://mojie.tos-cn-guangzhou.volces.com/nodes/gitlogo.svg" alt="Logo" style="width: 300px;">
</div>

<div align="center">
    <a href="https://space.bilibili.com/483532108" target="_blank">
        <img src="https://img.shields.io/badge/Bilibili-B站-blue?logo=bilibili" alt="Bilibili">
    </a>
    <a href="#" target="_blank">
        <img src="https://img.shields.io/badge/YouTube-YouTube-red?logo=youtube" alt="YouTube">
    </a>
    <a href="/README.md" target="_blank">
        <img src="https://img.shields.io/badge/Docs-Documentation-green?logo=readme" alt="Documentation">
    </a>
</div>
  

***  

ComfyUI custom node tool developed by MojieAI. To address the challenges of managing API keys and endpoints when calling external APIs in ComfyUI, and considering that many superior models require substantial local computing power and time-consuming local deployment, mjapi-party integrates numerous excellent and commonly used API nodes. With just one API key, you can access API capabilities across the web while maintaining the flexibility of ComfyUI's node-based operations, greatly enhancing ComfyUI's usability. More API nodes are being added gradually, and support for Koishi and n8n will be added in the future.

***
To use this node, please register an account at [mojieaigc.com](https://www.mojieaigc.com/)
For detailed instructions, see:
> [Detailed Installation Steps](#installation-steps)

### Currently Supported Nodes
- [seededit3.0](/doc/node_list.md#seededit30)
- [Dreamina](/doc/node_list.md#Dreamina(即梦)) 
- [Redux Migration](/doc/node_list.md#redux万物迁移)
- [Kontext-pro&max](/doc/node_list.md#Kontext-pro&max)
- [Automatic Image Matting](/doc/node_list.md#自动抠图)

### Node Usage Instructions
All node documentation can be found in:
> [node_list.md](doc/node_list.md) in the doc directory

All node example workflows are in:
> workflow directory

Find mjapiparty in the ComfyUI node list
![alt text](doc/assets/node.png)

- 250714-New Node:
seededit3.0
SeedEdit 3.0 is an image editing tool developed by ByteDance that can modify images through text descriptions. For example, you can say "change the background to a beach." It supports Chinese prompts, Chinese output, maintains better consistency compared to Kontext, and supports Chinese prompt input and Chinese text output. The results are quite impressive.
![alt text](doc/assets/seed.png)
![alt text](doc/assets/seed2.png)
#### Redux Migration
This is a flux-redux migration integration node. Everything is configured and ready to use without downloading models.
![alt text](doc/assets/redux.png)
- migrate_image and migrate_mask are required uploads for the image to be migrated and the mask for the migration area.
- Product_image and Product_mask are for uploading the product image to be migrated. The mask is not mandatory.
- However, adding a mask to Product_mask details can make detail restoration more accurate.
- Prompts are optional as there are default prompts. You can simply describe what the item is.
- Strength between 0.6-0.9 is sufficient
#### Kontext-pro&max
![alt text](doc/assets/kontext.png)
Kontext is an AI drawing tool based on large models that can generate images through text descriptions.
- Added translation switch is_translation in each node, which is off by default. When enabled, you can input Chinese.
- aspect_ratio controls dimensions, default is "default" where Kontext controls the output image size. You can also enable it to select dimensions according to your needs.
- max has better effects, pro offers better value for money. Video tutorial available at:
> [Kontext-pro&max Detailed Review Tutorial](https://www.bilibili.com/video/BV19931zAE4c/?vd_source=25d3add966daa64cbb811354319ec18d#reply268510289936)
- Please ensure you have sufficient balance in your account before use
#### Dreamina
![alt text](doc/assets/Dreamina.png)
Dreamina is an AI drawing tool based on large models that supports Chinese input and output. It was specifically added to mjapiparty to fully leverage ComfyUI's flexible combination capabilities, and to avoid having to recharge in Dreamina itself. The mojie-api-party node includes two Dreamina nodes: text-to-image and image-to-image.
- Dreamina text-to-image supports Chinese input and output. It has good understanding of obscure or Chinese-specific concepts.
- Dreamina image-to-image has multiple reference modes in gen_mode selection:
  - First mode, creative, is creative mode, which can be understood as full image reference
  - Second mode, reference, is face reference
  - Third mode, reference_char, is character reference
- The default cfg is 2.5, please do not modify

***


### Installation Steps
1. Make sure you have installed ComfyUI.
2. Search for mojieapi_party in comfyui-manager to install this project directly
3. Or in the comfyui/custom_nodes directory:
```plaintext
git clone https://github.com/MoJIeAIGC/comfyui-MJAPI-party.git
4. Run requirements to install dependencies:

pip install -r requirements.txt

6. Register an account on mojieaigc.com website
7. Log in to get your API-KEY
8. Create a config.ini file in the project root directory with the following content:
```
[API]
```
KEY = your_api_key
BASE_URL = https://www.mojieaigc.com/v1/
completions
```
Do not change the request address, just fill in the KEY.
Remember to restart ComfyUI after entering the key

### Contact Us
WeChat: mojie_AIGC
Scan the QR code below
