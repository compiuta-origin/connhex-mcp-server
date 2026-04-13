"""
Helpers for flattening JSON:API responses into a friendlier shape for LLM
consumption.

Behavior:
- Each resource becomes a flat dict: id + type + attributes hoisted to the top
  level + relationships rendered as either nested resources (when present in
  the response's `included` array) or as bare reference IDs.
- Relationship resolution is **one level deep**: included resources have their
  own relationships left as bare IDs to avoid recursion blow-ups and cycles.
"""

from typing import Any

# Lookup keyed by JSON:API resource identity (type, id) → flattened resource.
IncludedLookup = dict[tuple[str, str], dict]


# ---------------------------------------------------------------------------
# Filter query builder
# ---------------------------------------------------------------------------


def _serialize_filter_value(value: Any) -> str:
    """Serialize a leaf filter value to its JSON:API query-string form."""
    if isinstance(value, bool):
        # Booleans must come before int — bool is a subclass of int.
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(_serialize_filter_value(v) for v in value)
    return str(value)


def _walk_filter(node: Any, prefix: str, out: dict[str, str]) -> None:
    if not isinstance(node, dict):
        out[prefix] = _serialize_filter_value(node)
        return
    for key, value in node.items():
        _walk_filter(value, f"{prefix}[{key}]", out)


def build_filter_params(filter_tree: dict | None) -> dict[str, str]:
    """
    Translate a JSON:API filter tree into HTTP query-param key/value pairs.

    Examples (input → output):
        {"serial": "ABC"}                       → {"filter[serial]": "ABC"}
        {"serial": ["A", "B"]}                  → {"filter[serial]": "A,B"}
        {"serial": {"fuzzy-match": "ABC"}}      → {"filter[serial][fuzzy-match]": "ABC"}
        {"site": {"exists": True}}              → {"filter[site][exists]": "true"}
        {"or": {"a": {"match": "x"},
                "b": {"match": "y"}}}           → {"filter[or][a][match]": "x",
                                                    "filter[or][b][match]": "y"}

    The walker is intentionally **format-agnostic**: it does not validate
    operator names, combinators, or field names. The upstream API is the
    source of truth — invalid grammar surfaces as a 4xx, not a client-side
    error here.
    """
    if not filter_tree:
        return {}
    params: dict[str, str] = {}
    _walk_filter(filter_tree, "filter", params)
    return params


def _resolve_ref(ref: dict, included_lookup: IncludedLookup | None) -> Any:
    """
    Resolve a single JSON:API resource identifier (`{"type": ..., "id": ...}`)
    against the included-lookup. Returns the fully flattened resource if it
    exists in `included`, otherwise just the id string (preserving the prior
    behavior so callers always get *something* useful).
    """
    if not isinstance(ref, dict) or "id" not in ref:
        return ref
    if included_lookup is not None:
        full = included_lookup.get((ref.get("type"), ref["id"]))
        if full is not None:
            return full
    return ref["id"]


def flatten_resource(
    resource: dict,
    included_lookup: IncludedLookup | None = None,
) -> dict:
    """
    Flatten a JSON:API resource object into a simple dict.

    Input:  {"type": "devices", "id": "...", "attributes": {"serial": "X"},
             "relationships": {"site": {"data": {"type": "sites", "id": "..."}}}}
    Output: {"id": "...", "type": "devices", "serial": "X", "site": "<id or nested dict>"}

    Relationships:
        - to-one with data == None       → None
        - to-one with data == {type, id} → resolved (full nested dict if found
                                            in `included_lookup`, else id)
        - to-many                        → list of the above
    """
    flat: dict = {
        "id": resource.get("id"),
        "type": resource.get("type"),
    }
    flat.update(resource.get("attributes", {}))

    for rel_name, rel_data in (resource.get("relationships") or {}).items():
        data = rel_data.get("data") if isinstance(rel_data, dict) else None
        if data is None:
            flat[rel_name] = None
        elif isinstance(data, list):
            flat[rel_name] = [_resolve_ref(d, included_lookup) for d in data]
        elif isinstance(data, dict):
            flat[rel_name] = _resolve_ref(data, included_lookup)

    return flat


def _build_included_lookup(included: list[dict]) -> IncludedLookup:
    """
    Build a `(type, id) -> flattened` lookup from a JSON:API `included` array.
    Included resources are flattened **without** further include resolution
    (one level deep) to keep payloads bounded and avoid cycles.
    """
    lookup: IncludedLookup = {}
    for raw in included:
        rtype, rid = raw.get("type"), raw.get("id")
        if rtype is None or rid is None:
            continue
        lookup[(rtype, rid)] = flatten_resource(raw, included_lookup=None)
    return lookup


def flatten_response(response: dict) -> dict:
    """
    Flatten a full JSON:API response.

    Returns:
        {"data": <flat resource | list[flat resource]>,
         "total": <int, if `meta.count` was present>,
         "has_next": <bool, true if `links.next` was present>}

    When the response includes an `included` array (because the request used
    `?include=...`), every relationship reference in `data` that points to a
    resource in `included` is replaced with the full nested flattened resource.
    """
    included = response.get("included") or []
    included_lookup = _build_included_lookup(included) if included else None

    data = response.get("data")
    if isinstance(data, list):
        items: Any = [flatten_resource(r, included_lookup) for r in data]
    elif isinstance(data, dict):
        items = flatten_resource(data, included_lookup)
    else:
        items = data

    result: dict = {"data": items}

    meta = response.get("meta") or {}
    if "count" in meta:
        result["total"] = meta["count"]

    links = response.get("links") or {}
    result["has_next"] = "next" in links

    return result
