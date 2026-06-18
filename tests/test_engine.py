"""Tests for indicator normalization."""

import pytest
from malrt.core.engine import normalize_indicator
from malrt.core.models import IndicatorType


def test_detects_url():
    ind = normalize_indicator("https://evil.com/malware")
    assert ind.type == IndicatorType.url
    assert ind.value == "https://evil.com/malware"


def test_strips_trailing_slash():
    ind = normalize_indicator("https://evil.com/path/")
    assert ind.value == "https://evil.com/path"


def test_detects_ipv4():
    ind = normalize_indicator("192.168.1.1")
    assert ind.type == IndicatorType.ip
    assert ind.value == "192.168.1.1"


def test_detects_md5():
    ind = normalize_indicator("d41d8cd98f00b204e9800998ecf8427e")
    assert ind.type == IndicatorType.hash
    assert ind.value == "D41D8CD98F00B204E9800998ECF8427E"


def test_detects_sha256():
    h = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ind = normalize_indicator(h)
    assert ind.type == IndicatorType.hash
    assert ind.value == h.upper()


def test_detects_domain():
    ind = normalize_indicator("evil.com")
    assert ind.type == IndicatorType.domain
    assert ind.value == "evil.com"


def test_domain_lowercased():
    ind = normalize_indicator("EVIL.COM")
    assert ind.value == "evil.com"


def test_strips_whitespace():
    ind = normalize_indicator("  https://evil.com  ")
    assert ind.type == IndicatorType.url
    assert ind.value == "https://evil.com"
