import dataclasses
from typing import Any, Dict


@dataclasses.dataclass
class Annotation:
    start_idx: str
    end_idx: str
    annotation_type: str  # TODO: add better typing here in the future
    annotation_data: Dict[str, Any]
