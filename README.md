# 🔄 Enterprise P2P Cycle Tracker

> Full procure-to-pay lifecycle tracker with automated slippage alerts

[![Python](https://img.shields.io/badge/Python-3.8+-3572A5?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 📌 Overview

Tracks every purchase order through the **full enterprise P2P lifecycle** — from PR submission to final payment — with automated slippage detection at every stage. Flags SLA breaches, commit date slips, supplier acknowledgement delays, delivery overruns, 3-way match mismatches, and payment holds before they become line-down events.

Built from 3 years of owning full P2P cycles at **Daimler Trucks** across 3 truck model lines, maintaining **95% material availability**.

---

## 🔁 P2P Stages Tracked

```
PR Submitted → PR Approved → PO Placed → Supplier Acknowledged
     → In Transit (Lead Time + Commit Date Tracking)
          → GR (Goods Receipt) → GI (Goods Issue)
               → 3-Way Match (PO vs GR vs Invoice)
                    → Payment Released
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔁 **9-Stage Tracker** | Full PR → Payment lifecycle with live stage per PO |
| 🚨 **Slippage Alert Engine** | Auto-detects SLA breaches at every stage |
| 📅 **Commit Date Monitoring** | Alerts when supplier commit dates approach or slip |
| 🚚 **Delivery Tracking** | Warning + critical alerts for expected delivery dates |
| 🔍 **3-Way Match** | PO vs GR vs Invoice — flags price and qty mismatches |
| ⏱️ **PO Aging Buckets** | Buckets open POs by days open (0–7, 8–14, 15–30, 30+) |
| 📈 **Cycle Time Analysis** | Stage-by-stage avg cycle time vs SLA for closed POs |
| 📁 **5 CSV Exports** | Tracker, alerts, 3-way match, aging, cycle time |

---

## 🚨 Alert Types

| Alert | Severity | Trigger |
|---|---|---|
| `PR_APPROVAL_DELAY` | 🟡 Warning | PR pending approval > 2 days |
| `PO_ISSUANCE_DELAY` | 🟡 Warning | Approved PR not converted to PO > 2 days |
| `ACK_OVERDUE` | 🔴 Critical | Supplier not acknowledged PO > 3 days |
| `COMMIT_DATE_SLIP` | 🔴 Critical | Supplier commit date passed, no GR |
| `COMMIT_DATE_APPROACHING` | 🟡 Warning | Commit date within 3 days |
| `DELIVERY_SLIP` | 🔴 Critical | Expected delivery passed, no GR |
| `DELIVERY_WARNING` | 🟡 Warning | Delivery within 5 days, unconfirmed |
| `GI_DELAY` | 🟠 Moderate | GR done but GI not posted > 1 day |
| `3WAY_MATCH_DELAY` | 🟠 Moderate | GI done but match not completed > 3 days |
| `PAYMENT_OVERDUE` | 🔴 Critical | 3-way match cleared but payment not released > 30 days |

---

## 🗂️ Project Structure

```
p2p-cycle-tracker/
│
├── p2p_engine.py              # Core engine — stages, alerts, analytics
├── main.py                    # Pipeline runner — load → stage → report → export
├── po_data.csv                # Sample data: 15 POs across all 9 stages
│
├── output_po_tracker.csv      # Generated: full tracker with current stage
├── output_alerts.csv          # Generated: all active slippage alerts
├── output_3way_match.csv      # Generated: invoice vs PO vs GR match results
├── output_aging.csv           # Generated: open PO aging buckets
├── output_cycle_time.csv      # Generated: stage-by-stage cycle times
│
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/nisargamurthy1/p2p-cycle-tracker.git
cd p2p-cycle-tracker
```

### 2. Install dependencies
```bash
pip install pandas
```

### 3. Add your PO data
Edit `po_data.csv`. Required columns:
```
po_number, part_description, vendor_name, unit_cost, quantity, total_value,
pr_date, approval_date, po_date, supplier_ack_date, commit_date,
expected_delivery, gr_date, gi_date, three_way_match_date, payment_date,
invoice_qty, invoice_unit_price, buyer, category
```
Leave date fields blank if that stage hasn't happened yet.

### 4. Run
```bash
python main.py
```

### 5. Review outputs
- `output_po_tracker.csv` — all POs with current stage
- `output_alerts.csv` — every active alert with recommended action
- `output_3way_match.csv` — invoice matching results
- `output_aging.csv` — open PO aging
- `output_cycle_time.csv` — how long each stage takes

---

## 📊 Sample Output

```
EXECUTIVE SUMMARY
   Total POs tracked     : 15
   Fully closed          : 3
   Open / In-progress    : 12
   On-Time Delivery Rate : 100.0%

STAGE SNAPSHOT
   PR Submitted          ██ (2)
   In Transit            █  (1)
   Delivery Overdue      ██ (2)
   3-Way Match           ███ (3)
   Payment Released      ███ (3)

SLIPPAGE ALERT REPORT
   🔴 CRITICAL  [COMMIT_DATE_SLIP]
   PO-2006 | Encoder Cable Assembly | CableTech
   Issue  : Supplier commit date passed 10 days ago — material not received
   Action : Escalate to vendor. Assess build impact. Identify alternate source.

   🔴 CRITICAL  [PAYMENT_OVERDUE]
   PO-2013 | Power Supply 48V | PowerSys
   Issue  : 3-way match cleared 32 days ago — payment not released (Net-30)
   Action : Escalate to AP team. Risk of supplier relationship damage.

3-WAY MATCH
   PO-2011 | Titanium Fastener Kit | BoltPro  → ❌ MISMATCH (price: $9.20 vs $9.50)
```

---

## 🔧 Customize SLA Thresholds

Edit `SLA` in `p2p_engine.py`:
```python
SLA = {
    "pr_to_approval_days":    2,   # How fast PRs should be approved
    "po_to_ack_days":         3,   # Supplier acknowledgement window
    "delivery_warning_days":  5,   # Days before delivery to start warning
    "3way_to_payment_days":  30,   # Your payment terms (Net-30, Net-45, etc.)
}
```

---

## 📈 Real-World Results

Replicates the P2P workflow owned at **Daimler Trucks India**:

- ✅ Managed full P2P cycle across **3 truck models**
- 📦 Maintained **95% material availability** throughout production
- 🚛 Drove **12% improvement in on-time delivery**
- 📋 Managed **BOMs and ECOs** with 98% data accuracy
- 🏭 Reduced line-down risk incidents by **~20%**

---

## 👩‍💻 Author

**Nisarga Narasimhamurthy**  
Supply Chain & Procurement Professional | San Jose, CA  
[LinkedIn](https://linkedin.com/in/nisarga-narasimhamurthy) · [Email](mailto:nnarasimhamu@umass.edu)
