import argparse
import os
import shutil
import json
import logging
import logging.handlers
import getpass
import socket
import time
import re
from datetime import datetime, timedelta


class AuditLogger:
    """审计日志记录器（修正版）"""

    def __init__(self):
        # 创建基础Logger对象用于配置
        self._logger = logging.getLogger("FileArchiveAudit")
        self._logger.setLevel(logging.INFO)

        # 防止重复添加handler
        if not self._logger.handlers:
            self._setup_audit_logging()

        # 创建LoggerAdapter实例用于实际记录
        self.logger = logging.LoggerAdapter(
            self._logger, {
                'host': socket.gethostname(),
                'user': getpass.getuser(),
                'action': 'UNKNOWN',
                'target': 'UNKNOWN',
                'status': 'UNKNOWN',
                'duration_ms': 0
            })

    def _setup_audit_logging(self):
        """配置审计日志存储"""
        audit_dir = "audit_logs"
        os.makedirs(audit_dir, exist_ok=True)

        # 审计日志格式
        formatter = logging.Formatter(
            '%(asctime)s | %(host)s | %(user)s | %(action)s | %(target)s | '
            '%(status)s | %(duration_ms)dms | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')

        # 文件处理器（按日期轮转）
        file_handler = logging.handlers.TimedRotatingFileHandler(
            os.path.join(audit_dir, "archive_audit.log"),
            when='midnight',
            backupCount=30,
            encoding='utf-8')
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)

        # 控制台处理器（用于调试）
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

    def log(self, action, target, status, start_time=None, message=""):
        """
        记录审计日志
        :param action: 操作类型（如FILE_MOVE）
        :param target: 操作目标路径
        :param status: 状态（SUCCESS/FAILED等）
        :param start_time: 操作开始时间戳
        :param message: 附加消息
        """
        duration_ms = int(
            (time.time() - start_time) * 1000) if start_time else 0
        self.logger.info(message,
                         extra={
                             'action': action,
                             'target': target,
                             'status': status,
                             'duration_ms': duration_ms
                         })


class ArchiveConfig:
    """归档配置管理"""

    def __init__(self, args):
        self.args = args
        self.settings = self._load_settings()
        self.filters = self._build_filters()
        self.log_config = self.settings.get('logging',
                                            {}) if self.settings else {}

    def _load_settings(self):
        """加载配置文件"""
        if self.args.no_config:
            return None

        config_path = self.args.config
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"配置文件加载错误: {str(e)}")
        return None

    def _build_filters(self):
        """构建筛选条件"""
        filters = {}

        if self.settings and 'default_filters' in self.settings:
            filters.update(self.settings['default_filters'])

        if self.args.extensions:
            filters['extensions'] = [
                ext.lower().strip() for ext in self.args.extensions.split(',')
            ]
        if self.args.size_limit:
            filters['size_limit'] = self.args.size_limit
        if self.args.min_size:
            filters['min_size'] = self.args.min_size
        if self.args.modified_days:
            filters['modified_days'] = self.args.modified_days
        if self.args.created_days:
            filters['created_days'] = self.args.created_days
        if self.args.regex:
            filters['regex'] = self.args.regex
        if self.args.exclude:
            filters['exclude'] = [
                pattern.strip() for pattern in self.args.exclude.split(',')
            ]

        return filters


def setup_logging(log_config):
    """配置应用日志系统"""
    logger = logging.getLogger("FileArchiver")
    logger.setLevel(
        logging.DEBUG if log_config.get('verbose') else logging.INFO)

    # 清除现有handler防止重复
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')

    # 始终启用控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 条件启用文件日志
    if log_config.get('enable_file_logging', True):
        try:
            log_dir = log_config.get('log_dir', 'logs')
            os.makedirs(log_dir, exist_ok=True)

            if log_config.get('enable_rotate', True):
                file_handler = logging.handlers.RotatingFileHandler(
                    os.path.join(log_dir, "archive.log"),
                    maxBytes=log_config.get('max_size_mb', 10) * 1024 * 1024,
                    backupCount=log_config.get('backup_count', 5),
                    encoding='utf-8')
            else:
                file_handler = logging.FileHandler(os.path.join(
                    log_dir, "archive.log"),
                                                   encoding='utf-8')

            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"文件日志配置失败: {str(e)}")

    return logger


def parse_size(size_str):
    """解析人类可读的文件大小"""
    if not size_str:
        return 0

    size_str = size_str.upper().strip()
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    return int(size_str)


def should_archive(filepath, filters, audit_logger):
    """判断文件是否符合归档条件"""
    check_start = time.time()
    try:
        stat = os.stat(filepath)
        filename = os.path.basename(filepath)

        # 扩展名筛选
        if 'extensions' in filters:
            file_ext = os.path.splitext(filepath)[1].lower()
            allowed_ext = [ext.lower() for ext in filters['extensions']]
            if not file_ext or file_ext not in allowed_ext:
                audit_logger.log("FILTER_CHECK", filepath, "SKIPPED",
                                 check_start, f"扩展名 {file_ext} 不在允许列表中")
                return False

        # 大小筛选
        if 'size_limit' in filters:
            if stat.st_size > parse_size(filters['size_limit']):
                audit_logger.log("FILTER_CHECK", filepath, "SKIPPED",
                                 check_start,
                                 f"超过最大限制 {filters['size_limit']}")
                return False

        if 'min_size' in filters:
            if stat.st_size < parse_size(filters['min_size']):
                audit_logger.log("FILTER_CHECK", filepath, "SKIPPED",
                                 check_start, f"小于最小限制 {filters['min_size']}")
                return False

        # 时间筛选
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        create_time = datetime.fromtimestamp(stat.st_ctime)

        if 'modified_days' in filters:
            cutoff = datetime.now() - timedelta(
                days=int(filters['modified_days']))
            if mod_time > cutoff:
                audit_logger.log("FILTER_CHECK", filepath, "SKIPPED",
                                 check_start,
                                 f"在最近 {filters['modified_days']} 天内修改过")
                return False

        if 'created_days' in filters:
            cutoff = datetime.now() - timedelta(
                days=int(filters['created_days']))
            if create_time > cutoff:
                audit_logger.log("FILTER_CHECK", filepath, "SKIPPED",
                                 check_start,
                                 f"在最近 {filters['created_days']} 天内创建")
                return False

        # 正则匹配
        if 'regex' in filters:
            if not re.search(filters['regex'], filename):
                audit_logger.log("FILTER_CHECK", filepath, "SKIPPED",
                                 check_start, f"不匹配正则表达式 {filters['regex']}")
                return False

        # 排除模式
        if 'exclude' in filters:
            for pattern in filters['exclude']:
                if pattern in filename:
                    audit_logger.log("FILTER_CHECK", filepath, "SKIPPED",
                                     check_start, f"匹配排除模式 {pattern}")
                    return False

        return True

    except Exception as e:
        audit_logger.log("FILTER_CHECK", filepath, "ERROR", check_start,
                         f"筛选检查失败: {str(e)}")
        return False


def archive_folder(source_path, config, logger, audit_logger):
    """处理单个文件夹归档"""
    folder_start = time.time()
    audit_logger.log("FOLDER_START", source_path, "STARTED", folder_start,
                     "开始处理文件夹")

    if not os.path.exists(source_path):
        logger.error(f"文件夹不存在: {source_path}")
        audit_logger.log("FOLDER_ERROR", source_path, "FAILED", folder_start,
                         "文件夹不存在")
        return False

    # 创建归档子目录
    archive_path = os.path.join(source_path,
                                datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    try:
        os.makedirs(archive_path, exist_ok=True)
        audit_logger.log("FOLDER_CREATE", archive_path, "SUCCESS",
                         folder_start, "成功创建归档目录")
    except Exception as e:
        logger.error(f"创建归档目录失败: {str(e)}")
        audit_logger.log("FOLDER_CREATE", archive_path, "FAILED", folder_start,
                         f"创建失败: {str(e)}")
        return False

    # 处理文件
    processed = 0
    skipped = 0
    failed = 0

    for filename in os.listdir(source_path):
        filepath = os.path.join(source_path, filename)

        if os.path.isfile(filepath):
            file_start = time.time()
            try:
                if config.args.dry_run:
                    logger.info(f"[模拟] 将归档: {filename}")
                    processed += 1
                elif should_archive(filepath, config.filters, audit_logger):
                    shutil.move(filepath, os.path.join(archive_path, filename))
                    processed += 1
                    logger.debug(f"已归档: {filename}")
                    audit_logger.log("FILE_MOVE", filepath, "SUCCESS",
                                     file_start, f"成功归档到 {archive_path}")
                else:
                    skipped += 1
            except Exception as e:
                failed += 1
                logger.error(f"处理文件失败 {filename}: {str(e)}")
                audit_logger.log("FILE_MOVE", filepath, "FAILED", file_start,
                                 f"归档失败: {str(e)}")

    # 记录完成状态
    logger.info(
        f"完成 {source_path}: 已归档 {processed}, 跳过 {skipped}, 失败 {failed}")
    audit_logger.log("FOLDER_COMPLETE", source_path, "COMPLETED", folder_start,
                     f"处理结果: {processed} 已归档, {skipped} 跳过, {failed} 失败")

    return processed > 0 or failed == 0


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="高级文件归档工具 v2.0",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # 核心参数
    parser.add_argument('folders', nargs='*', help='要处理的文件夹路径')
    parser.add_argument('-c',
                        '--config',
                        default='settings.json',
                        help='配置文件路径')
    parser.add_argument('--no-config', action='store_true', help='忽略配置文件')

    # 筛选参数
    parser.add_argument('--extensions', help='逗号分隔的允许扩展名（如 .pdf,.docx）')
    parser.add_argument('--size-limit', help='最大文件大小（如 10MB, 500KB）')
    parser.add_argument('--min-size', help='最小文件大小（如 1MB, 100KB）')
    parser.add_argument('--modified-days', type=int, help='仅归档X天前修改的文件')
    parser.add_argument('--created-days', type=int, help='仅归档X天前创建的文件')
    parser.add_argument('--regex', help='文件名必须匹配的正则表达式')
    parser.add_argument('--exclude', help='逗号分隔的排除模式')

    # 行为参数
    parser.add_argument('--strict', action='store_true', help='遇到错误立即停止')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行不实际移动文件')
    parser.add_argument('--verbose', action='store_true', help='显示详细调试信息')

    return parser.parse_args()


def main():
    """主程序入口"""
    args = parse_arguments()
    config = ArchiveConfig(args)

    # 初始化日志系统
    logger = setup_logging({**config.log_config, 'verbose': args.verbose})
    audit_logger = AuditLogger()

    # 获取待处理文件夹列表
    folders_to_process = []
    if not args.no_config and config.settings and 'folders' in config.settings:
        folders_to_process.extend(
            [f['path'] for f in config.settings['folders'] if 'path' in f])
    folders_to_process.extend(args.folders)

    if not folders_to_process:
        logger.error("错误：未指定要处理的文件夹")
        return 1

    # 处理文件夹
    success_count = 0
    for folder in folders_to_process:
        try:
            if archive_folder(folder, config, logger, audit_logger):
                success_count += 1
            elif args.strict:
                raise RuntimeError(f"严格模式：终止于失败文件夹 {folder}")
        except Exception as e:
            logger.error(f"处理文件夹 {folder} 失败: {str(e)}")
            if args.strict:
                return 1

    logger.info(f"归档完成：成功处理 {success_count}/{len(folders_to_process)} 个文件夹")
    return 0 if success_count == len(folders_to_process) else 1


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        exit(1)
    except Exception as e:
        print(f"程序错误: {str(e)}")
        exit(1)
