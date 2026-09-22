# 公网部署脚本说明

## 一行命令让别人访问

```bash
bash scripts/pct_public.sh start
```

执行后输出形如：
```
公网访问(任何人可访问):
  https://sheets-casting-lynn-mpeg.trycloudflare.com

内网访问:
  http://master:7861
```

把那个 `https://...trycloudflare.com` 链接发给任何人即可访问,无需安装、无需登录、不依赖内网。

## 脚本一览

| 脚本 | 作用 |
| :--- | :--- |
| `pct_service.sh` | 仅管理 Gradio 应用(PID 文件 + 启动/停止/状态) |
| `pct_public.sh` | 一站式:启动应用 + Cloudflare Tunnel,打印公网 URL |

## 常用命令

```bash
# 启动(Gradio + 公网隧道)
bash scripts/pct_public.sh start

# 查看状态 / 公网 URL
bash scripts/pct_public.sh status
bash scripts/pct_public.sh url

# 实时日志
bash scripts/pct_public.sh logs           # Gradio 应用日志
tail -f /tmp/pcf_tunnel_7861.log          # Tunnel 日志
tail -f /tmp/pct_cron.log                 # cron 自愈日志

# 重启 / 停止
bash scripts/pct_public.sh restart
bash scripts/pct_public.sh stop
```

## 自动保活(已配置)

`/tmp/pct_cron_check.sh` 由 crontab 每分钟调用一次:
- 检测 `http://127.0.0.1:7861` → 不健康就重启 Gradio
- 检测 `cloudflared tunnel ...` 进程 → 不存在就重启 Tunnel
- 日志写入 `/tmp/pct_cron.log`

服务器重启后只需执行 `bash scripts/pct_public.sh start` 即可恢复。

## 公网 URL 的特性

- ✅ **任何人**(无需在内网、无需安装 VPN)都能访问
- ✅ **HTTPS** 自带证书,浏览器无警告
- ✅ **零配置**,无需 Cloudflare 账号
- ⚠️ **72 小时有效**(Cloudflare Quick Tunnel 限制)
- ⚠️ 每次重启 URL 会变化,需要重新发给用户

如需长期固定域名,在 https://dash.cloudflare.com/ 创建账号 + 命名 Tunnel 即可(进阶)。

## 架构图

```
Internet (任意位置)
    │
    ↓ HTTPS
┌──────────────────────────────────────┐
│  Cloudflare Edge (自动 HTTPS + 缓存) │
└──────────────────────────────────────┘
    │
    ↓ QUIC/HTTP2 tunnel (cloudflared)
[本机服务器] cloudflared ─── http://127.0.0.1:7861 ──→ Gradio 应用
                                                  └─→ joblib 模型 + Magpie 特征
```
