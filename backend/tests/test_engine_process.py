"""Tests for the OpenCode process manager."""

from __future__ import annotations

from opensec.engine.process import OpenCodeProcess


def test_is_running_false_initially():
    proc = OpenCodeProcess()
    assert proc.is_running is False


def test_is_healthy_false_initially():
    proc = OpenCodeProcess()
    assert proc.is_healthy is False
