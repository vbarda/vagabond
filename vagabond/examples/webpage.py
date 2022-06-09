from vagabond.annotator import FLAIR_MODEL_NAME, FlairAnnotator
from vagabond.extractor import ReadabilityExtractor
from vagabond.store import DictStore
from vagabond.processor import Processor, process_webpage


EXAMPLE_URL = "https://www.reuters.com/markets/us/us-mulls-lifting-some-china-tariffs-fight-inflation-commerce-secretary-says-2022-06-05/"


def run(url: str) -> None:
    store = DictStore()
    readability_extractor = ReadabilityExtractor()
    flair_annotator = FlairAnnotator(FLAIR_MODEL_NAME)
    processor = Processor(store, readability_extractor, [flair_annotator])
    uid = process_webpage(processor, url)
    text = store.get_text(uid)
    annotations = store.get_annotations(uid)
    for annotation in annotations:
        print(
            text[annotation.start_idx : annotation.end_idx],
            annotation.annotation_data["entity_type"],
        )


if __name__ == "__main__":
    run(EXAMPLE_URL)
