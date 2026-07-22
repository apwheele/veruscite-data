"""
Accuracy tables for the V1 benchmark (same numbers as CiteCheck validation.html).

Quarto example:

    from src.metrics import extraction_report, checking_report, load_ground_truth

    extraction_report("V1")
    checking_report("V1")
    load_ground_truth("V1")
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.match import identity_key, identity_keys, norm_doi, pair_by_row_order, pair_citations

# Hand labels (public CSV) and checker predictions map into four categories.
STATUS_TO_CATEGORY = {
    "verified": "verified",
    "minor_error": "minor_error",
    "uncertain": "minor_error",
    "unverified": "minor_error",
    "hallucination": "hallucination",
    "possible_hallucination": "hallucination",
    "not_found": "not_found",
}
CATEGORIES = ("verified", "minor_error", "hallucination", "not_found")
NON_VERIFIED = ("minor_error", "hallucination", "not_found")


def _as_path(v1_dir: str | Path) -> Path:
    return Path(v1_dir).expanduser().resolve()


def load_ground_truth(v1_dir: str | Path = "V1") -> pd.DataFrame:
    """Load the single concatenated ground-truth CSV."""
    path = _as_path(v1_dir) / "ground_truth.csv"
    return pd.read_csv(path)


def _document_stem(source_pdf: Any) -> str:
    text = "" if source_pdf is None or (isinstance(source_pdf, float) and pd.isna(source_pdf)) else str(source_pdf)
    text = text.strip()
    if text.lower().endswith(".pdf"):
        return text[:-4]
    return text


def ground_truth_by_document(v1_dir: str | Path = "V1") -> dict[str, pd.DataFrame]:
    """Map document stem → ground-truth rows (without source_pdf column)."""
    full = load_ground_truth(v1_dir)
    if "source_pdf" not in full.columns:
        raise ValueError("ground_truth.csv must include a source_pdf column")
    out: dict[str, pd.DataFrame] = {}
    for source_pdf, group in full.groupby(full["source_pdf"].map(_document_stem), sort=True):
        out[str(source_pdf)] = group.drop(columns=["source_pdf"]).reset_index(drop=True)
    return out


def list_run_ids(v1_dir: str | Path, kind: str) -> list[str]:
    """kind is 'extraction' or 'checking'."""
    parent = _as_path(v1_dir) / f"{kind}_run"
    if not parent.is_dir():
        return []
    return sorted(
        p.name
        for p in parent.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )


def _run_dir(v1_dir: str | Path, kind: str, run_id: str) -> Path:
    return _as_path(v1_dir) / f"{kind}_run" / run_id


def _load_metadata(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "run_metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _run_csv_stems(run_dir: Path) -> list[str]:
    return sorted(
        p.stem
        for p in run_dir.glob("*.csv")
        if p.name != "document_metrics.csv"
    )


def _load_run_csv(run_dir: Path, stem: str) -> pd.DataFrame:
    path = run_dir / f"{stem}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _norm_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _status_category(value: Any) -> str:
    text = _norm_text(value)
    text = re.sub(r"^verificationstatus\.", "", text)
    return STATUS_TO_CATEGORY.get(text, "minor_error" if text else "verified")


def _expected_category(row: pd.Series) -> str:
    """Map hand labels to metric categories (matches CiteCheck get_expected_status)."""
    # Public labels we treat as intentional annotations.
    labeled = {
        "verified",
        "minor_error",
        "hallucination",
        "possible_hallucination",
        "not_found",
    }
    for col in ("expected_status", "notes"):
        if col not in row.index:
            continue
        text = _norm_text(row.get(col))
        if text in labeled:
            return STATUS_TO_CATEGORY[text]
    # Unknown labels (e.g. rare "uncertain") default to verified, as in CiteCheck.
    return "verified"


def _model_and_date(run_id: str, metadata: dict[str, Any]) -> tuple[str, str]:
    model = metadata.get("model") or run_id.rsplit("_", 1)[0]
    date_run = metadata.get("started_at") or (
        run_id.rsplit("_", 1)[-1] if "_" in run_id else run_id
    )
    return str(model), str(date_run)


def _ocr_backend(metadata: dict[str, Any]) -> str:
    raw = str(metadata.get("ocr_backend") or "").strip()
    if not raw:
        return ""
    lowered = raw.lower().replace("_", "")
    if lowered in {"pypdfium2", "pypdfium"}:
        return "pypdfium2"
    if lowered == "liteparse":
        return "liteparse"
    return raw


def _cost_usd(metadata: dict[str, Any], run_dir: Path) -> float:
    totals = metadata.get("totals") or {}
    if totals.get("cost_usd") is not None:
        return round(float(totals["cost_usd"]), 6)
    cost = 0.0
    for stem in _run_csv_stems(run_dir):
        df = _load_run_csv(run_dir, stem)
        if not df.empty and "cost_usd" in df.columns:
            cost += float(df["cost_usd"].fillna(0).sum())
    return round(cost, 6)


def _cost_component(metadata: dict[str, Any], run_dir: Path, key: str) -> float:
    totals = metadata.get("totals") or {}
    if totals.get(key) is not None:
        return round(float(totals[key]), 6)
    cost = 0.0
    for stem in _run_csv_stems(run_dir):
        df = _load_run_csv(run_dir, stem)
        if not df.empty and key in df.columns:
            cost += float(df[key].fillna(0).sum())
    return round(cost, 6)


def _latency_stats(run_dir: Path, metadata: dict[str, Any]) -> dict[str, float | None]:
    latencies: list[float] = []
    for stem in _run_csv_stems(run_dir):
        df = _load_run_csv(run_dir, stem)
        if df.empty or "elapsed_seconds" not in df.columns:
            continue
        for value in df["elapsed_seconds"].dropna():
            try:
                latencies.append(float(value))
            except (TypeError, ValueError):
                continue

    totals = metadata.get("totals") or {}
    wall = metadata.get("elapsed_seconds")
    cite_count = int(totals.get("citation_count") or 0)

    if latencies:
        ordered = sorted(latencies)
        n = len(ordered)
        p95_idx = min(n - 1, max(0, int((n - 1) * 0.95)))
        total = sum(ordered)
        avg = total / n
        max_sec = ordered[-1]
        p95 = ordered[p95_idx]
    else:
        avg = totals.get("avg_seconds_per_citation")
        max_sec = totals.get("max_seconds_per_citation")
        p95 = totals.get("p95_seconds_per_citation")
        total = totals.get("total_citation_latency_seconds")

    cpm = totals.get("citations_per_minute")
    if cpm is None and wall and cite_count:
        cpm = round(cite_count / (float(wall) / 60.0), 2)

    def _f(value: Any) -> float | None:
        if value is None:
            return None
        return float(value)

    return {
        "wall_elapsed_seconds": _f(wall),
        "avg_seconds_per_citation": _f(avg),
        "max_seconds_per_citation": _f(max_sec),
        "p95_seconds_per_citation": _f(p95),
        "citations_per_minute": _f(cpm),
    }


def _fmt_rate(count: int, total: int) -> str:
    if total <= 0:
        return "—" if count == 0 else f"100.0% ({count})"
    return f"{100.0 * count / total:.1f}% ({count})"


def _fmt_recall(correct: int, total: int) -> str:
    if total <= 0:
        return "—" if correct == 0 else f"100.0% ({correct}/{correct})"
    return f"{100.0 * correct / total:.1f}% ({correct}/{total})"


def _count_true_extra(
    extracted: pd.DataFrame,
    ground_truth: pd.DataFrame,
    pairing,
) -> int:
    """Unmatched extraction rows that are not duplicates of already-matched work.

    An unmatched extraction is ignored (not a hallucination) when it shares a
    DOI/identity with a matched ground-truth row, or with another extraction row
    that was successfully matched (near-duplicate listing).
    """
    unmatched = pairing.unmatched_other
    if not unmatched:
        return 0

    matched_keys: set[str] = set()
    matched_dois: set[str] = set()
    matched_ext = {oi for _gi, oi, _score in pairing.pairs}

    for gi, oi, _score in pairing.pairs:
        for row in (ground_truth.iloc[gi], extracted.iloc[oi]):
            matched_keys.update(identity_keys(row))
            doi = norm_doi(row.get("doi"))
            if doi:
                matched_dois.add(doi)

    # Also link later extraction rows that only collide with earlier matched
    # extraction identity keys (title/DOI/raw), same idea as mark_duplicate_citations.
    seen_ext_keys: set[str] = set()
    for oi in range(len(extracted)):
        keys = set(identity_keys(extracted.iloc[oi]))
        if oi in matched_ext:
            seen_ext_keys.update(keys)

    n_extra = 0
    for oi in unmatched:
        row = extracted.iloc[oi]
        keys = set(identity_keys(row))
        doi = norm_doi(row.get("doi"))
        if keys & matched_keys or keys & seen_ext_keys or (doi and doi in matched_dois):
            continue
        n_extra += 1
    return n_extra


def extraction_report(v1_dir: str | Path = "V1") -> pd.DataFrame:
    """One row per extraction run (correct / missing / extra vs ground truth)."""
    v1 = _as_path(v1_dir)
    gt_by_doc = ground_truth_by_document(v1)
    rows: list[dict[str, Any]] = []

    for run_id in list_run_ids(v1, "extraction"):
        run_dir = _run_dir(v1, "extraction", run_id)
        metadata = _load_metadata(run_dir)
        model, date_run = _model_and_date(run_id, metadata)

        real = 0
        correct = 0
        missing = 0
        hallucinated = 0

        for stem in _run_csv_stems(run_dir):
            gt = gt_by_doc.get(stem)
            ext = _load_run_csv(run_dir, stem)
            if gt is None or gt.empty or ext.empty:
                continue
            real += len(gt)
            pairing = pair_citations(gt, ext)
            correct += pairing.matched_count
            missing += len(pairing.unmatched_ground_truth)
            hallucinated += _count_true_extra(ext, gt, pairing)

        totals = metadata.get("totals") or {}
        wall = metadata.get("elapsed_seconds")
        try:
            wall_f = float(wall) if wall is not None else None
        except (TypeError, ValueError):
            wall_f = None
        try:
            extract_sec = totals.get("extract_seconds")
            extract_f = float(extract_sec) if extract_sec is not None else None
        except (TypeError, ValueError):
            extract_f = None
        docs_per_min = None
        if wall_f and wall_f > 0:
            n_docs = len(_run_csv_stems(run_dir))
            docs_per_min = round(n_docs / (wall_f / 60.0), 2)

        rows.append(
            {
                "model": model,
                "provider": str(metadata.get("provider") or "").strip(),
                "ocr_backend": _ocr_backend(metadata),
                "date_run": date_run,
                "real_citations": real,
                "correctly_extracted": correct,
                "missing_citations": missing,
                "hallucinated_citations": hallucinated,
                "wall_elapsed_seconds": wall_f,
                "extract_seconds": extract_f,
                "docs_per_minute": docs_per_min,
                "cost_usd": _cost_usd(metadata, run_dir),
                "run_id": run_id,
            }
        )

    columns = [
        "model",
        "provider",
        "ocr_backend",
        "date_run",
        "real_citations",
        "correctly_extracted",
        "missing_citations",
        "hallucinated_citations",
        "wall_elapsed_seconds",
        "extract_seconds",
        "docs_per_minute",
        "cost_usd",
        "run_id",
    ]
    return pd.DataFrame(rows, columns=columns)


def checking_report(v1_dir: str | Path = "V1") -> pd.DataFrame:
    """One row per checker run (FPs on verified, recall on non-verified labels).

    V1 checker runs are ground-truth-fed, so predictions pair to labels by row order.
    """
    v1 = _as_path(v1_dir)
    gt_by_doc = ground_truth_by_document(v1)
    rows: list[dict[str, Any]] = []

    for run_id in list_run_ids(v1, "checking"):
        run_dir = _run_dir(v1, "checking", run_id)
        metadata = _load_metadata(run_dir)
        model, date_run = _model_and_date(run_id, metadata)

        actual = {c: 0 for c in CATEGORIES}
        verified_fp = {c: 0 for c in NON_VERIFIED}
        category_fn = {c: 0 for c in NON_VERIFIED}
        not_verified_fn_n = 0
        verified_via_crossref = 0
        non_verified = set(NON_VERIFIED)

        for stem in _run_csv_stems(run_dir):
            gt = gt_by_doc.get(stem)
            if gt is None or gt.empty:
                continue
            expected = gt.apply(_expected_category, axis=1)
            for category in CATEGORIES:
                actual[category] += int(expected.eq(category).sum())

            chk = _load_run_csv(run_dir, stem)
            if chk.empty:
                for category in expected:
                    if category == "verified":
                        continue
                    if category in category_fn:
                        category_fn[category] += 1
                        not_verified_fn_n += 1
                continue

            predicted = chk["verification_status"].map(_status_category)
            if "source" in chk.columns:
                verified_via_crossref += int(
                    (
                        predicted.eq("verified")
                        & chk["source"].map(_norm_text).str.startswith("crossref")
                    ).sum()
                )

            pairing = pair_by_row_order(gt, chk)
            for gt_idx, chk_idx, _score in pairing.pairs:
                exp = expected.iloc[gt_idx]
                pred = predicted.iloc[chk_idx]
                if exp == pred:
                    continue
                if exp == "verified":
                    if pred in verified_fp:
                        verified_fp[pred] += 1
                elif exp in category_fn:
                    category_fn[exp] += 1
                    if pred not in non_verified:
                        not_verified_fn_n += 1

            for gt_idx in pairing.unmatched_ground_truth:
                exp = expected.iloc[gt_idx]
                if exp in category_fn:
                    category_fn[exp] += 1
                    not_verified_fn_n += 1

        actual_not_verified = (
            actual["minor_error"] + actual["hallucination"] + actual["not_found"]
        )
        latency = _latency_stats(run_dir, metadata)

        rows.append(
            {
                "model": model,
                "provider": str(metadata.get("provider") or "").strip(),
                "date_run": date_run,
                "actual_verified": actual["verified"],
                "actual_minor_error": actual["minor_error"],
                "actual_hallucination": actual["hallucination"],
                "actual_not_found": actual["not_found"],
                "actual_not_verified": actual_not_verified,
                "verified_fp_minor_error": _fmt_rate(
                    verified_fp["minor_error"], actual["verified"]
                ),
                "verified_fp_hallucination": _fmt_rate(
                    verified_fp["hallucination"], actual["verified"]
                ),
                "verified_fp_not_found": _fmt_rate(
                    verified_fp["not_found"], actual["verified"]
                ),
                "minor_error_recall": _fmt_recall(
                    actual["minor_error"] - category_fn["minor_error"],
                    actual["minor_error"],
                ),
                "hallucination_recall": _fmt_recall(
                    actual["hallucination"] - category_fn["hallucination"],
                    actual["hallucination"],
                ),
                "not_found_recall": _fmt_recall(
                    actual["not_found"] - category_fn["not_found"],
                    actual["not_found"],
                ),
                "not_verified_recall": _fmt_recall(
                    actual_not_verified - not_verified_fn_n,
                    actual_not_verified,
                ),
                "verified_via_crossref": verified_via_crossref,
                **latency,
                "token_cost_usd": _cost_component(metadata, run_dir, "token_cost_usd"),
                "web_search_cost_usd": _cost_component(
                    metadata, run_dir, "web_search_cost_usd"
                ),
                "cost_usd": _cost_usd(metadata, run_dir),
                "run_id": run_id,
            }
        )

    columns = [
        "model",
        "provider",
        "date_run",
        "actual_verified",
        "actual_minor_error",
        "actual_hallucination",
        "actual_not_found",
        "actual_not_verified",
        "verified_fp_minor_error",
        "verified_fp_hallucination",
        "verified_fp_not_found",
        "minor_error_recall",
        "hallucination_recall",
        "not_found_recall",
        "not_verified_recall",
        "verified_via_crossref",
        "wall_elapsed_seconds",
        "avg_seconds_per_citation",
        "max_seconds_per_citation",
        "p95_seconds_per_citation",
        "citations_per_minute",
        "token_cost_usd",
        "web_search_cost_usd",
        "cost_usd",
        "run_id",
    ]
    return pd.DataFrame(rows, columns=columns)
