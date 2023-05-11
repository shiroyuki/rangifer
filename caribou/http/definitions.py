from abc import ABC
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


_HIDDEN_DEFINITION_ATTR_NAME = "__caribou_definition__"


class HttpMethod(Enum):
    """ Recognized HTTP Methods """
    GET = "get"
    DELETE = "delete"
    HEAD = "head"
    OPTION = "option"
    PATCH = "patch"
    POST = "post"
    PUT = "put"


class Endpoint(BaseModel):
    """ API Endpoint Definition """
    path: str
    methods: List[HttpMethod]
    extra_args: List[Any] = Field(default_factory=list)
    extra_kwargs: Dict[str, Any] = Field(default_factory=dict)


class Helper:
    """ Endpoint utility to help inspect and define endpoint definitions """

    @staticmethod
    def is_endpoint(obj) -> bool:
        return hasattr(obj, _HIDDEN_DEFINITION_ATTR_NAME)

    @staticmethod
    def set_definition(obj, endpoint: Endpoint):
        setattr(obj, _HIDDEN_DEFINITION_ATTR_NAME, endpoint)

    @staticmethod
    def get_definition(obj) -> Endpoint:
        return getattr(obj, _HIDDEN_DEFINITION_ATTR_NAME)


def endpoint(path: str, methods: Optional[List[HttpMethod]] = None, *args, **kwargs):
    """ Define an endpoint """
    def inner_decorator(handler: Callable):
        setattr(
            handler,
            _HIDDEN_DEFINITION_ATTR_NAME,
            Endpoint(path=path,
                        methods=methods or [HttpMethod.GET],
                        extra_args=args,
                        extra_kwargs=kwargs),
        )
        return handler

    return inner_decorator