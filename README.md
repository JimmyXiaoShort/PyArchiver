# PyArchiver

## 简介 / Introduction

这是一个功能强大的文件归档工具，支持多种筛选条件和详细的审计日志记录。
This is a powerful file archiving tool with multiple filtering options and detailed audit logging.

```text
主要功能 / Key Features:
- 按扩展名/大小/时间筛选文件 / Filter by extension/size/time
- 支持正则表达式匹配 / Regex pattern matching
- 详细的审计日志 / Detailed audit logs
- 命令行参数配置 / Command-line configuration
- 配置文件支持 / Config file support
```

## 安装要求 / Requirements

- Python 3.6+
- 无额外依赖 / No extra dependencies required

## 使用方法 / Usage

### 基本命令 / Basic Command

```bash
python archiver.py [文件夹路径] [选项]
python archiver.py [folder_path] [options]
```

### 常用示例 / Common Examples

1. **归档指定扩展名的文件** / Archive by extensions:

```bash
python archiver.py /data --extensions .pdf,.docx
```

2. **按时间筛选** / Filter by time:

```bash
# 30天前修改的文件 / Files modified 30+ days ago
python archiver.py /backup --modified-days 30
```

3. **复杂筛选** / Advanced filtering:

```bash
python archiver.py /docs \
    --extensions .pdf,.docx \
    --size-limit 10MB \
    --regex "report_.*" \
    --exclude "draft,temp"
```

4. **模拟运行** / Dry run:

```bash
python archiver.py /data --dry-run --verbose
```

## 配置文件 / Configuration File

默认配置文件 `settings.json` 示例：
Sample config file `settings.json`:

```json
{
    "logging": {
        "log_dir": "logs",
        "max_size_mb": 10,
        "backup_count": 5
    },
    "default_filters": {
        "extensions": [".doc", ".pdf"],
        "size_limit": "20MB"
    },
    "folders": [
        {
            "path": "/regular/backup/path",
            "filters": {
                "modified_days": 30
            }
        }
    ]
}
```

## 命令行参数 / CLI Options


| 参数 / Parameter  | 描述 / Description                                              |
| ----------------- | --------------------------------------------------------------- |
| `-c, --config`    | 指定配置文件路径 / Config file path                             |
| `--no-config`     | 忽略配置文件 / Ignore config file                               |
| `--extensions`    | 允许的扩展名（逗号分隔） / Allowed extensions (comma-separated) |
| `--size-limit`    | 最大文件大小 / Max file size (e.g. 10MB)                        |
| `--min-size`      | 最小文件大小 / Min file size (e.g. 100KB)                       |
| `--modified-days` | 修改时间在X天前 / Modified X+ days ago                          |
| `--created-days`  | 创建时间在X天前 / Created X+ days ago                           |
| `--regex`         | 文件名正则匹配 / Filename regex pattern                         |
| `--exclude`       | 排除模式（逗号分隔） / Exclusion patterns (comma-separated)     |
| `--strict`        | 遇到错误立即停止 / Exit on first error                          |
| `--dry-run`       | 模拟运行 / Simulation mode                                      |
| `--verbose`       | 显示详细日志 / Verbose logging                                  |

## 日志系统 / Logging System

**审计日志** / Audit logs:
`audit_logs/archive_audit.log` (按日轮转 / Daily rotation)

**应用日志** / Application logs:
`logs/archive.log` (按大小轮转 / Size-based rotation)

日志格式示例 / Sample log format:

```log
2023-11-20 14:30:45 | DESKTOP-01 | user1 | FILE_MOVE | /data/file.pdf | SUCCESS | 120ms | 已归档到 /data/archive
```

## 退出代码 / Exit Codes


| 代码 / Code | 含义 / Meaning            |
| ----------- | ------------------------- |
| 0           | 成功 / Success            |
| 1           | 一般错误 / General error  |
| 2           | 用户中断 / User interrupt |

## 注意事项 / Notes

1. 使用 `--dry-run`测试参数效果
   Use `--dry-run` to test parameters
2. 严格模式(`--strict`)适合自动化任务
   Strict mode is good for automated tasks
3. 日志文件默认保留30天
   Logs are kept for 30 days by default
4. 中文路径需确保系统编码为UTF-8
   For Chinese paths, ensure system encoding is UTF-8
5. 使用 `--exclude`时注意文件名大小写
   Be aware of case sensitivity when using `--exclude`

## 贡献 / Contribution

欢迎提交问题或建议 / Welcome to submit issues or suggestions.
