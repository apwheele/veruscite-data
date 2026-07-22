"""Fuzzy one-to-one citation matching (extraction vs ground truth)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

DEFAULT_MATCH_THRESHOLD = 0.82


def normalize_string(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def similarity(a: Any, b: Any) -> float:
    return SequenceMatcher(None, normalize_string(a), normalize_string(b)).ratio()


def norm_doi(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip().lower()
    if "doi.org/" in text:
        text = re.split(r"doi\.org/", text, maxsplit=1)[-1]
    text = re.sub(r"^doi:\s*", "", text)
    text = re.sub(r"\s+", "", text)  # OCR/export noise: "10.1016/ j.nds...."
    return text.rstrip(".)],;").strip()


def _norm_year(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    match = re.search(r"\d{4}", text)
    return match.group(0) if match else text


def _authors_list(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(a).strip() for a in value if str(a).strip()]
    return [part.strip() for part in str(value).split("|") if part.strip()]


def row_to_citation(row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    data = row.to_dict() if isinstance(row, pd.Series) else dict(row)
    return {
        "raw_text": data.get("raw_text") or "",
        "title": data.get("title") or "",
        "authors": _authors_list(data.get("authors")),
        "year": _norm_year(data.get("year")),
        "doi": norm_doi(data.get("doi")),
    }


def citation_match_score(left: dict[str, Any], right: dict[str, Any]) -> float:
    doi_left = left.get("doi") or ""
    doi_right = right.get("doi") or ""
    if doi_left and doi_right and doi_left == doi_right:
        return 1.0

    title_sim = similarity(left.get("title", ""), right.get("title", ""))
    raw_sim = similarity(left.get("raw_text", ""), right.get("raw_text", ""))

    year_left = left.get("year") or ""
    year_right = right.get("year") or ""
    year_match = 0.0
    if year_left and year_right:
        try:
            if abs(int(year_left) - int(year_right)) <= 1:
                year_match = 1.0
        except ValueError:
            year_match = similarity(year_left, year_right)

    authors_left = left.get("authors") or []
    authors_right = right.get("authors") or []
    author_sim = 0.0
    if authors_left and authors_right:
        author_sim = similarity(" ".join(authors_left), " ".join(authors_right))
        first_author = authors_left[0]
        if "," in first_author:
            surname = first_author.split(",")[0].strip().lower()
        else:
            parts = first_author.split()
            surname = parts[-1].lower() if parts else ""
        cand_str = normalize_string(" ".join(authors_right))
        if len(surname) > 2 and surname in cand_str:
            author_sim = max(author_sim, 0.95)

    has_title = bool(normalize_string(left.get("title"))) and bool(
        normalize_string(right.get("title"))
    )
    if has_title:
        score = (title_sim * 0.50) + (author_sim * 0.25) + (year_match * 0.15) + (
            raw_sim * 0.10
        )
    else:
        score = (raw_sim * 0.55) + (author_sim * 0.25) + (year_match * 0.20)

    if title_sim > 0.95 and author_sim > 0.90:
        score = max(score, 0.98)
    if title_sim >= 0.98:
        score = max(score, 0.92)
    if title_sim >= 0.95 and year_match == 1.0:
        score = max(score, 0.88)

    raw_left = normalize_string(left.get("raw_text"))
    raw_right = normalize_string(right.get("raw_text"))
    if raw_left and raw_right and raw_sim > 0.97 and year_match == 1.0:
        score = max(score, 0.95)

    return min(score, 1.0)


@dataclass(frozen=True)
class CitationMatchResult:
    pairs: list[tuple[int, int, float]]
    unmatched_ground_truth: list[int]
    unmatched_other: list[int]

    @property
    def matched_count(self) -> int:
        return len(self.pairs)


def _row_value(row: pd.Series | dict[str, Any], field: str) -> Any:
    if isinstance(row, pd.Series):
        return row.get(field)
    return row.get(field)


def _doi_key(row: pd.Series | dict[str, Any]) -> str:
    return norm_doi(_row_value(row, "doi"))


def _raw_text_key(row: pd.Series | dict[str, Any]) -> str:
    return normalize_string(_row_value(row, "raw_text"))


def _title_authors_key(row: pd.Series | dict[str, Any]) -> str:
    title = normalize_string(_row_value(row, "title"))
    authors = normalize_string(" ".join(_authors_list(_row_value(row, "authors"))))
    if not title or not authors:
        return ""
    return f"{title}\x1f{authors}"


def _pair_unique_keys(
    ground_truth: pd.DataFrame,
    other: pd.DataFrame,
    key_fn,
    *,
    pairs: list[tuple[int, int, float]],
    matched_gt: set[int],
    matched_other: set[int],
) -> None:
    left_by_key: dict[str, list[int]] = {}
    for gi in range(len(ground_truth)):
        if gi in matched_gt:
            continue
        key = key_fn(ground_truth.iloc[gi])
        if key:
            left_by_key.setdefault(key, []).append(gi)

    right_by_key: dict[str, list[int]] = {}
    for oi in range(len(other)):
        if oi in matched_other:
            continue
        key = key_fn(other.iloc[oi])
        if key:
            right_by_key.setdefault(key, []).append(oi)

    for key, gt_indices in left_by_key.items():
        other_indices = right_by_key.get(key)
        if not other_indices or len(gt_indices) != 1 or len(other_indices) != 1:
            continue
        gi, oi = gt_indices[0], other_indices[0]
        pairs.append((gi, oi, 1.0))
        matched_gt.add(gi)
        matched_other.add(oi)


def _pair_citations_fuzzy(
    ground_truth: pd.DataFrame,
    other: pd.DataFrame,
    gt_indices: list[int],
    other_indices: list[int],
    *,
    threshold: float,
) -> list[tuple[int, int, float]]:
    if not gt_indices or not other_indices:
        return []

    gt_citations = {gi: row_to_citation(ground_truth.iloc[gi]) for gi in gt_indices}
    other_citations = {oi: row_to_citation(other.iloc[oi]) for oi in other_indices}

    candidates: list[tuple[float, int, int]] = []
    for gi, gt_row in gt_citations.items():
        for oi, other_row in other_citations.items():
            score = citation_match_score(gt_row, other_row)
            if score >= threshold:
                candidates.append((score, gi, oi))

    candidates.sort(reverse=True)
    matched_gt: set[int] = set()
    matched_other: set[int] = set()
    pairs: list[tuple[int, int, float]] = []
    for score, gi, oi in candidates:
        if gi in matched_gt or oi in matched_other:
            continue
        pairs.append((gi, oi, score))
        matched_gt.add(gi)
        matched_other.add(oi)
    return pairs


def pair_citations(
    ground_truth: pd.DataFrame,
    other: pd.DataFrame,
    *,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> CitationMatchResult:
    """Pair rows: exact DOI/raw/title+authors, then fuzzy."""
    if ground_truth.empty:
        return CitationMatchResult([], [], list(range(len(other))))
    if other.empty:
        return CitationMatchResult([], list(range(len(ground_truth))), [])

    pairs: list[tuple[int, int, float]] = []
    matched_gt: set[int] = set()
    matched_other: set[int] = set()

    for key_fn in (_doi_key, _raw_text_key, _title_authors_key):
        _pair_unique_keys(
            ground_truth,
            other,
            key_fn,
            pairs=pairs,
            matched_gt=matched_gt,
            matched_other=matched_other,
        )

    unmatched_gt = [i for i in range(len(ground_truth)) if i not in matched_gt]
    unmatched_other = [i for i in range(len(other)) if i not in matched_other]
    pairs.extend(
        _pair_citations_fuzzy(
            ground_truth,
            other,
            unmatched_gt,
            unmatched_other,
            threshold=threshold,
        )
    )

    matched_gt = {gi for gi, _oi, _score in pairs}
    matched_other = {oi for _gi, oi, _score in pairs}
    return CitationMatchResult(
        pairs,
        [i for i in range(len(ground_truth)) if i not in matched_gt],
        [i for i in range(len(other)) if i not in matched_other],
    )


def pair_by_row_order(
    ground_truth: pd.DataFrame,
    checked: pd.DataFrame,
) -> CitationMatchResult:
    """1:1 pairing by CSV row order (ground-truth-fed checker runs)."""
    if ground_truth.empty:
        return CitationMatchResult([], [], list(range(len(checked))))
    if checked.empty:
        return CitationMatchResult([], list(range(len(ground_truth))), [])
    n = min(len(ground_truth), len(checked))
    return CitationMatchResult(
        [(i, i, 1.0) for i in range(n)],
        list(range(n, len(ground_truth))),
        list(range(n, len(checked))),
    )


def _author_surnames_fingerprint(authors: list[str]) -> str:
    """Surname-level tokens so middle-initial OCR variants still match."""
    tokens: list[str] = []
    for author in authors:
        parts = normalize_string(author).split()
        multi = [p for p in parts if len(p) > 1]
        if multi:
            tokens.append(multi[-1])
        elif parts:
            tokens.append(parts[-1])
    return "|".join(tokens)


def identity_keys(row: pd.Series | dict[str, Any]) -> list[str]:
    """All identity keys for a citation (DOI, title+surnames, raw prefix)."""
    keys: list[str] = []
    doi = norm_doi(_row_value(row, "doi"))
    if doi:
        keys.append(f"doi:{doi}")
    title = normalize_string(_row_value(row, "title"))
    authors_fp = _author_surnames_fingerprint(_authors_list(_row_value(row, "authors")))
    if title:
        keys.append(f"title:{title}|authors:{authors_fp}")
    if keys:
        return keys
    raw = normalize_string(_row_value(row, "raw_text"))
    return [f"raw:{raw[:160]}"] if raw else ["meta:::"]


def identity_key(row: pd.Series | dict[str, Any]) -> str:
    """Primary stable key for stripping duplicate extraction rows against matched GT."""
    keys = identity_keys(row)
    return keys[0] if keys else "meta:::"
