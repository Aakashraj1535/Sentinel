"""
Synthetic data generator for the Supply Chain Sentinel project.

Produces:
  - suppliers.json
  - orders.json
  - knowledge_documents.json   (SOPs, contracts, incident logs — text chunks)
  - knowledge_edges.json       (lightweight knowledge-graph relationships)

Run:  python generate_synthetic_data.py
Output lands in this same folder as JSON files, which db/load_data.py
will later read and insert into PostgreSQL (with embeddings).
"""

import json
import random
from datetime import datetime, timedelta

random.seed(42)  # reproducible data for demos

OUT_DIR = "."

SUPPLIER_NAMES = [
    ("SUP-001", "Meridian Logistics Co.", "APAC"),
    ("SUP-002", "Atlas Freight Partners", "EU"),
    ("SUP-003", "Horizon Components Ltd.", "NA"),
    ("SUP-004", "Bluewave Materials", "APAC"),
    ("SUP-005", "Crestline Industrial Supply", "NA"),
    ("SUP-006", "Norlink Distribution", "EU"),
    ("SUP-007", "Pinecrest Manufacturing", "NA"),
    ("SUP-008", "Delta Rivers Trading", "APAC"),
]

ITEMS = [
    "Packaging Material - Corrugated", "Steel Fasteners (M6)", "Injection-Molded Housings",
    "Circuit Board Assemblies", "Industrial Adhesive - 20L Drum", "Polymer Resin Pellets",
    "Aluminum Extrusions", "Rubber Gaskets - Bulk",
]

WAREHOUSES = ["WH-A (Chennai)", "WH-B (Coimbatore)", "WH-C (Bengaluru)", "WH-D (Hyderabad)"]

EXCEPTION_TYPES = ["Shipment Delay", "Stockout", "Quality Issue", "Customs Hold", "Supplier Outage"]

DELAY_REASONS = [
    ("Regional highway closure due to flooding", "genuine", "Shipment Delay"),
    ("Port congestion at origin port", "genuine", "Shipment Delay"),
    ("Customs inspection hold - routine", "genuine", "Customs Hold"),
    ("Vehicle breakdown during transit", "genuine", "Shipment Delay"),
    ("Vague: 'unforeseen circumstances'", "low-confidence", "Shipment Delay"),
    ("Supplier production line malfunction", "genuine", "Supplier Outage"),
    ("Raw material shortage at supplier factory", "genuine", "Stockout"),
    ("Incorrect quantity shipped", "genuine", "Quality Issue"),
]


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def gen_suppliers():
    suppliers = []
    for sid, name, region in SUPPLIER_NAMES:
        total_orders = random.randint(15, 40)
        incidents = random.randint(0, 6)
        on_time_rate = round(100 * (1 - incidents / total_orders), 2)
        suppliers.append({
            "id": sid,
            "name": name,
            "region": region,
            "on_time_rate": on_time_rate,
            "total_incidents": incidents,
        })
    return suppliers


def gen_orders(suppliers, n=60):
    orders = []
    base_date = datetime(2026, 6, 1)
    for i in range(n):
        supplier = random.choice(suppliers)
        expected = base_date + timedelta(days=random.randint(0, 42), hours=random.randint(0, 23))
        is_delayed = random.random() < 0.35
        if is_delayed:
            actual = expected + timedelta(days=random.randint(1, 9))
            status = "delayed"
        else:
            actual = expected + timedelta(hours=random.randint(-6, 6))
            status = "delivered"
        # Some orders still in transit (no actual_delivery yet)
        if random.random() < 0.1:
            actual = None
            status = "pending"

        orders.append({
            "id": f"PO-{88000 + i}",
            "supplier_id": supplier["id"],
            "item": random.choice(ITEMS),
            "quantity": random.randint(50, 2000),
            "warehouse_id": random.choice(WAREHOUSES),
            "expected_delivery": iso(expected),
            "actual_delivery": iso(actual) if actual else None,
            "status": status,
        })
    return orders


SOP_TEMPLATES = [
    ("SOP-14", "Handling Shipment Delays",
     "If a shipment delay exceeds 2 days, check alternate warehouse stock before contacting the "
     "supplier. If no alternate stock is available, request an updated ETA from the supplier. "
     "If the delay exceeds 5 days, escalate to procurement for a backup supplier. Document the "
     "root cause for any delay exceeding 3 days."),
    ("SOP-22", "Stockout Response Procedure",
     "When inventory falls below the safety stock threshold, first check for surplus stock at "
     "other warehouses in the same region. If a transfer is feasible within 48 hours, initiate it "
     "immediately. If no transfer is possible, place an expedited reorder with the primary supplier. "
     "Notify the affected production or fulfillment team of expected resolution time."),
    ("SOP-31", "Supplier Reliability Escalation",
     "A supplier is flagged for reliability review if they record more than 3 delivery delays "
     "within a rolling 30-day window, or if any single delay exceeds 7 days without a documented "
     "external cause. Reliability reviews should consider the supplier's overall on-time rate "
     "before recommending contract action."),
    ("SOP-08", "Quality Issue Handling",
     "Upon receipt of a quality issue report, quarantine the affected batch immediately and notify "
     "quality assurance. If the defect rate exceeds 5% of the shipment, reject the batch and request "
     "replacement at the supplier's cost per contract terms."),
    ("SOP-19", "Customs Hold Resolution",
     "For shipments held at customs, verify documentation completeness within 24 hours. Routine "
     "inspection holds typically resolve within 3-5 business days and do not require escalation "
     "unless the shipment contains temperature-sensitive or time-critical goods."),
]

CONTRACT_TEMPLATES = [
    "Agreed delivery window: {window} business days from purchase order confirmation. "
    "Penalty clause: {penalty}% cost deduction per day late beyond the agreed window. "
    "Force majeure clause: natural disasters, strikes, and government-mandated closures are exempt "
    "from penalty, subject to documented evidence. Minimum order quantity: {moq} units.",
]


def gen_knowledge_documents(suppliers, orders):
    docs = []
    edges = []

    # SOPs
    for label, title, text in SOP_TEMPLATES:
        docs.append({
            "doc_label": label,
            "doc_kind": "SOP",
            "supplier_id": None,
            "exception_type": _sop_exception_type(title),
            "chunk_text": f"{title}: {text}",
        })

    # Contracts — one per supplier
    for s in suppliers:
        window = random.choice([5, 6, 7, 10])
        penalty = random.choice([1, 2, 3])
        moq = random.choice([250, 500, 1000])
        text = CONTRACT_TEMPLATES[0].format(window=window, penalty=penalty, moq=moq)
        label = f"Contract-{s['id']}"
        docs.append({
            "doc_label": label,
            "doc_kind": "Contract",
            "supplier_id": s["id"],
            "exception_type": None,
            "chunk_text": f"Supplier Contract ({s['name']}): {text}",
        })
        edges.append({"from_label": label, "relation": "governs", "to_label": s["id"]})

    # Incidents — generate a history per supplier based on delayed orders
    RESOLUTIONS_BY_TYPE = {
        "Shipment Delay": [
            "Transferred stock from alternate warehouse; no stockout occurred.",
            "Contacted supplier for updated ETA; customer notified of delay.",
            "Escalated to procurement; backup supplier engaged for future orders.",
        ],
        "Stockout": [
            "Transferred surplus stock from a nearby warehouse within 48 hours.",
            "Placed expedited reorder with primary supplier per SOP-22.",
        ],
        "Customs Hold": [
            "Documentation resolved within 3 business days; no escalation required.",
            "Expedited customs clearance requested due to time-sensitive goods.",
        ],
        "Quality Issue": [
            "Batch quarantined and rejected; replacement requested at supplier's cost.",
            "Defect rate below threshold; batch accepted with quality note logged.",
        ],
        "Supplier Outage": [
            "Backup supplier engaged temporarily while primary line was restored.",
            "Escalated to procurement for alternate sourcing during outage.",
        ],
    }

    incident_num = 100
    delayed_orders = [o for o in orders if o["status"] == "delayed"]
    for o in delayed_orders:
        reason_text, confidence, exc_type = random.choice(DELAY_REASONS)
        incident_num += 1
        label = f"Incident #{incident_num}"
        resolution = random.choice(RESOLUTIONS_BY_TYPE.get(exc_type, RESOLUTIONS_BY_TYPE["Shipment Delay"]))
        text = (
            f"{label} | Supplier: {o['supplier_id']} | Type: {exc_type} | "
            f"Cause: {reason_text}. Resolution: {resolution}"
        )
        docs.append({
            "doc_label": label,
            "doc_kind": "Incident",
            "supplier_id": o["supplier_id"],
            "exception_type": exc_type,
            "chunk_text": text,
        })
        edges.append({"from_label": label, "relation": "caused_by", "to_label": o["supplier_id"]})
        edges.append({"from_label": label, "relation": "applies_to", "to_label": exc_type})

    return docs, edges


def _sop_exception_type(title):
    if "Delay" in title:
        return "Shipment Delay"
    if "Stockout" in title:
        return "Stockout"
    if "Quality" in title:
        return "Quality Issue"
    if "Customs" in title:
        return "Customs Hold"
    if "Reliability" in title:
        return None  # applies broadly
    return None


def main():
    suppliers = gen_suppliers()
    orders = gen_orders(suppliers, n=60)
    docs, edges = gen_knowledge_documents(suppliers, orders)

    with open(f"{OUT_DIR}/suppliers.json", "w") as f:
        json.dump(suppliers, f, indent=2)
    with open(f"{OUT_DIR}/orders.json", "w") as f:
        json.dump(orders, f, indent=2)
    with open(f"{OUT_DIR}/knowledge_documents.json", "w") as f:
        json.dump(docs, f, indent=2)
    with open(f"{OUT_DIR}/knowledge_edges.json", "w") as f:
        json.dump(edges, f, indent=2)

    print(f"Generated {len(suppliers)} suppliers")
    print(f"Generated {len(orders)} orders ({len([o for o in orders if o['status']=='delayed'])} delayed)")
    print(f"Generated {len(docs)} knowledge document chunks")
    print(f"Generated {len(edges)} knowledge graph edges")


if __name__ == "__main__":
    main()
