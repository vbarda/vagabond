import logging
from typing import List

import requests

from vagabond.annotator import Annotator
from vagabond.extractor import Extractor
from vagabond.store import Store


logger = logging.getLogger(__name__)


class Processor:
    def __init__(
        self, store: Store, extractor: Extractor, annotators: List[Annotator]
    ) -> None:
        self._store = store
        self._extractor = extractor
        self._annotators = annotators

    def process(self, raw_data: bytes) -> str:
        logger.info("Extracting text from raw data...")
        text = self._extractor.extract(raw_data.decode("utf-8"))
        logger.info("Successfully extracted text from raw data.")

        logger.info("Annotating text...")
        annotations = []
        for annotator in self._annotators:
            logger.info("Annotating with '%s' annotator...", annotator.name)
            annotations.extend(annotator.annotate(text))

        logger.info("Successfully annotated text.")

        logger.info("Writing the data to the store...")
        uid = self._store.set_raw_data(raw_data)
        self._store.set_text(uid, text)
        self._store.set_annotations(uid, annotations)
        logger.info("Successfully wrote the data to the store.")
        return uid


def process_webpage(processor: Processor, url: str) -> str:
    logger.info("Fetching data for url: %s", url)
    webpage_content = requests.get(url).text
    uid = processor.process(webpage_content.encode("utf-8"))
    return uid
