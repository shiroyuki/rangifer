from glob import glob
from importlib import import_module
import inspect
import logging
import os
import re
import sys
from threading import Lock
from typing import Callable, List, Optional, Type, Union
from uuid import uuid4
from fastapi import FastAPI
from imagination.debug import get_logger

from caribou.http.definitions import Helper, Endpoint


class MethodWithoutRouteError(RuntimeError):
    def __init__(self, handler: Callable):
        super().__init__(handler)

    def __str__(self):
        handler = self.args[0]
        return f"No routes defined for {handler.__module__}.{handler.__name__}"


class Server:
    __RE_PATH_DELIMITER = re.compile(r'/|\\')
    __SERVER_COUNT_LOCK = Lock()
    __SERVER_COUNT = 0

    def __init__(self, name: Optional[str] = None, debug: bool = False, *args, **kwargs):
        with self.__SERVER_COUNT_LOCK:
            self._proc_index = self.__SERVER_COUNT
            self.__SERVER_COUNT += 1

        self._guid = str(uuid4())
        self._name = name
        self._app = FastAPI(debug=debug, *args, **kwargs, **(dict(title=self._name) if self._name else dict()))
        self._log = get_logger(f'{self._name or type(self).__name__}/{self._proc_index}', level=logging.DEBUG if debug else getattr(logging, os.getenv('CARIBOU_LOG_LEVEL') or 'INFO'))

    def auto_import(self, *module_names: str, root_dir: Optional[str] = None):
        target_module_root_dirs: List[str] = list(module_names)

        # If the module names are not defined, scan the root dir for potential Python modules.
        if not module_names:
            scanning_path = os.path.join("**", "*.py")
            if root_dir:
                scanning_path = os.path.join(root_dir, scanning_path)

            module_paths = set()

            for path in glob(scanning_path):
                module_paths.add(os.path.dirname(path))

            target_module_root_dirs.extend(
                [
                    self.__RE_PATH_DELIMITER.split(module_path)[0]
                    for module_path in module_paths
                ]
            )

        for target_module_root_dir in target_module_root_dirs:
            # Define the scanning path.
            scanning_path = os.path.join(target_module_root_dir, '**', "*.py")
            if root_dir:
                scanning_path = os.path.join(root_dir, scanning_path)

            # For each path...
            self._log.debug(f'scanning_path: {scanning_path}')
            for path in glob(scanning_path, recursive=True):
                dir_name, file_name = os.path.split(path)
                package_name = '.'.join(self.__RE_PATH_DELIMITER.split(dir_name))
                module_name = file_name[:-3]
                mod_qualified_name = '.'.join([package_name, module_name])
                # If the module is not already loaded...
                if mod_qualified_name not in sys.modules.keys():
                    # Import the module.
                    self._log.info(f'import: {mod_qualified_name}')
                    module = import_module(f'.{module_name}', package=package_name)

                    # For each symbol
                    for obj_name in dir(module):
                        if obj_name[0] == '_':
                            # Ignore a non-private symbol
                            continue

                        obj = getattr(module, obj_name)

                        # If the object has an endpoint defition.
                        if Helper.is_endpoint(obj):
                            self._log.info(f'handler/{obj.__module__}.{obj.__name__}: {obj}')
                            self._register_endpoint(obj)
                        else:
                            self._log.info(f'ignored: {mod_qualified_name}.{obj_name}')

        return self

    def _register_endpoint(self, obj: Union[Callable, Type]):
        if inspect.isfunction(obj):
            self._register_one_function_as_endpoint(obj)
        if inspect.isclass(obj):
            self._log.warn(f'Cannot register {obj.__module__}.{obj.__name__} as the support for a controller class has not been implemented')

    def _register_one_function_as_endpoint(self, obj: Callable):
        endpoint_config: Endpoint = Helper.get_definition(obj)
        for http_method in endpoint_config.methods:
            getattr(self._app, http_method.value)(endpoint_config.path)(obj)

    def _register_one_class_as_endpoint(self, obj: Type):
        endpoint_config: Endpoint = Helper.get_definition(obj)
        for http_method in endpoint_config.methods:
            getattr(self._app, http_method.value)(endpoint_config.path)(obj)

    def instance(self) -> FastAPI:
        return self._app
