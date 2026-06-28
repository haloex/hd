# HDHive GitHub Actions 多账号签到

用于部署到 GitHub Actions：

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

## 推荐的 Secrets 配置

进入 GitHub 仓库：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

推荐把每个账号拆成独立 Cookie Secret。这样哪个账号过期，只改那一个 Secret，不用重写整段 JSON。

账号 1：

```text
HDHIVE_ACCOUNT_1_NAME
HDHIVE_COOKIE_1
```

账号 2：

```text
HDHIVE_ACCOUNT_2_NAME
HDHIVE_COOKIE_2
```

账号 3 到账号 5 也已经在 workflow 里预留：

```text
HDHIVE_ACCOUNT_3_NAME / HDHIVE_COOKIE_3
HDHIVE_ACCOUNT_4_NAME / HDHIVE_COOKIE_4
HDHIVE_ACCOUNT_5_NAME / HDHIVE_COOKIE_5
```

`HDHIVE_ACCOUNT_X_NAME` 可以填邮箱或备注名，例如：

```text
596592413@qq.com
```

`HDHIVE_COOKIE_X` 填完整 Cookie，一行即可：

```text
csrf_access_token=...; hdh_sa_token=...; hdh_uid=...; refresh_token=...; token=...
```

Cookie 必须包含：

```text
csrf_access_token
hdh_sa_token
hdh_uid
refresh_token
token
```

## Telegram Secrets

还需要添加：

```text
TG_BOT_TOKEN
TG_CHAT_ID
```

`TG_BOT_TOKEN`：在 Telegram 找 `@BotFather`，用 `/newbot` 创建 bot 后复制 token。

`TG_CHAT_ID`：先给 bot 发一条消息，然后打开：

```text
https://api.telegram.org/bot你的TG_BOT_TOKEN/getUpdates
```

返回 JSON 里找到：

```json
"chat": {
  "id": 123456789
}
```

这个 `id` 就是 `TG_CHAT_ID`。如果发到群里，把 bot 拉进群，给群里发一条消息，再用 `getUpdates` 找群的 `chat.id`。群 ID 通常是负数。

## 旧 JSON 配置方式

脚本仍兼容旧的 `HDHIVE_ACCOUNTS`：

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

但更推荐用 `HDHIVE_COOKIE_1`、`HDHIVE_COOKIE_2` 这种独立 Secret。

如果同时配置了独立 Cookie 和 `HDHIVE_ACCOUNTS`，脚本会优先使用独立 Cookie。

## 运行时间

workflow 默认每天：

```text
01:00 Asia/Shanghai
```

触发，然后随机等待 0 到 30 分钟再签到。

对应配置：

```yaml
- cron: "0 17 * * *"
RANDOM_DELAY_SECONDS: 1800
```

GitHub Actions 的 cron 使用 UTC，所以 UTC 17:00 等于北京时间第二天 01:00。

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
