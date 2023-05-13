from abc import ABC
from enum import Enum
from inspect import isclass, isfunction
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union

from imagination.debug import get_logger
from pydantic import BaseModel, Field

from rangifer.common import ref_fqcn


_LOG = get_logger("rangifer.definition", logging.DEBUG)
_HIDDEN_DEFINITION_ATTR_NAME = "__caribou_definition__"


class HttpMethod(Enum):
    """Recognized HTTP Methods"""

    GET = "get"
    DELETE = "delete"
    HEAD = "head"
    OPTION = "option"
    PATCH = "patch"
    POST = "post"
    PUT = "put"


class ControllerDefinition(BaseModel):
    """API Controller Definition"""

    base_path: str
    auto_wired: bool = Field(default=True)
    init_args: List[Any] = Field(default_factory=list)
    init_kwargs: Dict[str, Any] = Field(default_factory=dict)


class EndpointDefinition(BaseModel):
    """API Endpoint Definition"""

    path: str
    methods: List[HttpMethod]
    extra_args: List[Any] = Field(default_factory=list)
    extra_kwargs: Dict[str, Any] = Field(default_factory=dict)


class Helper:
    """Endpoint utility to help inspect and define endpoint definitions"""

    @classmethod
    def is_controller(cls, obj) -> bool:
        return (
            hasattr(obj, _HIDDEN_DEFINITION_ATTR_NAME)
            and isclass(obj)
            and isinstance(cls.get_definition(obj), ControllerDefinition)
        )

    @classmethod
    def is_endpoint(cls, obj) -> bool:
        return (
            hasattr(obj, _HIDDEN_DEFINITION_ATTR_NAME)
            and isfunction(obj)
            and isinstance(cls.get_definition(obj), EndpointDefinition)
        )

    @staticmethod
    def set_definition(obj, endpoint: Union[ControllerDefinition, EndpointDefinition]):
        setattr(obj, _HIDDEN_DEFINITION_ATTR_NAME, endpoint)

    @staticmethod
    def get_definition(obj) -> Union[ControllerDefinition, EndpointDefinition]:
        return getattr(obj, _HIDDEN_DEFINITION_ATTR_NAME)


def endpoint(path: str, methods: Optional[List[HttpMethod]] = None, *args, **kwargs):
    """Define an endpoint"""

    def inner_decorator(handler: Callable):
        if not hasattr(handler, _HIDDEN_DEFINITION_ATTR_NAME):
            _LOG.debug(
                f"This method ({ref_fqcn(handler)}) is designated as API endpoint."
            )
        else:
            raise AssertionError(
                f"This method ({ref_fqcn(handler)}) already has the API endpoint definition. It cannot be defined twice."
            )

        setattr(
            handler,
            _HIDDEN_DEFINITION_ATTR_NAME,
            EndpointDefinition(
                path=path,
                methods=methods or [HttpMethod.GET],
                extra_args=args or list(),
                extra_kwargs=kwargs or dict(),
            ),
        )

        return handler

    return inner_decorator


def controller(base_path: str, auto_wired: bool = True, *init_args, **init_kwargs):
    def inner_decorator(cls: Type):
        if not hasattr(cls, _HIDDEN_DEFINITION_ATTR_NAME):
            _LOG.debug(f"This class ({ref_fqcn(cls)}) is designated as API controller.")
        else:
            raise AssertionError(
                f"This class ({ref_fqcn(cls)}) already has the API controller definition. It cannot be defined twice."
            )

        setattr(
            cls,
            _HIDDEN_DEFINITION_ATTR_NAME,
            ControllerDefinition(
                base_path=base_path,
                auto_wired=auto_wired,
                init_args=init_args or list(),
                init_kwargs=init_kwargs or dict(),
            ),
        )

        return cls

    return inner_decorator
