# 面向监管制度与统计报表的可信 RAG 问答系统

基于检索增强生成（RAG）的银行业监管制度问答系统。从 Word / PDF / Excel 多源异构资料中检索依据，回答制度事实、条款阈值、统计取数、跨文件比较等问题，并返回可追溯证据（文件名、页码/段落/章节/条款、Sheet/单元格坐标）。

核心原则：**Evidence First（证据优先）**、**No Evidence, No Answer（无证据不答）**、**Text 与 Table 分路径处理**。

---

## 系统架构

```
用户问题
   ↓
Query Router（text / table / mixed / unknown）
   ↙                    ↘
文本检索 BM25        表格查询 Table Engine
（Word/PDF Chunk）    （Excel 结构化取数）
   ↘                    ↙
      证据 + 来源
        ↓
   答案生成器（规则/可选 LLM）
        ↓
   置信度 / 拒答
        ↓
   答案 + 证据 + 来源
```

## 目录结构

```
├── src/
│   ├── parsers/       Word/PDF/Excel 解析 + 统一 Schema
│   ├── knowledge/     文本切分与元数据
│   ├── retrieval/     BM25 / 向量 / 混合检索 / 重排
│   ├── table_query/   表格索引与取数引擎
│   ├── qa/            路由、答案生成、置信度、流水线
│   ├── evaluation/    评测器、指标、错误分析
│   ├── utils/         配置、日志
│   └── main.py        CLI 入口
├── data/
│   ├── documents/     制度文档（Word/PDF）
│   ├── tables/        统计报表（Excel）
│   └── questions/     测试问题集
├── tests/             pytest 测试
├── scripts/           样例数据生成脚本
├── reports/           数据检查/设计文档/错误分析/开发记录
├── indexes/           索引缓存（自动生成）
└── outputs/           评测输出（自动生成）
```

## 运行环境

- **Python 3.9+**（开发环境为 3.9.11）
- 跨平台（Windows / macOS / Linux），支持中文文件名

## 安装依赖

```bash
pip install -r requirements.txt
```

核心依赖：`python-docx`、`PyMuPDF`、`openpyxl`、`pandas`、`rank-bm25`、`jieba`、`rapidfuzz`、`numpy`、`pytest`。

> 注：如遇 pip 网络问题，可配置国内镜像或系统代理。

## 数据目录

将数据放入对应目录即可，系统会自动扫描：

| 目录 | 内容 |
|------|------|
| `data/documents/` | `.docx` / `.pdf`（`.doc` 需先转为 `.docx`） |
| `data/tables/` | `.xlsx` / `.xlsm`（`.xls` 需先转为 `.xlsx`） |
| `data/questions/` | 测试集 `.json` / `.csv` / `.xlsx` |

**无真实数据时**，可生成合成样例数据验证流程：

```bash
python scripts/generate_sample_data.py
```

## 使用方法

### 1. 建立索引

```bash
python -m src.main index          # 增量（缓存有效则复用）
python -m src.main index --force  # 强制重建
```

### 2. 提问

```bash
python -m src.main ask "商业银行资本充足率不得低于多少？"
python -m src.main ask "2024年一季度商业银行营业收入是多少亿元？"
```

### 3. 运行评测

```bash
python -m src.main evaluate                 # 自动使用 data/questions 下第一个测试集
python -m src.main evaluate --dataset data/questions/testset.json
```

### 4. 运行测试

```bash
python -m pytest
```

### 5. 端到端演示

```bash
python -m src.main demo
```

### 6.（可选）Web UI

安装 `streamlit` 后：

```bash
streamlit run app.py
```

## Text Retrieval 原理

- **BM25**（`rank-bm25` + `jieba` 中文分词）：对文件名、条款号、监管术语、数字、日期等精确关键词检索效果好。
- 额外把"条款号"（第X条）与"数字/百分号"作为独立 token，并对命中条款号/数字的 Chunk 做规则加分。
- 统一接口 `retrieve(query, top_k)`，返回 `[{text, score, source}]`。
- 向量检索（Embedding）为可选增强，未安装 `sentence-transformers` 时自动回退纯 BM25。

## Excel Query 原理

不把 Excel 转成文本交给模型猜测，而是结构化取数：

1. `openpyxl(data_only=True)` 读取计算值；合并单元格 forward-fill；
2. 自动识别表头行（年份/季度等多级表头）与标签列（机构/指标）；
3. 为每个数值单元格生成 `TableRecord`（行标签 + 列表头 + 单位 + 坐标）；
4. 解析问题意图（指标/期间/机构），用 `rapidfuzz` 模糊匹配定位单元格；
5. 返回数值 + 单位 + Sheet + 单元格坐标作为证据。

## Evidence 机制

每个答案附带：

- **文本证据**：文件名、页码、段落、章节、条款；
- **表格证据**：文件名、Sheet、行列、Excel 坐标（如 `D12`）、指标/期间/值/单位。

## No Evidence 机制

- **文本**：问题内容词在 Top-1 证据中的覆盖率低于阈值（0.6）时，返回"未找到足够证据"。
- **表格**：指标/期间/机构匹配不足，或指定期间无命中时，返回"未找到足够证据"。
- 使用 LLM 时，通过 System Prompt 约束其只能依据证据回答。

## 主要评测结果

| 指标 | 值 |
|------|-----|
| 总体正确率 | 100%（20/20） |
| 文本题正确率 | 100% |
| 表格题正确率 | 100% |
| 单元测试 | 30 项全部通过 |

## 已知限制

- 向量/混合检索需额外安装 `sentence-transformers`（可选），当前默认纯 BM25。
- 旧格式 `.doc` / `.xls` 需先转换为 `.docx` / `.xlsx`。
- 默认使用抽取式回答（无 LLM），多事实整合与自然语言表达能力有限。
- 表格计算仅支持简单差值类问题。

## 安全说明

- 系统不依赖商业 API，默认无需任何密钥即可运行。
- 如使用 LLM，密钥仅从环境变量读取（参考 `.env.example`），**绝不写入代码、README 或提交材料**。
