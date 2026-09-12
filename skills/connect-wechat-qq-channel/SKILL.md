---
name: "connect-wechat-qq-channel"
description: "接入/重扫 OpenClaw 微信(openclaw-weixin)与QQ Bot 通道。Use when 接入QQ/微信、扫码登录、重新扫描。"
---

# 接入 OpenClaw 微信 / QQ 消息通道

## 适用场景
用户要求接入、重扫、重新登录 OpenClaw 的微信或 QQ 消息通道（让 Agent 能收发该平台消息）。

## 先分类：微信要扫码，QQ 官方 Bot 不扫码
这两条是不同机制，先想清楚再动手：
- **微信（`openclaw-weixin`）**：扫码登录个人微信。通道 enabled 但 `configured:false` 时 = 未登录，需扫码。
- **QQ（`qqbot`）**：官方开放平台机器人，用 `appId` + `clientSecret`（token）连接，**不需要扫码**。已 connected 就不用动。若用户想要"个人 QQ 号扫码"，那是另一套（需另装协议插件），先向用户澄清，勿默认。

## 诊断通道状态
```
openclaw channels list --all
openclaw channels status                       # 总览 connected/running
openclaw channels status --channel <id> --json # 单通道详情：configured/running/connected
```
注意：`status --deep` 不是本版本有效参数（会报 unrecognized）。微信通道 id 是 `openclaw-weixin`，但 `--channel` 过滤可能不显示它；用 `list --all` 和 `status` 看。

复用 `openclaw channels list --all` 时通道可能显示为 `openclaw-weixin default: installed, configured, enabled` —— 要看 `openclaw channels status --channel openclaw-weixin --json` 的 `configured` 字段判断是否真登录（默认 account 无账号、`configured:false` = 未登录）。

## 微信扫码登录（必须由用户在终端跑）
`exec` 工具会**硬拦截**任何 `openclaw channels login ...` 命令（连 `--help` 都被拒），无法代跑交互式扫码。因此必须引导用户在 gateway 主机/OpenClaw 控制台的**真实终端**里执行：
```
openclaw channels login --channel openclaw-weixin
```
终端显示二维码 → 手机微信扫码 → 手机上确认授权 → 凭证自动保存。然后重启 gateway 生效：
```
openclaw gateway restart
```
- Web 控制台（含终端面板）：`http://127.0.0.1:18789/`（loopback，仅本机）
- 或让用户直接开 cmd / PowerShell / Windows Terminal 跑。

## 插件文档位置（如需查细节）
`~/.openclaw/npm/projects/tencent-weixin-*/node_modules/@tencent-weixin/openclaw-weixin/README.zh_CN.md`

## 验证
扫码 + 重启后，`openclaw channels status --channel openclaw-weixin --json` 的 `configured` 应变 `true`。向用户汇报：改动的通道、配置含义、微信需要其本人扫码、QQ 已连接的现状。
