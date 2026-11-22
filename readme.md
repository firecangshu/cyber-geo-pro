# 赛博GEO·诊断Pro（cyber-geo-pro）

> AI 搜索时代，你的品牌在 DeepSeek / 通义 / 豆包 / 讯飞等大模型答案里被提到了吗？
> 「赛博GEO·诊断Pro」是一套面向 **GEO（Generative Engine Optimization，生成式引擎优化）** 的品牌可见度诊断 Skill 资产包，按次付费，已作为腾讯 SkillHub SkillPay 付费 Skill 上架。

本仓库公开的是 **Skill 侧资产**：主入口、接口契约、部署指引与零依赖客户端。核心诊断引擎与服务端为私产，不在本仓库公开。

## 它能做什么

- 按 5 类用户意图构造探测查询，跨多个大模型引擎检查品牌提及情况
- 输出品牌可见度评分、归因分析与修复建议
- 支持「未支付 → 402 账单 → 支付确认 → 200 报告」的两段式调用闭环
- 客户端零第三方依赖，仅用 Python 标准库，可在任意 Agent 运行环境执行

## 仓库结构

```
cyber-geo-pro/
├── SKILL.md                       # 付费版主入口（收集参数 → 支付确认 → 调云端 → 渲染报告）
├── readme.md                      # 本文件
├── changelog.md                   # 版本记录
├── references/
│   ├── api-contract.md            # 客户端 / 服务端接口契约 + 支付协议对接说明
│   ├── backend-deploy.md          # 云函数部署指引与成本测算
│   └── freemium-split.md          # 免费 / 付费资产切分边界（防泄露清单）
└── scripts/
    ├── geo_api_client.py          # 诊断客户端（零依赖，含 mock 联调模式）
    └── test_client_a2m.py         # 客户端协议形态本地验证脚本
```

> 核心诊断引擎（`server/`）为私产，不在本仓库公开。

## 与免费版的分工

| | cyber-geo-lite（待建） | cyber-geo-pro（本包） |
|---|---|---|
| 定位 | 免费引流：评分 + 提及/未提及简报 | 付费变现：完整诊断 + 归因 + 修复药方 |
| 核心资产 | 无（只有展示层） | 全部在服务端执行 |
| 定价 | 0 元 | 标准深度 59 元/次，深度 99 元/次（参考，以支付页为准） |

资产切分边界见 `references/freemium-split.md`。

## 快速开始

### 1. mock 模式（无需服务端）

```bash
export GEO_API_MOCK=1
python scripts/geo_api_client.py probe --brand "示例品牌" --state-dir ".state/demo"
```

### 2. 本地协议自测

```bash
python scripts/test_client_a2m.py
# 预期输出：ALL PASS
```

### 3. 接入服务端

```bash
export GEO_API_ENDPOINT="https://your-endpoint.example.com"
export GEO_API_TOKEN="your-token"
python scripts/geo_api_client.py probe --brand "示例品牌" --state-dir ".state/demo"
```

> 凭证一律走环境变量，禁止硬编码进代码或提交到仓库。详见 `.gitignore`。
> 真实服务端需私产授权，公开仓库仅提供客户端与契约。

## 设计原则

1. **零依赖**：客户端仅用 Python 标准库，开箱即用
2. **凭证隔离**：所有密钥走环境变量，代码与参数中不落盘
3. **mock 联调**：本地无服务端也能跑通完整协议流程
4. **结构化错误**：所有异常以 JSON 返回，便于 Agent 消费

## 发布规范检查清单（对照 SkillHub）

- [x] `GEO_API_MOCK` 调试说明保留，服务端地址/凭证不入包
- [x] 全包仅白名单扩展名：.md / .py
- [x] 敏感值（密钥 / AppId / 企业主体 / 真实账单）已脱敏
- [x] `server/` 私产目录已从打包范围排除
- [x] 「未支付 → 402 → 重新确认 → 200」全链路实测通过

## 资产边界与声明

- 本仓库内容用于 Skill 资产分发与技术交流
- `references/freemium-split.md` 定义了免费 / 付费资产边界；服务端核心算法、评分基准表与私产目录不在公开范围
- 版本记录与接口文档中的敏感值均已脱敏
- 如需商用服务端能力，请联系作者获取授权

## 作者

firecangshu · GitHub: [@firecangshu](https://github.com/firecangshu)
