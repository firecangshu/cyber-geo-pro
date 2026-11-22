# 腾讯云函数部署指引（vibe coding 友好版）

> 目标：把 server/ 目录的零依赖诊断引擎部署为公网可达的 HTTPS 服务，
> 供 SkillPay 环境的 Agent 调用。预计耗时：半天。

## 方案选择

| 方案 | 月成本 | 适用 |
|------|--------|------|
| **腾讯云函数 SCF（推荐）** | 免费额度内≈0（万次级调用） | 按次付费天然匹配，试水首选 |
| 轻量应用服务器 | ~50 元/月 | 后续要加定时复测/看板时再迁 |

## SCF 部署步骤

1. **开通服务**：腾讯云控制台 → 云函数 SCF → 创建函数 → 运行环境 Python 3.13
2. **上传代码**：把 `server/` 下 `app.py`、`core_diagnosis.py` 打 zip 上传
   （执行入口改为 `app.handler`——需先按 `app.py` 内 `handler()` 注释完成 event 解析适配）
3. **环境变量**（函数配置 → 环境变量）：
   - `GEO_API_TOKEN`：自定义接入凭证（随机长字符串）
   - `PORT`：不需要（SCF 托管）
4. **触发器**：创建 API 网关触发器，拿到公网 HTTPS 地址 → 即 `GEO_API_ENDPOINT`
5. **本地验收**：
   ```
   set GEO_API_ENDPOINT=<网关地址>
   set GEO_API_TOKEN=<你的凭证>
   set GEO_API_MOCK=            # 关闭 mock
   python scripts/geo_api_client.py --brand "测试品牌" --payment-token "test"
   ```
   返回 `ok: true` 且含 `data_source_level` 即部署成功
6. **安全项**：凭证不要提交进任何 git 仓库；SCF 日志确认不打印请求体

## L2/L3 实测能力升级（付费版上线后迭代）

当前部署为 L1 理论诊断（`core_diagnosis.py` 的 TODO 桩）。
升级实测探测时：
1. 在 `core_diagnosis.py` 的 `run_layer3_probe()` 桩内接入大模型 API（密钥走 SCF 环境变量，勿入代码）
2. 按查询矩阵（5 意图 × N 引擎 × 轮数）发起真实探测，解析命中/排名/情感
3. 用评分公式计算实测分，替换 `data_source_level` 标注为「实测」
4. **成本控制**：标准深度 1 轮、深度 3 轮；单次诊断 API 成本预估 5-20 元，
   对照定价 59/99 元仍留足毛利——上线前先跑 10 次实测记录真实成本再定终价

## 域名与合规

- API 网关默认域名即可用；正式化后可绑自有域名
- 服务仅做只读诊断，无用户注册体系，不涉及个人信息收集；隐私声明见 SKILL.md
