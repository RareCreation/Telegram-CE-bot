"""
- Colored log output in console (colorama)
- Log files saved in ./logs (new file per run)
- Supports different log levels with colors
- Format: [date/time] - LEVEL - file/function:line -> message

Usage:
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
"""

import logging
from colorama import init, Fore, Style

init(autoreset=True)

class CustomLogger(logging.Logger):
    def __init__(
        self,
        name: str = "root",
        level: int = logging.DEBUG,
        use_default_handlers: bool = True,
        logging_exceptions: dict[str, int] = {},
    ) -> None:
        super().__init__(name, logging_exceptions.get(name, level))
        if use_default_handlers:
            self.set_default_handlers()

    def set_default_handlers(self) -> None:
        import os
        from datetime import datetime
        from logging.handlers import RotatingFileHandler

        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        file_handler = RotatingFileHandler(
            filename=f"./logs/{timestamp}.log",
            encoding="utf-8",
            backupCount=0,
            maxBytes=104857600,
            errors="warning",
        )
        file_handler.setFormatter(
            logging.Formatter(
                fmt="[%(asctime)s] %(levelname)s %(name)s -> %(message)s",
                datefmt="%Y.%m.%d %H:%M",
            )
        )

        stream_handler = logging.StreamHandler()

        def colorize_level(record: logging.LogRecord) -> str:
            record.asctime = logging.Formatter().formatTime(record, "%Y.%m.%d %H:%M")

            level = record.levelname

            match record.levelno:
                case logging.DEBUG:
                    level = f"{Fore.CYAN}{level}{Style.RESET_ALL}"
                case logging.INFO:
                    level = f"{Fore.GREEN}{level}{Style.RESET_ALL}"
                case logging.WARNING:
                    level = f"{Fore.YELLOW}{level}{Style.RESET_ALL}"
                case logging.ERROR:
                    level = f"{Fore.RED}{level}{Style.RESET_ALL}"
                case logging.CRITICAL:
                    level = f"{Fore.RED}{Style.BRIGHT}{level}{Style.RESET_ALL}"

            return level

        class ColorFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                level = colorize_level(record)
                return (
                    f"[{record.asctime}] - {level} - {record.filename}/{record.funcName}:{record.lineno} "
                    f"-> {record.getMessage()}"
                )

        formatter = ColorFormatter()
        stream_handler.setFormatter(formatter)

        self.addHandler(stream_handler)
        self.addHandler(file_handler)


logging.setLoggerClass(CustomLogger)

logger = logging.getLogger("logger")
logger.setLevel(logging.DEBUG)
