#!/usr/bin/env python3
"""
VoltaGrid Palantir Foundry — Ontology Explorer
================================================
This script connects to VoltaGrid's Foundry instance and dumps the complete
Ontology structure (object types, properties, link types, action types) into
a structured JSON file that can be shared for analysis.

SETUP:
------
1. Install the Foundry Platform SDK:
   pip install foundry-platform-sdk

2. (Optional) If you've generated a Python OSDK from Developer Console:
   pip install <your-generated-osdk-package>

3. Get an API token:
   - Go to your Foundry instance → Settings → Tokens → Generate new token
   - Or use Developer Console to create an OAuth2 client
   - Store the token as an environment variable:
     PowerShell: $env:FOUNDRY_TOKEN="your-token-here"
     Bash/zsh:   export FOUNDRY_TOKEN="your-token-here"

4. Run:
   python voltagrid_ontology_explorer.py

OUTPUT:
-------
- voltagrid_ontology_dump.json  — Full structured dump of the Ontology
- Console output with a human-readable summary
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

FOUNDRY_HOSTNAME = "voltagrid.palantirfoundry.com"
FOUNDRY_TOKEN = os.environ.get("FOUNDRY_TOKEN", "")
OUTPUT_FILE = "voltagrid_ontology_dump.json"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ontology-explorer")


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def safe_dict(obj: Any) -> dict:
    """Convert SDK response objects to plain dicts for JSON serialization."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return {"_raw": str(obj)}


def truncate(s: str, max_len: int = 120) -> str:
    """Truncate a string for display."""
    if not s:
        return ""
    return s[:max_len] + ("..." if len(s) > max_len else "")


def build_user_token_auth(user_token_auth_cls: Any, hostname: str, token: str) -> Any:
    """Support both current and older foundry_sdk UserTokenAuth signatures."""
    try:
        return user_token_auth_cls(hostname=hostname, token=token)
    except TypeError:
        try:
            return user_token_auth_cls(token=token)
        except TypeError:
            return user_token_auth_cls(token)


# ─────────────────────────────────────────────────────────────────────────────
# Platform SDK approach (foundry-platform-sdk)
# Works without generating an OSDK — uses the REST API layer directly
# ─────────────────────────────────────────────────────────────────────────────

def explore_with_platform_sdk() -> dict:
    """
    Uses the Foundry Platform SDK to enumerate Ontology metadata.
    This works with the generic SDK — no OSDK generation needed.
    """
    try:
        from foundry_sdk import FoundryClient, UserTokenAuth
    except ImportError:
        log.error(
            "foundry-platform-sdk not installed.\n"
            "Run: pip install foundry-platform-sdk"
        )
        return {}

    if not FOUNDRY_TOKEN:
        log.error(
            "FOUNDRY_TOKEN environment variable not set.\n"
            "Get a token from Foundry → Settings → Tokens"
        )
        return {}

    log.info(f"Connecting to {FOUNDRY_HOSTNAME}...")
    client = FoundryClient(
        auth=build_user_token_auth(
            UserTokenAuth,
            hostname=FOUNDRY_HOSTNAME,
            token=FOUNDRY_TOKEN,
        ),
        hostname=FOUNDRY_HOSTNAME,
    )

    result = {
        "metadata": {
            "hostname": FOUNDRY_HOSTNAME,
            "extracted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "tool": "voltagrid_ontology_explorer.py",
        },
        "ontologies": [],
        "object_types": [],
        "link_types": [],
        "action_types": [],
        "datasets_sample": [],
    }

    # ── Step 1: List Ontologies ──────────────────────────────────────────
    log.info("Fetching ontologies...")
    try:
        ontologies_response = client.ontologies.Ontology.list()
        for ont in ontologies_response.data:
            ont_data = safe_dict(ont)
            result["ontologies"].append(ont_data)
            log.info(f"  Found ontology: {ont_data.get('displayName', ont_data.get('rid', 'unknown'))}")
    except Exception as e:
        log.warning(f"Could not list ontologies: {e}")
        # Try alternative endpoint structure
        try:
            ontologies_response = client.ontologies.Ontology.page()
            for ont in ontologies_response.data:
                result["ontologies"].append(safe_dict(ont))
        except Exception as e2:
            log.warning(f"Alternative ontology listing also failed: {e2}")

    # ── Step 2: For each ontology, get object types ──────────────────────
    for ont in result["ontologies"]:
        ont_rid = ont.get("rid") or ont.get("apiName") or ont.get("ontologyRid")
        if not ont_rid:
            continue

        log.info(f"Fetching object types for ontology: {ont_rid}...")
        try:
            obj_types_response = client.ontologies.Ontology.ObjectType.list(ont_rid)
            for ot in obj_types_response.data:
                ot_data = safe_dict(ot)
                ot_data["_ontology_rid"] = ont_rid
                result["object_types"].append(ot_data)

                # Get properties detail
                api_name = ot_data.get("apiName", "")
                log.info(f"  Object type: {api_name}")

                # Try to get full object type details including properties
                try:
                    detail = client.ontologies.Ontology.ObjectType.get(
                        ont_rid, api_name
                    )
                    detail_data = safe_dict(detail)
                    # Merge details back
                    ot_data.update(detail_data)
                except Exception:
                    pass

        except Exception as e:
            log.warning(f"Could not list object types: {e}")

        # ── Step 3: Get link types ───────────────────────────────────────
        log.info(f"Fetching link types...")
        try:
            # Link types may be per object type
            for ot in result["object_types"]:
                api_name = ot.get("apiName", "")
                if not api_name:
                    continue
                try:
                    links_response = client.ontologies.Ontology.ObjectType.list_outgoing_link_types(
                        ont_rid, api_name
                    )
                    for lt in links_response.data:
                        lt_data = safe_dict(lt)
                        lt_data["_source_object_type"] = api_name
                        lt_data["_ontology_rid"] = ont_rid
                        result["link_types"].append(lt_data)
                        log.info(f"    Link: {api_name} → {lt_data.get('objectTypeApiName', '?')} ({lt_data.get('apiName', '?')})")
                except Exception:
                    pass
        except Exception as e:
            log.warning(f"Could not fetch link types: {e}")

        # ── Step 4: Get action types ─────────────────────────────────────
        log.info(f"Fetching action types...")
        try:
            actions_response = client.ontologies.Ontology.ActionType.list(ont_rid)
            for at in actions_response.data:
                at_data = safe_dict(at)
                at_data["_ontology_rid"] = ont_rid
                result["action_types"].append(at_data)
                log.info(f"  Action: {at_data.get('apiName', at_data.get('displayName', '?'))}")
        except Exception as e:
            log.warning(f"Could not list action types: {e}")

    # ── Step 5: Sample recent datasets (top-level view) ──────────────────
    log.info("Fetching sample datasets...")
    try:
        datasets_response = client.datasets.Dataset.list()
        count = 0
        for ds in datasets_response:
            if count >= 50:  # Limit to first 50 for overview
                break
            ds_data = safe_dict(ds)
            result["datasets_sample"].append(ds_data)
            count += 1
        log.info(f"  Found {count} datasets (showing first 50)")
    except Exception as e:
        log.warning(f"Could not list datasets: {e}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# REST API fallback (if SDK methods don't match your version)
# Uses raw HTTP requests to the Foundry API
# ─────────────────────────────────────────────────────────────────────────────

def explore_with_rest_api() -> dict:
    """
    Fallback: hit the Foundry REST API directly if the SDK methods
    don't align with your enrollment's version.
    """
    import urllib.request
    import urllib.error

    if not FOUNDRY_TOKEN:
        log.error("FOUNDRY_TOKEN not set")
        return {}

    BASE = f"https://{FOUNDRY_HOSTNAME}/api"
    HEADERS = {
        "Authorization": f"Bearer {FOUNDRY_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    def api_get(path: str) -> Optional[dict]:
        url = f"{BASE}{path}"
        req = urllib.request.Request(url, headers=HEADERS, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            log.warning(f"  HTTP {e.code} for {path}: {e.reason}")
            return None
        except Exception as e:
            log.warning(f"  Error for {path}: {e}")
            return None

    result = {
        "metadata": {
            "hostname": FOUNDRY_HOSTNAME,
            "extracted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "tool": "voltagrid_ontology_explorer.py (REST fallback)",
        },
        "ontologies": [],
        "object_types": [],
        "link_types": [],
        "action_types": [],
        "query_types": [],
    }

    # ── List ontologies ──────────────────────────────────────────────────
    log.info("REST API: Listing ontologies...")
    onts = api_get("/v2/ontologies")
    if onts and "data" in onts:
        result["ontologies"] = onts["data"]
        for o in onts["data"]:
            log.info(f"  Ontology: {o.get('displayName', o.get('rid'))}")
    elif onts:
        # Single ontology response
        result["ontologies"] = [onts] if isinstance(onts, dict) else onts

    # ── For each ontology, enumerate everything ──────────────────────────
    for ont in result["ontologies"]:
        ont_rid = ont.get("rid", ont.get("apiName", ""))
        if not ont_rid:
            continue

        # Object types
        log.info(f"REST API: Listing object types for {ont_rid}...")
        ots = api_get(f"/v2/ontologies/{ont_rid}/objectTypes")
        if ots and "data" in ots:
            for ot in ots["data"]:
                ot["_ontology_rid"] = ont_rid
                result["object_types"].append(ot)
                api_name = ot.get("apiName", "?")
                prop_count = len(ot.get("properties", {}))
                log.info(f"  Object: {api_name} ({prop_count} properties)")

                # Get outgoing link types for this object type
                links = api_get(
                    f"/v2/ontologies/{ont_rid}/objectTypes/{api_name}/outgoingLinkTypes"
                )
                if links and "data" in links:
                    for lt in links["data"]:
                        lt["_source_object_type"] = api_name
                        lt["_ontology_rid"] = ont_rid
                        result["link_types"].append(lt)
                        target = lt.get("objectTypeApiName", "?")
                        link_name = lt.get("apiName", "?")
                        log.info(f"    Link: {api_name} —[{link_name}]→ {target}")

            # Pagination
            while ots.get("nextPageToken"):
                ots = api_get(
                    f"/v2/ontologies/{ont_rid}/objectTypes?pageToken={ots['nextPageToken']}"
                )
                if ots and "data" in ots:
                    for ot in ots["data"]:
                        ot["_ontology_rid"] = ont_rid
                        result["object_types"].append(ot)

        # Action types
        log.info(f"REST API: Listing action types...")
        ats = api_get(f"/v2/ontologies/{ont_rid}/actionTypes")
        if ats and "data" in ats:
            for at in ats["data"]:
                at["_ontology_rid"] = ont_rid
                result["action_types"].append(at)
                log.info(f"  Action: {at.get('apiName', at.get('displayName', '?'))}")

        # Query types
        log.info(f"REST API: Listing query types...")
        qts = api_get(f"/v2/ontologies/{ont_rid}/queryTypes")
        if qts and "data" in qts:
            for qt in qts["data"]:
                qt["_ontology_rid"] = ont_rid
                result["query_types"].append(qt)
                log.info(f"  Query: {qt.get('apiName', '?')}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Summary printer
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(data: dict):
    """Print a human-readable summary of the Ontology dump."""
    print("\n" + "=" * 72)
    print("  VOLTAGRID FOUNDRY ONTOLOGY — SUMMARY")
    print("=" * 72)
    print(f"  Hostname:      {data.get('metadata', {}).get('hostname', '?')}")
    print(f"  Extracted:     {data.get('metadata', {}).get('extracted_at', '?')}")
    print(f"  Ontologies:    {len(data.get('ontologies', []))}")
    print(f"  Object Types:  {len(data.get('object_types', []))}")
    print(f"  Link Types:    {len(data.get('link_types', []))}")
    print(f"  Action Types:  {len(data.get('action_types', []))}")
    print(f"  Query Types:   {len(data.get('query_types', []))}")
    print("=" * 72)

    # ── Object types detail ──────────────────────────────────────────────
    if data.get("object_types"):
        print("\n  OBJECT TYPES:")
        print("  " + "-" * 68)
        for ot in sorted(data["object_types"], key=lambda x: x.get("apiName", "")):
            api_name = ot.get("apiName", "?")
            display = ot.get("displayName", api_name)
            desc = truncate(ot.get("description", ""), 60)
            props = ot.get("properties", {})
            prop_count = len(props) if isinstance(props, dict) else 0
            pk = ot.get("primaryKey", "?")

            print(f"\n  ▸ {display}  (api: {api_name})")
            if desc:
                print(f"    Description: {desc}")
            print(f"    Primary Key: {pk}")
            print(f"    Properties ({prop_count}):")

            if isinstance(props, dict):
                for pname, pdef in sorted(props.items()):
                    if isinstance(pdef, dict):
                        ptype = pdef.get("dataType", {})
                        if isinstance(ptype, dict):
                            type_str = ptype.get("type", "?")
                        else:
                            type_str = str(ptype)
                        pdesc = truncate(pdef.get("description", ""), 40)
                        print(f"      • {pname}: {type_str}" + (f"  — {pdesc}" if pdesc else ""))
                    else:
                        print(f"      • {pname}: {pdef}")

    # ── Link types ───────────────────────────────────────────────────────
    if data.get("link_types"):
        print(f"\n  LINK TYPES ({len(data['link_types'])}):")
        print("  " + "-" * 68)
        for lt in data["link_types"]:
            src = lt.get("_source_object_type", "?")
            tgt = lt.get("objectTypeApiName", lt.get("targetObjectTypeApiName", "?"))
            name = lt.get("apiName", lt.get("displayName", "?"))
            card = lt.get("cardinality", "?")
            print(f"  ▸ {src} —[{name}]→ {tgt}  (cardinality: {card})")

    # ── Action types ─────────────────────────────────────────────────────
    if data.get("action_types"):
        print(f"\n  ACTION TYPES ({len(data['action_types'])}):")
        print("  " + "-" * 68)
        for at in data["action_types"]:
            name = at.get("apiName", at.get("displayName", "?"))
            desc = truncate(at.get("description", ""), 60)
            params = at.get("parameters", {})
            param_count = len(params) if isinstance(params, dict) else 0
            print(f"  ▸ {name}  ({param_count} params)")
            if desc:
                print(f"    {desc}")
            if isinstance(params, dict):
                for pname, pdef in params.items():
                    if isinstance(pdef, dict):
                        print(f"      • {pname}: {pdef.get('dataType', {}).get('type', '?')}")

    # ── Query types ──────────────────────────────────────────────────────
    if data.get("query_types"):
        print(f"\n  QUERY TYPES ({len(data['query_types'])}):")
        print("  " + "-" * 68)
        for qt in data["query_types"]:
            name = qt.get("apiName", "?")
            desc = truncate(qt.get("description", ""), 60)
            print(f"  ▸ {name}")
            if desc:
                print(f"    {desc}")

    print("\n" + "=" * 72)
    print(f"  Full dump saved to: {OUTPUT_FILE}")
    print("=" * 72 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(r"""
    ╔══════════════════════════════════════════════════════════╗
    ║   VoltaGrid — Palantir Foundry Ontology Explorer        ║
    ║   Dumps object types, links, actions, and properties    ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    if not FOUNDRY_TOKEN:
        print("  ⚠  FOUNDRY_TOKEN environment variable not set!")
        print("  Set it with:")
        print("    PowerShell: $env:FOUNDRY_TOKEN='your-token-here'")
        print("    Bash/zsh:   export FOUNDRY_TOKEN='your-token-here'")
        print()
        print("  To get a token:")
        print(f"    1. Go to https://{FOUNDRY_HOSTNAME}")
        print("    2. Settings → Tokens → Generate new token")
        print("    3. Copy the token and set it as shown above")
        print()
        sys.exit(1)

    # Try Platform SDK first, fall back to REST API
    log.info("Attempting Platform SDK approach...")
    data = explore_with_platform_sdk()

    # If SDK didn't return object types, try REST API directly
    if not data.get("object_types"):
        log.info("Platform SDK returned no object types, trying REST API fallback...")
        data = explore_with_rest_api()

    if not data.get("object_types"):
        log.warning(
            "No object types found. Possible causes:\n"
            "  - Token doesn't have Ontology read permissions\n"
            "  - No Ontology has been created yet in this enrollment\n"
            "  - Network/auth issue\n"
            "Check your token and try again."
        )

    # Save full dump
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)
    log.info(f"Full dump saved to {OUTPUT_FILE}")

    # Print summary
    print_summary(data)

    print("  NEXT STEPS:")
    print(f"  1. Share {OUTPUT_FILE} with Claude for Ontology analysis")
    print("  2. Generate a Python OSDK from Developer Console for")
    print("     richer object queries and action execution")
    print("  3. Use the OSDK to sample actual object data:")
    print()
    print("     from ontology_sdk.ontology.objects import YourObjectType")
    print("     objects = list(client.ontology.objects.YourObjectType.iterate())")
    print()


if __name__ == "__main__":
    main()
