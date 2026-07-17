from grapheinstein.core.parsers.media_av import Segment, merge_segments


def test_merge_segments_short_stays_one():
    segs = [Segment(0.0, 1.0, "hello"), Segment(1.0, 2.0, "world")]
    merged = merge_segments(segs)
    assert len(merged) == 1
    assert "hello" in merged[0].text and "world" in merged[0].text


def test_merge_segments_splits_on_char_threshold():
    # Force multiple chunks with long text
    long_a = "word " * 100  # > 400 chars when combined carefully
    segs = [
        Segment(0.0, 5.0, long_a.strip()),
        Segment(5.0, 10.0, long_a.strip()),
        Segment(10.0, 12.0, "tail"),
    ]
    merged = merge_segments(segs)
    assert len(merged) >= 2
    assert merged[0].start == 0.0


def test_merge_drops_empty():
    assert merge_segments([Segment(0.0, 1.0, "  "), Segment(1.0, 2.0, "ok")])[0].text == "ok"
