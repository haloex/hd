# HDHive GitHub Actions 多账号签到

这个版本用于部署到 GitHub Actions：

- 支持多个 HDHive 账号。
- 每天定时触发，并随机延迟一段时间后签到。
- 签到后通过 Telegram Bot 通知成功、已签到、失败、Cookie 过期。
- Cookie、Bot Token、Chat ID 全部放在 GitHub Secrets，不要写进代码。

## 仓库文件

把这个目录里的文件放到你的 GitHub 仓库根目录：

```text
hdhive_checkin_multi.py
.github/workflows/hdhive-checkin.yml
```

## 配置 GitHub Secrets

进入你的 GitHub 仓库：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

需要添加 3 个 Secret。

### 1. HDHIVE_ACCOUNTS

值是 JSON 数组。每个账号一个对象：

```json
[
  {
    "name": "账号1",
    "cookie": "csrf_access_token=...; hdh_sa_token=...; hdh_uid=...; refresh_token=...; token=..."
  },
  {
    "name": "账号2",
    "cookie": "csrf_access_token=...; hdh_sa_token=...; hdh_uid=...; refresh_token=...; token=..."
  }
]
```

Cookie 必须是完整的一行，包含这几个值：

```text
csrf_access_token
hdh_sa_token
hdh_uid
refresh_token
token
```

### 2. TG_BOT_TOKEN

在 Telegram 找 `@BotFather`：

```text
/newbot
```

创建 bot 后复制 token，格式类似：

```text
1234567890:AA...
```

### 3. TG_CHAT_ID

先给你的 bot 发一条消息，然后打开：

```text
https://api.telegram.org/bot你的TG_BOT_TOKEN/getUpdates
```

返回 JSON 里找到：

```json
"chat": {
  "id": 123456789
}
```

这个 `id` 就是 `TG_CHAT_ID`。

如果要发到群里，把 bot 拉进群，给群里发一条消息，再用同样的 `getUpdates` 找群的 `chat.id`。群 ID 通常是负数。

## 运行时间

workflow 默认每天：

```text
09:00 Asia/Shanghai
```

触发，然后随机等待 0 到 6 小时再签到。

你可以改 `.github/workflows/hdhive-checkin.yml` 里的：

```yaml
RANDOM_DELAY_SECONDS: 21600
```

例如随机 0 到 2 小时：

```yaml
RANDOM_DELAY_SECONDS: 7200
```

## 手动测试

进入仓库 Actions 页面，打开 `HDHive Checkin`，点：

```text
Run workflow
```

手动运行时不会随机等待，会立刻签到。

## 通知含义

```text
[SUCCESS] 签到成功
[ALREADY] 今天已经签到过了
[EXPIRED] Cookie 可能过期，需要重新复制
[FAILED] 其他失败，需要看 Actions 日志
```

## 注意

GitHub Actions 的定时任务可能会有几分钟到几十分钟延迟，这是 GitHub 自身调度造成的。

随机 sleep 会占用 Actions 运行分钟数。公开仓库一般影响不大；私有仓库如果很在意分钟数，可以后续换成 Cloudflare Workers、VPS、青龙面板等方式。
