#!/usr/bin/env python3
"""Independent re-check of report.md numbers straight from orders_2025.csv.
Standard library only. Does NOT import or reuse analysis.py. Read-only on data.
Usage: python3 recheck.py  -> prints one line per number: label | report | mine | match/MISMATCH
"""
import csv
import sys
from collections import Counter

DATA = "/private/tmp/orgmcp-d-1792266290/data/orders_2025.csv"

with open(DATA, newline="", encoding="utf-8") as fh:
    rd = csv.reader(fh)
    head = next(rd)
    raw = [r for r in rd]
ix = {h: i for i, h in enumerate(head)}
orders = []
for r in raw:
    orders.append(dict(
        id=r[ix["order_id"]], date=r[ix["order_date"]], cat=r[ix["category"]],
        prod=r[ix["product"]], price=float(r[ix["unit_price"]]),
        qty=int(r[ix["quantity"]]), reg=r[ix["region"]], ch=r[ix["channel"]],
        ret=(r[ix["returned"]].strip().lower() == "yes"),
        why=r[ix["return_reason"]].strip()))


def band(p):
    if p < 20:
        return "<20"
    if p < 50:
        return "20-49.99"
    if p < 100:
        return "50-99.99"
    return "100+"


def cnt(pred):
    sub = [o for o in orders if pred(o)]
    return len(sub), sum(1 for o in sub if o["ret"])


def pc(k, n):
    return "%.1f%%" % (100.0 * k / n)


lines = []


def chk(label, reported, mine):
    ok = (str(reported) == str(mine))
    lines.append((label, str(reported), str(mine), ok))


def rate(label, pred, rep_n=None, rep_k=None, rep_rate=None):
    n, k = cnt(pred)
    if rep_n is not None:
        chk(label + " orders", rep_n, n)
    if rep_k is not None:
        chk(label + " returns", rep_k, k)
    if rep_rate is not None:
        chk(label + " rate", rep_rate, pc(k, n))


# data-quality statements
chk("rows", 3000, len(orders))
chk("distinct order_id", 3000, len({o["id"] for o in orders}))
chk("blank cells (excl. return_reason)", 0, sum(1 for r in raw for h in head if h != "return_reason" and r[ix[h]].strip() == ""))
chk("orders dated outside 2025", 0, sum(1 for o in orders if not o["date"].startswith("2025-")))
chk("returned orders without reason", 0, sum(1 for o in orders if o["ret"] and not o["why"]))
chk("returned values", "['no', 'yes']", str(sorted({o_r[ix['returned']] for o_r in raw})))

# overall
rate("overall", lambda o: True, 3000, 216, "7.2%")

# categories
for c, n, k, r in [("Home Textiles", 451, 59, "13.1%"), ("Furniture", 239, 24, "10.0%"),
                   ("Outdoor Gear", 317, 22, "6.9%"), ("Kitchenware", 465, 30, "6.5%"),
                   ("Garden", 398, 25, "6.3%"), ("Bath & Body", 338, 20, "5.9%"),
                   ("Stationery", 371, 18, "4.9%"), ("Candles & Scents", 421, 18, "4.3%")]:
    rate("category " + c, lambda o, c=c: o["cat"] == c, n, k, r)
chk("number of categories in data", 8, len({o["cat"] for o in orders}))
chk("sum of category orders", 3000, sum(cnt(lambda o, c=c: o["cat"] == c)[0] for c in {o["cat"] for o in orders}))

# channels
for c, n, k, r in [("marketplace", 901, 82, "9.1%"), ("web", 1340, 98, "7.3%"), ("app", 759, 36, "4.7%")]:
    rate("channel " + c, lambda o, c=c: o["ch"] == c, n, k, r)
chk("number of channels in data", 3, len({o["ch"] for o in orders}))

# highest category / channel claims
cr = {c: cnt(lambda o, c=c: o["cat"] == c) for c in {o["cat"] for o in orders}}
chk("highest-rate category", "Home Textiles", max(cr, key=lambda c: cr[c][1] / cr[c][0]))
chr_ = {c: cnt(lambda o, c=c: o["ch"] == c) for c in {o["ch"] for o in orders}}
chk("highest-rate channel", "marketplace", max(chr_, key=lambda c: chr_[c][1] / chr_[c][0]))

# finding 1
hot = lambda o: o["cat"] == "Home Textiles" and o["ch"] == "marketplace"
rate("F1 HT x marketplace", hot, 122, 37, "30.3%")
rate("F1 all other orders", lambda o: not hot(o), 2878, 179, "6.2%")
rate("F1 Linen throw x marketplace", lambda o: hot(o) and o["prod"] == "Linen throw", 33, 15, "45.5%")
rate("F1 Wool blanket x marketplace", lambda o: hot(o) and o["prod"] == "Wool blanket", 26, 10, "38.5%")
hp = {p: cnt(lambda o, p=p: hot(o) and o["prod"] == p) for p in {o["prod"] for o in orders if hot(o)}}
chk("F1 worst two HT-marketplace products", "['Linen throw', 'Wool blanket']",
    str(sorted(sorted(hp, key=lambda p: -hp[p][1] / hp[p][0])[:2])))
chk("F1 share of returns from slice 37/216", "37", str(cnt(hot)[1]))

# finding 2
rate("F2 HT on web/app", lambda o: o["cat"] == "Home Textiles" and o["ch"] != "marketplace", 329, 22, "6.7%")
rate("F2 marketplace other categories", lambda o: o["ch"] == "marketplace" and o["cat"] != "Home Textiles", 779, 45, "5.8%")

# finding 3
rate("F3 price >=100", lambda o: o["price"] >= 100, 568, 55, "9.7%")
rate("F3 price <20", lambda o: o["price"] < 20, 556, 27, "4.9%")
rate("F3 price >=100 excl hot", lambda o: o["price"] >= 100 and not hot(o), 540, 52, "9.6%")
rate("F3 price <20 excl hot", lambda o: o["price"] < 20 and not hot(o), 554, 26, "4.7%")
rate("F3 web price >=100", lambda o: o["ch"] == "web" and o["price"] >= 100, 256, 32, "12.5%")
rate("F3 web price <20", lambda o: o["ch"] == "web" and o["price"] < 20, 261, 10, "3.8%")
rate("F3 marketplace price >=100", lambda o: o["ch"] == "marketplace" and o["price"] >= 100, 169, 16, "9.5%")
rate("F3 marketplace price <20", lambda o: o["ch"] == "marketplace" and o["price"] < 20, 155, 11, "7.1%")
rate("F3 app price >=100", lambda o: o["ch"] == "app" and o["price"] >= 100, 143, 7, "4.9%")
rate("F3 app price <20", lambda o: o["ch"] == "app" and o["price"] < 20, 140, 6, "4.3%")
rate("F3 Furniture", lambda o: o["cat"] == "Furniture", 239, 24, "10.0%")
regs = {}
for g in {o["reg"] for o in orders}:
    n, k = cnt(lambda o, g=g: o["reg"] == g)
    regs[g] = 100.0 * k / n
chk("F3 region min rate", "6.8%", "%.1f%%" % min(regs.values()))
chk("F3 region max rate", "7.6%", "%.1f%%" % max(regs.values()))
rate("F3 quantity 4", lambda o: o["qty"] == 4, 100, 10, "10.0%")

# reasons
reasons = Counter(o["why"] for o in orders if o["ret"])
chk("reasons total", 216, sum(reasons.values()))
for name, k, s in [("Not as described", 52, "24.1%"), ("Late delivery", 46, "21.3%"),
                   ("Wrong size/colour", 45, "20.8%"), ("Changed mind", 42, "19.4%"),
                   ("Arrived damaged", 31, "14.4%")]:
    chk("reason %s count" % name, k, reasons[name])
    chk("reason %s share" % name, s, pc(reasons[name], 216))
hr = Counter(o["why"] for o in orders if o["ret"] and hot(o))
chk("HT-mkt reason Not as described count", 13, hr["Not as described"])
chk("HT-mkt reason Not as described share", "35.1%", pc(hr["Not as described"], 37))
chk("HT-mkt reason Wrong size/colour count", 9, hr["Wrong size/colour"])
chk("HT-mkt reason Wrong size/colour share", "24.3%", pc(hr["Wrong size/colour"], 37))
chk("HT-mkt most common reason", "Not as described", hr.most_common(1)[0][0])
chk("HT-mkt second reason", "Wrong size/colour", hr.most_common(2)[1][0])

# recommendation 2: regions inside the hot slice
for g, n, k, r in [("South", 43, 17, "39.5%"), ("West", 27, 10, "37.0%"), ("East", 23, 3, "13.0%")]:
    rate("R2 HT-mkt " + g, lambda o, g=g: hot(o) and o["reg"] == g, n, k, r)
sizes = sorted(cnt(lambda o, g=g: hot(o) and o["reg"] == g)[0] for g in {o["reg"] for o in orders})
chk("R2/caveat: regional groups in slice 'range 23 to 43 orders each' (min,max)", "(23, 43)", str((sizes[0], sizes[-1])))
rate("R2 HT-mkt North", lambda o: hot(o) and o["reg"] == "North", 29, 7, "24.1%")
chk("R2 HT-mkt regional orders sum to 122", 122, sum(cnt(lambda o, g=g: hot(o) and o["reg"] == g)[0] for g in {o["reg"] for o in orders}))
chk("R2 HT-mkt regions are exactly 4", 4, len({o["reg"] for o in orders if hot(o)}))
chk("R2 South highest, then West, then North, East", "['South', 'West', 'North', 'East']", str(sorted({o["reg"] for o in orders}, key=lambda g: -cnt(lambda o: hot(o) and o["reg"] == g)[1] / cnt(lambda o: hot(o) and o["reg"] == g)[0])))
# R3
rate("R3 price>=100", lambda o: o["price"] >= 100, None, None, "9.7%")

bad = [l for l in lines if not l[3]]
for l in lines:
    print("%-50s | report: %-18s | mine: %-18s | %s" % (l[0], l[1], l[2], "match" if l[3] else "MISMATCH"))
print("\n%d of %d numbers match" % (len(lines) - len(bad), len(lines)))
sys.exit(0)
