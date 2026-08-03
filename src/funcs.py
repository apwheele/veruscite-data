"""Table and figure helpers for the VerusCite V1 benchmark report."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from IPython.display import Markdown

from src.metrics import (
    checking_report,
    extraction_report,
    load_ground_truth,
)

# Plain numbers, one-decimal strings, and metric cells like "0.1% (2)" / "63.1% (89/141)".
_NUMERIC_CELL = re.compile(
    r"""^
    [\d,]+(?:\.\d+)?%?          # 12 / 1.15 / 63.1%
    (?:\s*\([^)]*\))?           # optional (2) or (89/141)
    $""",
    re.VERBOSE,
)

# Public package ships as V1/ (capital V); accept either spelling on case-sensitive FS.
_ROOT = Path(__file__).resolve().parent.parent
V1_DIR = _ROOT / "V1" if (_ROOT / "V1").is_dir() else _ROOT / "v1"


def md_table(df: pd.DataFrame) -> Markdown:
    """Render a DataFrame as markdown with numeric columns right-aligned.

    Uses disable_numparse so pre-formatted decimals (e.g. Docs/min ``3.0``)
    are preserved, and colalign so number columns stay right-aligned in PDF.
    """
    aligns = [_column_align(df[col]) for col in df.columns]
    return Markdown(
        df.to_markdown(index=False, disable_numparse=True, colalign=aligns)
    )


def _column_align(series: pd.Series) -> str:
    """Return 'right' for numeric / metric columns, else 'left'."""
    if pd.api.types.is_numeric_dtype(series):
        return "right"
    vals = [
        str(v).strip()
        for v in series
        if pd.notna(v) and str(v).strip() != ""
    ]
    if vals and all(_NUMERIC_CELL.match(v) for v in vals):
        return "right"
    return "left"


def ground_truth_summary() -> pd.DataFrame:
    """Summary of ground-truth labels by document."""
    gt = load_ground_truth(V1_DIR)
    gt["category"] = gt.apply(_expected_category, axis=1)
    summary = (
        gt.groupby("source_pdf")["category"]
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )
    summary["total"] = summary.drop(columns=["source_pdf"]).sum(axis=1)
    summary = summary.sort_values("source_pdf").reset_index(drop=True)
    return summary


def ground_truth_totals() -> pd.Series:
    """Aggregate counts across all documents."""
    gt = load_ground_truth(V1_DIR)
    gt["category"] = gt.apply(_expected_category, axis=1)
    return gt["category"].value_counts()


def extraction_table() -> pd.DataFrame:
    """Formatted extraction results table (accuracy + speed)."""
    df = extraction_report(V1_DIR)
    df["extraction_rate"] = (
        df["correctly_extracted"] / df["real_citations"] * 100
    ).round(1)
    df["cost_usd"] = df["cost_usd"].round(2)
    if "wall_elapsed_seconds" in df.columns:
        df["wall_min"] = (df["wall_elapsed_seconds"] / 60.0).round(1)
    else:
        df["wall_min"] = pd.NA
    if "docs_per_minute" in df.columns:
        # Force one decimal in markdown/PDF (avoids 3 vs 3.0).
        df["docs_per_min"] = df["docs_per_minute"].map(
            lambda x: f"{float(x):.1f}" if pd.notna(x) else ""
        )
    else:
        df["docs_per_min"] = ""
    # Default model first (gemini-3.1-flash-lite), then by extraction rate desc.
    df["_default"] = df["model"].eq("gemini-3.1-flash-lite").astype(int)
    df = df.sort_values(
        ["_default", "extraction_rate", "wall_min"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    cols = [
        "model",
        "real_citations",
        "correctly_extracted",
        "missing_citations",
        "hallucinated_citations",
        "extraction_rate",
        "wall_min",
        "docs_per_min",
        "cost_usd",
    ]
    out = df[cols].copy()
    out.columns = [
        "Model",
        "Real",
        "Correct",
        "Missing",
        "Extra",
        "Rate (%)",
        "Wall min",
        "Docs/min",
        "Cost",
    ]
    return out


def checking_table() -> pd.DataFrame:
    """Formatted checker results table (key metrics only).

    Includes a Date column so repeat runs of the same model/provider can be
    compared (run-to-run variance).
    """
    df = checking_report(V1_DIR)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date_run"], utc=True, errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    cols = [
        "model",
        "provider",
        "date",
        "verified_fp_hallucination",
        "verified_fp_minor_error",
        "hallucination_recall",
        "not_verified_recall",
    ]
    out = df[cols].copy()
    # Compact headers avoid PDF column collision on letter-size pages.
    out.columns = [
        "Model",
        "Provider",
        "Date",
        "FP Hall.",
        "FP Minor",
        "Hall. Recall",
        "NV Recall",
    ]
    return out


def checking_full_table() -> pd.DataFrame:
    """Full checker report (all columns, human-readable names)."""
    df = checking_report(V1_DIR)
    df = df.drop(columns=["run_id", "date_run"])
    return df


def cost_comparison_table() -> pd.DataFrame:
    """Cost breakdown for checker runs, including wall time per paper."""
    df = checking_report(V1_DIR)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date_run"], utc=True, errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    df["token_cost_usd"] = df["token_cost_usd"].round(2)
    df["web_search_cost_usd"] = df["web_search_cost_usd"].round(2)
    df["cost_usd"] = df["cost_usd"].round(2)

    n_docs = 36
    # Prefer mean document elapsed from document_metrics (true per-paper runtime).
    # Fall back to full-corpus wall / n_docs if metrics are missing.
    sec_per_paper: list[float | None] = []
    for run_id in df["run_id"]:
        metrics_path = V1_DIR / "checking_run" / str(run_id) / "document_metrics.csv"
        if metrics_path.is_file():
            metrics = pd.read_csv(metrics_path)
            if "elapsed_seconds" in metrics.columns and not metrics.empty:
                sec_per_paper.append(round(float(metrics["elapsed_seconds"].mean()), 1))
                continue
        wall = df.loc[df["run_id"] == run_id, "wall_elapsed_seconds"]
        if not wall.empty and pd.notna(wall.iloc[0]):
            sec_per_paper.append(round(float(wall.iloc[0]) / n_docs, 1))
        else:
            sec_per_paper.append(None)
    df["sec_per_paper"] = sec_per_paper
    df["per_paper_usd"] = (df["cost_usd"] / n_docs).round(2)
    if "wall_elapsed_seconds" in df.columns:
        df["wall_min"] = (df["wall_elapsed_seconds"] / 60.0).round(1)
    else:
        df["wall_min"] = pd.NA

    cols = [
        "model",
        "provider",
        "date",
        "token_cost_usd",
        "web_search_cost_usd",
        "cost_usd",
        "per_paper_usd",
        "sec_per_paper",
        "wall_min",
    ]
    out = df[cols].copy()
    out.columns = [
        "Model",
        "Provider",
        "Date",
        "Token Cost (USD)",
        "Search Cost (USD)",
        "Total (USD)",
        "Per Paper (USD)",
        "Sec/paper",
        "Wall min",
    ]
    return out


def _expected_category(row: pd.Series) -> str:
    """Map hand labels to metric categories."""
    STATUS_MAP = {
        "verified": "verified",
        "minor_error": "minor_error",
        "uncertain": "minor_error",
        "unverified": "minor_error",
        "hallucination": "hallucination",
        "possible_hallucination": "hallucination",
        "not_found": "not_found",
    }
    for col in ("expected_status", "notes"):
        if col not in row.index:
            continue
        text = str(row.get(col, "")).strip().lower() if pd.notna(row.get(col)) else ""
        if text in STATUS_MAP:
            return STATUS_MAP[text]
    return "verified"
