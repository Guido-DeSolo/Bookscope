"""Write a deterministic replay that demonstrates a liquidity shock."""

import argparse
import json
import random
from pathlib import Path


def generate(path: str | Path) -> int:
    rng, rows = random.Random(41), []
    rows.append({"type":"meta","symbol":"BTC/USD · SIMULATED","tick_size":0.01,
                 "title":"Bid liquidity shock","source":"deterministic synthetic market"})
    bids=[[round(100-i*.01,2),round(rng.uniform(1.2,5.5),2)] for i in range(10)]
    asks=[[round(100.01+i*.01,2),round(rng.uniform(1.2,5.5),2)] for i in range(10)]
    bids[0][1],bids[4][1]=8.4,12.7
    rows.append({"t":0,"type":"snapshot","bids":bids,"asks":asks})
    t=0.0
    for i in range(80):
        t+=rng.uniform(.09,.22)
        if i%3:
            side=rng.choice(["buy","sell"])
            price=asks[0][0] if side=="buy" else bids[0][0]
            rows.append({"t":round(t,4),"type":"trade","side":side,"price":price,"size":round(rng.uniform(.03,.4),3)})
        else:
            side=rng.choice(["bid","ask"]); levels=bids if side=="bid" else asks
            level=rng.choice([1,2,3,5,6,7,8]) if side=="bid" else rng.randrange(1,9)
            levels[level][1]=round(rng.uniform(.3,5),2)
            rows.append({"t":round(t,4),"type":"book","side":side,"price":levels[level][0],"size":levels[level][1]})
    for level in (0,1,2,3,4):
        t+=.11; rows.append({"t":round(t,4),"type":"book","side":"bid","price":bids[level][0],"size":0})
    for _ in range(24):
        t+=rng.uniform(.025,.09)
        price=bids[5][0]
        rows.append({"t":round(t,4),"type":"trade","side":"sell","price":price,"size":round(rng.uniform(.2,1.4),3)})
    for level in (5,6):
        t+=.13; rows.append({"t":round(t,4),"type":"book","side":"bid","price":bids[level][0],"size":0})
    for i in range(36):
        t+=rng.uniform(.1,.3)
        side="buy" if i%4==0 else "sell"
        rows.append({"t":round(t,4),"type":"trade","side":side,
                     "price":asks[0][0] if side=="buy" else bids[7][0],"size":round(rng.uniform(.04,.6),3)})
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("".join(json.dumps(row,separators=(",",":"))+"\n" for row in rows),encoding="utf-8")
    return len(rows)-1


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("output",nargs="?",default="data/liquidity_shock.jsonl")
    args=parser.parse_args(); print(f"Wrote {generate(args.output)} events to {args.output}")


if __name__=="__main__": main()
