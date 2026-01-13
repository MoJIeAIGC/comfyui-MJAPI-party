import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// 辅助函数：根据名称查找控件
const findWidgetByName = (node, name) => {
    return node.widgets ? node.widgets.find((w) => w.name === name) : null;
};

// 家具照片节点的处理函数
function handleFurniturePhotoNode(node) {
    console.log('[FurniturePhotoNode] 开始处理节点:', node.comfyClass);
    
    if (node.comfyClass !== "FurniturePhotoNode") {
        console.log('[FurniturePhotoNode] 节点类型不匹配:', node.comfyClass);
        return;
    }

    // 定义默认的家具类型对应的风格列表
    const parentname_dict = {
        '主卧床': ['中古风', '浅灰现代风', '法式奶油风'],
        ' 客厅大沙发': ['中古风', '浅灰现代风', '法式奶油风', '宋氏美学'],
        '餐桌': ['中古风', '浅灰现代风', '法式奶油风'],
        '斗柜': ['中古风', '宋氏美学']
    };
    
    console.log('[FurniturePhotoNode] 使用的风格数据:', parentname_dict);

    // 查找控件
    const furnitureTypesWidget = findWidgetByName(node, "furniture_types");
    const styleTypeWidget = findWidgetByName(node, "style_type");

    console.log('[FurniturePhotoNode] 找到的控件:', {
        furnitureTypesWidget: furnitureTypesWidget ? furnitureTypesWidget.name : '未找到',
        styleTypeWidget: styleTypeWidget ? styleTypeWidget.name : '未找到'
    });

    if (!furnitureTypesWidget || !styleTypeWidget) {
        console.error('[FurniturePhotoNode] 找不到必要的控件');
        return;
    }

    // 更新style_type选项的函数
    const updateStyleOptions = () => {
        console.log('[FurniturePhotoNode] 开始更新风格选项');
        const selectedFurniture = furnitureTypesWidget.value;
        console.log('[FurniturePhotoNode] 当前选择的家具类型:', selectedFurniture);
        
        const availableStyles = parentname_dict[selectedFurniture] || [];
        console.log('[FurniturePhotoNode] 可用的风格列表:', availableStyles);

        // 更新控件选项
        if (styleTypeWidget.options) {
            console.log('[FurniturePhotoNode] 更新控件选项:', availableStyles);
            styleTypeWidget.options.values = availableStyles;
            styleTypeWidget.options.labels = availableStyles;
        } else {
            console.error('[FurniturePhotoNode] styleTypeWidget.options 不存在');
        }

        // 如果当前选中的风格不在新选项中，选择第一个选项
        if (availableStyles.length > 0) {
            if (!availableStyles.includes(styleTypeWidget.value)) {
                console.log('[FurniturePhotoNode] 选中的风格不在新选项中，切换到第一个选项:', availableStyles[0]);
                styleTypeWidget.value = availableStyles[0];
            }
        } else {
            console.warn('[FurniturePhotoNode] 没有可用的风格选项');
        }

        // 触发UI更新
        if (styleTypeWidget.callback) {
            console.log('[FurniturePhotoNode] 触发UI更新回调');
            styleTypeWidget.callback(styleTypeWidget.value);
        }
        
        // 强制刷新节点UI
        if (node.onResize) {
            console.log('[FurniturePhotoNode] 调用节点onResize方法刷新UI');
            node.onResize();
        }
    };

    // 初始化时更新一次
    console.log('[FurniturePhotoNode] 初始化更新风格选项');
    updateStyleOptions();

    // 为家具类型控件添加值变化监听
    console.log('[FurniturePhotoNode] 为家具类型控件添加值变化监听');
    
    // 保存原始的value setter
    const originalDescriptor = Object.getOwnPropertyDescriptor(furnitureTypesWidget, 'value') || 
        Object.getOwnPropertyDescriptor(Object.getPrototypeOf(furnitureTypesWidget), 'value');

    if (!originalDescriptor) {
        console.log('[FurniturePhotoNode] 未找到原始的value描述符，使用直接赋值方式');
    }

    let widgetValue = furnitureTypesWidget.value;

    // 重写value属性，添加监听
    Object.defineProperty(furnitureTypesWidget, 'value', {
        get() {
            const value = originalDescriptor && originalDescriptor.get 
                ? originalDescriptor.get.call(furnitureTypesWidget) 
                : widgetValue;
            return value;
        },
        set(newVal) {
            console.log('[FurniturePhotoNode] 家具类型值变化:', newVal);
            if (originalDescriptor && originalDescriptor.set) {
                originalDescriptor.set.call(furnitureTypesWidget, newVal);
            } else {
                widgetValue = newVal;
            }
            // 更新风格选项
            updateStyleOptions();
        }
    });

    console.log('[FurniturePhotoNode] 节点处理完成');
}

// 文件加载节点的处理函数
function handleFileLoaderNode(node) {
    console.log('[FileLoaderNode] 开始处理节点:', node.comfyClass);
    
    if (node.comfyClass !== "FileLoaderNode") {
        console.log('[FileLoaderNode] 节点类型不匹配:', node.comfyClass);
        return;
    }

    // 查找file_path输入框
    const filePathWidget = findWidgetByName(node, "file_path");
    console.log('[FileLoaderNode] 找到的file_path控件:', filePathWidget ? filePathWidget.name : '未找到');

    if (!filePathWidget) {
        console.error('[FileLoaderNode] 找不到file_path输入框');
        return;
    }

    // 检查是否已经创建了上传按钮
    if (filePathWidget.uploadButton) {
        console.log('[FileLoaderNode] 上传按钮已存在');
        return;
    }

    // 创建文件输入元素（隐藏）
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.pdf,.docx,.doc';
    fileInput.style.display = 'none';
    
    // 处理文件选择事件
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            console.log('[FileLoaderNode] 选择了文件:', file.name);
            // 设置文件路径到输入框
            filePathWidget.value = file.path;
            
            // 触发输入框的更新事件
            if (filePathWidget.callback) {
                filePathWidget.callback(filePathWidget.value);
            }
            
            // 刷新节点UI
            if (node.onResize) {
                node.onResize();
            }
        }
    });
    
    // 添加到文档中
    document.body.appendChild(fileInput);
    
    // 创建上传按钮
    const uploadButton = document.createElement('button');
    uploadButton.className = 'comfy-btn';
    uploadButton.innerText = '上传文件';
    uploadButton.style.marginLeft = '8px';
    uploadButton.style.padding = '4px 8px';
    uploadButton.style.fontSize = '12px';
    
    // 点击按钮触发文件选择
    uploadButton.addEventListener('click', () => {
        console.log('[FileLoaderNode] 点击上传按钮');
        fileInput.click();
    });
    
    // 将按钮添加到节点界面
    // 等待节点渲染完成后添加按钮
    setTimeout(() => {
        try {
            // 查找输入框元素
            const widgetElement = document.querySelector(`#node-${node.id} .comfy-widget.string`);
            if (widgetElement) {
                // 创建容器
                const container = document.createElement('div');
                container.style.display = 'flex';
                container.style.alignItems = 'center';
                container.style.gap = '8px';
                
                // 将现有的输入框移到容器中
                const inputElement = widgetElement.querySelector('input');
                if (inputElement) {
                    container.appendChild(inputElement);
                    container.appendChild(uploadButton);
                    widgetElement.appendChild(container);
                    
                    // 保存按钮引用
                    filePathWidget.uploadButton = uploadButton;
                    filePathWidget.fileInput = fileInput;
                    
                    console.log('[FileLoaderNode] 上传按钮添加成功');
                }
            }
        } catch (e) {
            console.error('[FileLoaderNode] 添加按钮失败:', e);
        }
    }, 100);

    console.log('[FileLoaderNode] 节点处理完成');
}

app.registerExtension({
    name: "ComfyUI.Mjapi",
    nodeCreated(node) {
        console.log('[节点创建] 检测到节点创建:', node.comfyClass);
        handleFurniturePhotoNode(node);
        handleFileLoaderNode(node);
    },
    async setup() {

        app.ui.settings.addSetting({
            id: "Mjapi.version",
            name: "当前版本",
            type: () => {
                const container = document.createElement("div");

                const versionText = document.createElement("span");
                versionText.className = "comfy-text";
                versionText.style.fontWeight = "bold";

                // 获取版本信息
                api.fetchApi("/my_node/get_key").then(async (resp) => {
                    const data = await resp.json();
                    console.log(data);
                    versionText.textContent = `v${data.version}`;  // 显示版本号
                });

                container.appendChild(versionText);

                return container; // ✅ 注意这里，不要 return <tr>
            },
        });

        app.ui.settings.addSetting({
            id: "Mjapi.api_key",
            name: "Mojie API Key (重启生效)",
            type: () => {
                const container = document.createElement("div");

                const input = document.createElement("input");
                input.type = "text";
                input.className = "comfy-input";
                input.style.width = "360px";

                // 默认值
                api.fetchApi("/my_node/get_key").then(async (resp) => {
                    const data = await resp.json();
                    console.log(data);
                    input.value = data.msg || "";
                });

                const button = document.createElement("button");
                button.className = "comfy-btn";
                button.innerText = "更新api-key";
                button.onclick = async () => {
                    const resp = await api.fetchApi("/my_node/set_key", {
                        method: "POST",
                        body: JSON.stringify({ api_key: input.value })
                    });
                    const data = await resp.json();
                    alert("保存结果: " + data.msg);
                };

                container.appendChild(input);
                container.appendChild(button);

                return container; // ✅ 注意这里，不要 return <tr>
            },
            // category: ["API KEY"]
        });


        // 更新按钮（git pull）
        app.ui.settings.addSetting({
            id: "Mjapi.node_update",
            name: "更新节点 (重启生效)",
            type: () => {
                const row = document.createElement("tr");
                const cell = document.createElement("td");
                const button = document.createElement("button");
                button.className = "comfy-btn";
                button.style.cssText = `
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                `;
                
                // 添加鼠标悬停效果
                button.addEventListener('mouseenter', () => {
                    button.style.transform = 'translateY(-2px)';
                    button.style.boxShadow = '0 4px 8px rgba(0,0,0,0.3)';
                });
                
                button.addEventListener('mouseleave', () => {
                    button.style.transform = 'translateY(0)';
                    button.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
                });
                
                button.innerText = "立即更新";
                button.onclick = async () => {
                    // 禁用按钮并显示加载状态
                    button.disabled = true;
                    button.style.opacity = '0.7';
                    button.style.cursor = 'not-allowed';
                    const originalText = button.innerText;
                    button.innerText = "更新中...";
                    
                    try {
                        const resp = await api.fetchApi("/my_node/update", { method: "POST" });
                        const data = await resp.json();
                        alert("更新结果: " + data.msg);
                    } catch (error) {
                        alert("更新失败: " + error.message);
                    } finally {
                        // 恢复按钮状态
                        button.disabled = false;
                        button.style.opacity = '1';
                        button.style.cursor = 'pointer';
                        button.innerText = originalText;
                    }
                };
                cell.appendChild(button);
                row.appendChild(cell);
                return row;
            },
            // category: ["Custom Nodes"]
        });

        // 账户充值入口
        app.ui.settings.addSetting({
            id: "Mjapi.recharge",
            name: "账户充值请前往：",
            type: () => {
                const container = document.createElement("div");

                const link = document.createElement("a");
                link.href = "https://mojieaigc.com";
                link.innerText = "https://mojieaigc.com";
                link.target = "_blank"; // ✅ 新窗口打开
                link.className = "comfy-text";
                link.style.color = "#00aaff";
                link.style.fontWeight = "bold";
                link.style.textDecoration = "underline";
                link.style.cursor = "pointer";

                container.appendChild(link);
                return container;
            },
        });

        // 用户信息
        app.ui.settings.addSetting({
            id: "Mjapi.userinfo",
            name: "账户信息",
            type: () => {
                const container = document.createElement("div");
                container.style.display = "flex";
                container.style.flexDirection = "column";
                container.style.gap = "6px"; // 每行间距
                container.style.fontSize = "14px";
                container.style.padding = "4px 0";

                // 第1行：用户名
                const userRow = document.createElement("div");
                userRow.style.display = "flex";
                userRow.style.justifyContent = "space-between";
                userRow.style.alignItems = "center";

                const userLabel = document.createElement("span");
                userLabel.textContent = "当前账户：";
                userLabel.style.color = "#888";

                const userValue = document.createElement("span");
                userValue.className = "comfy-text";
                userValue.style.fontWeight = "bold";
                userValue.style.color = "#00aaff";

                userRow.appendChild(userLabel);
                userRow.appendChild(userValue);

                // 第2行：余额
                const quotaRow = document.createElement("div");
                quotaRow.style.display = "flex";
                quotaRow.style.justifyContent = "space-between";
                quotaRow.style.alignItems = "center";

                const quotaLabel = document.createElement("span");
                quotaLabel.textContent = "当前余额：";
                quotaLabel.style.color = "#888";

                const quotaValue = document.createElement("span");
                quotaValue.className = "comfy-text";
                quotaValue.style.fontWeight = "bold";
                quotaValue.style.color = "#00cc66";

                quotaRow.appendChild(quotaLabel);
                quotaRow.appendChild(quotaValue);

                // 加入容器
                container.appendChild(userRow);
                container.appendChild(quotaRow);

                // 获取用户信息
                api.fetchApi("/my_node/get_user").then(async (resp) => {
                    const data = await resp.json();
                    console.log(data);
                    userValue.textContent = data.username || "未知";
                    quotaValue.textContent = data.quota !== undefined ? data.quota : "—";
                }).catch((err) => {
                    userValue.textContent = "加载失败";
                    quotaValue.textContent = "—";
                });

                return container;
            },
        });


    }
});
