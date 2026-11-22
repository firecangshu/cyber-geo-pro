
## v1.5.0（2026-10-23）· 收费升级为官方 A2M 协议（业务流程不变）

**只改收费闸门，业务一行未动**：诊断三层逻辑、报告渲染模板、呈现纪律、
质量门禁、两档一致性、方法论脚注全部保留原样。

- **流程改为五步**：需求收集 → **概述与报价** → **支付闸门** → 履约+诊断+报告呈现
  （原「支付确认」一步拆为「概述」与「支付闸门」两步；概述在收费之前，
  让用户先看清诊断范围与价格再决定付不付）
- **客户端改两段式**（`scripts/geo_api_client.py`）：
  - `probe`（无凭证）→ 服务端 402 + `Payment-Needed` → 账单原文按 **0600** 落盘，
    **不进 stdout**（stdout 会进 Agent 日志）；退出码 **7 = 需要付费**
  - `complete`（携 `Payment-Proof`）→ 原样重放同一 body → 200 + 完整诊断报告
  - 支付凭证**只走请求头**、不进 body；支持 `--payment-proof-file`（凭证不经过命令行）
  - 旧形态 `--payment-token` / `X-Payment-Token` 已移除
- **闸门语义写进 SKILL.md 红线**：未付款 / 付款失败 / 凭证无效或过期 → 一律停在
  Step 3，提示「需完成支付才能继续」，**不执行诊断、不输出任何分数或免费替代内容**；
  付款成功后**自动继续** Step 4 直至交付成果，不需用户再次确认
- `references/api-contract.md` 同步官方 A2M 契约（`Payment-Needed` 账单 / `Payment-Proof` 头 /
  402 语义 / 退出码表 / 安全纪律）
- 新增 `scripts/test_client_a2m.py`：本地端到端验证（probe→402→账单落盘、缺凭证拒绝、
  伪造凭证不交付、有效凭证 200+报告、body 一致、凭证走头、mock 可用）—— 全部通过
- **服务端加固 4 处（已应用并部署）**：
  ① `GEO_REQUIRE_A2M=on` 时支付配置不齐直接 **503 失败关闭**，绝不降级到联调桩
  （原状：`GEO_PAYMENT_VERIFY=off` 时"非空即过"= **付费可绕过**，资金漏洞）；
  ② 订单随 SCF `/tmp` 清空时，用**支付宝验付结果为权威恢复订单**（钱已收一定交付）；
  ③ 履约确认 `TRADE_STATUS_INVALID` 视为已履约（重复确认不再 502 阻断）；
  ④ 请求体上限 1MB → **413**（分块丢弃后响应）+ 顶层异常兜底 → **500**（防 439 进程退出）
- **真实付款验收通过**：¥4.99 实付 → 验付 active → 履约 → **31 字段完整诊断报告**
  → 幂等重放 `already_fulfilled=true`（同一份报告、不重复扣费）；
  期间修掉 5 个"名实不符"问题：沙箱当生产 / `seller_id` 冒充 AppId /
  **部署包漏 `alipay_api.py`（钱收了报告没出）** / bootstrap 缺 `cd` → 443 /
  诊断端点插错类。详见内部《GEO服务端收费加固补丁清单》（私产文档，不随包公开）
# 更新日志 - cyber-geo-pro

## [上架完成] - 2026-09-24

Pay Skill 全链路发布完成，等待平台审核生效。

### 已完成
- SKILL.md 添加支付协议实现章节（402/Payment-Proof/验付/履约确认/幂等，10/10 关键词命中）
- 支付宝 AI 付一站式接入完成（服务 ID: API_34CBC058D2EA4433）
- SCF 云函数部署（cyber-geo-pro，公网 402 实测通过）
- SkillHub Pay Skill 发布 4 步全部提交（改造/上传/计费 4.99/验证）
- SkillPay 入驻确认（支付宝渠道已绑定 136****9813）

### 等待
- SkillHub 平台审核（内容+安全+支付能力），通过后付费榜自动收录

## [1.5.2] - 2026-09-20（服务端引擎版本）

定价调整：深度档 29.90 → **9.90 元/次**（标准档 4.99 不变）。

### 变更
- server/a2m_pay.py SKU_PRICES：深度 9.90（A2M 402 订单金额映射同步）
- SKILL.md Step 2 支付确认文案同步
- 发布包重新打包

### 定价依据
- 深度档差异化支撑待补强（当前两档硬差异仅样本规模 15 vs 45 条），9.9 作为过渡定价，
  待深度版独占项（置信区间/竞品同测/复测权益）实装后再评估回调

## [1.5.1] - 2026-09-20（服务端引擎版本 + 发布包）

定价调整：标准档 9.90 → **4.99 元/次**（深度档 29.90 不变）。

### 变更
- server/a2m_pay.py SKU_PRICES：标准 4.99（A2M 402 订单金额映射同步）
- SKILL.md Step 2 支付确认文案同步
- 发布包 cyber-geo-pro-1.4.0.zip 重新打包（含新定价文案）

### 定价依据
- 平台轻工具均价 ¥2 的 2.5 倍，进一步压低决策门槛；单次成本 <1 分，毛利仍 >98%

## [1.5.0] - 2026-09-20（服务端引擎版本）

支付宝 AI 付「AI按量付费」A2M 协议完整集成。

### 新增
- a2m_pay.py：A2M 协议模块——402 Payment-Needed 构造（RSA2 商家签名）、
  Payment-Proof 解码验付（alipay.aipay.agent.payment.verify SDK Model 类）、
  履约确认（alipay.aipay.agent.fulfillment.confirm）、订单持久化端口
- order_store.py：sqlite 订单状态机（PENDING_PAYMENT→PAID→PENDING_CONFIRM→FULFILLED）
- app.py 双模式支付分支：A2M 密钥就绪 → 官方 402 协议；未配置 → 联调桩回退
- 金额映射接入：标准 9.90 / 深度 29.90（PRD 3.1 定价）
- requirements.txt：alipay-sdk-python + pycryptodome（私产）
- 沙箱密钥配置就绪（AppId 由技术集成页下发，敏感值不入包）

### 验收
- 无 Payment-Proof → HTTP 402 + Payment-Needed，protocol 8 字段 / method 6 字段无缺失，
  service_id=api_mock_service_id，签名 RSA2，金额 9.90
- 离线回归 20/20 全绿
- 完整沙箱收银链路（需沙箱买家 2088 账号）待跑：官方 local_402_sandbox_pay.py 就绪

### 支付宝侧进度
- 产品开通申请已提交（商业生活服务/在线工具），预计最晚 2026-09-21 12:55 生效
- 剩余：服务注册 → 密钥配置（正式）→ 线上验证 → SkillHub 上传配价

## [1.4.0] - 2026-09-18（发布包版本对齐服务端引擎）

发布包正式升版：服务端功能（L3 实测/技术层/引擎横评/HTML 报告/复测 delta）全部
收进发布包所依赖的云端接口，包版本与引擎版本统一为 1.4.0，准备 SkillPay 上架。

### 打包说明
- 发布包仅含：SKILL.md / readme.md / changelog.md / references×3 / scripts/geo_api_client.py
- 排除项：server/（引擎与核心资产）、本地凭据文件、snapshots/、reports/、tests/、__pycache__
- 合规：全白名单扩展名、无外部模型名、无平台路径残留（打包时复扫）

## [1.4.0] - 2026-09-18（服务端引擎版本）

轮次 3 完成：F4 HTML 报告交付 + 基线快照/复测 delta。PRD v1.1.0 三轮全部完成。

- report_html.py：单文件 HTML 报告（内联 CSS 零外部资源，双击即开可转发）
- 基线快照 snapshots/<request_id>.json + 复测 delta（传 baseline_request_id 触发，任一侧理论值时诚实标注）
- 响应新增 html_report_file / html_report_b64 / delta
- 回归测试扩至 20 项；三引擎实测华为云 36 分 + 复测 35 分（delta -1 为 LLM 波动）

## [1.3.0] - 2026-09-18（服务端引擎版本）

轮次 2 收尾：F1.2 技术层真实检测 + 引擎横评进报告。

- tech_checks.py：18 项技术检测全真实 HTTP（可爬取性25/内容结构30/权威信号25/新鲜度20）
  + 18 bot robots.txt 放行矩阵
- engine_breakdown 每引擎命中分布 + 全未提及引擎的定向语料建议
- robots 物料增量模式（有实测只放行缺失 bot）/ 全量模板回退
- 实测：xfyun.cn 31/100（JS 站被抓出 12 fail）；科大讯飞 6 分（三引擎命中 0/5 · 1/5 · 0/5）

## [1.2.3] - 2026-09-18（服务端引擎版本）

讯飞星火 Lite 实测接入（第三引擎在役）。

- 浏览器自动化代操作完成订阅：护院鹅应用领取 Spark Lite 无限量包（并发5，至 2036-12-31）
- 凭据写入本地环境配置（私产禁止入包）；APIKey:APISecret 实测通过 HTTP 认证
- 跨引擎共识价值实证：同品牌单引擎 58 → 双引擎 48 → 三引擎 19 分

## [1.2.2] - 2026-09-18（服务端引擎版本）

讯飞星火适配器 + 单引擎故障隔离验证。

- xfc_adapter.py（凭证走环境变量，lite/generalv3.5/4.0Ultra 自动降级）
- 注册表扩至 5 家；故障隔离实测：星火未订阅模型（AppIdNoAuthError×6）自动跳过不影响双引擎
- MaaS 网关 HMAC 签名方案探测留档（凭据未注册该产品线）

## [1.2.1] - 2026-09-18（服务端引擎版本）

多引擎注册表 + 智谱 GLM 接入（第二引擎在役）。

- _available_engines() 按环境变量自动发现，配几个跑几个；单引擎故障隔离
- glm_adapter.py（glm-4-flash 免费档，ZHIPU_MODEL 可覆盖）
- 双引擎实测：腾讯会议 48 分（10 样本），成本 0.0057 元/次

## [1.2.0] - 2026-09-18（服务端引擎版本）

L3 实测探测接入（PRD 轮次 2 · 第一引擎）。

- 首引擎适配器（密钥走环境变量，兼容接口，限流重试）
- 双模式诊断分支：GEO_LIVE=1 + 密钥 → L3 实测；未配置/失败 → L1 回退（live_error 如实标注）
- 实测解析：命中/近似排名/情感启发式/回答摘录存档；盲区矩阵改实测驱动
- 首测：腾讯会议 58 分（5 样本），成本 0.0033 元/次

## [1.1.1] - 2026-09-18

产出自检层（质量门禁）：档位分免费/付费，质量不分。

- quality_gate：物料包 11 项自动校验，不过禁止渲染并免费重出
- tests/test_golden.py 黄金样例回归（14 项）；SKILL.md 渲染纪律新增两档一致性条款

## [1.1.0] - 2026-09-17

付费版拆分首发（母本：cyber-geo v1.4.0）。

- 付费服务流程：需求收集 → 支付确认（付费门禁）→ 云端调用 → 报告渲染
- 云端诊断引擎接口契约 v1 + 零依赖客户端（含 mock 联调模式）
- 服务端 HTTP 入口 + 核心诊断引擎骨架（L1 理论诊断可用）
- SkillPay 支付核验对接桩（透传桩仅限联调，对接前禁止上架）
- 核心诊断资产自包内后移至服务端；异常路径全面不降级（防白嫖红线）

## [1.0.0] - 2026-09-17

付费版包骨架：壳化 SKILL.md + references（api-contract/backend-deploy/freemium-split）
+ scripts/geo_api_client.py + server/（app.py + core_diagnosis.py L1）。
