"""Near-duplicate detection using n-gram Jaccard similarity."""

import re
from typing import List, Set, Tuple, Union

from . import schema


_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "was", "are", "and", "or", "but",
    "in", "on", "at", "to", "for",
})


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, remove stop words, and collapse whitespace."""
    out = re.sub(r'[^\w\s]', ' ', text.lower())
    out = re.sub(r'\s+', ' ', out).strip()
    words = [w for w in out.split() if w not in _STOP_WORDS]
    return ' '.join(words)


def ngrams(text: str, n: int = 4) -> Set[str]:
    """Extract character n-grams from normalized text."""
    clean = normalize(text)
    if len(clean) < n:
        return {clean}
    return {clean[i:i + n] for i in range(len(clean) - n + 1)}


def jaccard(a: Set[str], b: Set[str]) -> float:
    """Compute Jaccard similarity coefficient between two sets."""
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / (union + 1e-10) if union else 0.0


def _text_of(
    item: Union[schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem],
) -> str:
    """Extract the primary text field from a content item."""
    if isinstance(item, (schema.RedditItem, schema.YouTubeItem)):
        return item.title
    return item.text


def find_dupes(
    items: List[Union[schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem]],
    threshold: float = 0.65,
) -> List[Tuple[int, int]]:
    """Return (i, j) index pairs where items exceed the similarity threshold."""
    fingerprints = [ngrams(_text_of(item)) for item in items]
    pairs = []

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if jaccard(fingerprints[i], fingerprints[j]) >= threshold:
                pairs.append((i, j))

    return pairs


def deduplicate(
    items: List[Union[schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem]],
    threshold: float = 0.65,
) -> List[Union[schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem]]:
    """Remove near-duplicates, keeping the higher-scored item from each pair."""
    if len(items) <= 1:
        return items

    dupes = find_dupes(items, threshold)

    discard = set()
    for i, j in dupes:
        if items[i].score >= items[j].score:
            discard.add(j)
        else:
            discard.add(i)

    return [item for idx, item in enumerate(items) if idx not in discard]


def dedupe_reddit(
    content_items: List[schema.RedditItem],
    similarity_threshold: float = 0.65,
) -> List[schema.RedditItem]:
    """Removes near-duplicate Reddit threads."""
    return deduplicate(content_items, similarity_threshold)


def dedupe_x(
    content_items: List[schema.XItem],
    similarity_threshold: float = 0.65,
) -> List[schema.XItem]:
    """Removes near-duplicate X posts."""
    return deduplicate(content_items, similarity_threshold)


def dedupe_youtube(
    content_items: List[schema.YouTubeItem],
    similarity_threshold: float = 0.65,
) -> List[schema.YouTubeItem]:
    """Removes near-duplicate YouTube videos."""
    return deduplicate(content_items, similarity_threshold)


def dedupe_linkedin(
    content_items: List[schema.LinkedInItem],
    similarity_threshold: float = 0.65,
) -> List[schema.LinkedInItem]:
    """Removes near-duplicate LinkedIn posts."""
    return deduplicate(content_items, similarity_threshold)
