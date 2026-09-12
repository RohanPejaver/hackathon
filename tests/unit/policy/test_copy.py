"""Copy guard (product/02, 26): headline length and prohibited claim words."""

import ast
from pathlib import Path

from src.policy import copy as text
from tests.property.test_architecture import prohibited_copy

COPY = Path(__file__).resolve().parents[3] / "src" / "policy" / "copy.py"


def _words(headline: str) -> int:
    return sum(1 for token in headline.split() if any(ch.isalnum() for ch in token))


def test_every_headline_template_is_at_most_six_words() -> None:
    samples = [
        text.tier0_headline("PINE_NUT"),
        text.tier0_headline("UNKNOWN_ALLERGEN_PROFILE"),
        text.tier0_headline("SHELLFISH"),
        text.MULTI_HEADLINE,
        text.tier1_headline("spreader", "pesto"),
        text.tier1_headline("bin:mayo", "mayo"),
        text.tier2_headline("T48"),
        text.tier2_headline("T-2026-0912"),
    ]
    for headline in samples:
        assert _words(headline) <= 6, headline


def test_copy_module_has_no_prohibited_claim_words() -> None:
    for node in ast.walk(ast.parse(COPY.read_text())):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not prohibited_copy(node.value), node.value


def test_rendered_copy_has_no_prohibited_claim_words() -> None:
    rendered = [
        text.tier0_headline("PINE_NUT"),
        text.tier1_headline("spreader", "pesto"),
        text.tier2_headline("T48"),
        text.tier1_body("spreader", "pesto"),
        text.tier2_body("PINE_NUT", "spreader", "pesto", 91_000),
        text.LABEL_SEALED_BACKUP.format(container=text.container_display("bin:mayo")),
        text.NARRATIVE_ABSENCE.format(reset_kind="GLOVE_CHANGE", carrier="gloves"),
        text.NARRATIVE_PATHWAY_OPEN.format(path="a -> b", hops=1),
    ]
    for s in rendered:
        assert not prohibited_copy(s), s


def test_formatters() -> None:
    assert text.allergen_display("PINE_NUT") == "PINE NUT"
    assert text.container_display("bin:mayo") == "Mayo container"
    assert text.container_display("bin:cream_cheese") == "Cream Cheese container"
    assert text.offset(91_000) == "+1:31"
    assert text.offset(0) == "+0:00"
    assert text.duration(400_000) == "400s"
    assert text.tier2_body("PINE_NUT", "spreader", "pesto", 91_000) == (
        "PINE NUT. spreader contacted pesto at +1:31. Replacement not observed."
    )
