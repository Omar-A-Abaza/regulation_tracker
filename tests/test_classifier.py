from processors.classifier import classify


def test_gpai():
    assert "gpai" in classify("Guidelines for providers of general-purpose AI models")


def test_several_categories():
    assert classify("Review of prohibited AI practices and high-risk systems in Annex III") == ["prohibited", "high_risk"]


def test_no_false_match_inside_words():
    # "define" should not count as "fine".
    assert "penalties" not in classify("Rules that define terms")


def test_fallback():
    assert classify("Correction to the EU AI Act (No. 4)") == ["other"]
