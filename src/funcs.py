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

V1_DIR = Path(__file__).resolve().parent.parent / "v1"


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
    """Formatted extraction results table."""
    df = extraction_report(V1_DIR)
    df["extraction_rate"] = (
        df["correctly_extracted"] / df["real_citations"] * 100
    ).round(1)
    cols = [
        "model",
        "ocr_backend",
        "real_citations",
        "correctly_extracted",
        "missing_citations",
        "hallucinated_citations",
        "extraction_rate",
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
        "Cost ($)",
    ]
    return out


def checking_table() -> pd.DataFrame:
    """Formatted checker results table (key metrics only)."""
    df = checking_report(V1_DIR)
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
        "FP → Hallucination",
        "FP → Minor Error",
        "Hallucination Recall",
        "Not-Verified Recall",
        "CrossRef Verified",
        "Cost ($)",
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
    cols = ["model", "provider", "token_cost_usd", "web_search_cost_usd", "cost_usd"]
    out = df[cols].copy()
    out.columns = ["Model", "Provider", "Token Cost ($)", "Search Cost ($)", "Total ($)"]
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
