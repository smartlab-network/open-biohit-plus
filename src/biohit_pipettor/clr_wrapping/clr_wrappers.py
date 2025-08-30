from typing import Any, Callable, Dict, Tuple, Type

# overload support only works with this combination of System imports!
import System
from System import Boolean, Int32, Object, Single

CLR_TYPES: Dict[str, Tuple[Type, Type]] = {
    "System.String": (System.String, str),
    "Single": (Single, float),
    "Boolean": (Boolean, bool),
    "System.Object": (Object, object),
    "Int32": (Int32, int),
}


class ClrObject:
    _wrapped_instance: Type

    def __init__(self, wrapped_instance: Any) -> None:
        """
        Wraps an instance of a CLR class.
        """
        self._wrapped_instance = wrapped_instance

        # set methods
        for name in dir(self._wrapped_instance):
            attr = getattr(self._wrapped_instance, name)
            if attr.__class__.__name__ == "MethodBinding":
                if name.startswith(("add_", "remove_")):  # event handlers
                    continue
                try:
                    setattr(self, name, ClrMethod(attr))
                except NotImplementedError:  # ignore all methods which are not supported yet by the wrapping class
                    pass

    def __getattr__(self, item):
        # support all attributes that are translated to builtin types
        attr = getattr(self._wrapped_instance, item)
        if type(attr).__module__ == "builtins":
            return attr
        return super().__getattribute__(item)


class ClrMethod:
    __overloads: Dict[Tuple[Type, ...], Callable]
    __wrapped_method: Callable

    def __init__(self, wrapped_method: Callable) -> None:
        """Wraps a method of a CLR class to automatically infer the correct overload"""
        self.__wrapped_method = wrapped_method  # type: ignore

        # parse overloads from string representation of `Overloads` attribute
        self.__overloads = {}
        raw_overloads = str(getattr(self.__wrapped_method, "Overloads")).splitlines(keepends=False)
        for line in raw_overloads:
            ret_type, rest = line.split(maxsplit=1)
            raw_param_types = rest[:-1].split("(")[1]
            if "ByRef" in raw_param_types:
                raise NotImplementedError("ref types not implemented")
            param_types = []
            for raw_param_type in raw_param_types.split(", "):
                if raw_param_type != "":  # not empty
                    try:
                        param_types.append(CLR_TYPES[raw_param_type][1])
                    except KeyError:
                        raise NotImplementedError(f"Type {raw_param_type} not implemented")
            if param_types:
                self.__overloads[tuple(param_types)] = eval(
                    f"self._ClrMethod__wrapped_method.Overloads[{raw_param_types}]"
                )
            else:
                self.__overloads[()] = self.__wrapped_method

    def __call__(self, *args, **kwargs):
        n_args = len(args) + len(kwargs)
        for signature, method in self.__overloads.items():
            if len(signature) == n_args:
                return method(*args, **kwargs)
        raise NotImplementedError("Method with this signature does not exist")
