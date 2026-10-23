import dataclasses

import pytest

from hyprmonctl.model.identity import candidates, default_identifier, matches, resolve_rule
from hyprmonctl.model.layout import Rect, find_detached, find_overlaps, logical_size
from hyprmonctl.model.monitor import Mode, resolve_special_mode
from hyprmonctl.model.rule import MonitorRule, parse_position, parse_scale
from hyprmonctl.model.scale import is_valid_scale, nearest_valid_scale, nice_scales, valid_scales


def by_name(monitors, name):
    return next(m for m in monitors if m.name == name)


# --- monitors ------------------------------------------------------------------------


def test_monitor_info_from_hyprctl(monitors):
    edp, dp = by_name(monitors, "eDP-1"), by_name(monitors, "DP-1")
    assert edp.is_internal and not dp.is_internal
    assert dp.label == '27.2" DP-1 external display'
    assert edp.label == '14.0" laptop display'
    # hyprctl lists 1920x1080@100.00Hz twice; duplicates are dropped
    assert len(dp.available_modes) == len(set(dp.available_modes))
    assert dp.available_modes[0] == Mode(1920, 1080, 100.0)


def test_mode_parsing_and_special_modes(monitors):
    assert Mode.parse("1920x1080@59.94Hz") == Mode(1920, 1080, 59.94)
    assert Mode.parse("2560x1440") == Mode(2560, 1440, 0.0)
    assert Mode.parse("modeline 1 2 3") is None
    assert str(Mode(1920, 1080, 100.0)) == "1920x1080@100.00"
    dp = by_name(monitors, "DP-1")
    assert resolve_special_mode("highrr", dp.available_modes).refresh == 100.0
    assert resolve_special_mode("preferred", dp.available_modes) == Mode(1920, 1080, 100.0)


# --- identity ------------------------------------------------------------------------


def test_matching_semantics(monitors):
    dp = by_name(monitors, "DP-1")
    assert matches("DP-1", dp)
    assert matches("desc:Dell Inc. DELL P2725QE FKYZQB4", dp)
    assert matches("desc:Dell Inc. DELL P2725QE", dp)  # prefix
    assert not matches("desc:Dell Inc. DELL S3422DWG", dp)
    assert not matches("", dp)
    assert not matches("desc:", dp)


def test_last_matching_rule_wins_and_fallback(monitors):
    dp = by_name(monitors, "DP-1")
    rules = [MonitorRule(output=""), MonitorRule(output="DP-1"), MonitorRule(output="desc:Dell Inc.")]
    assert resolve_rule(rules, dp).index == 2
    assert resolve_rule(rules[:1], dp).fallback is True
    assert resolve_rule([], dp) is None


def test_default_identifier_ranking(monitors):
    edp, dp = by_name(monitors, "eDP-1"), by_name(monitors, "DP-1")
    assert default_identifier(dp, monitors) == "desc:Dell Inc. DELL P2725QE FKYZQB4"  # has serial
    assert default_identifier(edp, monitors) == "eDP-1"  # built-in panel, no serial
    external_no_serial = dataclasses.replace(dp, serial="", description="Dell Inc. DELL P2725QE")
    assert default_identifier(external_no_serial, [edp, external_no_serial]) == "desc:Dell Inc. DELL P2725QE"
    twin = dataclasses.replace(external_no_serial, name="DP-2", id=5)
    assert default_identifier(external_no_serial, [external_no_serial, twin]) == "DP-1"  # not unique


def test_candidates(monitors):
    dp = by_name(monitors, "DP-1")
    kinds = [(c.kind, c.value) for c in candidates(dp, monitors)]
    assert kinds == [
        ("descFull", "desc:Dell Inc. DELL P2725QE FKYZQB4"),
        ("descModel", "desc:Dell Inc. DELL P2725QE"),
        ("port", "DP-1"),
    ]
    edp = by_name(monitors, "eDP-1")
    assert [c.kind for c in candidates(edp, monitors)] == ["descFull", "port"]


# --- rules ---------------------------------------------------------------------------


def test_rule_value_parsing():
    assert parse_scale("1.2") == 1.2
    assert parse_scale(2) == 2.0
    assert parse_scale("auto") == "auto"
    assert parse_scale(True) is None
    assert parse_position("-3440x-440") == (-3440, -440)
    assert parse_position("auto-left") is None


# --- scale and layout ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("w", "h", "scale", "valid"),
    [(1920, 1200, 1.2, True), (1920, 1200, 1.4, False), (1920, 1080, 1.5, True), (3840, 2160, 4 / 3, True), (1920, 1080, 1.75, False)],
)
def test_scale_validity(w, h, scale, valid):
    assert is_valid_scale(w, h, scale) is valid


def test_scale_lists():
    assert 1.2 in valid_scales(1920, 1200)
    assert all(is_valid_scale(1920, 1080, s) for s in valid_scales(1920, 1080))
    assert nice_scales(1920, 1200) == [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.75, 4.0]
    assert nearest_valid_scale(1920, 1200, 1.4) in (1.375, 1.4166666666666667, 1.3333333333333333)


def test_logical_size_and_geometry():
    assert logical_size(1920, 1200, 1.2) == (1600, 1000)
    assert logical_size(3840, 2160, 2, transform=1) == (1080, 1920)
    rects = {"a": Rect(0, 0, 1600, 1000), "b": Rect(1600, 0, 1920, 1080), "c": Rect(5000, 0, 100, 100)}
    assert find_overlaps(rects) == []
    assert find_detached(rects) == ["c"]
    rects["b"] = Rect(1500, 0, 1920, 1080)
    assert find_overlaps(rects) == [("a", "b")]
    assert find_detached(rects) == ["c"]  # overlapping monitors aren't also "detached"
    assert Rect(0, 0, 10, 10).touches(Rect(0, 10, 10, 10))
    assert not Rect(0, 0, 10, 10).touches(Rect(10, 10, 10, 10))  # corner only
