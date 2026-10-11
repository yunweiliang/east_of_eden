import json

import pytest
from cryptography.exceptions import InvalidTag

from eden.publish import lock, lock_json, unlock


def test_round_trip_and_gate_style_passcode_matching():
    data = lock("<h1>Yunwei</h1>", "  Open Sesame ")
    assert unlock(data, "open sesame") == "<h1>Yunwei</h1>"  # the gate trims and lowercases too


def test_wrong_passcode_is_rejected():
    with pytest.raises(InvalidTag):
        unlock(lock("secret page", "right"), "wrong")


def test_lock_json_has_the_fields_the_gate_reads():
    data = json.loads(lock_json(lock("x", "p")))
    assert set(data) == {"v", "iterations", "salt", "iv", "ct"} and data["iterations"] == 600_000


def test_each_lock_uses_fresh_salt_and_iv():
    a, b = lock("same", "p"), lock("same", "p")
    assert a["salt"] != b["salt"] and a["iv"] != b["iv"] and a["ct"] != b["ct"]


def test_preview_wraps_the_page_like_the_unlocked_site():
    from eden.publish import preview_page

    html = preview_page("<section class=\"home\"><h1>Yunwei</h1></section>", ":root { --bg: #fff; }")
    assert ":root { --bg: #fff; }" in html
    assert '<main id="main" class="page">\n<section class="home"><h1>Yunwei</h1></section>\n</main>' in html
