import abc
from typing import FrozenSet, List

from bs4 import BeautifulSoup
from readability import Document


DEFAULT_NODE_TYPES_TO_KEEP = frozenset(["p", "h1", "h2", "h3", "li"])
TEXT_SEPARATOR = " "


class Extractor(abc.ABC):
    @abc.abstractmethod
    def extract(self, raw_data: bytes) -> str:
        raise NotImplementedError()


class ReadabilityExtractor(Extractor):
    def __init__(
        self, node_types_to_keep: FrozenSet[str] = DEFAULT_NODE_TYPES_TO_KEEP
    ) -> None:
        self._node_types_to_keep = node_types_to_keep

    def extract(self, raw_data: bytes) -> List[str]:
        clean_html_text = Document(raw_data).summary()
        bs = BeautifulSoup(clean_html_text, features="html5lib")
        return TEXT_SEPARATOR.join(
            node.text
            for node in bs.find_all(list(self._node_types_to_keep))
            if node.text
        )
