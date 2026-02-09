# Evlin Calendar Scheduler — 架构与实现说明

本文档说明项目的**设计思路**、**技术栈**和**具体实现**，方便你整体理解并二次开发。

---

## 一、项目定位与设计目标

- **定位**：面向 Homeschool（在家教育）家庭的**课程排课与学习材料**一体化工具。
- **核心能力**：
  - 管理学生、课程、每周可用时间、已排课表；
  - 用 **AI 对话** 帮家长选课、排时间、检查冲突；
  - 生成 **PDF**（课表、练习册、课程概览等）；
  - **OCR** 上传文档并提取文字。

设计上采用「多数据源 + 单一应用入口」：关系数据在 Supabase，课程关系/先修在 Neo4j，向量检索在 Pinecone，文件在 MinIO，所有能力通过一个 Streamlit 应用暴露。

---

## 二、整体架构（分层与数据流）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Streamlit 应用 (app/)                             │
│  main.py → 侧边栏选学生 → 多页面: Dashboard / Scheduler / Courses / PDF / OCR  │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         业务层 (agents/, pdf/, ocr/)                      │
│  • Scheduler Agent (Gemini + 工具调用)                                    │
│  • PDF 生成 (ReportLab / WeasyPrint 模板)                                 │
│  • OCR 流水线 (PyMuPDF → EasyOCR)                                        │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         数据访问层 (db/, services/)                       │
│  db/queries.py (Supabase CRUD)   db/graph_queries.py (Neo4j)             │
│  db/vector_queries.py (Pinecone) services/minio_client.py (MinIO)         │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────┬──────────────┬──────────────┬──────────────┐
│  Supabase    │   Neo4j     │  Pinecone    │   MinIO      │
│  (Postgres)  │  (图数据库)   │  (向量索引)   │  (对象存储)   │
│  学生/课程/   │  课程先修    │  课程语义检索  │  PDF/OCR 文件 │
│  可用时间/   │  关系图      │  (可选)       │              │
│  课表/对话   │              │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

- **入口**：`app/main.py` 设置页面、侧边栏选学生，各功能在 `app/pages/` 下分页实现。
- **业务**：排课由 `agents/scheduler_agent.py` + 若干工具完成；PDF 由 `pdf/` 编排模板；OCR 由 `ocr/processor.py` 统一处理。
- **数据**：所有「查写库」都通过 `db/` 和 `services/`，不直接在页面里调 Supabase/Neo4j API。

---

## 三、技术栈一览

| 类别       | 技术               | 用途 |
|------------|--------------------|------|
| 前端/应用  | **Streamlit**      | 多页 Web 应用、表单、聊天界面 |
| AI         | **Google Gemini**  | 排课对话、Function Calling（工具调用） |
| 关系数据   | **Supabase**      | 学生、课程、可用时间、课表、PDF 元数据、OCR 记录、对话记录 |
| 图数据     | **Neo4j**         | 课程先修关系（PREREQUISITE_FOR）、RELATED_TO |
| 向量       | **Pinecone**      | 课程向量、语义检索（可选） |
| 对象存储   | **MinIO**         | 生成的 PDF、上传的 OCR 文件 |
| PDF 生成   | **ReportLab**     | 练习册、课程概览、课表报告等排版 |
| PDF 排版   | **WeasyPrint**    | 复杂版式（可选） |
| 文档解析   | **PyMuPDF**       | PDF 文本抽取、PDF 转图片 |
| OCR        | **EasyOCR**       | 图片/扫描 PDF 文字识别 |
| 配置       | **pydantic-settings** + **.env** | 各服务 URL/密钥 |

后端语言：**Python 3**；依赖与模型定义见 `requirements.txt`、`db/models.py`。

---

## 四、数据层设计

### 4.1 Supabase（PostgreSQL）— 主数据

在 Supabase SQL Editor 中执行 `setup_supabase.sql` 建表。核心表：

| 表名                 | 说明 |
|----------------------|------|
| **students**         | 学生：姓名、年级(1–12)、家长、备注等 |
| **courses**          | 课程：code、title、subject、年级范围、周课时、先修数组、tags 等 |
| **availability**     | 学生每周可用的时间段：student_id, day_of_week(0–6), start_time, end_time, preference(available/avoid/preferred) |
| **schedules**        | 选课记录：学生 + 课程 + 状态(proposed/active/completed) + 起止日期 |
| **schedule_slots**   | 某条 schedule 的每周上课时间：day_of_week, start_time, end_time, location |
| **generated_pdfs**   | 生成过的 PDF 元数据：minio_bucket, minio_key, pdf_type, title 等 |
| **ocr_documents**    | OCR 任务：original_filename, minio_key, extracted_text, status 等 |
| **agent_conversations** | 与 AI 的对话：student_id, agent_type, messages(JSONB) |

所有对上述表的读写都通过 `db/queries.py` 中的函数（如 `get_all_students`、`get_student_schedules`、`insert_schedule` 等），使用 Supabase 的 `table().select()/.insert()/.update()/.delete()`。

### 4.2 Neo4j — 课程图

- **节点**：`Course`，属性至少包含 `code`, `title`, `subject`。
- **关系**：
  - `(预修课)-[:PREREQUISITE_FOR]->(进阶课)`：先修关系；
  - `(A)-[:RELATED_TO {reason}]->(B)`：相关课程。
- **用途**：排课时检查「学生是否已修完某课的先修」。  
  实现：`db/graph_queries.py`（如 `get_prerequisites`, `check_prerequisites_met`），底层用 `services/neo4j_client.py` 的 `run_query` 执行 Cypher。
- **降级**：若 Neo4j 不可用，`agents/tools/course_recommender.py` 里的 `check_prerequisites` 会退化为用 Supabase 中课程的 `prerequisites` 数组判断。

### 4.3 Pinecone — 向量检索（可选）

- **索引**：`evlin-courses`，存课程向量 + metadata（如 subject, grade_level_min/max）。
- **用途**：按语义搜课程（例如自然语言描述）。  
  实现：`db/vector_queries.py`（`upsert_course_embedding`, `search_courses_by_embedding`），由 `services/pinecone_client.py` 连 Pinecone。
- 当前 Scheduler 的「搜课」主要用 Supabase 条件筛选（`agents/tools/course_recommender.search_courses`），Pinecone 可作为扩展。

### 4.4 MinIO — 文件存储

- **用途**：上传的 OCR 文件、生成的 PDF 文件。
- **实现**：`services/minio_client.py` 封装 MinIO 客户端、`ensure_bucket`；上传/下载在具体功能里调用（如 PDF 生成页、OCR 页）。
- 表里只存 `minio_bucket` + `minio_key`，不存文件内容。

---

## 五、核心业务实现

### 5.1 排课 Agent（Scheduler）

- **入口**：`agents/scheduler_agent.py` 的 `run_scheduler_agent(messages, student_id)`。
- **模型**：Gemini（如 `gemini-2.5-flash`），带 **Function Calling**：模型在对话中决定何时调用哪个工具、传什么参数。
- **系统提示**：定义「YES/NO/MAYBE」排课逻辑、工作流（先查可用时间与当前课表 → 搜课 → 查先修 → 检测冲突 → 提议/确认），以及沟通风格。
- **工具声明与实现**：
  - `get_student_availability` → 查该学生每周可用时间段（来自 `db.queries.get_student_availability`）；
  - `get_current_schedule` → 查该学生当前活跃课表（`get_student_schedules` + `get_schedule_slots`）；
  - `search_courses` → 按 subject/grade/difficulty/keyword 筛课程（`db.queries` + 内存过滤）；
  - `check_prerequisites` → 先修是否满足（优先 Neo4j `check_prerequisites_met`，失败则用 Supabase 的 prerequisites 数组）；
  - `detect_conflicts` → 判断提议时间段是否与已有课表冲突、是否落在 availability 内、preference 是否为 avoid（`agents/tools/conflict_detector.py`）；
  - `propose_schedule` → 在 Supabase 插入 `schedules` + `schedule_slots`，状态为 `proposed`；
  - `confirm_schedule` → 将对应 schedule 状态改为 `active`。
- **循环**：每次模型返回若包含 `function_call`，则执行对应工具、把结果以 `function_response` 形式追加到对话，再请求模型；直到模型不再调工具，返回最终文本给用户。最多 `max_turns` 轮以防死循环。

工具实现分布在 `agents/tools/`：  
`availability_checker.py`、`course_recommender.py`、`conflict_detector.py`、`schedule_writer.py`，它们内部统一通过 `db.queries` / `db.graph_queries` 访问数据。

### 5.2 PDF 生成

- **入口**：`pdf/generator.py` 提供多种生成函数，例如：
  - `generate_practice_pdf_from_sample(subject, grade)` — 从 `data/sample_problems/*.json` 读题目，用 ReportLab 生成练习册；
  - `generate_course_overview_pdf(course)` — 课程概览单页；
  - `generate_schedule_report_pdf(student_id)` — 某学生当前课表报告；
  - `generate_semester_calendar_pdf(...)` — 多月的学期日历（可接 DB 或 demo 数据）。
- **模板**：`pdf/templates/` 下用 ReportLab（及可选 WeasyPrint）写版式，如 `practice_problems.py`、`course_overview.py`、`schedule_report.py`、`textbook_base.py`；样式在 `pdf/styles.py`。
- **流程**：页面（如 `app/pages/4_PDF_Generator.py`）选择类型与参数 → 调 `pdf.generator` 对应函数得到 `bytes` → 通过 `pdf_preview` 组件展示/下载；若需要落盘则上传 MinIO 并写 `generated_pdfs` 表。

### 5.3 OCR

- **入口**：`ocr/processor.py` 的 `OCRProcessor.process(file_bytes, filename)`。
- **策略**：
  - **PDF**：先用 PyMuPDF 抽取文本；若文本很少（如扫描版），则把每页转成图，再走 EasyOCR；
  - **图片**：直接 EasyOCR。
- **返回**：`OCRResult(text, confidence, method)`，method 为 `pymupdf` 或 `easyocr`。
- **上传流程**：用户上传文件 → 可先存 MinIO → 在 `ocr_documents` 表插入记录 → 后台或同步调用 `OCRProcessor.process`，把 `extracted_text`、`confidence`、`status` 写回表。

---

## 六、前端（Streamlit）结构

- **入口**：`app/main.py`  
  - 设置 `st.set_page_config`、初始化 `st.session_state`（如 `selected_student_id`）；  
  - 侧边栏用 `db.queries.get_all_students()` 拉学生列表，用 `st.sidebar.selectbox` 选当前学生；  
  - 主区展示欢迎文案和当前学生的简要统计（活跃课程数、周课时、可用 slot 数）。
- **多页**：`app/pages/` 下按顺序命名的页面会自动出现在侧边栏：
  - `1_Dashboard.py` — 学生概览、当前课表/日历；
  - `2_Scheduler.py` — 排课聊天：`chat_interface` 维护消息列表，用户输入后调 `run_scheduler_agent`，把返回内容追加并展示；
  - `3_Courses.py` — 课程目录（从 `get_all_courses` / `search_courses` 读）；
  - `4_PDF_Generator.py` — 选择 PDF 类型与参数，调 `pdf.generator`，用 `pdf_preview` 展示；
  - `5_OCR_Upload.py` — 上传文件，调 OCR，展示提取文本。
- **组件**：`app/components/` 中复用：
  - `sidebar.py` — 学生选择器封装；
  - `chat_interface.py` — 聊天历史与输入框、session state 的 key 约定；
  - `schedule_calendar.py` — 课表/日历展示；
  - `pdf_preview.py` — PDF 下载/预览。

所有页面都依赖「当前选中的学生」在 `st.session_state` 里，因此 main 和 sidebar 必须先选好学生。

---

## 七、配置与运行

- **配置**：`app/config.py` 用 `pydantic_settings.BaseSettings` 从项目根目录的 `.env` 读取：
  - Supabase：`supabase_url`, `supabase_key`
  - Gemini：`gemini_api_key`
  - Pinecone：`pinecone_api_key`, `pinecone_index_name`
  - MinIO：`minio_endpoint`, `minio_access_key`, `minio_secret_key`, `minio_secure`
  - Neo4j：`neo4j_uri`, `neo4j_user`, `neo4j_password`
- **本地服务**：MinIO、Neo4j 由 `docker-compose.yml` 启动；Supabase、Pinecone、Gemini 为云服务。
- **建表与种子数据**：在 Supabase 执行 `setup_supabase.sql`；然后运行 `seed_data.py`（可按 `--supabase` / `--neo4j` / `--minio` 等只灌部分），写入示例学生、课程、可用时间、课表、图数据、MinIO 桶等。
- **启动应用**：`streamlit run app/main.py`，浏览器打开所示本地 URL。

---

## 八、小结

- **设计**：多数据源（Supabase + Neo4j + Pinecone + MinIO）通过统一的 db/services 层支撑一个 Streamlit 应用；排课以「Gemini + 工具」为核心，PDF/OCR 为独立流水线。
- **技术栈**：Streamlit、Gemini、Supabase、Neo4j、Pinecone、MinIO、ReportLab、PyMuPDF、EasyOCR，配置用 pydantic-settings + .env。
- **实现**：数据模型与表结构在 `setup_supabase.sql` 与 `db/models.py`；CRUD 在 `db/queries.py`，图在 `db/graph_queries.py`，向量在 `db/vector_queries.py`；排课逻辑在 `agents/scheduler_agent.py` 与 `agents/tools/*`；PDF 在 `pdf/`，OCR 在 `ocr/`；前端在 `app/main.py` 与 `app/pages/`、`app/components/`。

按上述结构阅读代码即可快速定位「谁在什么时候读写了哪类数据、AI 如何调工具、PDF/OCR 如何被触发」。
