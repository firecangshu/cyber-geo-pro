# 诊断引擎接口契约 v1.1

> 本文档是客户端（scripts/geo_api_client.py）与服务端（server/）之间的契约。
> SkillPay 对接时以本文档为基准填桩，改动需同步更新客户端与服务端。
> v1.1 变更：新增语义对齐、修复物料包、方法论标注、计量表、复测基线字段（全部增量兼容）。

## 1. 端点

```
POST {GEO_API_ENDPOINT}/v1/diagnose
Content-Type: application/json; charset=utf-8
Authorization: Bearer {GEO_API_TOKEN}       # 接入凭证（服务间鉴权）

# ① 首次调用（未支付）：不带任何支付凭证
→ 402 Payment Required
  响应头：Payment-Needed: {账单原值 Base64URL}

# ② 支付后重放：body 与 ① 完全一致，凭证走请求头
Payment-Proof: {Payment-Proof 原值}         # 支付凭证（Base64URL，官方 A2M 契约）
→ 200 + 诊断报告数据（履约完成）
```

> **协议要点**（官方《个人接入》2.5 / A2M 契约）：
> - 支付凭证只走 **`Payment-Proof` 请求头**，**不进请求体**；
> - 首次调用无凭证 → 服务端返回 **402 + `Payment-Needed` 账单**（协议 8 字段 + 方法 6 字段）；
> - 账单原值**原样**传递（不解码、不截断、不改写），**不写入任何日志**；
> - 支付后**重放同一请求**（body 逐字节一致）→ 服务端验付通过才执行诊断；
> - 验付失败 / 未支付 / 凭证过期 → 一律回 **402**，且**不产出任何诊断内容**。

## 2. 请求体

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| brand | string | ✅ | 品牌名，空则 400 |
| category | string | ⬜ | 品类；空则服务端按「新兴品类」处理 |
| competitors | string[] | ⬜ | 竞品列表，最多取前 5 |
| url | string | ⬜ | 官网 URL；提供时 L1 技术层输出待办，L3 执行真实抓取 |
| depth | string | ⬜ | `标准`（默认）/ `深度`（3 轮复测，分数区间呈现） |
| ~~payment_token~~ | — | — | **已废弃**（v1.2 起支付凭证只走 `Payment-Proof` 请求头，不进 body） |
| client_version | string | ⬜ | 客户端版本号，用于兼容性统计 |
| baseline_request_id | string | ⬜ | v1.1：传上次诊断 request_id 触发复测，响应含 delta |
| engine_set | string[] | ⬜ | v1.1：指定探测引擎子集（默认全量首发引擎；L3 启用后生效） |

## 3. 响应体（200）

顶层字段：`ok=true`、`request_id`、`engine_version`、`data_source_level`（数据来源层级标注，**必须原样透传到报告**）、
`depth`、`baseline_request_id`，以及业务数据 `diagnosis / competitors / blind_spot_detail / attribution /
semantic_alignment / fix_checklist / fix_package / methodology_refs / methodology_footnote /
cost_strategy / scenario_playbook / retest_advice / metering / raw_meta`。

v1.1 新增字段：
| 字段 | 说明 |
|------|------|
| semantic_alignment | 语义对齐分 + 风险等级 + 失配点清单（L1 启发式预检版） |
| fix_package | 修复物料包 [{filename, content, method_ref, deploy_hint}]，可直接部署文件 |
| methodology_refs | 修复建议的方法依据列表（九法标注） |
| methodology_footnote | 报告尾注（方法来源声明，渲染时不得删改） |
| metering | 本次诊断计量 {engine_calls, tokens_est, cost_est_cny} |
| baseline_request_id | 复测基线（L3 复测功能启用后配合 delta 输出） |

字段明细与示例见 `scripts/geo_api_client.py` 内的 mock 数据（结构与真实接口一致，联调即验收）。

## 4. SkillPay 支付链路（官方机制 · 2026-09-18 调研确认）

> 依据：微信支付官方文档（pay.wechatpay.cn/doc/v3/merchant/4035576711）与在架 Pay Skill
> 真实契约（如 AI 旅行 trip-assistant-pro）。**本机制与旧版「透传桩」方向不同，服务端需按此改造。**

### 4.1 入驻五阶段（用户侧动作）

| 阶段 | 内容 | 说明 |
|---|---|---|
| ① | 申请微信支付商户号（普通直连商户） | 已有可跳过 |
| ② | SkillHub 注册开发者 → **认证企业主体** → 开通 SkillPay 并绑定商户号 | 最长链 |
| ③ | 开发 Skill：**声明 AI 支付插件** + 实现业务逻辑 | 本包已具备业务逻辑 |
| ④ | 支付接入：传统微信支付下单（Native/JSAPI）或 **X402 协议下单（用 SkillHub 入驻密钥鉴权）** | 本服务端改造点 |
| ⑤ | 上架分发，平台代为分发到各智能体平台，按调用量结算 | |

### 4.2 支付触发模型（服务端改造核心）

真实 Pay Skill 契约显示：**未支付调用由服务端返回 402 触发平台支付弹窗**，支付成功后平台继续业务：

```
客户端 → 服务端 POST /v1/diagnose（无支付凭证）
服务端 → 返回 HTTP 402
         头: WeixinPay-Required: true
         头: X-Out-Trade-No: <商户订单号>
         body: { "weixin_pay": {...}, "out_trade_no": "..." }   ← 平台据此弹 AI 专属卡授权
平台完成支付 → 携带支付成功凭证重放/继续调用 → 服务端核验后放行执行业务
```

### 4.3 服务端改造清单（SkillPay 入驻完成后执行）

1. `server/app.py` 增加 402 分支：请求未带有效支付凭证时，返回 402 + `WeixinPay-Required` +
   `X-Out-Trade-No` + `WeixinPay{...}` body（订单号由服务端生成并记录，防重放）
2. 支付成功回调/重放校验：按 X402 协议验证签名（SkillHub 入驻密钥）与订单状态，校验通过才执行诊断
3. 订单与支付状态落库（sqlite 即可，本服务单机低频）：out_trade_no → 状态机（未支付/已支付/已消费）
4. 防重放：同一 out_trade_no 已消费则直接放行；跨单重放拒绝
5. 计费模式配置在平台侧（按次/单价 4.99，标准与深度同价），服务端不做金额校验
6. 联调链路：`无凭证 → 402 → 模拟支付 → 带凭证重放 → 200 出报告`

> 红线不变：上述改造完成前，服务端不对外提供服务；发布包中的透传桩仅用于本地联调。

### 4.4 已调研的信息源（复查用）

- 微信支付 v3 文档「开发接入准备」merchant/4035576711（2026-08-27 更新）
- skillhub.cn/skillpay 官方页（支付确认链路三步骤）
- 在架 Pay Skill 请求/响应契约示例（AI 旅行）
- SkillHub 服务协议（2026-07-20 生效）

## 5. 错误码

| HTTP | error | 客户端行为 |
|------|-------|-----------|
| 400 | BAD_REQUEST / MISSING_BRAND | 回 Step 1 补齐输入 |
| 401 | AUTH_FAILED | 提示接入配置问题，不收费 |
| 402 | PAYMENT_REQUIRED | **需要付费**：未支付 / 凭证无效或过期。客户端退出码 **7**，业务必须停在此步，不执行诊断 |
| 404 | NOT_FOUND | 提示服务地址配置错误 |
| 429 | RATE_LIMITED | 提示稍后重试 |
| 5xx | SERVER_ERROR | 提示服务暂不可用，不收费 |

## 6. 频控

服务端按来源 IP 限 6 次/分钟。个人试水阶段够用；放量后改按 token 限流 + 队列。


## 附录 · 客户端两段式调用（v1.2 起）

```bash
# ① 取账单（无凭证）→ 退出码 7（需付费），账单原文 0600 落盘到 --state-dir
python scripts/geo_api_client.py probe \
  --brand "品牌名" [--category "品类"] [--competitors "A,B"] \
  [--url "https://..."] [--depth 标准|深度] --state-dir ".state/SESSION"

# ② 支付后重放（携 Payment-Proof）→ 退出码 0，返回完整诊断报告
python scripts/geo_api_client.py complete \
  --state-dir ".state/SESSION" \
  --payment-proof-file ".state/SESSION/payment-proof.txt"
```

| 退出码 | 含义 | Agent 应做什么 |
|---|---|---|
| 0 | 成功 | 直接进入报告渲染 |
| 2 | 配置缺失 / 接入凭证无效 | 提示服务方检查 `GEO_API_ENDPOINT` / `GEO_API_TOKEN`；本次不收费 |
| 3 | 参数缺失（品牌名 / 凭证 / 状态文件） | 回到 Step 1 补齐或先跑 probe；禁止占位符调用 |
| 5 | 服务端错误 | 告知"服务暂时不可用，本次不收费"，建议稍后重试 |
| 6 | 网络错误 | 同上 |
| **7** | **需要付费（PAYMENT_REQUIRED）** | **停在闸门**：提示用户完成支付才能继续；不执行诊断、不输出任何诊断内容 |

**安全纪律**
- 账单原文与支付凭证**均不进 stdout**（stdout 会进 Agent 日志）；
- 账单/凭证按 **0600** 落盘，用完即删；
- 支付凭证建议用 `--payment-proof-file` 传入，**不要用命令行**（会进 shell 历史与进程列表）；
- `probe` 与 `complete` 的 **body 必须逐字节一致**（由 `--state-dir` 保存原请求体保证）。
