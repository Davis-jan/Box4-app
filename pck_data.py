"""Data loading, cleaning flags and KPI logic for the PCK Box4 dashboard.

Kept separate from the Streamlit UI so the same functions can be verified
independently (see verify_calculations.py).
"""
from __future__ import annotations

import pandas as pd

SCI_PATTERN = r"^\d+(?:\.\d+)?[eE][+-]?\d+$"


def load_data(source) -> pd.DataFrame:
    """Read the CSV with every column as text, then convert deliberately.

    Reading as text protects reference fields (e.g. 3.86E+14) from being
    silently altered by type inference.
    """
    raw = pd.read_csv(source, dtype=str, keep_default_na=False, na_values=[""])
    raw.columns = [c.strip() for c in raw.columns]
    df = pd.DataFrame(
        {
            "post_office": raw["Post_Office"].str.strip(),
            "ecitizen_ref": raw["Ecitizen Reference"].str.strip(),
            "channel_raw": raw["Payment Channel"].str.strip(),
            "payment_ref": raw["MPESA/Payment Reference"].str.strip(),
            "amount_paid": pd.to_numeric(raw["Amount Paid"], errors="raise"),
            "net_amount": pd.to_numeric(raw["Net Amount"], errors="raise"),
            "action": raw["Action"].str.strip(),
            "hour": pd.to_numeric(raw["Hour"], errors="raise").astype(int),
        }
    )
    df["date"] = pd.to_datetime(raw["Date"], format="%d/%m/%Y", errors="raise")
    df["time"] = raw["Time"]
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["weekday"] = df["date"].dt.day_name()

    # Payment channel groupings (exact labels preserved in channel_raw)
    mpesa_labels = {"MPESA", "MPesa"}
    df["is_mpesa"] = df["channel_raw"].isin(mpesa_labels)
    df["channel_group"] = df["channel_raw"].where(
        ~df["is_mpesa"], "M-Pesa (MPESA + MPesa)"
    )
    df["channel_family"] = df["is_mpesa"].map({True: "M-Pesa", False: "Other channels"})

    # Reconciliation
    df["variance"] = (df["amount_paid"] - df["net_amount"]).round(2)
    df["has_variance"] = df["variance"] != 0

    # Reference verification flags
    ref = df["payment_ref"]
    df["ref_missing"] = ref.isna()
    df["ref_sci"] = ref.fillna("").str.match(SCI_PATTERN)
    exact_dup = ref.notna() & ref.duplicated(keep=False)
    df["ref_repeat_clean"] = exact_dup & ~df["ref_sci"]  # verifiable repeats
    df["ref_repeat_sci"] = exact_dup & df["ref_sci"]  # unverifiable repeats

    def ref_status(r):
        if r.ref_missing:
            return "Missing reference"
        if r.ref_repeat_clean:
            return "Repeated reference (verifiable)"
        if r.ref_repeat_sci:
            return "Repeated, scientific notation (unverifiable)"
        if r.ref_sci:
            return "Scientific notation (precision lost)"
        return "Clean and unique"

    df["ref_status"] = df.apply(ref_status, axis=1)

    # Post office identifier type
    df["po_type"] = df["post_office"].fillna("").str.match(r"^\d+$").map(
        {True: "Numeric office code", False: "BOX account number"}
    )
    df.loc[df["post_office"].isna(), "po_type"] = "Missing"
    df["zero_amount"] = (df["amount_paid"] == 0) | (df["net_amount"] == 0)
    return df


def kpis(d: pd.DataFrame) -> dict:
    n = len(d)
    paid = float(d["amount_paid"].sum())
    net = float(d["net_amount"].sum())
    renewed = int((d["action"] == "Renewed successfully").sum())
    return {
        "records": n,
        "amount_paid": paid,
        "net_amount": net,
        "variance": round(paid - net, 2),
        "variance_records": int(d["has_variance"].sum()),
        "avg_paid": paid / n if n else 0.0,
        "renewed": renewed,
        "extend": int((d["action"] == "Extend").sum()),
        "renewal_rate": renewed / n if n else 0.0,
        "mpesa_exact_MPESA": int((d["channel_raw"] == "MPESA").sum()),
        "mpesa_exact_MPesa": int((d["channel_raw"] == "MPesa").sum()),
        "mpesa_combined": int(d["is_mpesa"].sum()),
        "mpesa_share_exact": (d["channel_raw"] == "MPESA").mean() if n else 0.0,
        "mpesa_share_combined": d["is_mpesa"].mean() if n else 0.0,
    }
