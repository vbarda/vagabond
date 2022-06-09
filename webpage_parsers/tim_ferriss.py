import dataclasses
import enum
import re
import regex
from typing import Dict, Iterator, List, Tuple

import funcy
from bs4 import BeautifulSoup, NavigableString, PageElement, Tag
from typing import Optional


@dataclasses.dataclass
class Span:
    start_idx: int
    end_idx: int


class MentionType(enum.Enum):
    PERSON = enum.auto()
    OTHER = enum.auto()


@dataclasses.dataclass
class Mention:
    text: str
    span: Span
    mention_type: MentionType


@dataclasses.dataclass
class Paragraph:
    # We want to preserve text & mentions in the paragraph
    text: str
    mentions: List[Mention]


def _make_html_tag_expression(tag: str) -> regex.Pattern:
    pattern_string = rf"(<{tag}>(?P<content>[^\<>]+)</{tag}>)+"
    return regex.compile(pattern_string)


class HTMLTagMatcher:
    def __init__(self, html_tag: str):
        self.html_tag = html_tag
        self._regex_pattern = _make_html_tag_expression(html_tag)

    def match(
        self, html_text: str, adjust_spans_for_tags: bool = True
    ) -> Iterator[Span]:
        start_tag = f"<{self.html_tag}>"
        end_tag = f"</{self.html_tag}>"
        for match in self._regex_pattern.finditer(html_text):
            start_idx = match.start()
            end_idx = match.end()
            if adjust_spans_for_tags:
                start_idx += len(start_tag)
                end_idx -= len(end_tag)

            yield Span(start_idx=start_idx, end_idx=end_idx)


EM_MATCHER = HTMLTagMatcher("em")
EM_TAG_REGEX = _make_html_tag_expression("strong")
TAG_REGEX = re.compile(r"<[a-z]+[^\<>]*>|</[a-z]+[^\<>]*>")
MAX_MENTION_LENGTH = 64  # arbitrary -- remove mentions with long text


def _get_adjusted_mention_spans(
    mention_spans: Iterator[Span], html_text: str
) -> Iterator[Span]:
    # TODO: rewrite this to not have to call TAG_REGEX twice
    start_idx_to_mention_span = {span.start_idx: span for span in mention_spans}
    adjustment = 0
    for tag_match in TAG_REGEX.finditer(html_text):
        tag_start_idx, tag_end_idx = tag_match.span()
        adjustment += tag_end_idx - tag_start_idx
        mention_span = start_idx_to_mention_span.get(tag_end_idx)
        if mention_span is not None:
            adjusted_mention_span = Span(
                start_idx=mention_span.start_idx - adjustment,
                end_idx=mention_span.end_idx - adjustment,
            )
            yield adjusted_mention_span


def _get_mentions_from_mention_spans(
    text: str, mention_spans: Iterator[Span]
) -> Iterator[Mention]:
    for span in mention_spans:
        yield Mention(
            text=text[span.start_idx : span.end_idx],
            span=span,
            mention_type=MentionType.OTHER,
        )


def _filter_mentions(mentions: Iterator[Mention]) -> Iterator[Mention]:
    for mention in mentions:
        if (
            len(mention.text) >= MAX_MENTION_LENGTH
            or mention.text.isupper()
            or mention.text.islower()
        ):
            continue

        yield mention


def _collect_paragraph_nodes(html_text: str) -> List[Tag]:
    bs = BeautifulSoup(html_text, features="html5lib")
    return bs.find_all("p", attrs={"class": None})


def get_paragraph(mention_matcher: HTMLTagMatcher, paragraph_node: Tag) -> Paragraph:
    paragraph_html_text = paragraph_node.decode()
    mention_spans = mention_matcher.match(
        paragraph_html_text, adjust_spans_for_tags=True
    )
    adjusted_mention_spans = _get_adjusted_mention_spans(
        mention_spans, paragraph_html_text
    )

    paragraph_text = TAG_REGEX.sub("", paragraph_html_text)
    mentions = _get_mentions_from_mention_spans(paragraph_text, adjusted_mention_spans)
    filtered_mentions = _filter_mentions(mentions)
    return Paragraph(text=paragraph_text, mentions=list(filtered_mentions))


def get_paragraphs(mention_matcher: HTMLTagMatcher, html_text: str) -> List[Paragraph]:
    return [
        get_paragraph(mention_matcher, _t) for _t in _collect_paragraph_nodes(html_text)
    ]


# Additional logic to pull references


def _process_string(s):
    return s.lower().strip()


def _has_preceding_item_with_text(
    item: PageElement, title: str, max_lookback: int
) -> bool:
    title_str = _process_string(title)
    previous_item = item.previous
    n_steps = 1
    while n_steps <= max_lookback:
        if isinstance(previous_item, NavigableString):
            previous_item_str = _process_string(str(previous_item))
            if previous_item_str == title_str:
                return True

        previous_item = previous_item.previous
        n_steps += 1

    return False


def _has_preceding_title(item: PageElement, title: str) -> bool:
    title_str = _process_string(title)
    for title_level in ("h4", "h3", "h2", "h1"):
        previous_title_node = item.find_previous(title_level)
        if previous_title_node is None:
            continue

        previous_title_str = _process_string(previous_title_node.text)
        if previous_title_str == title_str:
            return True

    return False


HAS_PEOPLE_MENTIONED_TITLE = funcy.partial(
    _has_preceding_title, title="people mentioned"
)
HAS_SELECTED_LINKS_TITLE = funcy.partial(
    _has_preceding_title, title="selected links from the episode"
)
KEY_TO_FILTER_FUNC = {
    "selected_links": HAS_SELECTED_LINKS_TITLE,
    "people_mentioned": HAS_PEOPLE_MENTIONED_TITLE,
}


def _get_list_nodes_from_show_notes(html_text: str) -> Dict[str, PageElement]:
    list_nodes = {
        "selected_links": None,
        "people_mentioned": None,
    }
    bs = BeautifulSoup(html_text, features="html5lib")
    for list_node in bs.find_all("ul", attrs={"class": None}):
        for key, filter_func in KEY_TO_FILTER_FUNC.items():
            if filter_func(list_node):
                list_nodes[key] = list_node

    return list_nodes


@dataclasses.dataclass
class Reference:
    text: str
    source: Optional[str]


def _convert_link_node_to_reference(link_node: Tag) -> Reference:
    return Reference(text=link_node.text, source=link_node.attrs.get("href"))


def _deduplicate_references(references: List[Reference]) -> List[Reference]:
    references_by_text = funcy.group_by(lambda ref: ref.text, references)
    deduplicated: List[Reference] = []
    true_duplicates: List[Tuple[str, Reference]] = []
    for reference_text, references_for_text in references_by_text.items():
        sources = set(ref.source for ref in references_for_text)
        if len(sources) == 1:
            deduplicated.append(references_for_text[0])
        else:
            true_duplicates.append((text, references_for_text))

    if true_duplicates:
        most_common_duplicates = sorted(
            true_duplicates, key=lambda dup: len(dup[1]), reverse=True
        )[:5]
        raise ValueError(
            f"References must have unique texts, found duplicates (showing first 5 values): {most_common_duplicates}"
        )

    return sorted(deduplicated, key=lambda ref: (-len(ref.text), ref.text))


def get_people_references(people_mentioned_list_node: Tag) -> List[Reference]:
    link_nodes = people_mentioned_list_node.find_all("a")
    return [_convert_link_node_to_reference(link_node) for link_node in link_nodes]


def get_deduplicated_people_references(
    text: str, speaker_names: List[str]
) -> List[Reference]:
    list_nodes = _get_list_nodes_from_show_notes(text)
    people_references = get_people_references(list_nodes["people_mentioned"])
    deduplicated_people_references = _deduplicate_references(
        [ref for ref in people_references if ref.text not in speaker_names]
    )
    return deduplicated_people_references


def annotate_paragraph_with_references(
    paragraph: Paragraph, references: List[Reference], mention_type: MentionType
) -> Paragraph:
    min_reference_length = min(len(ref.text) for ref in references)
    if len(paragraph.text) < min_reference_length:
        # there is nothing to annotate
        return paragraph

    mentions = []
    for reference in references:
        for match in re.finditer(reference.text, paragraph.text):
            span = Span(start_idx=match.start(), end_idx=match.end())
            mention = Mention(match.group(), span=span, mention_type=mention_type)
            mentions.append(mention)

    merged_mentions = paragraph.mentions + mentions
    return dataclasses.replace(paragraph, mentions=merged_mentions)
