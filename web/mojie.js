import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "ComfyUI.Mjapi",
    async setup() {

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



    }
});
