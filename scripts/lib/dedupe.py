#
# Similarity Detection: Near-duplicate identification for the BriefBot skill
# Uses n-gram analysis and Jaccard similarity to find redundant content
#

import re
from typing import List, Set, Tuple, Union

from . import schema


def standardize_text(raw_text: str) -> str:
    """
    Prepares text for comparison by applying normalization rules.

    Transformations applied:
    - Convert to lowercase
    - Replace punctuation with spaces
    - Collapse consecutive whitespace
    - Strip leading/trailing whitespace
    """
    processed = raw_text.lower()
    processed = re.sub(r'[^\w\s]', ' ', processed)
    processed = re.sub(r'\s+', ' ', processed)
    return processed.strip()


def extract_character_ngrams(raw_text: str, gram_size: int = 3) -> Set[str]:
    """
    Extracts overlapping character sequences from text.

    These n-grams serve as fingerprints for fuzzy matching,
    allowing detection of similar but not identical content.
    """
    cleaned_text = standardize_text(raw_text)

    # Handle edge case where text is shorter than gram_size
    if len(cleaned_text) < gram_size:
        return {cleaned_text}

    ngram_collection = set()
    position = 0
    while position <= len(cleaned_text) - gram_size:
        fragment = cleaned_text[position:position + gram_size]
        ngram_collection.add(fragment)
        position += 1

    return ngram_collection


def compute_jaccard_coefficient(collection_a: Set[str], collection_b: Set[str]) -> float:
    """
    Measures similarity between two sets using Jaccard index.

    The coefficient ranges from 0.0 (completely different) to 1.0 (identical).
    """
    if len(collection_a) == 0 or len(collection_b) == 0:
        return 0.0

    shared_elements = len(collection_a & collection_b)
    total_elements = len(collection_a | collection_b)

    if total_elements == 0:
        return 0.0

    return shared_elements / total_elements


def extract_comparable_text(
    content_item: Union[schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem]
) -> str:
    """
    Retrieves the primary text field from an item for comparison purposes.

    Different item types store their main content in different fields.
    """
    if isinstance(content_item, schema.RedditItem):
        return content_item.title
    elif isinstance(content_item, schema.YouTubeItem):
        return content_item.title
    else:
        # XItem and LinkedInItem both use 'text' field
        return content_item.text


def identify_duplicate_pairs(
    content_items: List[Union[schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem]],
    similarity_threshold: float = 0.7,
) -> List[Tuple[int, int]]:
    """
    Finds pairs of items that are likely duplicates based on text similarity.

    Returns a list of (index_a, index_b) tuples where index_a < index_b.
    Pairs exceeding the similarity threshold are considered duplicates.
    """
    duplicate_pairs = []

    # Pre-compute n-grams for all items to avoid redundant processing
    ngram_fingerprints = [
        extract_character_ngrams(extract_comparable_text(item))
        for item in content_items
    ]

    outer_index = 0
    while outer_index < len(content_items):
        inner_index = outer_index + 1
        while inner_index < len(content_items):
            similarity = compute_jaccard_coefficient(
                ngram_fingerprints[outer_index],
                ngram_fingerprints[inner_index]
            )
            if similarity >= similarity_threshold:
                duplicate_pairs.append((outer_index, inner_index))
            inner_index += 1
        outer_index += 1

    return duplicate_pairs


def remove_near_duplicates(
    content_items: List[Union[schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem]],
    similarity_threshold: float = 0.7,
) -> List[Union[schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem]]:
    """
    Filters out duplicate items, keeping the highest-scored version of each.

    Important: Items should be pre-sorted by score in descending order
    so that the kept item is always the better one.
    """
    if len(content_items) <= 1:
        return content_items

    duplicate_pairs = identify_duplicate_pairs(content_items, similarity_threshold)

    # Determine which indices to discard
    # We keep the higher-scored item (lower index in sorted list)
    indices_to_discard = set()
    for index_a, index_b in duplicate_pairs:
        if content_items[index_a].score >= content_items[index_b].score:
            indices_to_discard.add(index_b)
        else:
            indices_to_discard.add(index_a)

    # Build the filtered result
    filtered_items = []
    item_index = 0
    while item_index < len(content_items):
        if item_index not in indices_to_discard:
            filtered_items.append(content_items[item_index])
        item_index += 1

    return filtered_items


def dedupe_reddit(
    content_items: List[schema.RedditItem],
    similarity_threshold: float = 0.7,
) -> List[schema.RedditItem]:
    """Removes near-duplicate Reddit threads."""
    return remove_near_duplicates(content_items, similarity_threshold)


def dedupe_x(
    content_items: List[schema.XItem],
    similarity_threshold: float = 0.7,
) -> List[schema.XItem]:
    """Removes near-duplicate X posts."""
    return remove_near_duplicates(content_items, similarity_threshold)


def dedupe_youtube(
    content_items: List[schema.YouTubeItem],
    similarity_threshold: float = 0.7,
) -> List[schema.YouTubeItem]:
    """Removes near-duplicate YouTube videos."""
    return remove_near_duplicates(content_items, similarity_threshold)


def dedupe_linkedin(
    content_items: List[schema.LinkedInItem],
    similarity_threshold: float = 0.7,
) -> List[schema.LinkedInItem]:
    """Removes near-duplicate LinkedIn posts."""
    return remove_near_duplicates(content_items, similarity_threshold)
