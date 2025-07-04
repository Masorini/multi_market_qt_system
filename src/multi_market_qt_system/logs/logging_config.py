import logging
import os
from logging import handlers


def init_logging(
        log_dir: str = None,
        log_file: str = "app.log",
        console: bool = True,
        level: int = logging.INFO
) -> None:
    """
    Initialize logging configuration.

    :param log_dir: Directory to store log files. Defaults to a "logs" folder next to this script.
    :param log_file: Name of the log file.
    :param console: Whether to output logs to console (stdout).
    :param level: Logging level (e.g., logging.INFO).
    """
    # Determine log directory
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Get root logger and set level
    root = logging.getLogger()
    root.setLevel(level)

    # Formatter for both console and file
    log_format = "%(asctime)s.%(msecs)03d %(levelname)-5s %(name)-40s [Line:%(lineno)d] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # File handler (rotating)
    file_path = os.path.join(log_dir, log_file)
    file_handler = handlers.RotatingFileHandler(
        filename=file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Console handler (optional)
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

# Use example:
# init_logging(console=True)  # enable console output
# init_logging(console=False) # disable console output
