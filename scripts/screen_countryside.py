#!/usr/bin/env python3
"""Conservative countryside screening for Canadian Pursuit.
Requires: pip install requests shapely pyproj
Run at repo root: python scripts/screen_countryside.py
Produces data/countryside-review.csv and data/countryside-candidates.json.
Never publishes a verified eligibility manifest automatically.
"""
import csv
import json
import re
from pathlib import Path
import requests
from shapely.geometry import LineString, shape, box
from shapely.ops import transform
from shapely.prepared import prep
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
API="https://geo.statcan.gc.ca/geo_wa/rest/services/2021/Cartographic_boundary_files/MapServer"
REGIONS=["NL","NS","PE","NB","QC","ON","MBSK","ABBC","NT","NU","YT"]
SESSION=requests.Session()
PROJECT=Transformer.from_crs("EPSG:4326","EPSG:3347",always_xy=True).transform

def get_json(url,params):
    response=SESSION.get(url,params=params,timeout=90)
    response.raise_for_status()
    data=response.json()
    if "error" in data: raise RuntimeError(f"GIS service error: {data['error']}")
    return data

def load_segments():
    out=[]
    unresolved=[]
    for key in REGIONS:
        raw=(ROOT/"data"/(key+".js")).read_text(encoding="utf-8")
        marker="window.CP_REGION_DATA["+json.dumps(key)+"]="
        start=raw.index(marker)+len(marker)
        data=json.JSONDecoder().raw_decode(raw[start:])[0]
        for s in data["segments"]:
            coords=s.get("geometry") or []
            if len(coords)<2:\n                unresolved.append({"segment_id":s["id"],"region":key,"day":s["day"],"reason":"Insufficient route polyline coordinates"})\n                continue
            line=LineString([(p[1],p[0]) for p in coords])
            out.append((s,key,line))
    return out,unresolved

def fetch_layer(layer,bounds):
    """Retrieve all polygons in a bbox using pagination; fail on errors."""
    xmin,ymin,xmax,ymax=bounds
    url=f"{API}/{layer}/query"
    params={"where":"1=1","geometry":f"{xmin},{ymin},{xmax},{ymax}",
            "geometryType":"esriGeometryEnvelope","inSR":"4326",
            "spatialRel":"esriSpatialRelIntersects","outFields":"*",
            "outSR":"4326","returnGeometry":"true","f":"geojson",
            "resultRecordCount":1000,"resultOffset":0}
    features=[]
    while True:
        data=get_json(url,params)
        chunk=data.get("features")
        if chunk is None: raise RuntimeError(f"Unexpected GIS response for layer {layer}")
        features.extend(chunk)
        if len(chunk)<1000: break
        params["resultOffset"]+=len(chunk)
        if params["resultOffset"]>50000: raise RuntimeError("Pagination safety limit")
    return features

def main():
    segments,unresolved=load_segments()
    print(f"Loaded {len(segments)} segments with usable geometry; {len(unresolved)} unresolved (excluded from candidates)")
    # Query by regional extent to avoid downloading unrelated polygons.
    regions={}
    for s,k,line in segments: regions.setdefault(k,[]).append((s,line))
    results=[]
    for key,items in regions.items():
        bounds=(
            min(l.bounds[0] for _,l in items)-.05,
            min(l.bounds[1] for _,l in items)-.05,
            max(l.bounds[2] for _,l in items)+.05,
            max(l.bounds[3] for _,l in items)+.05
        )
        # 7: population centres, 8: designated places.
        settlement=[]
        for layer in (7,8):
            features=fetch_layer(layer,bounds)
            settlement.extend((layer,shape(f["geometry"]),f.get("properties",{})) for f in features if f.get("geometry"))
        projected=[(layer,prep(transform(PROJECT,poly)),props) for layer,poly,props in settlement]
        for segment,line in items:
            projected_line=transform(PROJECT,line)
            hits=[(layer,props) for layer,poly,props in projected if poly.intersects(projected_line)]
            results.append({
                "segment_id":segment["id"],"region":key,"day":segment["day"],
                "label":segment.get("label",""),"length_km":segment.get("lengthKm"),
                "census_overlap":bool(hits),
                "population_centre_overlap":any(layer==7 for layer,_ in hits),
                "designated_place_overlap":any(layer==8 for layer,_ in hits),
                "classification":"excluded_census_settlement" if hits else "candidate_needs_small_settlement_review"
            })
        print(f"{key}: {len(items)} segments; {len(settlement)} settlement polygons")
    if len(results)!=len(segments): raise RuntimeError("Missing segment classifications")\n    for item in unresolved:\n        results.append({"segment_id":item["segment_id"],"region":item["region"],"day":item["day"],"label":"","length_km":"","census_overlap":"","population_centre_overlap":"","designated_place_overlap":"","classification":"unresolved_missing_geometry"})
    output=ROOT/"data"
    with (output/"countryside-review.csv").open("w",newline="",encoding="utf-8") as file:
        writer=csv.DictWriter(file,fieldnames=list(results[0]))
        writer.writeheader();writer.writerows(results)
    candidates=[r["segment_id"] for r in results if r["classification"]=="candidate_needs_small_settlement_review"]
    (output/"countryside-candidates.json").write_text(json.dumps({
        "status":"UNVERIFIED: candidates only, NOT eligible for assignment",
        "sources":["Statistics Canada 2021 Cartographic Boundary Files, PC layer 7, DPL layer 8"],
        "candidates":candidates
    },indent=2)+"\n",encoding="utf-8")
    print(f"{len(candidates)} preliminary candidates; {len(unresolved)} segments excluded for missing geometry. Manual small-settlement review REQUIRED.")
    print("The website's countryside-eligible.js is intentionally NOT updated.")

if __name__=="__main__":
    main()
