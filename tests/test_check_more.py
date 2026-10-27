"""More tests for ra.check: test_check.py holds the first ones and is at the 400-line limit.

DECISION_EDITED, the rule that reads git history, is tested in test_check_decisions.py.
"""

import pytest
from conftest import _lit
from ra.check import run_checks

# --- DUP_LITERATURE ----------------------------------------------------------------------


@pytest.mark.parametrize(("key", "value"), [("doi", "—"), ("arxiv", "n/a")])
def test_placeholder_ids_are_not_duplicates(repo, make_pdf, key, value):
    _lit(repo, make_pdf, "a2024-x", **{key: value})
    _lit(repo, make_pdf, "b2024-y", **{key: value})
    assert run_checks(repo) == []
