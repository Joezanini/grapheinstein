from grapheinstein.core.path import (
    DEFAULT_CONFIDENCE,
    DEFAULT_CONFIDENCE_FLOOR,
    DEFAULT_INFERRED_FACTOR,
    edge_cost,
)


def test_extracted_cheaper_than_inferred_same_type_and_confidence():
    extracted = edge_cost(
        {"type": "calls", "provenance": "extracted", "confidence": 0.8}
    )
    inferred = edge_cost(
        {"type": "calls", "provenance": "inferred", "confidence": 0.8}
    )
    assert extracted < inferred
    assert inferred == extracted * DEFAULT_INFERRED_FACTOR


def test_higher_confidence_cheaper():
    high = edge_cost({"type": "calls", "provenance": "extracted", "confidence": 0.9})
    low = edge_cost({"type": "calls", "provenance": "extracted", "confidence": 0.4})
    assert high < low


def test_missing_confidence_uses_default_then_floor():
    missing = edge_cost({"type": "calls", "provenance": "extracted"})
    expected_conf = max(DEFAULT_CONFIDENCE, DEFAULT_CONFIDENCE_FLOOR)
    expected = 1.0 * 1.0 / expected_conf
    assert abs(missing - expected) < 1e-9


def test_contains_costlier_than_calls():
    contains = edge_cost(
        {"type": "contains", "provenance": "extracted", "confidence": 0.9}
    )
    calls = edge_cost({"type": "calls", "provenance": "extracted", "confidence": 0.9})
    assert contains > calls
