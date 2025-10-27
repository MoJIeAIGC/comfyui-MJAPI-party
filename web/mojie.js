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

        // 登录功能（美化版）
        app.ui.settings.addSetting({
            id: "Mjapi.login",
            name: "账户登录 (重启生效)",
            type: () => {
                const container = document.createElement("div");
                container.style.display = "flex";
                container.style.flexDirection = "column";
                container.style.alignItems = "center";
                container.style.justifyContent = "center";
                container.style.gap = "16px";
                container.style.padding = "25px";
                container.style.border = "1px solid rgba(255,255,255,0.15)";
                container.style.borderRadius = "12px";
                container.style.background = "linear-gradient(145deg, rgba(30,30,30,0.9), rgba(45,45,45,0.9))";
                container.style.boxShadow = "0 4px 12px rgba(0,0,0,0.3)";
                container.style.transition = "all 0.3s ease";
                container.style.width = "320px";
                container.style.margin = "0px auto";

                const title = document.createElement("h3");
                title.textContent = "账户登录";
                title.style.color = "#fff";
                title.style.marginBottom = "10px";
                title.style.textAlign = "center";
                title.style.fontSize = "18px";
                title.style.letterSpacing = "1px";
                title.style.fontWeight = "500";
                container.appendChild(title);

                // 创建带标签和输入框的组件
                const createInputRow = (labelText, inputType, placeholder) => {
                    const row = document.createElement("div");
                    row.style.display = "flex";
                    row.style.flexDirection = "column";
                    row.style.gap = "6px";
                    row.style.width = "100%";

                    const label = document.createElement("label");
                    label.textContent = labelText;
                    label.style.color = "#ccc";
                    label.style.fontSize = "14px";
                    label.style.marginLeft = "4px";

                    const input = document.createElement("input");
                    input.type = inputType;
                    input.className = "comfy-input";
                    input.placeholder = placeholder;
                    input.style.width = "100%";
                    input.style.padding = "8px 10px";
                    input.style.borderRadius = "6px";
                    input.style.border = "1px solid rgba(255,255,255,0.15)";
                    input.style.background = "rgba(255,255,255,0.05)";
                    input.style.color = "#fff";
                    input.style.transition = "all 0.3s ease";

                    input.addEventListener("focus", () => {
                        input.style.border = "1px solid #3b82f6";
                        input.style.boxShadow = "0 0 6px rgba(59,130,246,0.5)";
                    });
                    input.addEventListener("blur", () => {
                        input.style.border = "1px solid rgba(255,255,255,0.15)";
                        input.style.boxShadow = "none";
                    });

                    row.appendChild(label);
                    row.appendChild(input);
                    return { row, input };
                };

                const { row: usernameRow, input: usernameInput } = createInputRow("用户名", "text", "请输入用户名");
                const { row: passwordRow, input: passwordInput } = createInputRow("密码", "password", "请输入密码");

                // 登录按钮
                const buttonRow = document.createElement("div");
                buttonRow.style.display = "flex";
                buttonRow.style.justifyContent = "center";
                buttonRow.style.width = "100%";
                buttonRow.style.marginTop = "10px";

                const loginButton = document.createElement("button");
                loginButton.className = "comfy-btn";
                loginButton.innerText = "登 录";
                loginButton.style.padding = "8px 16px";
                loginButton.style.borderRadius = "6px";
                loginButton.style.border = "none";
                loginButton.style.background = "linear-gradient(135deg, #3b82f6, #2563eb)";
                loginButton.style.color = "#fff";
                loginButton.style.fontWeight = "600";
                loginButton.style.cursor = "pointer";
                loginButton.style.transition = "all 0.25s ease";
                loginButton.style.boxShadow = "0 3px 8px rgba(37,99,235,0.4)";

                loginButton.onmouseenter = () => {
                    loginButton.style.transform = "translateY(-1px)";
                    loginButton.style.boxShadow = "0 6px 12px rgba(37,99,235,0.6)";
                };
                loginButton.onmouseleave = () => {
                    loginButton.style.transform = "translateY(0)";
                    loginButton.style.boxShadow = "0 3px 8px rgba(37,99,235,0.4)";
                };

                loginButton.onclick = async () => {
                    const username = usernameInput.value.trim();
                    const password = passwordInput.value.trim();

                    if (!username || !password) {
                        showToast("⚠️ 用户名和密码不能为空", "error");
                        return;
                    }

                    loginButton.disabled = true;
                    loginButton.innerText = "登录中...";
                    loginButton.style.opacity = "0.7";

                    try {
                        const resp = await api.fetchApi("/my_node/login", {
                            method: "POST",
                            body: JSON.stringify({ username, password })
                        });
                        const data = await resp.json();
                        showToast("✅ 登录成功: " + (data.message || JSON.stringify(data)), "success");
                    } catch (error) {
                        showToast("❌ 登录请求失败: " + error.message, "error");
                    } finally {
                        loginButton.disabled = false;
                        loginButton.innerText = "登 录";
                        loginButton.style.opacity = "1";
                    }
                };

                buttonRow.appendChild(loginButton);

                // Toast 提示框
                const showToast = (message, type = "info") => {
                    const toast = document.createElement("div");
                    toast.textContent = message;
                    toast.style.position = "fixed";
                    toast.style.bottom = "30px";
                    toast.style.left = "50%";
                    toast.style.transform = "translateX(-50%)";
                    toast.style.background =
                        type === "success"
                            ? "rgba(16,185,129,0.9)"
                            : type === "error"
                                ? "rgba(239,68,68,0.9)"
                                : "rgba(59,130,246,0.9)";
                    toast.style.color = "#fff";
                    toast.style.padding = "10px 20px";
                    toast.style.borderRadius = "8px";
                    toast.style.boxShadow = "0 4px 12px rgba(0,0,0,0.3)";
                    toast.style.fontSize = "14px";
                    toast.style.transition = "opacity 0.5s ease, transform 0.5s ease";
                    toast.style.opacity = "0";
                    toast.style.zIndex = "9999";

                    document.body.appendChild(toast);
                    setTimeout(() => {
                        toast.style.opacity = "1";
                        toast.style.transform = "translateX(-50%) translateY(-10px)";
                    }, 50);

                    setTimeout(() => {
                        toast.style.opacity = "0";
                        toast.style.transform = "translateX(-50%) translateY(0)";
                        setTimeout(() => toast.remove(), 500);
                    }, 2500);
                };

                // 加入容器
                container.appendChild(usernameRow);
                container.appendChild(passwordRow);
                container.appendChild(buttonRow);

                return container;
            },
        });
        // 注册功能（适配手机号/邮箱，含验证码倒计时）
        app.ui.settings.addSetting({
            id: "Mjapi.register",
            name: "账户注册 (重启生效)",
            type: () => {
                const container = document.createElement("div");
                container.style.display = "flex";
                container.style.flexDirection = "column";
                container.style.alignItems = "center";
                container.style.justifyContent = "center";
                container.style.gap = "16px";
                container.style.padding = "25px";
                container.style.border = "1px solid rgba(255,255,255,0.15)";
                container.style.borderRadius = "12px";
                container.style.background = "linear-gradient(145deg, rgba(30,30,30,0.9), rgba(45,45,45,0.9))";
                container.style.boxShadow = "0 4px 12px rgba(0,0,0,0.3)";
                container.style.transition = "all 0.3s ease";
                container.style.width = "320px";
                container.style.margin = "0px auto";

                const title = document.createElement("h3");
                title.textContent = "账户注册";
                title.style.color = "#fff";
                title.style.marginBottom = "10px";
                title.style.textAlign = "center";
                title.style.fontSize = "18px";
                title.style.letterSpacing = "1px";
                title.style.fontWeight = "500";
                container.appendChild(title);

                // 创建带标签和输入框的组件
                const createInputRow = (labelText, inputType, placeholder, isVerifyCode = false) => {
                    const row = document.createElement("div");
                    row.style.display = "flex";
                    row.style.flexDirection = "column";
                    row.style.gap = "6px";
                    row.style.width = "100%";

                    const label = document.createElement("label");
                    label.textContent = labelText;
                    label.style.color = "#ccc";
                    label.style.fontSize = "14px";
                    label.style.marginLeft = "4px";

                    const input = document.createElement("input");
                    input.type = inputType;
                    input.className = "comfy-input";
                    input.placeholder = placeholder;
                    input.style.width = "100%";
                    input.style.padding = "8px 10px";
                    input.style.borderRadius = "6px";
                    input.style.border = "1px solid rgba(255,255,255,0.15)";
                    input.style.background = "rgba(255,255,255,0.05)";
                    input.style.color = "#fff";
                    input.style.transition = "all 0.3s ease";

                    input.addEventListener("focus", () => {
                        input.style.border = "1px solid #3b82f6";
                        input.style.boxShadow = "0 0 6px rgba(59,130,246,0.5)";
                    });
                    input.addEventListener("blur", () => {
                        input.style.border = "1px solid rgba(255,255,255,0.15)";
                        input.style.boxShadow = "none";
                    });

                    row.appendChild(label);
                    row.appendChild(input);
                    return { row, input };
                };

                // 手机号/邮箱输入行
                const { row: accountRow, input: accountInput } = createInputRow("手机号/邮箱", "text", "请输入手机号或邮箱");
                // 验证码输入行
                const { row: verifyCodeRow, input: verifyCodeInput } = createInputRow("", "text", "请输入验证码");
                // 修改验证码输入框样式，确保与按钮在同一行
                verifyCodeInput.style.width = "60%"; // 减去按钮宽度和间距
                verifyCodeInput.style.marginRight = "10px";
                verifyCodeInput.style.display = "inline-block";
                verifyCodeInput.style.marginLeft = "-10px";
                // 修改验证码行样式
                verifyCodeRow.style.display = "flex";
                verifyCodeRow.style.alignItems = "center"; // 确保垂直居中
                verifyCodeRow.style.width = "100%";
                verifyCodeRow.style.flexDirection = "row";
                verifyCodeRow.style.justifyContent = "space-between";


                // 密码输入行
                const { row: passwordRow, input: passwordInput } = createInputRow("密码", "password", "请设置密码");
                // 确认密码输入行
                const { row: confirmPwdRow, input: confirmPwdInput } = createInputRow("确认密码", "password", "请再次输入密码");

                // 发送验证码按钮
                const sendCodeRow = document.createElement("div");
                sendCodeRow.style.display = "flex";
                sendCodeRow.style.width = "100%";
                sendCodeRow.style.justifyContent = "flex-end";

                const sendCodeBtn = document.createElement("button");
                sendCodeBtn.className = "comfy-btn";
                sendCodeBtn.innerText = "发送验证码";
                sendCodeBtn.style.padding = "6px 6px";
                sendCodeBtn.style.width = "100px";
                sendCodeBtn.style.borderRadius = "6px";
                sendCodeBtn.style.border = "none";
                sendCodeBtn.style.background = "linear-gradient(135deg, #3b82f6, #2563eb)";
                sendCodeBtn.style.color = "#fff";
                sendCodeBtn.style.fontSize = "14px";
                sendCodeBtn.style.cursor = "pointer";
                sendCodeBtn.style.transition = "all 0.25s ease";
                sendCodeBtn.style.display = "inline-block";


                let countdown = 0;
                let countdownTimer = null;

                sendCodeBtn.onclick = async () => {
                    const account = accountInput.value.trim();
                    if (!account) {
                        showToast("⚠️ 请输入手机号或邮箱", "error");
                        return;
                    }

                    if (countdown > 0) return;

                    // 开始倒计时
                    countdown = 60;
                    sendCodeBtn.disabled = true;
                    sendCodeBtn.style.opacity = "0.7";
                    sendCodeBtn.innerText = ` ${countdown}s`;

                    countdownTimer = setInterval(() => {
                        countdown--;
                        sendCodeBtn.innerText = ` ${countdown}s`;
                        if (countdown <= 0) {
                            clearInterval(countdownTimer);
                            sendCodeBtn.disabled = false;
                            sendCodeBtn.style.opacity = "1";
                            sendCodeBtn.innerText = "发送验证码";
                        }
                    }, 1000);

                    // 调用发送验证码接口
                    try {
                        const resp = await api.fetchApi("/my_node/send_message", {
                            method: "POST",
                            body: JSON.stringify({ email: account })
                        });
                        const data = await resp.json();
                        // alert("保存结果: " + data.msg);
                        // const resp = await fetch(`https://mojieaigc.com/api/verification?email=${account}&turnstile=`, {
                        //     method: "GET"
                        // });
                        // const data = await resp.json();
                        console.log("验证码发送接口返回数据:", data);
                        if (data.success) {
                            showToast("✅ 验证码发送成功", "success");
                        } else {
                            showToast(`❌ 验证码发送失败: ${data.message || "未知错误"}`, "error");
                            // 发送失败时清除倒计时
                            clearInterval(countdownTimer);
                            countdown = 0;
                            sendCodeBtn.disabled = false;
                            sendCodeBtn.style.opacity = "1";
                            sendCodeBtn.innerText = "发送验证码";
                        }
                    } catch (error) {
                        showToast(`❌ 接口请求失败: ${error.message}`, "error");
                        // 请求失败时清除倒计时
                        clearInterval(countdownTimer);
                        countdown = 0;
                        sendCodeBtn.disabled = false;
                        sendCodeBtn.style.opacity = "1";
                        sendCodeBtn.innerText = "发送验证码";
                    }
                };

                verifyCodeRow.appendChild(sendCodeBtn);

                // 注册按钮
                const registerRow = document.createElement("div");
                registerRow.style.display = "flex";
                registerRow.style.justifyContent = "center";
                registerRow.style.width = "100%";
                registerRow.style.marginTop = "10px";

                const registerBtn = document.createElement("button");
                registerBtn.className = "comfy-btn";
                registerBtn.innerText = "注 册";
                registerBtn.style.padding = "8px 16px";
                registerBtn.style.borderRadius = "6px";
                registerBtn.style.border = "none";
                registerBtn.style.background = "linear-gradient(135deg, #3b82f6, #2563eb)";
                registerBtn.style.color = "#fff";
                registerBtn.style.fontWeight = "600";
                registerBtn.style.cursor = "pointer";
                registerBtn.style.transition = "all 0.25s ease";
                registerBtn.style.boxShadow = "0 3px 8px rgba(37,99,235,0.4)";

                registerBtn.onmouseenter = () => {
                    registerBtn.style.transform = "translateY(-1px)";
                    registerBtn.style.boxShadow = "0 6px 12px rgba(37,99,235,0.6)";
                };
                registerBtn.onmouseleave = () => {
                    registerBtn.style.transform = "translateY(0)";
                    registerBtn.style.boxShadow = "0 3px 8px rgba(37,99,235,0.4)";
                };

                registerBtn.onclick = async () => {
                    const account = accountInput.value.trim();
                    const verifyCode = verifyCodeInput.value.trim();
                    const password = passwordInput.value.trim();
                    const confirmPwd = confirmPwdInput.value.trim();

                    if (!account || !verifyCode || !password || !confirmPwd) {
                        showToast("⚠️ 所有字段不能为空", "error");
                        return;
                    }

                    if (password !== confirmPwd) {
                        showToast("⚠️ 两次密码输入不一致", "error");
                        return;
                    }

                    registerBtn.disabled = true;
                    registerBtn.innerText = "注册中...";
                    registerBtn.style.opacity = "0.7";

                    try {
                        // 调用注册接口
                        const resp = await api.fetchApi("/my_node/register", {
                            method: "POST",
                            body: JSON.stringify({ 
                                email: account,
                                password: password,
                                confirmPassword: confirmPwd,
                                verification_code: verifyCode
                            })
                        });
                        const data = await resp.json();
                        if (data.success) {
                            showToast("✅ 注册成功", "success");
                            console.log("注册成功信息:", data); // 打印成功信息
                        } else {
                            showToast(`❌ 注册失败: ${data.message || "未知错误"}`, "error");
                        }
                    } catch (error) {
                        showToast(`❌ 注册请求失败: ${error.message}`, "error");
                    } finally {
                        registerBtn.disabled = false;
                        registerBtn.innerText = "注 册";
                        registerBtn.style.opacity = "1";
                    }
                };

                registerRow.appendChild(registerBtn);

                // Toast 提示框
                const showToast = (message, type = "info") => {
                    const toast = document.createElement("div");
                    toast.textContent = message;
                    toast.style.position = "fixed";
                    toast.style.bottom = "30px";
                    toast.style.left = "50%";
                    toast.style.transform = "translateX(-50%)";
                    toast.style.background =
                        type === "success"
                            ? "rgba(16,185,129,0.9)"
                            : type === "error"
                                ? "rgba(239,68,68,0.9)"
                                : "rgba(59,130,246,0.9)";
                    toast.style.color = "#fff";
                    toast.style.padding = "10px 20px";
                    toast.style.borderRadius = "8px";
                    toast.style.boxShadow = "0 4px 12px rgba(0,0,0,0.3)";
                    toast.style.fontSize = "14px";
                    toast.style.transition = "opacity 0.5s ease, transform 0.5s ease";
                    toast.style.opacity = "0";
                    toast.style.zIndex = "9999";

                    document.body.appendChild(toast);
                    setTimeout(() => {
                        toast.style.opacity = "1";
                        toast.style.transform = "translateX(-50%) translateY(-10px)";
                    }, 50);

                    setTimeout(() => {
                        toast.style.opacity = "0";
                        toast.style.transform = "translateX(-50%) translateY(0)";
                        setTimeout(() => toast.remove(), 500);
                    }, 2500);
                };

                // 加入容器
                container.appendChild(accountRow);
                container.appendChild(verifyCodeRow);
                container.appendChild(passwordRow);
                container.appendChild(confirmPwdRow);
                container.appendChild(registerRow);

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
