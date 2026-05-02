from __future__ import annotations

import importlib
import importlib.util as util
import inspect
import os
import traceback

from utils.logger_util import logger


async def load_routers(routers_dir: str = "routers", **kwargs: any) -> None:
    routers_dir_spec = routers_dir.replace(os.sep, '.')
    for root, _, files in os.walk(routers_dir):
        for filename in files:
            if filename.endswith(".py") and filename != "__init__.py":
                module_path = os.path.join(root, filename)
                relative_module = os.path.relpath(module_path, routers_dir)
                module_name = f"{routers_dir_spec}.{relative_module.replace(os.sep, '.')[:-3]}"

                try:
                    spec = util.find_spec(module_name)
                    if spec is None:
                        continue

                    module = importlib.import_module(module_name)

                    if hasattr(module, "load"):
                        func = getattr(module, "load")
                        if callable(func):
                            func_kwargs: dict[str, any] = {}
                            for arg_name, arg_annotation in func.__annotations__.items():
                                if arg_name in kwargs.keys():
                                    func_kwargs[arg_name] = kwargs[arg_name]

                            if inspect.iscoroutinefunction(func):
                                await func(**func_kwargs)
                            else:
                                func(**func_kwargs)

                            logger.info(f"{module_name} loaded successfully")
                        else:
                            logger.warning(f"{module_name} can't be loaded")
                    else:
                        logger.warning(f"{module_name} doesn't have a load function")
                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(f"{module_name} could not be loaded: {e}\n{tb}")