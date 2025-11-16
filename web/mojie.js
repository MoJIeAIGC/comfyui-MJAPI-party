import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "ComfyUI.Mjapi",
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
                button.innerText = "更新";
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
                button.innerText = "立即更新";
                button.onclick = async () => {
                    const resp = await api.fetchApi("/my_node/update", { method: "POST" });
                    const data = await resp.json();
                    alert("更新结果: " + data.msg);
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
