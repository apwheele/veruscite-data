"""Table and figure helpers for the VerusCite V1 benchmark report."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.metrics import (
    checking_report,
    extraction_report,
    load_ground_truth,
)

# Public package ships as V1/ (capital V); accept either spelling on case-sensitive FS.
_ROOT = Path(__file__).resolve().parent.parent
V1_DIR = _ROOT / "V1" if (_ROOT / "V1").is_dir() else _ROOT / "v1"


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
        df["docs_per_min"] = df["docs_per_minute"].round(1)
    else:
        df["docs_per_min"] = pd.NA
    # Default model first (gemini-3.1-flash-lite), then by extraction rate desc.
    df["_default"] = df["model"].eq("gemini-3.1-flash-lite").astype(int)
    df = df.sort_values(
        ["_default", "extraction_rate", "wall_min"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    cols = [
        "model",
        "ocr_backend",
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
        "OCR",
        "Real",
        "Correct",
        "Missing",
        "Extra",
        "Rate (%)",
        "Wall (min)",
        "Docs/min",
        "Cost (USD)",
    ]
    return out


def checking_table() -> pd.DataFrame:
    """Formatted checker results table (key metrics only)."""
    df = checking_report(V1_DIR)
    df["cost_usd"] = df["cost_usd"].round(2)
    cols = [
        "model",
        "provider",
        "verified_fp_hallucination",
        "verified_fp_minor_error",
        "hallucination_recall",
        "not_verified_recall",
        "verified_via_crossref",
        "cost_usd",
    ]
    out = df[cols].copy()
    out.columns = [
        "Model",
        "Provider",
        "FP Hallucination",
        "FP Minor Error",
        "Hallucination Recall",
        "Not-Verified Recall",
        "CrossRef Verified",
        "Cost (USD)",
    ]
    return out


def checking_full_table() -> pd.DataFrame:
    """Full checker report (all columns, human-readable names)."""
    df = checking_report(V1_DIR)
    df = df.drop(columns=["run_id", "date_run"])
    return df


def cost_comparison_table() -> pd.DataFrame:
    """Cost breakdown for checker runs."""
    df = checking_report(V1_DIR)
    df["token_cost_usd"] = df["token_cost_usd"].round(2)
    df["web_search_cost_usd"] = df["web_search_cost_usd"].round(2)
    df["cost_usd"] = df["cost_usd"].round(2)
    cols = ["model", "provider", "token_cost_usd", "web_search_cost_usd", "cost_usd"]
    out = df[cols].copy()
    out.columns = ["Model", "Provider", "Token Cost (USD)", "Search Cost (USD)", "Total (USD)"]
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
