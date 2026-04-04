"""
main.py
Enterprise P2P Cycle Tracker — Full Pipeline Runner
Usage: python main.py
"""

import pandas as pd
from p2p_engine import (
    determine_stage, generate_alerts, cycle_time_analysis,
    po_aging_buckets, on_time_delivery_rate, three_way_match_summary, TODAY
)

SEP = "=" * 68
DIV = "-" * 68

print(f"\n{SEP}")
print("  ENTERPRISE P2P CYCLE TRACKER")
print("  PR → Approval → PO → Supplier Ack → In Transit →")
print("  GR → GI → 3-Way Match → Payment")
print("  Nisarga Narasimhamurthy | Supply Chain Portfolio")
print(f"  Run date: {TODAY.strftime('%Y-%m-%d')}")
print(SEP)

# ── 1. Load & stage ──────────────────────────────────────────────────────────
df = pd.read_csv("po_data.csv")
df["stage"] = df.apply(determine_stage, axis=1)

total     = len(df)
closed    = (df["stage"] == "Payment Released").sum()
open_pos  = total - closed
otd       = on_time_delivery_rate(df)
total_val = df["total_value"].sum()

print(f"""
📋 EXECUTIVE SUMMARY
{DIV}
   Total POs tracked          : {total}
   Fully closed (Payment)     : {closed}
   Open / In-progress         : {open_pos}
   Total PO Value             : ${total_val:,.2f}
   On-Time Delivery Rate      : {otd}%
""")

# ── 2. Stage snapshot ────────────────────────────────────────────────────────
print(f"📍 STAGE SNAPSHOT")
print(DIV)
stage_counts = df["stage"].value_counts()
stage_order = ["PR Submitted","PR Approved","PO Placed","In Transit",
               "Delivery Overdue","GR Done","GI Done","3-Way Match","Payment Released"]
for s in stage_order:
    if s in stage_counts.index:
        n   = stage_counts[s]
        bar = "█" * n
        print(f"   {s:<26} {bar} ({n})")

# ── 3. Full PO tracker ───────────────────────────────────────────────────────
print(f"\n\n📦 FULL PO TRACKER")
print(DIV)
cols = ["po_number","part_description","vendor_name","total_value","stage","expected_delivery"]
print(df[cols].to_string(index=False))

# ── 4. Slippage alerts ───────────────────────────────────────────────────────
print(f"\n\n🚨 SLIPPAGE & ALERT REPORT")
print(DIV)
alerts = generate_alerts(df)

if alerts.empty:
    print("   ✅ No alerts — all POs within SLA.")
else:
    crit = alerts[alerts["severity"].str.contains("CRITICAL")]
    warn = alerts[alerts["severity"].str.contains("WARNING")]
    mod  = alerts[alerts["severity"].str.contains("MODERATE")]
    print(f"   Total alerts  : {len(alerts)}")
    print(f"   🔴 Critical   : {len(crit)}")
    print(f"   🟡 Warning    : {len(warn)}")
    print(f"   🟠 Moderate   : {len(mod)}\n")

    for sev_label in ["🔴 CRITICAL", "🟡 WARNING", "🟠 MODERATE"]:
        group = alerts[alerts["severity"] == sev_label]
        for _, a in group.iterrows():
            print(f"   {a['severity']}  [{a['alert_type']}]")
            print(f"   PO: {a['po_number']} | {a['part']} | {a['vendor']}")
            print(f"   Stage   : {a['stage']}")
            print(f"   Issue   : {a['message']}")
            print(f"   Action  : {a['action']}")
            print()

# ── 5. 3-Way Match ───────────────────────────────────────────────────────────
print(f"\n🔍 3-WAY MATCH SUMMARY (PO vs GR vs Invoice)")
print(DIV)
match_df = three_way_match_summary(df)
if match_df.empty:
    print("   No invoices received yet.")
else:
    print(match_df.to_string(index=False))
    mismatches = (match_df["match_status"] == "❌ MISMATCH").sum()
    print(f"\n   ❌ Mismatches requiring resolution : {mismatches}")
    if mismatches:
        print("   → Review invoice vs PO price/qty. Raise credit note or revised invoice request.")

# ── 6. PO Aging ──────────────────────────────────────────────────────────────
print(f"\n\n⏱️  OPEN PO AGING BUCKETS")
print(DIV)
aging = po_aging_buckets(df)
print(aging.to_string(index=False))

bucket_summary = aging["aging_bucket"].value_counts()
print()
for b, c in bucket_summary.items():
    print(f"   {b:<20} : {c} PO(s)")

# ── 7. Cycle time ────────────────────────────────────────────────────────────
print(f"\n\n📈 CYCLE TIME ANALYSIS (Closed POs)")
print(DIV)
ct = cycle_time_analysis(df)
if ct.empty:
    print("   No closed POs yet.")
else:
    print(ct.to_string(index=False))
    print(f"""
   Stage Averages (closed POs):
   PR → Approval        : {ct['pr_to_approval'].mean():.1f} days  (SLA: 2 days)
   Approval → PO        : {ct['approval_to_po'].mean():.1f} days  (SLA: 2 days)
   PO → Supplier Ack    : {ct['po_to_ack'].mean():.1f} days  (SLA: 3 days)
   Ack → GR (Lead Time) : {ct['ack_to_gr'].mean():.1f} days
   GR → GI              : {ct['gr_to_gi'].mean():.1f} days  (SLA: 1 day)
   GI → 3-Way Match     : {ct['gi_to_match'].mean():.1f} days  (SLA: 3 days)
   Match → Payment      : {ct['match_to_payment'].mean():.1f} days  (SLA: 30 days)
   ─────────────────────────────────
   Total Avg Cycle      : {ct['total_cycle'].mean():.1f} days
""")

# ── 8. Export ─────────────────────────────────────────────────────────────────
df.to_csv("output_po_tracker.csv", index=False)
alerts.to_csv("output_alerts.csv", index=False)
if not match_df.empty:
    match_df.to_csv("output_3way_match.csv", index=False)
aging.to_csv("output_aging.csv", index=False)
if not ct.empty:
    ct.to_csv("output_cycle_time.csv", index=False)

print(f"\n📁 EXPORTS SAVED")
print("   output_po_tracker.csv    — full PO tracker with stages")
print("   output_alerts.csv        — all slippage alerts with actions")
print("   output_3way_match.csv    — invoice vs PO vs GR match results")
print("   output_aging.csv         — open PO aging buckets")
print("   output_cycle_time.csv    — stage-by-stage cycle times")
print(f"\n{SEP}\n")
