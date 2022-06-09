import abc
import hashlib
from typing import List

from vagabond.typedefs import Annotation


class Store(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def get_uid(self, raw_data: bytes) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def set_raw_data(self, raw_data: bytes) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_raw_data(self, uid: str) -> bytes:
        raise NotImplementedError()

    @abc.abstractmethod
    def set_text(self, uid: str, text: str) -> None:
        # TODO: this should automatically invalidate annotations if the text changed
        raise NotImplementedError()

    @abc.abstractmethod
    def get_text(self, uid: str) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def set_annotations(self, uid: str, annotations: List[Annotation]) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_annotations(self, uid: str) -> List[Annotation]:
        raise NotImplementedError()


class DictStore(Store):
    _uid_to_raw_data = {}
    _uid_to_text = {}
    _uid_to_annotations = {}

    @staticmethod
    def get_uid(raw_data: bytes) -> str:
        return hashlib.md5(raw_data).hexdigest()

    def set_raw_data(self, raw_data: bytes) -> str:
        uid = self.get_uid(raw_data)
        self._uid_to_raw_data[uid] = raw_data
        return uid

    def get_raw_data(self, uid: str) -> bytes:
        if uid not in self._uid_to_raw_data:
            raise AssertionError(f"Missing raw data for uid {uid}")
        return self._uid_to_raw_data[uid]

    def set_text(self, uid: str, text: str) -> None:
        if self._uid_to_text.get(uid) != text:
            # invalidate annotations
            _ = self._uid_to_annotations.pop(uid, None)
        self._uid_to_text[uid] = text

    def get_text(self, uid: str) -> str:
        if uid not in self._uid_to_text:
            raise AssertionError(f"Missing text for uid {uid}")
        return self._uid_to_text[uid]

    def set_annotations(self, uid: str, annotations: List[Annotation]) -> None:
        self._uid_to_annotations[uid] = annotations

    def get_annotations(self, uid):
        if uid not in self._uid_to_annotations:
            raise AssertionError(f"Missing annotations for uid {uid}")
        return self._uid_to_annotations[uid]
