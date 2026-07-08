# 更新日志

## [1.1.3] - 2026-07-08

### 修复
- CI 的 `.gitignore` 中包含了 `.coupon_history.json`（既被 gitignore 又未被跟踪），导致 `git add` 返回 exit code 1，整个提交步骤终止，`data.csv` 无法被推送至仓库

### 杂项
- 将 `.coupon_history.json` 从 `.gitignore` 中移除并重新跟踪；`git add` 现在正常执行，每日 workflow 恢复自动提交

## [1.1.0] - 2026-07-01

### 新增
- `--yes` / `--non-interactive` 标志，用于 CI / 自动化脚本
- `--export-json FILE` — 导出全部优惠券为 JSON
- `--export-md PATH` — 导出全部数据为 Markdown 表格（不再限于前 50）
- 所有 export 标志的 metavar 从 `FILE` 改为 `PATH`，明确需要提供完整路径
- `--quiet` / `-q` — 静默模式，不打印欢迎头、免责声明、来源行、底部提示
- `requirements-lock.txt` — 锁定依赖版本，支持可复现安装
- `latest_data.json` 现受 git 跟踪（已从 `.gitignore` 移除），保证 `--diff` 正常工作
- 通过 API 的 `couponActivityName` 字段动态推导未知专区的名称

### 变更
- `--top` 现在会尊重 `--min-rate` 和 `--brand` 过滤条件
- `--section` 名称关键词匹配现在显示**全部**匹配的专区（原来只取第一个）
- `--diff` 区分首次运行（无历史记录）和历史文件损坏两种场景，给出不同提示
- 参数校验（`--combo -1`、`--min-rate -5` 等）移至**数据加载之前**，避免先打 Banner 再报错
- "来源" 行现在受 `--quiet` 控制
- `print_diff()` 错误处理拆分为 `FileNotFoundError`、`json.JSONDecodeError`、`OSError`，分别给出明确消息
- `_save_history()` 添加 try/except 保护，防止不可写路径导致崩溃
- `format_amount()` 处理缺失或为零的 `couponDiscount`，不再显示 "0折"
- 所有导出路径（`--export`、`--export-csv`、`--export-json`、`--export-md`）捕获 `OSError`/`PermissionError`
- `parse_coupons()` 增加对非 dict 类型的 `couponModelVOListMap` 的防护
- `_git_pull_data()` 在失败时输出 stderr 详细信息
- `--quiet` 模式下自动跳过数据过期询问
- GitHub Actions 定时任务调整为北京时间 23:45

### 修复
- `--combo 0` 和 `--combo -50` 现在被正确拒绝（预算必须 > 0）
- `--min-rate 200` 不再对非过滤命令（如 `--stats`）误报 "无券可匹配"
- `--brand ""`（空字符串）现在显示警告，而非静默跳过过滤
- Rich 不可用时的降级 `Console` 类新增 `width` 属性
- 修复因文件损坏/缺失、路径不可写、API 数据异常导致的各类崩溃

### 杂项
- 用最新 API 数据更新了 `data.csv`（600 行）
- 内部注释标记升级为 `# ═══` 风格并添加目录索引
