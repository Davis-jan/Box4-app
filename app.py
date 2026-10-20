"""PCK Box4 Executive Dashboard  (Streamlit + Pandas + Plotly)

Run:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pck_data import kpis, load_data

# ---------- PCK identity ----------
BLUE_DARK, BLUE, BLUE_MID, BLUE_LIGHT, BLUE_PALE = (
    "#0B2A5B", "#1558B0", "#4A8BDF", "#9DC3F2", "#E6EFFB",
)
RED = "#C8102E"
GREY = "#5F6B7A"
BLUES = [BLUE_DARK, BLUE, BLUE_MID, BLUE_LIGHT, "#6C7A92", "#B7C4D9"]
DEFAULT_CSV = Path(__file__).parent / "cleaned_pck_Box4_dataset.csv"

st.set_page_config(page_title="PCK Box4 Executive Dashboard", page_icon="📮", layout="wide")

st.markdown(
    f"""
    <style>
    .block-container {{padding-top: 1.2rem; max-width: 1400px;}}
    h1, h2, h3 {{color: {BLUE_DARK};}}
    .hdr {{background: linear-gradient(90deg,{BLUE_DARK},{BLUE}); color:#fff;
           padding: 18px 24px; border-radius: 10px; margin-bottom: 14px;}}
    .hdr h1 {{color:#fff; margin:0; font-size:1.7rem;}}
    .hdr p {{margin:2px 0 0 0; opacity:.9; font-size:.95rem;}}
    .kpi {{background:#fff; border:1px solid #D8E2F0; border-left:5px solid {BLUE};
           border-radius:8px; padding:12px 14px; height:100%;}}
    .kpi.alert {{border-left-color:{RED}; background:#FFF6F7;}}
    .kpi .l {{color:{GREY}; font-size:.78rem; text-transform:uppercase; letter-spacing:.04em;}}
    .kpi .v {{color:{BLUE_DARK}; font-size:1.55rem; font-weight:700; line-height:1.25;}}
    .kpi.alert .v {{color:{RED};}}
    .kpi .s {{color:{GREY}; font-size:.78rem;}}
    .note {{background:{BLUE_PALE}; border-left:4px solid {BLUE}; padding:10px 14px;
            border-radius:6px; font-size:.92rem; color:{BLUE_DARK};}}
    .note.alert {{background:#FFF1F3; border-left-color:{RED}; color:#6B0A1A;}}
    </style>
    """,
    unsafe_allow_html=True,
)


def kpi(label, value, sub="", alert=False):
    st.markdown(
        f'<div class="kpi {"alert" if alert else ""}"><div class="l">{label}</div>'
        f'<div class="v">{value}</div><div class="s">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def note(text, alert=False):
    st.markdown(f'<div class="note {"alert" if alert else ""}">{text}</div>', unsafe_allow_html=True)


def style(fig, h=360, legend=False):
    fig.update_layout(
        height=h, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="white",
        plot_bgcolor="white", font=dict(color=BLUE_DARK, size=12), showlegend=legend,
        title_font=dict(size=15, color=BLUE_DARK),
    )
    fig.update_xaxes(showgrid=False, linecolor="#C9D4E5")
    fig.update_yaxes(gridcolor="#E6ECF5", zeroline=False)
    return fig


def _stretch(fn, *a, **k):
    """Full-width rendering that works on both old and new Streamlit versions."""
    try:
        return fn(*a, width="stretch", **k)
    except TypeError:
        return fn(*a, use_container_width=True, **k)


def pchart(fig, **k):
    return _stretch(st.plotly_chart, fig, **k)


def dfshow(data, **k):
    return _stretch(st.dataframe, data, **k)


def ksh(x, dec=0):
    return f"KSh {x:,.{dec}f}"


@st.cache_data(show_spinner="Loading data…")
def get_data(file_bytes_or_path):
    return load_data(file_bytes_or_path)


# ---------- data source ----------
with st.sidebar:
    st.markdown(f"### 📮 PCK Box4")
    up = st.file_uploader("Replace dataset (optional CSV)", type="csv")

df = None
try:
    df = get_data(up if up is not None else DEFAULT_CSV)
except Exception as e:  # noqa: BLE001
    st.error(f"Could not load dataset: {e}")
    st.exception(e)
    st.stop()
if df is None:
    raise SystemExit("Dataset failed to load. Use: streamlit run app.py")
# ---------- filters ----------
with st.sidebar:
    st.markdown("#### Filters")
    dmin, dmax = df["date"].min().date(), df["date"].max().date()
    dr = st.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
    if isinstance(dr, tuple) and len(dr) == 2:
        d0, d1 = dr
    elif isinstance(dr, tuple):
        d0 = d1 = dmin if not dr else dr[0]
    else:
        d0 = d1 = dr
    actions = st.multiselect("Action", sorted(df["action"].unique()), default=sorted(df["action"].unique()))
    fam = st.multiselect("Channel family", ["M-Pesa", "Other channels"], default=["M-Pesa", "Other channels"])
    chans = st.multiselect(
        "Payment channel (exact label)", sorted(df["channel_raw"].unique()),
        default=[], placeholder="All channels",
    )
    potypes = st.multiselect(
        "Account identifier type", sorted(df["po_type"].unique()), default=[], placeholder="All",
    )
    only_var = st.checkbox("Only records with amount variance")
    st.caption("All KPIs and charts respond to these filters.")

f = df[(df["date"].dt.date >= d0) & (df["date"].dt.date <= d1)]
f = f[f["action"].isin(actions) & f["channel_family"].isin(fam)]
if chans:
    f = f[f["channel_raw"].isin(chans)]
if potypes:
    f = f[f["po_type"].isin(potypes)]
if only_var:
    f = f[f["has_variance"]]

st.markdown(
    f'<div class="hdr"><h1>PCK Box4 Executive Dashboard</h1>'
    f'<p>Box renewals &amp; extensions · {df["date"].min():%d %b %Y} – {df["date"].max():%d %b %Y} · '
    f'Showing {len(f):,} of {len(df):,} records</p></div>',
    unsafe_allow_html=True,
)
if f.empty:
    st.warning("No records match the current filters.")
    st.stop()

K = kpis(f)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Executive overview", "Payment channels", "Timing patterns", "Financial reconciliation", "Data quality & references"]
)

# ============ TAB 1 ============
with tab1:
    c = st.columns(6)
    with c[0]: kpi("Total records", f"{K['records']:,}", "payments in view")
    with c[1]: kpi("Amount paid", ksh(K["amount_paid"]), "recorded")
    with c[2]: kpi("Net amount", ksh(K["net_amount"]), "recorded")
    with c[3]: kpi("Paid − Net", ksh(K["variance"]), f"{K['variance_records']:,} records differ", alert=K["variance"] != 0)
    with c[4]: kpi("Renewal rate", f"{K['renewal_rate']:.1%}", f"{K['renewed']:,} renewed · {K['extend']:,} extend")
    with c[5]: kpi("Avg amount paid", ksh(K["avg_paid"]), "per record")
    st.write("")

    m = f.groupby("month").agg(records=("ecitizen_ref", "count"), paid=("amount_paid", "sum")).reset_index()
    m["label"] = m["month"].dt.strftime("%b %Y")
    partial = f["date"].max()
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(go.Bar(x=m["label"], y=m["paid"], marker_color=BLUE,
                               hovertemplate="%{x}<br>KSh %{y:,.0f}<extra></extra>"))
        fig.update_layout(title="Amount paid by month (KSh)")
        pchart(style(fig))
    with col2:
        fig = go.Figure(go.Scatter(x=m["label"], y=m["records"], mode="lines+markers",
                                   line=dict(color=BLUE_DARK, width=3), marker=dict(size=8, color=BLUE)))
        fig.update_layout(title="Records by month")
        pchart(style(fig))
    st.caption(f"Months at the edges of the range may be partial (data ends {partial:%d %b %Y}).")

    col3, col4 = st.columns(2)
    with col3:
        a = f["action"].value_counts().reset_index()
        a.columns = ["action", "n"]
        fig = go.Figure(go.Pie(labels=a["action"], values=a["n"], hole=.6,
                               marker=dict(colors=[BLUE_DARK, BLUE_LIGHT]), textinfo="label+percent"))
        fig.update_layout(title="Renewed vs Extend")
        pchart(style(fig))
    with col4:
        top = f["amount_paid"].value_counts().head(10).reset_index()
        top.columns = ["amount", "n"]
        top["amt"] = top["amount"].map(lambda x: f"{x:,.0f}")
        fig = go.Figure(go.Bar(x=top["n"], y=top["amt"], orientation="h", marker_color=BLUE))
        fig.update_yaxes(autorange="reversed", type="category")
        fig.update_layout(title="Most common amounts paid (KSh) – record count")
        pchart(style(fig))

# ============ TAB 2 ============
with tab2:
    c = st.columns(4)
    with c[0]: kpi("MPESA (exact label)", f"{K['mpesa_exact_MPESA']:,}", f"{K['mpesa_share_exact']:.2%} of records")
    with c[1]: kpi("MPesa (separate label)", f"{K['mpesa_exact_MPesa']:,}", "written differently")
    with c[2]: kpi("M-Pesa combined", f"{K['mpesa_combined']:,}", f"{K['mpesa_share_combined']:.2%} of records")
    with c[3]: kpi("Non-M-Pesa records", f"{K['records'] - K['mpesa_combined']:,}", f"{1 - K['mpesa_share_combined']:.2%} of records")
    st.write("")
    note("<b>Concentration:</b> M-Pesa dominates. The label <i>MPESA</i> alone carries the share quoted in the brief; "
         "the separately written <i>MPesa</i> label adds a few more records. Both are shown so the labelling "
         "inconsistency is visible rather than hidden.")
    st.write("")
    ch = f.groupby("channel_raw").agg(records=("ecitizen_ref", "count"), paid=("amount_paid", "sum")).reset_index()
    ch["share"] = ch["records"] / ch["records"].sum()
    ch = ch.sort_values("records", ascending=False)
    col1, col2 = st.columns([3, 2])
    with col1:
        oth = ch[~ch["channel_raw"].isin(["MPESA", "MPesa"])].sort_values("records")
        fig = go.Figure(go.Bar(x=oth["records"], y=oth["channel_raw"], orientation="h", marker_color=BLUE_MID,
                               hovertemplate="%{y}: %{x} records<extra></extra>"))
        fig.update_layout(title="Non-M-Pesa channels – records (M-Pesa excluded for readability)")
        pchart(style(fig, h=470))
    with col2:
        fig = go.Figure(go.Pie(labels=["M-Pesa", "Other"], values=[K["mpesa_combined"], K["records"] - K["mpesa_combined"]],
                               hole=.62, marker=dict(colors=[BLUE_DARK, BLUE_LIGHT]), sort=False))
        fig.update_layout(title="M-Pesa vs other channels")
        pchart(style(fig, h=470))
    show = ch.rename(columns={"channel_raw": "Channel (exact label)", "records": "Records", "paid": "Amount paid (KSh)", "share": "Share"})
    dfshow(show.style.format({"Records": "{:,}", "Amount paid (KSh)": "{:,.0f}", "Share": "{:.2%}"}),
                 hide_index=True)

# ============ TAB 3 ============
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        hr = f.groupby("hour").size().reindex(range(24), fill_value=0).reset_index()
        hr.columns = ["hour", "n"]
        fig = go.Figure(go.Bar(x=hr["hour"], y=hr["n"], marker_color=BLUE))
        fig.update_xaxes(dtick=1, title="Hour of day")
        fig.update_layout(title="Records by hour of day")
        pchart(style(fig))
    with col2:
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        wd = f.groupby("weekday").size().reindex(order, fill_value=0).reset_index()
        wd.columns = ["weekday", "n"]
        fig = go.Figure(go.Bar(x=wd["weekday"], y=wd["n"], marker_color=BLUE_DARK))
        fig.update_layout(title="Records by day of week")
        pchart(style(fig))
    heat = f.pivot_table(index="weekday", columns="hour", values="ecitizen_ref", aggfunc="count", fill_value=0)
    heat = heat.reindex(index=order, columns=range(24), fill_value=0)
    fig = go.Figure(go.Heatmap(z=heat.values, x=heat.columns, y=heat.index,
                               colorscale=[[0, "#FFFFFF"], [.5, BLUE_LIGHT], [1, BLUE_DARK]],
                               hovertemplate="%{y} %{x}:00 – %{z} records<extra></extra>"))
    fig.update_xaxes(dtick=1, title="Hour of day")
    fig.update_layout(title="Activity heatmap – weekday × hour")
    pchart(style(fig, h=380))
    daily = f.groupby("date").size().reset_index(name="n")
    fig = go.Figure(go.Scatter(x=daily["date"], y=daily["n"], mode="lines", line=dict(color=BLUE, width=2),
                               fill="tozeroy", fillcolor="rgba(21,88,176,.12)"))
    fig.update_layout(title="Daily records")
    pchart(style(fig))

# ============ TAB 4 ============
with tab4:
    total_var = K["variance"]
    c = st.columns(4)
    with c[0]: kpi("Total amount paid", ksh(K["amount_paid"], 2), "sum of Amount Paid")
    with c[1]: kpi("Total net amount", ksh(K["net_amount"], 2), "sum of Net Amount")
    with c[2]: kpi("Difference (Paid − Net)", ksh(total_var, 2), "for investigation", alert=total_var != 0)
    with c[3]: kpi("Records with a difference", f"{K['variance_records']:,}", f"{K['variance_records'] / K['records']:.2%} of records", alert=K["variance_records"] > 0)
    st.write("")
    note("<b>Exposed, not explained:</b> the data records a difference between Amount Paid and Net Amount. "
         "The dashboard does not assume why (for example fees, charges, overpayments or capture errors). "
         "The records below are listed for investigation.", alert=True)
    st.write("")
    v = f[f["has_variance"]]
    if v.empty:
        st.success("No Paid vs Net differences in the current filter.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            vm = v.groupby("month")["variance"].sum().reset_index()
            fig = go.Figure(go.Bar(x=vm["month"].dt.strftime("%b %Y"), y=vm["variance"], marker_color=RED))
            fig.update_layout(title="Difference by month (KSh)")
            pchart(style(fig))
        with col2:
            vd = v["variance"].round(2).value_counts().reset_index()
            vd.columns = ["difference", "records"]
            vd["difference"] = vd["difference"].map(lambda x: f"KSh {x:,.2f}")
            fig = go.Figure(go.Bar(x=vd["difference"], y=vd["records"], marker_color=RED))
            fig.update_layout(title="Distribution of per-record difference")
            pchart(style(fig))
        col3, col4 = st.columns(2)
        with col3:
            va = v.groupby("amount_paid")["variance"].agg(["count", "sum"]).sort_values("count", ascending=False).head(10).reset_index()
            va["amt"] = va["amount_paid"].map(lambda x: f"{x:,.0f}")
            fig = go.Figure(go.Bar(x=va["count"], y=va["amt"], orientation="h", marker_color=BLUE))
            fig.update_yaxes(autorange="reversed", type="category")
            fig.update_layout(title="Amount-paid values with a difference (record count)")
            pchart(style(fig))
        with col4:
            vc = v.groupby("channel_raw")["variance"].agg(["count", "sum"]).reset_index().sort_values("count")
            fig = go.Figure(go.Bar(x=vc["count"], y=vc["channel_raw"], orientation="h", marker_color=BLUE_MID))
            fig.update_layout(title="Records with a difference by channel")
            pchart(style(fig))
        st.markdown("##### Records for investigation")
        cols = ["date", "time", "post_office", "ecitizen_ref", "channel_raw", "payment_ref", "amount_paid", "net_amount", "variance", "action"]
        tbl = v[cols].sort_values(["variance", "date"], ascending=[False, False])
        dfshow(tbl, hide_index=True, height=340)
        st.download_button("Download variance records (CSV)", tbl.to_csv(index=False).encode(), "pck_variance_records.csv", "text/csv")

# ============ TAB 5 ============
with tab5:
    st.markdown("##### Payment reference verification")
    rs = f["ref_status"].value_counts()
    sci_n = int(f["ref_sci"].sum())
    c = st.columns(4)
    with c[0]: kpi("Scientific-notation refs", f"{sci_n:,}", "precision likely lost", alert=sci_n > 0)
    with c[1]: kpi("Repeated, verifiable", f"{int(f['ref_repeat_clean'].sum()):,}", "full-text refs that repeat", alert=bool(f["ref_repeat_clean"].any()))
    with c[2]: kpi("Repeated, unverifiable", f"{int(f['ref_repeat_sci'].sum()):,}", "scientific notation only", alert=bool(f["ref_repeat_sci"].any()))
    with c[3]: kpi("Missing references", f"{int(f['ref_missing'].sum()):,}", "blank value")
    st.write("")
    note("<b>How to read this:</b> a reference such as <i>3.86E+14</i> has been rounded by spreadsheet software, so many different "
         "transactions can collapse to the same text. Repeats of this kind are <b>not</b> proof of duplicate payments. "
         "Only repeated references that appear in full, unrounded form are treated as genuine duplicate candidates. "
         "Unverifiable repeats need the original source references before any conclusion.")
    st.write("")
    col1, col2 = st.columns([2, 3])
    with col1:
        sd = rs.reset_index()
        sd.columns = ["Status", "Records"]
        dfshow(sd, hide_index=True)
    with col2:
        sci_ch = f[f["ref_sci"]]["channel_raw"].value_counts().reset_index()
        sci_ch.columns = ["channel", "n"]
        if not sci_ch.empty:
            fig = go.Figure(go.Bar(x=sci_ch["n"], y=sci_ch["channel"], orientation="h", marker_color=RED))
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(title="Scientific-notation references by channel")
            pchart(style(fig, h=300))
    flagged = f[f["ref_status"] != "Clean and unique"]
    if not flagged.empty:
        st.markdown("##### References requiring verification")
        t = flagged[["date", "time", "post_office", "ecitizen_ref", "channel_raw", "payment_ref", "amount_paid", "ref_status"]].sort_values(["payment_ref", "date"])
        dfshow(t, hide_index=True)
        st.download_button("Download reference exceptions (CSV)", t.to_csv(index=False).encode(), "pck_reference_exceptions.csv", "text/csv")

    st.markdown("##### Other data-quality checks")
    dq = pd.DataFrame(
        {
            "Check": ["Missing Post_Office", "Zero Amount Paid or Net Amount", "Duplicate eCitizen references",
                      "Numeric office code identifiers", "BOX account-number identifiers", "MPesa label variant in use"],
            "Records": [
                int((f["po_type"] == "Missing").sum()), int(f["zero_amount"].sum()),
                int(f["ecitizen_ref"].duplicated(keep=False).sum()),
                int((f["po_type"] == "Numeric office code").sum()), int((f["po_type"] == "BOX account number").sum()),
                int((f["channel_raw"] == "MPesa").sum()),
            ],
        }
    )
    dfshow(dq, hide_index=True)
    st.caption("The Post_Office field mixes short numeric codes with full BOX account numbers; they are counted, not merged.")
