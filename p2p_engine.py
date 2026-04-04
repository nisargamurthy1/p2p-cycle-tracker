"""
p2p_engine.py
Enterprise P2P Cycle Tracker
Stages: PR → Approval → PO → Supplier Ack → In Transit → GR → GI → 3-Way Match → Payment
Author: Nisarga Narasimhamurthy
"""

import pandas as pd
from datetime import datetime

TODAY = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

# ---------------------------------------------------------------------------
# SLA THRESHOLDS (days)
# ---------------------------------------------------------------------------
SLA = {
    "pr_to_approval_days":     2,
    "approval_to_po_days":     2,
    "po_to_ack_days":          3,
    "gr_to_gi_days":           1,
    "gi_to_3way_days":         3,
    "3way_to_payment_days":   30,
    "delivery_warning_days":   5,
    "delivery_critical_days":  0,
    "commit_warning_days":     3,
    "ack_overdue_days":        3,
}

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def _to_dt(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return pd.to_datetime(val)
    except Exception:
        return None

def days_between(start, end=None):
    s = _to_dt(start)
    if s is None:
        return None
    e = _to_dt(end) if end else TODAY
    return (e - s).days

# ---------------------------------------------------------------------------
# STAGE DETERMINATION
# ---------------------------------------------------------------------------
def determine_stage(row):
    if _to_dt(row.get("payment_date")):          return "Payment Released"
    if _to_dt(row.get("three_way_match_date")):  return "3-Way Match"
    if _to_dt(row.get("gi_date")):               return "GI Done"
    if _to_dt(row.get("gr_date")):               return "GR Done"
    if _to_dt(row.get("supplier_ack_date")):
        exp = _to_dt(row.get("expected_delivery"))
        gr  = _to_dt(row.get("gr_date"))
        if not gr and exp and TODAY > exp:
            return "Delivery Overdue"
        return "In Transit"
    if _to_dt(row.get("po_date")):               return "PO Placed"
    if _to_dt(row.get("approval_date")):         return "PR Approved"
    if _to_dt(row.get("pr_date")):               return "PR Submitted"
    return "Not Started"

STAGE_ORDER = {
    "PR Submitted": 1, "PR Approved": 2, "PO Placed": 3,
    "In Transit": 4, "Delivery Overdue": 4, "GR Done": 5,
    "GI Done": 6, "3-Way Match": 7, "Payment Released": 8,
}

def stage_pct(stage):
    return round(STAGE_ORDER.get(stage, 0) / 8 * 100)

# ---------------------------------------------------------------------------
# SLIPPAGE ALERT ENGINE
# ---------------------------------------------------------------------------
def generate_alerts(df):
    alerts = []

    for _, row in df.iterrows():
        po    = row.get("po_number", "")
        part  = row.get("part_description", "")
        vend  = row.get("vendor_name", "")
        stage = row.get("stage", "")

        def add(alert_type, severity, days, message, action):
            alerts.append({
                "po_number":  po,
                "part":       part,
                "vendor":     vend,
                "stage":      stage,
                "alert_type": alert_type,
                "severity":   severity,
                "days":       days,
                "message":    message,
                "action":     action,
            })

        pr_dt     = _to_dt(row.get("pr_date"))
        appr_dt   = _to_dt(row.get("approval_date"))
        po_dt     = _to_dt(row.get("po_date"))
        ack_dt    = _to_dt(row.get("supplier_ack_date"))
        commit_dt = _to_dt(row.get("commit_date"))
        exp_del   = _to_dt(row.get("expected_delivery"))
        gr_dt     = _to_dt(row.get("gr_date"))
        gi_dt     = _to_dt(row.get("gi_date"))
        match_dt  = _to_dt(row.get("three_way_match_date"))
        pay_dt    = _to_dt(row.get("payment_date"))

        # STAGE 1→2: PR Approval delay
        if pr_dt and not appr_dt:
            d = days_between(pr_dt)
            if d > SLA["pr_to_approval_days"]:
                add("PR_APPROVAL_DELAY", "🟡 WARNING", d,
                    f"PR pending approval for {d} days (SLA: {SLA['pr_to_approval_days']} days)",
                    "Follow up with approver — check budget hold or missing info")

        # STAGE 2→3: Approved but PO not placed
        if appr_dt and not po_dt:
            d = days_between(appr_dt)
            if d > SLA["approval_to_po_days"]:
                add("PO_ISSUANCE_DELAY", "🟡 WARNING", d,
                    f"Approved PR not converted to PO in {d} days (SLA: {SLA['approval_to_po_days']} days)",
                    "Place PO immediately — check for missing vendor/pricing setup")

        # STAGE 3→4: Supplier acknowledgement overdue
        if po_dt and not ack_dt:
            d = days_between(po_dt)
            if d > SLA["ack_overdue_days"]:
                add("ACK_OVERDUE", "🔴 CRITICAL", d,
                    f"Supplier has NOT acknowledged PO after {d} days (SLA: {SLA['ack_overdue_days']} days)",
                    "Call supplier directly. Confirm PO receipt. Get written ack + confirmed delivery date")

        # STAGE 4: Commit date slip
        if po_dt and not gr_dt and commit_dt:
            d = (commit_dt - TODAY).days
            if d < 0:
                add("COMMIT_DATE_SLIP", "🔴 CRITICAL", abs(d),
                    f"Supplier commit date passed {abs(d)} day(s) ago — material not received",
                    "Escalate to vendor. Assess build impact. Identify alternate source or buffer stock")
            elif d <= SLA["commit_warning_days"]:
                add("COMMIT_DATE_APPROACHING", "🟡 WARNING", d,
                    f"Commit date in {d} day(s) — confirm supplier is on track",
                    "Request shipping confirmation and tracking number from supplier now")

        # STAGE 4: Expected delivery slip
        if ack_dt and not gr_dt and exp_del:
            d = (exp_del - TODAY).days
            if d < 0:
                add("DELIVERY_SLIP", "🔴 CRITICAL", abs(d),
                    f"Expected delivery passed {abs(d)} day(s) ago — GR not received",
                    "Expedite with supplier. Check freight/port status. Escalate if critical path")
            elif d <= SLA["delivery_warning_days"]:
                add("DELIVERY_WARNING", "🟡 WARNING", d,
                    f"Delivery expected in {d} day(s) — confirm shipment status",
                    "Request live tracking update from supplier or freight forwarder")

        # STAGE 5→6: GI delay after GR
        if gr_dt and not gi_dt:
            d = days_between(gr_dt)
            if d > SLA["gr_to_gi_days"]:
                add("GI_DELAY", "🟠 MODERATE", d,
                    f"GR done {d} day(s) ago — Goods Issue not posted in ERP (SLA: {SLA['gr_to_gi_days']} day)",
                    "Post GI in ERP. Check if material is on quality hold or still in receiving dock")

        # STAGE 6→7: 3-Way match delay after GI
        if gi_dt and not match_dt:
            d = days_between(gi_dt)
            if d > SLA["gi_to_3way_days"]:
                add("3WAY_MATCH_DELAY", "🟠 MODERATE", d,
                    f"GI posted {d} days ago — 3-way match not completed (SLA: {SLA['gi_to_3way_days']} days)",
                    "Confirm invoice received. Check PO/GR/invoice price and qty alignment")

        # STAGE 7→8: Payment overdue after 3-way match
        if match_dt and not pay_dt:
            d = days_between(match_dt)
            if d > SLA["3way_to_payment_days"]:
                add("PAYMENT_OVERDUE", "🔴 CRITICAL", d,
                    f"3-way match cleared {d} days ago — payment not released (Net-{SLA['3way_to_payment_days']})",
                    "Escalate to AP team. Risk of supplier relationship damage and delivery holds")

    return pd.DataFrame(alerts) if alerts else pd.DataFrame(
        columns=["po_number","part","vendor","stage","alert_type","severity","days","message","action"])

# ---------------------------------------------------------------------------
# ANALYTICS
# ---------------------------------------------------------------------------
def cycle_time_analysis(df):
    closed = df[df["stage"] == "Payment Released"].copy()
    if closed.empty:
        return pd.DataFrame()
    closed["pr_to_approval"]   = closed.apply(lambda r: days_between(r["pr_date"], r["approval_date"]), axis=1)
    closed["approval_to_po"]   = closed.apply(lambda r: days_between(r["approval_date"], r["po_date"]), axis=1)
    closed["po_to_ack"]        = closed.apply(lambda r: days_between(r["po_date"], r["supplier_ack_date"]), axis=1)
    closed["ack_to_gr"]        = closed.apply(lambda r: days_between(r["supplier_ack_date"], r["gr_date"]), axis=1)
    closed["gr_to_gi"]         = closed.apply(lambda r: days_between(r["gr_date"], r["gi_date"]), axis=1)
    closed["gi_to_match"]      = closed.apply(lambda r: days_between(r["gi_date"], r["three_way_match_date"]), axis=1)
    closed["match_to_payment"] = closed.apply(lambda r: days_between(r["three_way_match_date"], r["payment_date"]), axis=1)
    closed["total_cycle"]      = closed.apply(lambda r: days_between(r["pr_date"], r["payment_date"]), axis=1)
    return closed[["po_number","part_description",
                   "pr_to_approval","approval_to_po","po_to_ack",
                   "ack_to_gr","gr_to_gi","gi_to_match","match_to_payment","total_cycle"]]

def po_aging_buckets(df):
    open_df = df[df["stage"] != "Payment Released"].copy()
    open_df["days_open"] = open_df["pr_date"].apply(days_between)
    def bucket(d):
        if d is None: return "Unknown"
        if d <= 7:    return "0-7 days"
        if d <= 14:   return "8-14 days"
        if d <= 30:   return "15-30 days"
        return "30+ days 🔴"
    open_df["aging_bucket"] = open_df["days_open"].apply(bucket)
    return open_df[["po_number","part_description","vendor_name","stage","days_open","aging_bucket"]]

def on_time_delivery_rate(df):
    delivered = df[df["stage"].isin(["GR Done","GI Done","3-Way Match","Payment Released"])].copy()
    delivered = delivered.dropna(subset=["gr_date","expected_delivery"])
    if delivered.empty:
        return 0.0
    delivered["gr_date"]           = pd.to_datetime(delivered["gr_date"])
    delivered["expected_delivery"]  = pd.to_datetime(delivered["expected_delivery"])
    on_time = (delivered["gr_date"] <= delivered["expected_delivery"]).sum()
    return round(on_time / len(delivered) * 100, 1)

def three_way_match_summary(df):
    rows = []
    for _, r in df.iterrows():
        inv_qty   = r.get("invoice_qty")
        inv_price = r.get("invoice_unit_price")
        if pd.isna(inv_qty) or pd.isna(inv_price):
            continue
        po_qty    = float(r.get("quantity", 0))
        po_price  = float(r.get("unit_cost", 0))
        inv_qty   = float(inv_qty)
        inv_price = float(inv_price)
        qty_ok    = abs(po_qty - inv_qty) < 0.01
        price_ok  = abs(po_price - inv_price) < 0.01
        rows.append({
            "po_number":     r["po_number"],
            "part":          r["part_description"],
            "po_qty":        po_qty,   "invoice_qty":   inv_qty,   "qty_match":   "✅" if qty_ok   else "❌",
            "po_price":      po_price, "invoice_price": inv_price, "price_match": "✅" if price_ok else "❌",
            "match_status":  "✅ PASS" if (qty_ok and price_ok) else "❌ MISMATCH",
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()
