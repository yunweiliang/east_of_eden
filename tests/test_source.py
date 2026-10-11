from conftest import FIXTURES
from eden.source import load_book, normalize_for_match, roman_to_int


def test_splits_chapters_and_skips_table_of_contents():
    book = load_book(FIXTURES / "mini_book.txt")
    assert [c.number for c in book.chapters] == [1, 2, 3]
    assert book.chapter(1).text.startswith("The orchard")
    assert "SYNTHETIC" not in book.chapter(1).text


def test_roman_numerals():
    assert [roman_to_int(s) for s in ["iii", "iv", "ix", "xlv", "lv"]] == [3, 4, 9, 45, 55]


def test_quote_matching_ignores_curly_quotes_dashes_and_wrapping():
    book = load_book(FIXTURES / "mini_book.txt")
    assert normalize_for_match('The older one said, "We will water it every day."') in normalize_for_match(book.chapter(1).text)
    assert normalize_for_match("until the rains came - late,\n and heavy") in normalize_for_match(book.chapter(2).text)


def test_sha_is_stable():
    assert load_book(FIXTURES / "mini_book.txt").sha256 == load_book(FIXTURES / "mini_book.txt").sha256
