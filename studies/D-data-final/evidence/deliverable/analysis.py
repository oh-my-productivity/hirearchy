#!/usr/bin/env python3
"""Returns analysis for orders_2025.csv (standard library only).

Return rate = orders with returned == "yes" / all orders in the group.
Each row is one order; "returned" is yes or no.

Usage: python3 analysis.py [--data PATH] [--out PATH]
Prints the results and writes the identical text to results.txt
(next to this script). Output is deterministic: sorted, fixed rounding,
no timestamps.
"""
import argparse
import csv
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = "/private/tmp/orgmcp-d-1792266290/data/orders_2025.csv"
DEFAULT_OUT = os.path.join(HERE, "results.txt")

EXPECTED = ["order_id", "order_date", "category", "product", "unit_price",
            "quantity", "region", "channel", "returned", "return_reason"]

PRICE_BANDS = [(0.0, 20.0, "under 20"), (20.0, 50.0, "20 to 49.99"),
               (50.0, 100.0, "50 to 99.99"), (100.0, None, "100 and over")]


def price_band(price):
    for lo, hi, label in PRICE_BANDS:
        if price >= lo and (hi is None or price < hi):
            return label
    return "unknown"


def pct(a, b):
    return "n/a" if b == 0 else "%.1f%%" % (100.0 * a / b)


def load(path):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames
        rows = list(reader)
    return header, rows


def quality(header, rows):
    notes = []
    if header != EXPECTED:
        notes.append("Unexpected header: %s" % header)
    notes.append("Rows read: %d" % len(rows))
    ids = Counter(r["order_id"] for r in rows)
    dups = sorted(k for k, v in ids.items() if v > 1)
    notes.append("Duplicate order_id values: %d" % len(dups))
    full = Counter(tuple(r[c] for c in EXPECTED) for r in rows)
    notes.append("Fully identical duplicate rows: %d"
                 % sum(v - 1 for v in full.values() if v > 1))
    for c in EXPECTED:
        if c == "return_reason":
            continue
        blanks = sum(1 for r in rows if (r[c] or "").strip() == "")
        notes.append("Blank values in %s: %d" % (c, blanks))
    notes.append("Values of returned: %s" % ", ".join(
        "%r=%d" % kv for kv in sorted(Counter(r["returned"] for r in rows).items())))
    bad_price = [r["order_id"] for r in rows if not _is_pos_float(r["unit_price"])]
    notes.append("Unit price missing, non-numeric or not above 0: %d" % len(bad_price))
    bad_qty = [r["order_id"] for r in rows if not r["quantity"].strip().isdigit()
               or int(r["quantity"]) < 1]
    notes.append("Quantity missing or not a whole number of at least 1: %d" % len(bad_qty))
    dates = sorted(r["order_date"] for r in rows)
    notes.append("Order dates range: %s to %s" % (dates[0], dates[-1]))
    outside = sum(1 for d in dates if not d.startswith("2025-"))
    notes.append("Orders dated outside 2025: %d" % outside)
    yes_no_reason = sum(1 for r in rows if r["returned"] == "yes"
                        and not r["return_reason"].strip())
    no_with_reason = sum(1 for r in rows if r["returned"] != "yes"
                         and r["return_reason"].strip())
    notes.append("Returned orders without a stated reason: %d" % yes_no_reason)
    notes.append("Non-returned orders with a stated reason: %d" % no_with_reason)
    prod_cat = defaultdict(set)
    for r in rows:
        prod_cat[r["product"]].add(r["category"])
    multi = sorted(p for p, s in prod_cat.items() if len(s) > 1)
    notes.append("Products listed under more than one category: %d" % len(multi))
    return notes


def _is_pos_float(s):
    try:
        return float(s) > 0
    except ValueError:
        return False


def group_table(rows, keyfunc, order=None):
    tot = Counter()
    ret = Counter()
    for r in rows:
        k = keyfunc(r)
        tot[k] += 1
        if r["returned"] == "yes":
            ret[k] += 1
    keys = order if order else sorted(tot)
    lines = ["%-34s %8s %8s %8s" % ("group", "orders", "returns", "rate")]
    for k in keys:
        lines.append("%-34s %8d %8d %8s" % (k, tot[k], ret[k], pct(ret[k], tot[k])))
    return lines


def cross_table(rows, rowkey, colkey, rowlabel):
    cols = sorted({colkey(r) for r in rows})
    tot = Counter()
    ret = Counter()
    for r in rows:
        k = (rowkey(r), colkey(r))
        tot[k] += 1
        if r["returned"] == "yes":
            ret[k] += 1
    rks = sorted({rowkey(r) for r in rows})
    head = "%-34s" % rowlabel + "".join(" %22s" % c for c in cols)
    lines = [head, "(each cell: returns/orders = rate)"]
    for rk in rks:
        cells = "".join(" %22s" % ("%d/%d = %s" % (ret[(rk, c)], tot[(rk, c)],
                                                  pct(ret[(rk, c)], tot[(rk, c)])))
                        for c in cols)
        lines.append("%-34s" % rk + cells)
    return lines


def reason_table(rows, keyfunc=None, label="all returned orders"):
    ret = [r for r in rows if r["returned"] == "yes"]
    if keyfunc is None:
        c = Counter(r["return_reason"].strip() or "(blank)" for r in ret)
        n = len(ret)
        lines = ["Returned orders: %d" % n,
                 "%-34s %8s %8s" % ("reason", "count", "share")]
        for k in sorted(c, key=lambda x: (-c[x], x)):
            lines.append("%-34s %8d %8s" % (k, c[k], pct(c[k], n)))
        return lines
    reasons = sorted({r["return_reason"].strip() or "(blank)" for r in ret})
    groups = sorted({keyfunc(r) for r in ret})
    cnt = Counter((keyfunc(r), r["return_reason"].strip() or "(blank)") for r in ret)
    lines = ["%-20s" % label + "".join(" %18s" % x[:18] for x in reasons) + " %8s" % "total"]
    for g in groups:
        tot = sum(cnt[(g, x)] for x in reasons)
        lines.append("%-20s" % g + "".join(" %18d" % cnt[(g, x)] for x in reasons)
                     + " %8d" % tot)
    return lines


def build(rows, header):
    L = []
    add = L.append

    def section(title, lines):
        add("")
        add("== %s ==" % title)
        L.extend(lines)

    add("RETURNS ANALYSIS - orders_2025.csv")
    add("Return rate = orders with returned = yes / all orders in the group.")
    add("Each row is one order; returned is yes or no.")
    section("DATA QUALITY", quality(header, rows))

    n = len(rows)
    r = sum(1 for x in rows if x["returned"] == "yes")
    section("OVERALL", ["Orders: %d" % n, "Returns: %d" % r,
                        "Overall return rate: %s" % pct(r, n)])

    section("BY CATEGORY", group_table(rows, lambda x: x["category"]))
    section("BY PRODUCT (category / product)",
            group_table(rows, lambda x: "%s / %s" % (x["category"], x["product"])))
    section("BY REGION", group_table(rows, lambda x: x["region"]))
    section("BY CHANNEL", group_table(rows, lambda x: x["channel"]))
    section("BY PRICE BAND (unit price)",
            group_table(rows, lambda x: price_band(float(x["unit_price"])),
                        [b[2] for b in PRICE_BANDS]))
    section("BY QUANTITY (units in the order)",
            group_table(rows, lambda x: x["quantity"],
                        sorted({x["quantity"] for x in rows}, key=int)))
    section("RETURN REASONS (all returned orders)", reason_table(rows))
    section("RETURN REASONS BY CHANNEL (counts of returned orders)",
            reason_table(rows, lambda x: x["channel"], "channel"))
    section("RETURN REASONS BY CATEGORY (counts of returned orders)",
            reason_table(rows, lambda x: x["category"], "category"))
    section("CROSS-CHECK: CATEGORY x CHANNEL",
            cross_table(rows, lambda x: x["category"], lambda x: x["channel"], "category"))
    section("CROSS-CHECK: PRICE BAND x CHANNEL",
            cross_table(rows, lambda x: price_band(float(x["unit_price"])),
                        lambda x: x["channel"], "price band"))
    section("CROSS-CHECK: PRODUCT x CHANNEL",
            cross_table(rows, lambda x: "%s / %s" % (x["category"], x["product"]),
                        lambda x: x["channel"], "product"))
    section("CROSS-CHECK: CATEGORY x REGION",
            cross_table(rows, lambda x: x["category"], lambda x: x["region"], "category"))
    section("CROSS-CHECK: QUANTITY x CHANNEL",
            cross_table(rows, lambda x: x["quantity"], lambda x: x["channel"], "quantity"))
    # Focus on the hot spot seen in the category x channel table.
    def is_hot(x):
        return x["category"] == "Home Textiles" and x["channel"] == "marketplace"

    def seg(label, sub):
        t = len(sub)
        k = sum(1 for x in sub if x["returned"] == "yes")
        return "%-52s %8d %8d %8s" % (label, t, k, pct(k, t))

    cold = [x for x in rows if not is_hot(x)]
    ht = [x for x in rows if x["category"] == "Home Textiles"]
    mk = [x for x in rows if x["channel"] == "marketplace"]
    section("FOCUS: HOME TEXTILES ON MARKETPLACE", [
        "%-52s %8s %8s %8s" % ("segment", "orders", "returns", "rate"),
        seg("Home Textiles sold on marketplace", [x for x in ht if x["channel"] == "marketplace"]),
        seg("Home Textiles sold on web or app", [x for x in ht if x["channel"] != "marketplace"]),
        seg("Marketplace, all other categories", [x for x in mk if x["category"] != "Home Textiles"]),
        seg("All orders except Home Textiles on marketplace", cold),
        seg("All orders", rows),
    ])
    section("BY CATEGORY, EXCLUDING MARKETPLACE ORDERS",
            group_table([x for x in rows if x["channel"] != "marketplace"],
                        lambda x: x["category"]))
    section("BY CHANNEL, EXCLUDING HOME TEXTILES",
            group_table([x for x in rows if x["category"] != "Home Textiles"],
                        lambda x: x["channel"]))
    section("BY PRICE BAND, EXCLUDING HOME TEXTILES ON MARKETPLACE",
            group_table(cold, lambda x: price_band(float(x["unit_price"])),
                        [b[2] for b in PRICE_BANDS]))
    section("BY REGION, EXCLUDING HOME TEXTILES ON MARKETPLACE",
            group_table(cold, lambda x: x["region"]))
    section("HOME TEXTILES ON MARKETPLACE: BY PRODUCT",
            group_table([x for x in rows if is_hot(x)], lambda x: x["product"]))
    section("HOME TEXTILES ON MARKETPLACE: BY REGION",
            group_table([x for x in rows if is_hot(x)], lambda x: x["region"]))
    section("HOME TEXTILES ON MARKETPLACE: RETURN REASONS",
            reason_table([x for x in rows if is_hot(x)]))
    section("HOME TEXTILES ON WEB OR APP: RETURN REASONS",
            reason_table([x for x in ht if x["channel"] != "marketplace"]))
    section("HOME TEXTILES: AVERAGE UNIT PRICE BY CHANNEL (orders in that group)",
            ["%-20s %10s" % ("channel", "avg price")] + [
                "%-20s %10.2f" % (c, sum(float(x["unit_price"]) for x in ht if x["channel"] == c)
                                  / len([x for x in ht if x["channel"] == c]))
                for c in sorted({x["channel"] for x in ht})])
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    header, rows = load(a.data)
    text = build(rows, header)
    sys.stdout.write(text)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
