"""Tests for connhex_mcp.utils.jsonapi.build_filter_params."""

from connhex_sdk.resources.jsonapi import build_filter_params


def test_empty_filter_returns_empty_dict():
    assert build_filter_params(None) == {}
    assert build_filter_params({}) == {}


def test_implicit_match_scalar():
    assert build_filter_params({"serial": "ABC"}) == {"filter[serial]": "ABC"}


def test_explicit_match_operator():
    assert build_filter_params({"serial": {"match": "ABC"}}) == {
        "filter[serial][match]": "ABC"
    }


def test_fuzzy_match():
    assert build_filter_params({"serial": {"fuzzy-match": "ABC"}}) == {
        "filter[serial][fuzzy-match]": "ABC"
    }


def test_multiple_values_via_list_join_with_comma():
    assert build_filter_params({"serial": ["A", "B", "C"]}) == {
        "filter[serial]": "A,B,C"
    }


def test_min_max_range_emits_both_keys():
    out = build_filter_params(
        {"createdAt": {"min": "2024-01-01", "max": "2024-12-31"}}
    )
    assert out == {
        "filter[createdAt][min]": "2024-01-01",
        "filter[createdAt][max]": "2024-12-31",
    }


def test_exists_true_serializes_to_lowercase_string():
    assert build_filter_params({"site": {"exists": True}}) == {
        "filter[site][exists]": "true"
    }


def test_exists_false_serializes_to_lowercase_string():
    assert build_filter_params({"site": {"exists": False}}) == {
        "filter[site][exists]": "false"
    }


def test_object_property_dot_syntax_passes_through():
    assert build_filter_params({"address.city": "Milan"}) == {
        "filter[address.city]": "Milan"
    }


def test_related_resource_colon_syntax_passes_through():
    assert build_filter_params({"site:name": {"fuzzy-match": "Plant"}}) == {
        "filter[site:name][fuzzy-match]": "Plant"
    }


def test_and_combinator_multiple_fields():
    out = build_filter_params({"and": {"serial": "X", "name": "Y"}})
    assert out == {
        "filter[and][serial]": "X",
        "filter[and][name]": "Y",
    }


def test_or_combinator_multiple_fields_with_operators():
    out = build_filter_params(
        {
            "or": {
                "name": {"fuzzy-match": "x"},
                "serial": {"fuzzy-match": "x"},
            }
        }
    )
    assert out == {
        "filter[or][name][fuzzy-match]": "x",
        "filter[or][serial][fuzzy-match]": "x",
    }


def test_real_world_payload_matches_user_example():
    """
    Reproduces the exact filter set from the URL the user pasted:
    filter[or][site:name][fuzzy-match]=10
    filter[or][serial][fuzzy-match]=10
    filter[or][name][fuzzy-match]=10
    """
    out = build_filter_params(
        {
            "or": {
                "site:name": {"fuzzy-match": "10"},
                "serial": {"fuzzy-match": "10"},
                "name": {"fuzzy-match": "10"},
            }
        }
    )
    assert out == {
        "filter[or][site:name][fuzzy-match]": "10",
        "filter[or][serial][fuzzy-match]": "10",
        "filter[or][name][fuzzy-match]": "10",
    }


def test_integer_values_serialized_as_strings():
    assert build_filter_params({"port": 8080}) == {"filter[port]": "8080"}


def test_bool_in_list_does_not_become_int():
    """Edge case: bool is a subclass of int — make sure list values respect bool branch."""
    assert build_filter_params({"flags": [True, False]}) == {
        "filter[flags]": "true,false"
    }
