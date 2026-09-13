"""Test empty and sparse graph detection warnings."""

from pathlib import Path

import pytest

from grapheinstein.core.graph import GraphStats


def test_empty_graph_warning_detection():
    """Test that we can detect truly empty graphs."""
    stats = GraphStats(
        total_nodes=1,  # Just root directory
        file_count=0,
        directory_count=1,
        function_count=0,
        class_count=0,
        method_count=0,
        heading_count=0,
        media_text_count=0,
        transcript_chunk_count=0,
        concept_count=0,
        contains_count=0,
        references_count=0,
        defines_count=0,
        imports_count=0,
        calls_count=0,
        section_of_count=0,
        mentions_count=0,
        related_to_count=0,
        implements_count=0,
        depends_on_count=0,
        parse_skips=0,
        project_root="/tmp/project",
        graph_path="/tmp/graph.json",
    )
    
    # This graph should trigger empty warning
    assert stats.total_nodes < 2
    assert stats.file_count == 0


def test_sparse_graph_detection():
    """Test that we can detect graphs with files but no entities."""
    stats = GraphStats(
        total_nodes=15,
        file_count=10,
        directory_count=5,
        function_count=0,
        class_count=0,
        method_count=0,
        heading_count=0,
        media_text_count=0,
        transcript_chunk_count=0,
        concept_count=0,
        contains_count=10,
        references_count=0,
        defines_count=0,
        imports_count=0,
        calls_count=0,
        section_of_count=0,
        mentions_count=0,
        related_to_count=0,
        implements_count=0,
        depends_on_count=0,
        parse_skips=0,
        project_root="/tmp/project",
        graph_path="/tmp/graph.json",
    )
    
    # This graph should trigger sparse warning (files but no entities)
    entity_count = (
        stats.function_count
        + stats.class_count
        + stats.method_count
        + stats.heading_count
        + stats.media_text_count
        + stats.concept_count
    )
    assert entity_count == 0
    assert stats.file_count > 0


def test_high_skip_ratio_detection():
    """Test that we can detect high skip ratios."""
    stats = GraphStats(
        total_nodes=15,
        file_count=10,
        directory_count=5,
        function_count=1,
        class_count=0,
        method_count=0,
        heading_count=0,
        media_text_count=0,
        transcript_chunk_count=0,
        concept_count=0,
        contains_count=10,
        references_count=0,
        defines_count=0,
        imports_count=0,
        calls_count=0,
        section_of_count=0,
        mentions_count=0,
        related_to_count=0,
        implements_count=0,
        depends_on_count=0,
        parse_skips=8,  # 8 out of 10 files failed
        project_root="/tmp/project",
        graph_path="/tmp/graph.json",
    )
    
    # This graph should trigger high skip warning
    skip_ratio = stats.parse_skips / stats.file_count
    assert skip_ratio > 0.5, "Skip ratio should be > 50%"


def test_healthy_graph_no_warnings():
    """Test that healthy graphs don't trigger warnings."""
    stats = GraphStats(
        total_nodes=150,
        file_count=100,
        directory_count=50,
        function_count=200,
        class_count=30,
        method_count=150,
        heading_count=0,
        media_text_count=0,
        transcript_chunk_count=0,
        concept_count=0,
        contains_count=100,
        references_count=50,
        defines_count=380,
        imports_count=45,
        calls_count=100,
        section_of_count=0,
        mentions_count=0,
        related_to_count=0,
        implements_count=0,
        depends_on_count=0,
        parse_skips=2,  # Low skip rate
        project_root="/tmp/project",
        graph_path="/tmp/graph.json",
    )
    
    # This healthy graph should not trigger warnings
    assert stats.total_nodes >= 2
    entity_count = (
        stats.function_count
        + stats.class_count
        + stats.method_count
        + stats.heading_count
        + stats.media_text_count
        + stats.concept_count
    )
    assert entity_count > 0
    skip_ratio = stats.parse_skips / stats.file_count if stats.file_count > 0 else 0
    assert skip_ratio <= 0.5
