from glob import glob
from importlib import import_module
import inspect
import logging
import os
import re
import sys
from threading import Lock
from typing import Any, Callable, List, Optional, Type, Union
from urllib.parse import urljoin
from uuid import uuid4
from fastapi import FastAPI
from imagination.debug import get_logger
from imagination.decorator.service import registered
from imagination.standalone import container
from rangifer.common import ref_fqcn

from rangifer.http.definitions import ControllerDefinition, Helper, EndpointDefinition, controller as controller_decorator, endpoint as endpoint_decorator


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
        self._log = get_logger(f'{self._name or type(self).__name__}/{self._proc_index}', level=logging.DEBUG if debug else getattr(logging, os.getenv('RANGIFER_LOG_LEVEL') or 'INFO'))

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
                    if mod_qualified_name.startswith('rangifer.') or mod_qualified_name.startswith('rangifer'):
                        # If this is a framework code, ignore it.
                        continue

                    self._log.debug(f'import: {mod_qualified_name}')
                    module = import_module(f'.{module_name}', package=package_name)

                    # For each symbol
                    for ref_name in dir(module):
                        if ref_name[0] == '_':
                            # Ignore a non-private symbol
                            continue

                        reference = getattr(module, ref_name)

                        # If the object has an endpoint defition.
                        if Helper.is_endpoint(reference):
                            self._log.info(f'endpoint/{ref_fqcn(reference)}: {reference}')
                            self._register_endpoint(reference)
                        elif Helper.is_controller(reference):
                            self._log.info(f'controller/{ref_fqcn(reference)}: {reference}')
                            self._register_controller(reference)
                        elif reference in (controller_decorator, endpoint_decorator):
                            pass
                        else:
                            self._log.info(f'ignored: {mod_qualified_name}.{ref_name}')

        return self

    def _register_endpoint(self, obj: Callable, controller: Optional[Any] = None):
        controller_definition: Optional[ControllerDefinition] = Helper.get_definition(type(controller)) if controller else None
        endpoint_config: EndpointDefinition = Helper.get_definition(obj)
        self._bind(controller_definition, endpoint_config, obj)

    def _register_controller(self, cls: Type):
        controller_definition: ControllerDefinition = Helper.get_definition(cls)
        if controller_definition.auto_wired:
            # Register as a service.
            registered()(cls)
            # Then, let the container do the initialization.
            controller = container.get(cls)
        else:
            controller = cls(*controller_definition.init_args, **controller_definition.init_kwargs)
        for prop_name in dir(cls):
            if prop_name[0] == '_':
                continue

            # NOTE: The data injected to the method by the annotation can only be retrieved this way.
            cls_prop = getattr(cls, prop_name)

            if Helper.is_endpoint(cls_prop):
                self._log.info(f'endpoint/{ref_fqcn(cls)}/{prop_name}')
                self._bind(controller_definition, Helper.get_definition(cls_prop), getattr(controller, prop_name))
            else:
                self._log.info(f'ignored: {ref_fqcn(cls)}/{prop_name}')

    def _bind(self,
              controller_definition: Optional[ControllerDefinition],
              endpoint_config: EndpointDefinition,
              callable_obj: Callable):
        base_request_path: str = controller_definition.base_path if controller_definition else '/'
        if not base_request_path.endswith('/'):
            base_request_path += '/'
        for http_method in endpoint_config.methods:
            request_path = endpoint_config.path
            if request_path.startswith('/'):
                request_path = request_path[1:]
            request_path = urljoin(base_request_path, request_path)
            getattr(self._app, http_method.value)(request_path)(callable_obj)
            self._log.info(f'BIND {http_method.value} {request_path} to {callable_obj}')

    def instance(self) -> FastAPI:
        return self._app
