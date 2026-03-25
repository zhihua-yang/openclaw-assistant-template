<!-- 本文件：create_event.py 完整命令参考，在需要录入事件时由 AGENTS.md 索引调用 -->

# create_event.py 命令参考

## 最小模式（evidence 缺省 self）

```bash
python3 scripts/create_event.py \
  --type task-done \
  --content "完成 xxx" \
  --task-type yyy
```

## 完整模式

```bash
python3 scripts/create_event.py \
  --type task-done \
  --content "完成 xxx" \
  --task-type yyy \
  --difficulty stretch \
  --confidence medium \
  --evidence external \
  --evidence-ref "log:xxx" \
  --cap cap_yyy
```

## 场景示例

### 完成常规任务
```bash
python3 scripts/create_event.py \
  --type task-done \
  --content "完成 A 项目代码审查，发现 3 处潜在 bug" \
  --task-type code-review \
  --difficulty routine
```

### 修复 bug
```bash
python3 scripts/create_event.py \
  --type error-fix \
  --content "修复日志解析错误，原因是正则未处理 Unicode 字符" \
  --task-type log-analysis \
  --evidence external \
  --evidence-ref "test-pass:2026-03-25" \
  --cap cap_regex_matching
```

### 用户指出错误
```bash
python3 scripts/create_event.py \
  --type user-correction \
  --content "用户指出 summary 文本缺少关键信息，需补充成本分析" \
  --task-type document-generation
```

### 用户正向反馈
```bash
python3 scripts/create_event.py \
  --type user-positive-feedback \
  --content "用户表示 debug 方案效率提升 40%，符合预期" \
  --task-type problem-solving
```

### 错误驱动学习（必须有 --cognitive-update 和 --parent）
```bash
python3 scripts/create_event.py \
  --type learning-achievement \
  --content "理解了递归深度限制导致的 stack overflow" \
  --trigger error-driven \
  --cognitive-update "原来是调用链太深，应该用迭代或分页处理" \
  --parent evt-xxxxxxxx-xxxxxx
```

### 能力迁移（far transfer）
```bash
python3 scripts/create_event.py \
  --type capability-reuse \
  --content "将 log_parsing 能力迁移到新的日志格式解析" \
  --cap cap_log_parsing \
  --transfer far \
  --parent evt-xxxxxxxx-xxxxxx
```

### 故意挑战
```bash
python3 scripts/create_event.py \
  --type intentional-challenge \
  --content "挑战：在不查资料的情况下独立优化算法复杂度" \
  --difficulty novel \
  --challenge-type transfer \
  --outcome success \
  --cap cap_algorithm_optimization
```

## 字段取值速查表

| 字段 | 可选值 | 缺省值 |
|---|---|---|
| `--type` | task-done / error-fix / error-found / user-correction / user-positive-feedback / system-improvement / intentional-challenge / learning-achievement / capability-reuse | 必填 |
| `--difficulty` | routine / stretch / novel | routine |
| `--confidence` | high / medium / low | 可不填 |
| `--evidence` | external / logical / self | self |
| `--transfer` | near / far | near |
| `--trigger` | normal / error-driven / challenge-driven | normal |
| `--challenge-type` | consolidate / stretch / transfer | 可不填 |
| `--outcome` | success / partial / fail | 可不填 |

## 其他命令

```bash
# 查看所有可用事件类型
python3 scripts/create_event.py --list-types

# 预览事件（不写入）
python3 scripts/create_event.py --type task-done --content "xxx" --dry-run
```

## 关键提示

- `--evidence logical` 不允许手动填写，只能由系统自动推断
- `learning-achievement` 和 `capability-reuse` 必须有 `--parent` 参数
- `external` 证据尽量提供 `--evidence-ref`（日志、截图、测试通过等）
