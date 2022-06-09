import abc
from typing import List

from flair.data import Sentence
from flair.models import SequenceTagger

from vagabond.typedefs import Annotation


FLAIR_MODEL_NAME = "flair/ner-english"


class Annotator(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def annotate(self, text: str) -> List[Annotation]:
        raise NotImplementedError()


class FlairAnnotator(Annotator):
    def __init__(self, flair_model_name: str) -> None:
        self._flair_model_name = flair_model_name
        self._tagger = SequenceTagger.load(flair_model_name)

    @property
    def name(self) -> str:
        return f"Flair NER annotator, model '{self._flair_model_name}'"

    def annotate(self, text: str) -> List[Annotation]:
        sentence = Sentence(text)
        self._tagger.predict(sentence)
        annotations = [
            Annotation(
                start_idx=entity.start_position,
                end_idx=entity.end_position,
                annotation_type="ner",
                annotation_data={
                    "entity_type": entity.tag,
                    "model_name": self._flair_model_name,
                },
            )
            for entity in sentence.get_spans("ner")
        ]
        return annotations
