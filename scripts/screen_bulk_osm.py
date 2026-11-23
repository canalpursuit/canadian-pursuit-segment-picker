#!/usr/bin/env python3
"""Bulk OpenStreetMap countryside screening from Geofabrik regional shapefiles.

Requires pip install requests pyshp shapely pyproj
Reads existing data/countryside-review.csv. Never approves segments automatically.
Downloads one Canadian province/territory archive at a time, extracting ONLY
places and landuse shapefiles, then deletes each archive before moving on.
"""
import csv
import json
import os
import shutil
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import requests
import shapefile
from pyproj import Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
BASE="https://download.geofabrik.de/north-america/canada"
REGIONS=["NL","NS","PE","NB","QC","ON","MBSK","ABBC","NT","NU","YT"]
FILES={
    "NL":["newfoundland-and-labrador"],
    "NS":["nova-scotia"],
    "PE":["prince-edward-island"],
    "NB":["new-brunswick"],
    "QC":["quebec"],
    "ON":["ontario"],
    "MBSK":["manitoba","saskatchewan"],
    "ABBC":["alberta","british-columbia"],
    "NT":["northwest-territories"],
    "NU":["nunavut"],
    "YT":["yukon"],
}
# Settlement marker buffers are deliberately conservative; this is a REVIEW
# filter, not a claim that these distances are official built-up boundaries.
PLACE_RADII={"city":2500,"town":1500,"village":850,"hamlet":500,
             "isolated_dwelling":180,"suburb":500,"neighbourhood":350}
PROJECT=Transformer.from_crs("EPSG:4326","EPSG:3347",always_xy=True).transform
FIELDS=["segment_id","region","day","census_classification","bulk_osm_classification",
        "nearby_places","residential_overlap","data_status"]
SESSION=requests.Session()
SESSION.headers.update({"User-Agent":"CanadianPursuit-GeoReview/1.0 (research)"})

def route_segments():
    result={}
    for region in REGIONS:
        raw=(DATA/(region+".js")).read_text(encoding="utf-8")
        marker="window.CP_REGION_DATA["+json.dumps(region)+"]="
        obj=json.JSONDecoder().raw_decode(raw[raw.index(marker)+len(marker):])[0]
        for seg in obj["segments"]:
            coords=seg.get("geometry") or []
            if len(coords)>=2:
                result[seg["id"]]=transform(PROJECT,LineString([(p[1],p[0]) for p in coords]))
    return result

def download(url,target):
    print("Downloading",url,flush=True)
    for attempt in range(3):
        try:
            with SESSION.get(url,stream=True,timeout=(25,180)) as resp:
                resp.raise_for_status()
                with open(target,"wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024*1024):
                        if chunk:f.write(chunk)
            return
        except requests.RequestException as exc:
            if target.exists():target.unlink()
            print("Download failed:",str(exc)[:160],flush=True)
            if attempt==2:raise
            time.sleep(8*(attempt+1))

def extract_layers(archive,dest):
    selected=[]
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            base=Path(name).name.lower()
            if any(base.startswith(prefix) for prefix in (
                "gis_osm_places_free_","gis_osm_places_a_free_",
                "gis_osm_landuse_a_free_")) and base.endswith((".shp",".shx",".dbf",".prj",".cpg")):
                selected.append(name)
        if not selected:raise RuntimeError("Geofabrik archive contains no expected place/landuse shapefiles")
        for name in selected:
            destfile=dest/Path(name).name
            with z.open(name) as src,open(destfile,"wb") as dst:shutil.copyfileobj(src,dst)
    return list(dest.glob("*.shp"))

def read_features(files):
    features=[]
    for filename in files:
        is_landuse="landuse" in filename.name
        try:
            reader=shapefile.Reader(str(filename),encoding="utf-8",encodingErrors="replace")
            fields=[f[0] for f in reader.fields[1:]]
            skipped_empty=0
            for sr in reader.iterShapeRecords():
                tags=dict(zip(fields,sr.record))
                kind=str(tags.get("fclass") or tags.get("type") or "").lower()
                if is_landuse:
                    if kind!="residential":continue
                    buffer_m=100
                else:
                    if kind not in PLACE_RADII:continue
                    buffer_m=PLACE_RADII[kind]
                try:
                    if not sr.shape.points:
                        skipped_empty+=1
                        continue
                    geom=shape(sr.shape.__geo_interface__)
                    if geom.is_empty:continue
                    geom=transform(PROJECT,geom).buffer(buffer_m)
                except Exception:
                    skipped_empty+=1
                    continue
                features.append((geom,str(tags.get("name") or kind)))
            if skipped_empty:print(f"{filename.name}: skipped {skipped_empty} empty shapes",flush=True)
        except Exception as exc:
            raise RuntimeError(f"Unable to read {filename.name}: {exc}") from exc
    return features

def main():
    with (DATA/"countryside-review.csv").open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    routes=route_segments()
    result=[]
    groups=defaultdict(list)
    for original in rows:
        row={"segment_id":original["segment_id"],"region":original["region"],"day":original["day"],
             "census_classification":original["classification"],"bulk_osm_classification":"not_screened",
             "nearby_places":"","residential_overlap":"","data_status":"not_required"}
        result.append(row)
        if original["classification"]=="candidate_needs_small_settlement_review":
            if row["segment_id"] not in routes:
                row["bulk_osm_classification"]="unresolved_missing_geometry"
            else:
                groups[row["region"]].append(row)
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td)
        for region in REGIONS:
            pending=groups.get(region,[])
            if not pending:continue
            paths=FILES[region]
            # A combined MB/SK or AB/BC segment is checked against BOTH
            # provincial datasets; a single successful province is insufficient.
            hits=defaultdict(set)
            processed=0
            for province in paths:
                archive=temp/(province+".zip")
                folder=temp/province
                folder.mkdir()
                try:
                    download(f"{BASE}/{province}-latest-free.shp.zip",archive)
                    files=extract_layers(archive,folder)
                    features=read_features(files)
                    geometries=[f[0] for f in features]
                    tree=STRtree(geometries) if geometries else None
                    for row in pending:
                        route=routes[row["segment_id"]]
                        if tree is not None:
                            for idx in tree.query(route,predicate="intersects"):
                                hits[row["segment_id"]].add(features[int(idx)][1])
                    processed+=1
                    print(f"{region} / {province}: {len(features)} settlement/residential features; {len(pending)} candidate segments",flush=True)
                except Exception as exc:
                    print(f"{region} / {province}: FAILED: {exc}",flush=True)
                finally:
                    if archive.exists():archive.unlink()
                    shutil.rmtree(folder,ignore_errors=True)
            for row in pending:
                if processed!=len(paths):
                    row["bulk_osm_classification"]="unresolved_download_or_processing_failure"
                    row["data_status"]=f"{processed}/{len(paths)} extracts checked"
                else:
                    names=hits.get(row["segment_id"],set())
                    row["bulk_osm_classification"]=("excluded_osm_settlement" if names
                        else "candidate_needs_manual_review")
                    row["nearby_places"]="; ".join(sorted(names)[:15])
                    row["residential_overlap"]=str("residential" in names)
                    row["data_status"]="all_required_extracts_processed"
    with (DATA/"countryside-bulk-review.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(result)
    counts=dict(Counter(r["bulk_osm_classification"] for r in result))
    (DATA/"countryside-bulk-summary.json").write_text(json.dumps({
        "status":"UNVERIFIED: geographic review only, NOT eligible for assignment",
        "method":"Geofabrik OpenStreetMap province/territory free shapefiles: places and residential landuse",
        "counts":counts,
        "candidate_ids":[r["segment_id"] for r in result if r["bulk_osm_classification"]=="candidate_needs_manual_review"]
    },indent=2)+"\n",encoding="utf-8")
    print("Summary",counts,flush=True)
    print("Website eligibility manifest NOT updated.",flush=True)

if __name__=="__main__":main()
