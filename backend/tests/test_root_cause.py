from app.root_cause import classify_root_cause, ROOT_CAUSE_CATEGORIES, CAUSE_KEYWORDS


def test_classifies_port_congestion():
    result = classify_root_cause("Delay caused by severe port congestion at the destination.")
    assert result == "Port / logistics congestion"


def test_classifies_customs():
    result = classify_root_cause("Shipment held up in customs pending documentation review.")
    assert result == "Customs / documentation"


def test_classifies_capacity_issues():
    result = classify_root_cause("Supplier's production line is at full capacity this month.")
    assert result == "Supplier capacity issues"


def test_classifies_quality_control():
    result = classify_root_cause("Incoming inspection found a defect in the batch.")
    assert result == "Quality control"


def test_returns_none_for_unmatched_text():
    result = classify_root_cause("The delivery truck had a flat tire on the highway.")
    assert result is None


def test_returns_none_for_empty_text():
    assert classify_root_cause("") is None
    assert classify_root_cause(None) is None


def test_never_auto_returns_other():
    # "Other" is reserved for explicit human judgment, never an automatic
    # keyword-matching fallback -- see the docstring for why.
    for text in ["completely unrelated text", "", "random reason not in any list"]:
        assert classify_root_cause(text) != "Other"


def test_is_case_insensitive():
    result = classify_root_cause("CUSTOMS DELAY DUE TO PAPERWORK")
    assert result == "Customs / documentation"


def test_all_keyword_categories_are_in_the_category_list():
    # Guards against the two lists silently drifting apart if someone
    # edits one without the other.
    for category in CAUSE_KEYWORDS:
        assert category in ROOT_CAUSE_CATEGORIES


def test_other_is_a_valid_category_but_has_no_keywords():
    assert "Other" in ROOT_CAUSE_CATEGORIES
    assert "Other" not in CAUSE_KEYWORDS
