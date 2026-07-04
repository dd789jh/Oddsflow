# iOS 快捷指令设置指南

## 整体流程

```
X App 看到好视频 → 点分享 → 选快捷指令 → 自动转发到 Telegram 群
```

## 前置条件

1. 一台服务器 (VPS / 家里电脑 / 树莓派) 运行 webhook_server.py
2. Telegram Bot (从 @BotFather 获取)
3. iPhone 安装了「快捷指令」App

---

## 第 1 步: 部署 Webhook 服务器

### 在服务器上:

```bash
# 设置安全密钥 (记住这个值，iOS 快捷指令要用)
export WEBHOOK_SECRET=$(openssl rand -hex 16)
echo "你的密钥: $WEBHOOK_SECRET"

# 安装依赖
pip install -r requirements.txt

# 运行服务器
python webhook_server.py
```

服务器会在 `8899` 端口监听。

### 用 Docker:

```bash
export WEBHOOK_SECRET=$(openssl rand -hex 16)

docker run -d \
  --name x-to-telegram-webhook \
  -p 8899:8899 \
  -e WEBHOOK_SECRET=$WEBHOOK_SECRET \
  --restart unless-stopped \
  x-to-telegram python webhook_server.py
```

### 建议: 用 Cloudflare Tunnel 暴露服务 (免费，不需要公网 IP)

```bash
# 安装 cloudflared
# 然后:
cloudflared tunnel --url http://localhost:8899
```

这会给你一个 `https://xxx.trycloudflare.com` 的地址，iOS 直接用这个。

---

## 第 2 步: 创建 iOS 快捷指令

在 iPhone 上打开「快捷指令」App，创建新快捷指令:

### 基础版 (一键转发)

1. **接收** → 选择「共享表单输入」类型: URL
2. **添加动作** → 搜索「获取 URL 内容」(Get Contents of URL)
3. 配置:
   - URL: `https://你的服务器地址/forward`
   - 方法: `POST`
   - 请求体: `JSON`
   - 添加字段:
     - `url` → 「快捷指令输入」(Shortcut Input)
     - `caption` → (可选) 你的备注
   - 请求头:
     - `X-Webhook-Secret` → `你的WEBHOOK_SECRET值`
4. **添加动作** → 搜索「显示通知」
   - 标题: "已转发到 Telegram ✓"

### 进阶版 (带备注输入)

1. **接收** → 共享表单输入: URL
2. **添加动作** → 「要求输入」(Ask for Input)
   - 提示: "添加备注 (可选)"
   - 输入类型: 文本
   - 默认值: (留空)
3. **添加动作** → 「获取 URL 内容」
   - URL: `https://你的服务器地址/forward`
   - 方法: POST
   - 请求体: JSON
     - `url` → 「快捷指令输入」
     - `caption` → 「要求输入的结果」
   - 请求头:
     - `X-Webhook-Secret` → 你的密钥
4. **添加动作** → 「显示通知」
   - "已转发 ✓"

### 命名

给快捷指令起名: **"发到TG群"** 或 **"转发视频"**

---

## 第 3 步: 使用

1. 在 X App 打开一条有视频的推文
2. 点右下角 **分享按钮** (↗️)
3. 选择 **"发到TG群"** 快捷指令
4. (进阶版) 输入备注 → 点完成
5. 收到通知 "已转发到 Telegram ✓"
6. 去 Telegram 群查看 ✓

---

## 无服务器方案 (纯 iOS 快捷指令)

如果你不想部署服务器，可以用纯快捷指令实现 (只转发链接，不下载视频):

1. **接收** → 共享表单输入: URL
2. **添加动作** → 「获取 URL 内容」
   - URL: `https://api.telegram.org/bot你的TOKEN/sendMessage`
   - 方法: POST
   - 请求体: JSON
     - `chat_id` → 你的群组 ID
     - `text` → 「快捷指令输入」
     - `disable_web_page_preview` → false
3. **显示通知** → "已发送 ✓"

> 注意: 这种方式只发送链接，不会下载视频到 Telegram。
> Telegram 会自动预览链接，但不一定能展示视频。

---

## 故障排除

| 问题 | 解决 |
|------|------|
| 快捷指令超时 | 服务器处理是异步的，超时不影响实际转发 |
| 401 错误 | WEBHOOK_SECRET 不匹配，检查密钥 |
| 视频没发出来 | 检查服务器日志，可能 yt-dlp 需要更新 |
| 分享菜单没有快捷指令 | 确保快捷指令设置了「在共享表单中显示」|
