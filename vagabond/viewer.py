from collections import defaultdict
import re
from typing import Dict, Set, Tuple

from vagabond.store import Store


WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_entity_text(entity_text: str) -> str:
    char_translation_table = str.maketrans({char: "" for char in {",", ".", "-"}})
    normalized_entity_text = (
        entity_text.lower().strip().translate(char_translation_table)
    )
    normalized_entity_text = WHITESPACE_PATTERN.sub(" ", normalized_entity_text)
    return normalized_entity_text


class EntityViewer:
    def __init__(
        self, entity_name_and_type_to_uids: Dict[Tuple[str, str], Set[str]]
    ) -> None:
        self._entity_name_and_type_to_uids = entity_name_and_type_to_uids

    @classmethod
    def from_store(cls, store: Store) -> "EntityViewer":
        entity_name_and_type_to_uids = defaultdict(set)
        for uid in store.get_uid_generator():
            annotations = store.get_annotations(uid)
            text = store.get_text(uid)
            for annotation in annotations:
                entity_text = text[annotation.start_idx : annotation.end_idx]
                normalized_entity_text = normalize_entity_text(entity_text)
                entity_name_and_type_to_uids[
                    (normalized_entity_text, annotation.annotation_data["entity_type"])
                ].add(uid)

        return cls(dict(entity_name_and_type_to_uids))

    def get_uids_for_entity(self, entity_name: str, entity_type: str) -> Set[str]:
        normalized_entity_text = normalize_entity_text(entity_name)
        return self._entity_name_and_type_to_uids.get(
            (normalized_entity_text, entity_type), set()
        )
