import typing
import weakref
from collections import defaultdict


class BaseClass:

    __refs = defaultdict(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__refs[self.__class__].append(self)

    @classmethod
    def instances(cls) -> typing.List:
        for instance in cls.__refs.get(cls, []):
            yield instance


class BaseClassWeakRef:

    __refs = defaultdict(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__refs[self.__class__].append(weakref.ref(self))

    @classmethod
    def instances(cls) -> typing.List:
        for instance_ref in cls.__refs.get(cls, []):
            instance = instance_ref()
            if instance is not None:
                yield instance
