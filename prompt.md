---

# Agent 指令（含前端）｜美股“公开信息 → NLP → 信号提醒”系统 · MVP

## 角色与目标

你是资深平台/全栈工程师 + NLP/量化工程师。请在**单一代码仓库（monorepo）**内实现**端到端 MVP**：公开信息采集→NLP/事件抽取→信号融合与置信度→REST API→**前端控制台**→Slack 告警→基础回测。**首次启动即可跑通**并产出可查看的信号列表。

---

## 技术栈（必须）

* **后端**：Python 3.11+ · FastAPI + Uvicorn · Prefect 2.x（编排）
* **NLP**：spaCy、Transformers、sentence-transformers（FinBERT、all-mpnet-base-v2）
* **DB**：Postgres 15 + `pgvector`（SQLAlchemy + Alembic）
* **缓存/队列**：Redis（MVP 可仅做缓存）
* **容器**：Docker + docker-compose
* **告警**：Slack Incoming Webhook
* **前端**：Next.js 14+（App Router, TypeScript）+ TailwindCSS + shadcn/ui + SWR/React Query + Recharts（小型图表）

---

## 环境变量（根目录 `.env`）

```
POSTGRES_URL=postgresql+psycopg://user:pass@db:5432/signals
REDIS_URL=redis://redis:6379/0
SLACK_WEBHOOK=https://hooks.slack.com/services/xxx/yyy/zzz
FINBERT_MODEL=ProsusAI/finbert
EMBED_MODEL=sentence-transformers/all-mpnet-base-v2
NEWS_FEEDS=https://feeds.a.dj.com/rss/RSSMarketsMain.xml,https://www.nasdaq.com/feed/rssoutbound
API_PORT=8000
WEB_PORT=3000
API_BASE_URL=http://api:8000
WEB_PUBLIC_API=http://localhost:8000        # 前端本地请求后端时使用
```

---

## 仓库结构（必须）

```
repo/
  docker-compose.yml
  .env.example
  README.md
  api/                     # Python 后端
    app/
      api/                 # FastAPI 路由
        __init__.py
        signals.py
        documents.py
        tickers.py
        health.py
        backtest.py
      core/
        config.py
        logging.py
        deps.py
        calibrator.py
      db/
        base.py
        models.py
        session.py
        migrations/
        ddl/               # 扩展/索引原始SQL（含 CREATE EXTENSION vector）
      nlp/
        pipeline.py        # NER/情绪/embedding
        events.py          # 事件抽取（规则）
        novelty.py         # 新颖度计算
      flows/
        ingest.py          # Prefect Flow（采集→抽取→入库→NLP→事件→信号→告警）
        schedule.py
      services/
        fuse.py            # 置信度融合与打分
        notifier.py        # Slack 推送
        snapshots.py       # HTML/PDF 存证（MVP 本地目录）
      backtest/
        event_study.py
      tests/
        ...
    alembic.ini
    requirements.txt
  web/                     # Next.js 前端
    app/
      layout.tsx
      page.tsx             # / → 跳转 /signals
      signals/
        page.tsx           # 列表+过滤器+抽屉
        components/
          Filters.tsx
          SignalTable.tsx
          EvidenceDrawer.tsx
      documents/
        [id]/page.tsx      # 文档详情（摘录、实体、事件、快照链接、迷你行情图）
      tickers/
        [symbol]/page.tsx  # 单票据页（信号+迷你行情图）
      api/                 # （可选）前端代理/Mock
        signals/route.ts
    lib/types.ts
    lib/api.ts
    lib/utils.ts
    public/
    styles/globals.css
    package.json
    tsconfig.json
    next.config.js
  data/
    snapshots/             # 原文快照（MVP 本地）
```

---

## 数据库 Schema（必须实现）

沿用以下表（SQLAlchemy + Alembic），并创建关键索引/扩展：

* `companies, tickers`
* `documents(source, url, title, published_at, fetched_at, raw_text, html_snapshot_path, content_hash UNIQUE, lang, embedding VECTOR(768), sentiment, sentiment_score, meta JSONB)`

  * 索引：`published_at DESC`、`source`、`content_hash`、`embedding ivfflat(vector_cosine)`
* `entities, document_entities`
* `events(document_id, event_time, event_type, headline, confidence_extraction, affected_ticker, payload JSONB)`

  * 索引：`(affected_ticker, event_time DESC)`
* `signals(ticker_id, signal_time, base_score, confidence, direction, label, decay_seconds, meta)`

  * 索引：`(ticker_id, signal_time DESC)`
* `signal_evidence(signal_id, kind, ref_id, weight, details JSONB)`
* `prices(ticker_id, ts, ohlcv...) UNIQUE(ticker_id, ts)`
* `backtests(name, params, result)`
* `audit_log(occurred_at, actor, action, target_type, target_id, payload)`

---

## 核心流程（Prefect Flow · 必须可跑）

`api/app/flows/ingest.py`：

1. 读取 `NEWS_FEEDS`（RSS/HTTP，有网络不通时使用内置 mock）。
2. `trafilatura` 抽正文 → `content_hash` 去重。
3. 保存 HTML 快照到 `data/snapshots/`（封装 `services/snapshots.py`）。
4. NLP：NER + Ticker 归因、FinBERT 情绪、`sentence-transformers` 生成 `embedding`。
5. 事件抽取：规则识别（`guidance_up/down`, `mna`, `litigation`, …）。
6. 新颖度：与近 30 天同票据文档 `embedding` 做余弦距离→归一化\[0,1]。
7. 融合打分（见“置信度公式”），写入 `signals` 与 `signal_evidence`。
8. Slack 告警（无 webhook 则 DRY-RUN 打日志）。
9. `audit_log` 记录 `ingest_doc` / `create_signal` / `send_alert`。

---

## 置信度计算（实现到 `services/fuse.py`）

```
buzz_score = sigmoid(a * buzz_z) clipped [0,1]    # a=1.0
base_score = w_src*src_weight + w_novel*novelty + w_evt*evt_prior + w_buzz*buzz_score
consistency_adj  = k_cons * insider_contra        # insider_contra ∈ {-1,0,+1}
uncertainty_adj  = - k_unc * model_uncertainty
time_decay = exp(-Δt / τ)

raw_score = clip((base_score + consistency_adj + uncertainty_adj) * time_decay, 0, 1)
confidence = Calibrator.transform(raw_score)      # 先恒等映射，保留接口
```

默认权重（写入配置，可回测调参）：
`w_src=0.35, w_novel=0.25, w_evt=0.25, w_buzz=0.15, k_cons=0.1, k_unc=0.15, τ=86400`

---

## 后端 REST API（必须）

* `GET /health` → `{status:"ok"}`
* `GET /signals?q=&min_confidence=&date_from=&date_to=&limit=`

  * 返回：`{ items:[{id,ticker,signal_time,confidence,base_score,label,direction,sources:[{kind,id,title}]}], total }`
* `GET /documents/{id}` → 文档元数据+摘录+实体+事件+`html_snapshot_path`
* `GET /tickers/{symbol}/signals`
* `POST /backtest/event-study` → 输入 `event_types, window, min_confidence`，返回均值超额收益/t 值/样本数

---

## 前端页面（必须）

### 1) `/signals`

* 顶部过滤器：Ticker/公司搜索、`Min Confidence` 滑块（默认 0.6）、日期范围（可选）。
* 表格：`Ticker | Time | Confidence(进度条) | Label | Sources`；分页；点击行→右侧 **Evidence Drawer**。
* Evidence Drawer：显示 `confidence/base_score`、规则构成（源/新颖度/事件/舆情/一致性等要素）、来源条目（可点击打开 `/documents/{id}`），“Open Snapshot” 外链（指向 `html_snapshot_path`）。

### 2) `/documents/[id]`

* 标题、来源、发布时间、情绪分值、新颖度指标、主要实体与事件列表。
* 文本摘录（前 500–800 字）；“查看快照”按钮。
* **迷你行情图**（Recharts）：`published_at` 前后若干点（无真实行情则用 mock）。

### 3) `/tickers/[symbol]`

* 该票据的近期信号列表（与 `/signals` 相同列）。
* 迷你行情图（近 5–20 根 K 线或折线），标注信号时间点。

### 4) 交互与可用性

* 数据获取使用 SWR/React Query；轮询 10s（MVP，不做 SSE）。
* a11y：所有交互控件有 label，可键盘操作；色彩对比达标。
* 空态与加载态：骨架屏/占位。
* 错误提示：toast/inline error。

> UI 风格：Tailwind + shadcn/ui，干净、圆角、阴影、Varied font sizes；移动端 1 列，桌面端 2–3 列布局。

---

## 前后端联通

* 前端通过 `WEB_PUBLIC_API` 访问后端（开发时 `http://localhost:8000`）。
* 前端封装 `lib/api.ts`：`getSignals`, `getDocument`, `getTickerSignals`。
* 若后端暂无数据，前端 `signals/route.ts` 支持 **mock fallback**，以保证页面可演示。

---

## 合规与治理（代码中需体现）

* 仅处理公开来源；`documents` 存 URL 与 `html_snapshot_path`。
* 高等级提醒需：（来源权重≥0.8）或（新颖度≥0.7）；无二次来源时在 `meta.requires_second_source=true` 并在前端以黄色标签显示“Needs 2nd source”。
* `audit_log` 记录关键动作。前端 Evidence Drawer 中显示审计 ID 与触发时间。

---

## 监控与日志

* `/health` 路由。
* 结构化 JSON 日志（包括每次信号的 `ticker/base/conf/features`）。
* docker-compose logs 可看到端到端链路。

---

## 验收标准（全部必须通过）

1. `docker-compose up --build -d` 后：

   * 自动初始化 Postgres（含 `vector` 扩展与迁移）
   * Prefect worker 启动并运行一次 `ingest`，入库 ≥5 条 `documents`，产出 ≥1 条 `signals`
2. 打开 `http://localhost:3000/signals`：

   * 能看到列表；过滤器生效；点击行弹出 Evidence Drawer
   * 点击来源条目可跳转 `/documents/{id}`；能看到摘录、实体、事件、快照链接、迷你行情图
3. `GET http://localhost:8000/signals` 返回包含 `confidence` 字段的 JSON
4. Slack 配置存在则收到卡片推送；未配置则日志中明确标注 DRY-RUN
5. `POST /backtest/event-study` 对 `guidance_up`（mock 数据）能返回统计结果
6. README 包含：启动步骤、环境变量、截图（/signals、/documents）与示例 `curl`

---

## 运行说明（README 中写清）

* `cp .env.example .env`
* `docker-compose up --build -d`
* 首次迁移：`docker compose exec api alembic upgrade head`
* 手动触发采集：`docker compose exec api python -m app.flows.ingest --once`
* 访问前端：`http://localhost:3000/signals`

---

## 质量与测试

* 后端：`pytest` 覆盖 `services/fuse.py`、`nlp/novelty.py`（单调性/边界）
* 前端：Playwright 基本 e2e（能加载列表、打开抽屉、跳转文档页）
* 代码检查：mypy（宽松）、ruff/eslint

---

## 可扩展占位（接口保留）

* `services/snapshots.py` 未来切换 S3（WORM/版本）
* `nlp/events.py` 模型化接口（可更换为零样本/LLM）
* `core/calibrator.py` `fit/transform`（Isotonic/Platt + 回测样本）
* 前端 `/settings` 占位（阈值管理，MVP 可隐藏）

---

请严格按以上规范实现，**首次启动即可端到端跑通**并在前端看到 `signals` 与 `documents`。
