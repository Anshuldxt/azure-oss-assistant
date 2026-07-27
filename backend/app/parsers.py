"""
Turns a raw report file into rows filed under the correct physical NE
in the Store, using the column mappings from config.py.
"""

from pathlib import Path
from io import StringIO

import pandas as pd

from .config import VENDOR_PROFILES, normalize
from .store import store

CHUNK_SIZE = 50_000

KIND_SCHEMAS = {
    "devip": ["ip", "mask", "userLabel", "portType", "portNo", "vrfIndex",
              "cabinet", "subrack", "slot", "subboard", "ctrlMode", "borrowIfip"],
    "vlan": ["vrfIndex", "nextHopIp", "mask", "vlanMode", "vlanId", "setPrio",
             "vlanPrio", "vlanGroupNo"],
    "s1": ["connStatus", "s1IfId", "s1IfStatus", "sctpLinkNo", "sctpLinkStatus",
           "cause", "localIp", "localPort", "peerIp", "peerPort", "sctpBlock"],
    "lte": ["controller", "subarea", "rat", "enbId", "enbFunction", "connStatus",
            "cellId", "cellName", "localCellId", "tac", "band", "phyCellId",
            "earfcn", "adminStatus", "activationStatus", "operStatus", "availStatus"],
    "nr": ["controller", "subarea", "rat", "gnbId", "gnbFunction", "connStatus",
           "cellId", "cellName", "tac", "band", "phyCellId", "earfcn",
           "adminStatus", "activationStatus", "operStatus", "availStatus"],
    "gsm": ["bsc", "siteIndex", "cellIndex", "cellName", "activityStatus", "ci",
            "basei", "ni", "bcchno", "band", "blkStatus", "hopHsn", "hopTsc",
            "hopIndex", "lac", "rac", "model", "swVersion"],
    "umts": ["rnc", "nodebId", "nodebName", "cellId", "cellName", "connStatus",
             "activityStatus", "blkStatus", "lac", "sac", "rac", "ulFreq", "dlFreq",
             "maxPower", "cbsState", "mbmsState", "hsdpaOp", "hsupaOp"],
    "neReport": ["neType", "ip1", "ip2", "version", "medPartition", "subareaIp",
                 "timeZone", "physLocation", "vendor", "description", "district",
                 "longitude", "latitude", "capacity", "region", "maintStatus",
                 "neConnStatus", "baseStationRat", "baseStationId", "baseStationRnc",
                 "homeSubnet", "productType", "neMaintMode", "creationTime"],
}


def build_header_map(columns):
    hm = {}
    for c in columns:
        n = normalize(c)
        hm.setdefault(n, []).append(c)
    return hm


def detect_kind(vendor, columns):
    hm = build_header_map(columns)
    datasets = VENDOR_PROFILES.get(vendor, {}).get("datasets", {})
    for kind, ds in datasets.items():
        det = ds.get("detect", {})
        required = det.get("required", [])
        any_of = det.get("any_of", [])
        if not all(r in hm for r in required):
            continue
        if any_of and not any(a in hm for a in any_of):
            continue
        return kind
    return None


def extract_field(df, header_map, aliases):
    cols = []
    for alias in aliases:
        for orig in header_map.get(alias, []):
            if orig in df.columns and orig not in cols:
                cols.append(orig)
    if not cols:
        return pd.Series([""] * len(df), index=df.index)

    def clean(s):
        s = s.astype(str).str.strip()
        return s.replace({"nan": "", "None": "", "NaN": ""})

    result = clean(df[cols[0]])
    for c in cols[1:]:
        nxt = clean(df[c])
        result = result.mask(result == "", nxt)
    return result


def split_alias_ne(value):
    if not value:
        return "", ""
    if "@" in value:
        alias, ne = value.split("@", 1)
        return alias, ne
    return "", value


def ingest_dataframe(vendor, kind, df):
    ds = VENDOR_PROFILES[vendor]["datasets"][kind]
    fields = ds["fields"]
    header_map = build_header_map(df.columns)

    resolved = {}
    for canonical, aliases in fields.items():
        resolved[canonical] = extract_field(df, header_map, aliases)
    out = pd.DataFrame(resolved)

    ne_from_split = ds.get("ne_from_split")
    if ne_from_split and ne_from_split in out.columns:
        aliases_ne = out[ne_from_split].map(split_alias_ne)
        out["alias_resolved"] = aliases_ne.map(lambda t: t[0])
        out["ne_resolved"] = aliases_ne.map(lambda t: t[1])
    else:
        out["ne_resolved"] = out["ne"] if "ne" in out.columns else ""
        out["alias_resolved"] = ""

    out = out[out["ne_resolved"].astype(bool)]

    bucket = ds.get("bucket", kind)
    schema = KIND_SCHEMAS.get(bucket, [])
    added = 0

    if bucket in ("devip", "vlan", "s1"):
        for row in out.itertuples(index=False):
            store.ensure_ne(row.ne_resolved)[bucket].append(
                {k: getattr(row, k, "") for k in schema}
            )
            added += 1
        store.bump(bucket, added)

    elif bucket in ("lte", "nr"):
        for row in out.itertuples(index=False):
            cell_key = getattr(row, "cellId", "") or getattr(row, "cellName", "")
            if store.already_have_cell(row.ne_resolved, bucket, cell_key):
                continue
            store.ensure_ne(row.ne_resolved)[bucket].append(
                {k: getattr(row, k, "") for k in schema}
            )
            added += 1
        store.bump(bucket, added)

    elif bucket == "gsm":
        for row in out.itertuples(index=False):
            alias = getattr(row, "alias_resolved", "")
            if alias:
                store.add_alias(alias, row.ne_resolved)
            cell_key = getattr(row, "cellIndex", "") or getattr(row, "cellName", "")
            if store.already_have_cell(row.ne_resolved, "gsm", cell_key):
                continue
            rec = {k: getattr(row, k, "") for k in schema}
            rec["gbts"] = alias
            store.ensure_ne(row.ne_resolved)["gsm"].append(rec)
            added += 1
        store.bump("gsm", added)

    elif bucket == "umts":
        for row in out.itertuples(index=False):
            alias = getattr(row, "alias_resolved", "")
            if alias:
                store.add_alias(alias, row.ne_resolved)
            cell_key = getattr(row, "cellId", "") or getattr(row, "cellName", "")
            if store.already_have_cell(row.ne_resolved, "umts", cell_key):
                continue
            rec = {k: getattr(row, k, "") for k in schema}
            rec["nodeb"] = alias or getattr(row, "nodebName", "")
            store.ensure_ne(row.ne_resolved)["umts"].append(rec)
            added += 1
        store.bump("umts", added)

    elif bucket == "neReport":
        for row in out.itertuples(index=False):
            rec = {k: getattr(row, k, "") for k in schema}
            if not rec.get("vendor"):
                rec["vendor"] = VENDOR_PROFILES[vendor]["label"]
            store.merge_ne_report(row.ne_resolved, rec)
            added += 1

    return added


import re

_HEADER_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")


def _looks_like_header(line: str) -> bool:
    """A real header line's tab-separated tokens are all bare
    identifiers (e.g. "NodeId", "managementState"). Actual data lines
    fail this because node names contain digits+underscores/hyphens
    ("PHE0064P_9NB02"), which the regex rejects -- that's what tells
    the two apart."""
    tokens = line.rstrip("\n").split("\t")
    return len(tokens) >= 2 and all(_HEADER_TOKEN_RE.match(t) for t in tokens)


def _iter_ericsson_txt_blocks(path, filename):
    """Ericsson `cmedit` CLI dumps concatenate the output of many
    separate commands into one .txt file (one block per `emncli>
    cmedit get ...` line). Some blocks have a clean header row right
    after the command line (optionally preceded by a single bare
    object-type line like "NetworkElement"); others have none, because
    the CLI just dumps raw tab-separated values with column names only
    implied by the command text. We only parse the header-bearing
    blocks -- guessing columns for headerless ones risks silently
    mislabeling real network data, so those are reported as skipped
    instead."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    boundaries = [i for i, l in enumerate(lines) if l.startswith("emncli>") or l.startswith("cmedit get")]
    if not boundaries or boundaries[0] != 0:
        boundaries.insert(0, 0)
    boundaries.append(len(lines))

    for bi in range(len(boundaries) - 1):
        start, end = boundaries[bi], boundaries[bi + 1]
        command_line = lines[start].strip()
        block_lines = lines[start + 1:end]

        header_idx = None
        for i, line in enumerate(block_lines[:4]):
            if _looks_like_header(line):
                header_idx = i
                break

        if header_idx is None:
            yield {"label": command_line[:120], "status": "skipped",
                   "detail": "no header row in this cmedit block -- column names aren't self-describing, skipped rather than guessed"}
            continue

        tsv = "".join(block_lines[header_idx:])
        try:
            df = pd.read_csv(StringIO(tsv), sep="\t", dtype=str, keep_default_na=False,
                              engine="python", on_bad_lines="skip")
        except Exception as e:
            yield {"label": command_line[:120], "status": "error", "detail": str(e)}
            continue

        if len(df) == 0:
            continue
        yield {"label": "%s :: %s" % (filename, command_line[:80]), "df": df}


def _iter_source_frames(path, filename):
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        yield filename, pd.read_csv(path, dtype=str, keep_default_na=False)
    elif ext == ".txt":
        for block in _iter_ericsson_txt_blocks(path, filename):
            if "df" in block:
                yield block["label"], block["df"]
            # headerless/error blocks are surfaced by the caller via
            # a side list rather than as a frame -- see ingest_csv_path
    elif ext in (".xlsx", ".xls"):
        sheets = pd.read_excel(path, sheet_name=None, dtype=str)
        for sheet_name, df in sheets.items():
            if df is not None and len(df.columns) and len(df):
                yield "%s :: %s" % (filename, sheet_name), df.fillna("")
    else:
        return


def ingest_csv_path(vendor, path, filename):
    if VENDOR_PROFILES.get(vendor, {}).get("datasets", {}) == {}:
        return {"file": filename, "status": "error", "detail": "vendor '%s' has no column mapping configured yet" % vendor}

    if "bfkt" in filename.lower():
        return {"file": filename, "status": "skipped", "detail": "BFKT variant ignored per MOP"}

    ext = Path(filename).suffix.lower()
    if ext not in (".csv", ".txt", ".xlsx", ".xls"):
        return {"file": filename, "status": "error", "detail": "unsupported file type '%s'" % ext}

    sub_results = []
    any_ok = False

    def _ingest_one(label, df):
        nonlocal any_ok
        kind = detect_kind(vendor, df.columns)
        if kind is None:
            sub_results.append({"sheet": label, "status": "skipped", "detail": "no matching dataset mapping for this table's columns"})
            return
        try:
            rows = 0
            if len(df) > CHUNK_SIZE:
                for start in range(0, len(df), CHUNK_SIZE):
                    rows += ingest_dataframe(vendor, kind, df.iloc[start:start + CHUNK_SIZE])
            else:
                rows = ingest_dataframe(vendor, kind, df)
            title = VENDOR_PROFILES[vendor]["datasets"][kind]["title"]
            sub_results.append({"sheet": label, "status": "ok", "kind": kind, "title": title, "rows": rows})
            any_ok = True
        except Exception as e:
            sub_results.append({"sheet": label, "status": "error", "detail": str(e), "kind": kind})

    if ext == ".txt":
        try:
            blocks = list(_iter_ericsson_txt_blocks(path, filename))
        except Exception as e:
            return {"file": filename, "status": "error", "detail": "could not read file: %s" % e}
        if not blocks:
            return {"file": filename, "status": "error", "detail": "no readable tables found"}
        for block in blocks:
            if "df" in block:
                _ingest_one(block["label"], block["df"])
            else:
                sub_results.append({"sheet": block["label"], "status": block["status"], "detail": block["detail"]})
    else:
        try:
            frames = list(_iter_source_frames(path, filename))
        except Exception as e:
            return {"file": filename, "status": "error", "detail": "could not read file: %s" % e}
        if not frames:
            return {"file": filename, "status": "error", "detail": "no readable tables found"}
        for label, df in frames:
            _ingest_one(label, df)

    total_rows = sum(r.get("rows", 0) for r in sub_results)
    titles = sorted(set(r["title"] for r in sub_results if r.get("status") == "ok"))
    return {
        "file": filename,
        "status": "ok" if any_ok else "error",
        "title": " + ".join(titles) if titles else "unrecognized",
        "rows": total_rows,
        "sheets": sub_results,
    }
