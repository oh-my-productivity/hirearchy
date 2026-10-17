# Seeded generator for the Fernhill Goods orders export (study D). Facilitator-private ground truth is computed separately.
import csv, random, datetime, sys
rnd = random.Random(20251017)
out = sys.argv[1]
cats = {  # category: (products, price range, weight)
 "Home Textiles": (["Linen throw","Cotton duvet set","Wool blanket","Cushion cover"], (18,120), 14),
 "Kitchenware": (["Cast-iron pan","Ceramic bowl set","Knife block","Teapot"], (12,150), 17),
 "Garden": (["Planter","Trowel set","Seed kit","Watering can"], (6,70), 13),
 "Candles & Scents": (["Soy candle","Reed diffuser","Incense set"], (7,45), 15),
 "Furniture": (["Side table","Bookshelf","Stool","Floor lamp"], (45,420), 8),
 "Stationery": (["Notebook","Fountain pen","Desk organiser"], (4,60), 12),
 "Outdoor Gear": (["Camping mug","Picnic blanket","Lantern","Daypack"], (9,130), 10),
 "Bath & Body": (["Soap bar set","Bath salts","Body oil"], (5,40), 11),
}
regions = ["North","South","East","West"]; rw=[28,24,26,22]
channels = ["web","app","marketplace"]; cw=[45,25,30]
reasons = ["Arrived damaged","Wrong size/colour","Not as described","Late delivery","Changed mind"]
names=list(cats); w=[cats[c][2] for c in names]
rows=[]; d0=datetime.date(2025,1,1)
for i in range(1,3001):
    cat = rnd.choices(names,w)[0]; prods,(lo,hi),_=cats[cat]
    prod=rnd.choice(prods); price=round(rnd.uniform(lo,hi),2)
    qty=rnd.choices([1,2,3,4],[70,20,7,3])[0]
    region=rnd.choices(regions,rw)[0]; ch=rnd.choices(channels,cw)[0]
    # base return probability
    p=0.06
    if cat=="Furniture": p=0.09
    if cat=="Home Textiles" and ch=="marketplace": p=0.34   # planted: textiles via marketplace
    elif cat=="Home Textiles": p=0.07
    if ch=="app": p*=0.8
    ret = rnd.random()<p
    reason=""
    if ret:
        if region=="West":   # planted: West dominated by late delivery
            reason=rnd.choices(reasons,[8,7,7,64,14])[0]
        elif cat=="Home Textiles" and ch=="marketplace":
            reason=rnd.choices(reasons,[10,50,25,5,10])[0]
        else:
            reason=rnd.choices(reasons,[22,22,20,10,26])[0]
    date=d0+datetime.timedelta(days=rnd.randrange(365))
    rows.append((date,cat,prod,price,qty,region,ch,"yes" if ret else "no",reason))
rows.sort(key=lambda r:r[0])
with open(out,"w",newline="") as f:
    wr=csv.writer(f); wr.writerow(["order_id","order_date","category","product","unit_price","quantity","region","channel","returned","return_reason"])
    for n,r in enumerate(rows,1):
        wr.writerow([f"FG-{100000+n}",r[0].isoformat(),r[1],r[2],f"{r[3]:.2f}",r[4],r[5],r[6],r[7],r[8]])
