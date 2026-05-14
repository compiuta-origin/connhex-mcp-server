"""Tests for connhex_mcp.utils.jsonapi flattening helpers."""

from connhex.resources.jsonapi import flatten_resource, flatten_response

# ---------------------------------------------------------------------------
# flatten_resource
# ---------------------------------------------------------------------------


def test_flatten_resource_attributes_only():
    raw = {
        "type": "devices",
        "id": "abc",
        "attributes": {"serial": "X", "name": "thing"},
    }
    assert flatten_resource(raw) == {
        "id": "abc",
        "type": "devices",
        "serial": "X",
        "name": "thing",
    }


def test_flatten_resource_handles_missing_relationships_block():
    raw = {"type": "devices", "id": "abc", "attributes": {}}
    out = flatten_resource(raw)
    assert out == {"id": "abc", "type": "devices"}


def test_flatten_resource_to_one_relationship_without_lookup_returns_id():
    raw = {
        "type": "devices",
        "id": "abc",
        "attributes": {},
        "relationships": {
            "site": {
                "data": {"type": "sites", "id": "site-1"},
            }
        },
    }
    assert flatten_resource(raw)["site"] == "site-1"


def test_flatten_resource_to_many_relationship_without_lookup_returns_ids():
    raw = {
        "type": "devices",
        "id": "abc",
        "attributes": {},
        "relationships": {
            "tags": {
                "data": [
                    {"type": "tags", "id": "t1"},
                    {"type": "tags", "id": "t2"},
                ]
            }
        },
    }
    assert flatten_resource(raw)["tags"] == ["t1", "t2"]


def test_flatten_resource_null_to_one_relationship():
    raw = {
        "type": "devices",
        "id": "abc",
        "attributes": {},
        "relationships": {"site": {"data": None}},
    }
    assert flatten_resource(raw)["site"] is None


def test_flatten_resource_empty_to_many_relationship():
    raw = {
        "type": "devices",
        "id": "abc",
        "attributes": {},
        "relationships": {"tags": {"data": []}},
    }
    assert flatten_resource(raw)["tags"] == []


# ---------------------------------------------------------------------------
# flatten_response — basic shape, meta, pagination
# ---------------------------------------------------------------------------


def test_flatten_response_list_with_count_and_no_next():
    resp = {
        "data": [
            {"type": "devices", "id": "1", "attributes": {"serial": "A"}},
            {"type": "devices", "id": "2", "attributes": {"serial": "B"}},
        ],
        "meta": {"count": 2},
        "links": {"self": "..."},
    }
    out = flatten_response(resp)
    assert out["total"] == 2
    assert out["has_next"] is False
    assert [d["serial"] for d in out["data"]] == ["A", "B"]


def test_flatten_response_has_next_true_when_links_next_present():
    resp = {
        "data": [],
        "meta": {"count": 0},
        "links": {"self": "...", "next": "..."},
    }
    assert flatten_response(resp)["has_next"] is True


def test_flatten_response_single_resource():
    resp = {
        "data": {"type": "devices", "id": "1", "attributes": {"serial": "A"}},
    }
    out = flatten_response(resp)
    assert isinstance(out["data"], dict)
    assert out["data"]["serial"] == "A"
    assert "total" not in out


# ---------------------------------------------------------------------------
# flatten_response — `included` resolution
# ---------------------------------------------------------------------------


def test_flatten_response_resolves_included_to_one():
    resp = {
        "data": [
            {
                "type": "devices",
                "id": "d1",
                "attributes": {"serial": "A"},
                "relationships": {
                    "site": {"data": {"type": "sites", "id": "s1"}},
                },
            }
        ],
        "included": [
            {
                "type": "sites",
                "id": "s1",
                "attributes": {"name": "Plant 1"},
            }
        ],
    }
    out = flatten_response(resp)
    site = out["data"][0]["site"]
    assert isinstance(site, dict)
    assert site["id"] == "s1"
    assert site["type"] == "sites"
    assert site["name"] == "Plant 1"


def test_flatten_response_resolves_included_to_many():
    resp = {
        "data": [
            {
                "type": "devices",
                "id": "d1",
                "attributes": {},
                "relationships": {
                    "tags": {
                        "data": [
                            {"type": "tags", "id": "t1"},
                            {"type": "tags", "id": "t2"},
                        ]
                    }
                },
            }
        ],
        "included": [
            {"type": "tags", "id": "t1", "attributes": {"label": "alpha"}},
            {"type": "tags", "id": "t2", "attributes": {"label": "beta"}},
        ],
    }
    tags = flatten_response(resp)["data"][0]["tags"]
    assert [t["label"] for t in tags] == ["alpha", "beta"]


def test_flatten_response_unresolved_reference_falls_back_to_id():
    """A relationship that points to a resource NOT in `included` keeps its id."""
    resp = {
        "data": [
            {
                "type": "devices",
                "id": "d1",
                "attributes": {},
                "relationships": {
                    "site": {"data": {"type": "sites", "id": "missing"}},
                    "tags": {
                        "data": [
                            {"type": "tags", "id": "t1"},
                            {"type": "tags", "id": "missing-tag"},
                        ]
                    },
                },
            }
        ],
        "included": [
            {"type": "tags", "id": "t1", "attributes": {"label": "alpha"}},
        ],
    }
    row = flatten_response(resp)["data"][0]
    assert row["site"] == "missing"
    assert row["tags"][0]["label"] == "alpha"
    assert row["tags"][1] == "missing-tag"


def test_flatten_response_included_resources_keep_their_relationships_as_ids():
    """One-level resolution: included resources are NOT recursively expanded."""
    resp = {
        "data": [
            {
                "type": "devices",
                "id": "d1",
                "attributes": {},
                "relationships": {
                    "site": {"data": {"type": "sites", "id": "s1"}},
                },
            }
        ],
        "included": [
            {
                "type": "sites",
                "id": "s1",
                "attributes": {"name": "Plant 1"},
                "relationships": {
                    "owner": {"data": {"type": "orgs", "id": "o1"}},
                },
            },
            # `orgs/o1` is also in `included`, but the site's `owner` should
            # still be returned as the bare id since we only resolve one level.
            {"type": "orgs", "id": "o1", "attributes": {"name": "Acme"}},
        ],
    }
    site = flatten_response(resp)["data"][0]["site"]
    assert site["name"] == "Plant 1"
    assert site["owner"] == "o1"


# ---------------------------------------------------------------------------
# Real-world payload (the example the user pasted)
# ---------------------------------------------------------------------------


def test_flatten_response_against_real_devices_payload():
    """End-to-end against the actual payload shape from /resources/devices."""
    resp = {
        "jsonapi": {"version": "1.0"},
        "meta": {"count": 2},
        "links": {"self": "resources/devices?..."},
        "data": [
            {
                "type": "devices",
                "id": "35bc8632-11e0-416f-99cf-94a15bdf9bb1",
                "attributes": {
                    "connhex-id": "6bd2e843-9fe2-454e-8d31-06b962943a4c",
                    "name": "PEC-EM3-100A_1",
                    "serial": "002402554",
                    "tenants": [],
                },
                "relationships": {
                    "family": {
                        "data": {
                            "type": "device-families",
                            "id": "cf8dc2eb-d720-4e60-93ae-ce4341f17b57",
                        }
                    },
                    "site": {"data": None},
                    "favourite-variables": {"data": []},
                    "tags": {"data": []},
                },
            },
            {
                "type": "devices",
                "id": "61641cfb-d0cb-417a-9c4e-d29020302d62",
                "attributes": {
                    "connhex-id": "b2003918-d83d-4fd1-a2ca-ac83396e14fd",
                    "name": "test",
                    "serial": "100000009d0e53d7",
                    "tenants": [],
                },
                "relationships": {
                    "family": {
                        "data": {
                            "type": "device-families",
                            "id": "cf8dc2eb-d720-4e60-93ae-ce4341f17b57",
                        }
                    },
                    "site": {
                        "data": {
                            "type": "sites",
                            "id": "023edab3-e3d8-4f01-97ad-cade864eb505",
                        }
                    },
                    "favourite-variables": {"data": []},
                    "tags": {"data": []},
                },
            },
        ],
    }
    out = flatten_response(resp)
    assert out["total"] == 2
    assert out["has_next"] is False
    assert len(out["data"]) == 2

    first, second = out["data"]
    assert first["serial"] == "002402554"
    assert first["connhex-id"] == "6bd2e843-9fe2-454e-8d31-06b962943a4c"
    assert first["site"] is None
    assert first["tags"] == []
    assert first["family"] == "cf8dc2eb-d720-4e60-93ae-ce4341f17b57"

    assert second["site"] == "023edab3-e3d8-4f01-97ad-cade864eb505"
