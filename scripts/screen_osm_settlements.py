#!/usr/bin/env python3
"""Second-pass OSM settlement screen. Never approves segments automatically.

Run after screen_countryside.py. Queries Overpass for place nodes and
residential land-use ways/relations along each day's candidate route.
Conservative results: overlaps are excluded; non-overlaps remain UNVERIFIED.
"""
import csv
import json
import math
import os
import time
from collections import defaultdict
from pathlib import Path
import requests
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import transform
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
ENDPOINTS=["https://overpass.kumi.systems/api/interpreter",
           "https://overpass-api.de/api/interpreter"]
PROJ=Transformer.from_crs("EPSG:4326","EPSG:3347",always_xy=True).transform
REGIONS=["NL","NS","PE","NB","QC","ON","MBSK","ABBC","NT","NU","YT"]
RADIUS={"city":2500,"town":1500,"village":850,"hamlet":500,"isolated_dwelling":180}
FIELDS=["segment_id","region","day","census_classification","osm_classification","nearby_settlements","residential_overlap","osm_query_status"]
SESSION=requests.Session()

def load_route():
    segments={}
    for key in REGIONS:
        raw=(ROOT/"data"/(key+".js")).read_text(encoding="utf-8")
        marker="window.CP_REGION_DATA["+json.dumps(key)+"]="
        data=json.JSONDecoder().raw_decode(raw[raw.index(marker)+len(marker):])[0]
        for s in data["segments"]:
            coords=s.get("geometry") or []
            if len(coords)<2: continue
            segments[s["id"]]=(s,key,LineString([(p[1],p[0]) for p in coords]))
    return segments

def query_overpass(bbox):
    south,west,north,east=bbox
    area=f"{south:.6f},{west:.6f},{north:.6f},{east:.6f}"
    query=f"""[out:json][timeout:100];
(
  nwr["place"~"^(city|town|village|hamlet|isolated_dwelling)$"]({area});
  nwr["landuse"="residential"]({area});
);
out geom;"""
    last=None
    for attempt in range(5):
        endpoint=ENDPOINTS[attempt%len(ENDPOINTS)]
        try:
            response=SESSION.post(endpoint,data={"data":query},timeout=125,
                                  headers={"User-Agent":"CanadianPursuit-CountrysideScreen/1.0"})
            response.raise_for_status()
            data=response.json()
            if "elements" not in data: raise RuntimeError("Missing Overpass elements")
            return data["elements"]
        except (requests.RequestException,ValueError,RuntimeError) as exc:
            last=exc
            print(f"Overpass attempt {attempt+1} failed: {exc}",flush=True)
            time.sleep(min(30,4*(attempt+1)))
    raise RuntimeError(f"All Overpass attempts failed: {last}")

def feature_geometry(feature):
    if feature["type"]=="node":
        return Point(feature["lon"],feature["lat"])
    coords=feature.get("geometry",[])
    if not coords and feature.get("members"):
        coords=[p for m in feature["members"] for p in m.get("geometry",[])]
    if not coords: return None
    points=[(p["lon"],p["lat"]) for p in coords]
    if len(points)>=4 and points[0]==points[-1]:
        try:
            polygon=Polygon(points)
            if polygon.is_valid and not polygon.is_empty: return polygon
        except ValueError: pass
    if len(points)>=2: return LineString(points)
    return Point(*points[0])

def day_bbox(items):
    b=[line.bounds for _,line in items]
    # 0.04 degrees lat/long margin ensures nearby settlement markers are included.
    return (max(-90,min(x[1] for x in b)-.04),
            max(-180,min(x[0] for x in b)-.06),
            min(90,max(x[3] for x in b)+.04),
            min(180,max(x[2] for x in b)+.06))

def main():
    source=ROOT/"data"/"countryside-review.csv"
    if not source.exists(): raise RuntimeError("Run first-stage census screening first")
    with source.open(encoding="utf-8",newline="") as f:
        census=list(csv.DictReader(f))
    route=load_route()
    candidates=defaultdict(list)
    rows=[]
    for c in census:
        row={"segment_id":c["segment_id"],"region":c["region"],"day":c["day"],
             "census_classification":c["classification"],"osm_classification":"not_screened",
             "nearby_settlements":"","residential_overlap":"","osm_query_status":"not_required"}
        rows.append(row)
        if c["classification"]=="candidate_needs_small_settlement_review":
            item=route.get(c["segment_id"])
            if not item:
                row["osm_classification"]="unresolved_missing_geometry"
                continue
            candidates[(c["region"],c["day"])].append((row,item[2]))
    print(f"Checking {sum(map(len,candidates.values()))} census candidates across {len(candidates)} days",flush=True)
    for number,((region,day),items) in enumerate(sorted(candidates.items()),1):
        bbox=day_bbox(items)
        try:
            features=query_overpass(bbox)
        except RuntimeError as exc:
            for row,line in items:
                row["osm_classification"]="unresolved_query_failed"
                row["osm_query_status"]=str(exc)[:200]
            print(f"{number}/{len(candidates)} {region} day {day}: query failed",flush=True)
            continue
        geometries=[]
        for f in features:
            geom=feature_geometry(f)
            if geom is None: continue
            try: projected=transform(PROJ,geom)
            except Exception: continue
            geometries.append((f.get("tags",{}),projected))
        for row,line in items:
            projected=transform(PROJ,line)
            hits=[]
            residential=False
            for tags,geom in geometries:
                place=tags.get("place")
                if place in RADIUS and projected.distance(geom)<=RADIUS[place]:
                    hits.append(tags.get("name") or place)
                if tags.get("landuse")=="residential" and projected.distance(geom)<=100:
                    residential=True
            row["nearby_settlements"]="; ".join(sorted(set(hits))[:12])
            row["residential_overlap"]=str(residential)
            row["osm_classification"]=("excluded_osm_settlement" if hits or residential
                else "candidate_needs_manual_review")
            row["osm_query_status"]="success"
        print(f"{number}/{len(candidates)} {region} day {day}: {len(items)} segments; {len(features)} OSM features",flush=True)
        time.sleep(1.5)
    with (ROOT/"data"/"countryside-osm-review.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader();writer.writerows(rows)
    counts={}
    for row in rows: counts[row["osm_classification"]]=counts.get(row["osm_classification"],0)+1
    (ROOT/"data"/"countryside-osm-summary.json").write_text(json.dumps({
        "status":"UNVERIFIED REVIEW ONLY - NOT FOR RANDOM ASSIGNMENT",
        "method":"OSM Overpass place features with conservative distance thresholds and residential landuse; OSM completeness varies",
        "counts":counts,
        "candidate_ids":[r["segment_id"] for r in rows if r["osm_classification"]=="candidate_needs_manual_review"]
    },indent=2)+"\n",encoding="utf-8")
    print("OSM screen complete:",counts,flush=True)
    print("Eligibility manifest intentionally unchanged.",flush=True)

if __name__=="__main__": main()
