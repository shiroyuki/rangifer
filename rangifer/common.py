from typing import Callable, Type, Union


def ref_fqcn(ref: Union[Callable, Type]) -> str:
    return f'{ref.__module__}.{ref.__name__}'