import dataclasses

from hyprmonctl.luaconf.parser import parse_source
from hyprmonctl.model import draft as drafts
from hyprmonctl.model.rule import LuaTable, MonitorRule
from hyprmonctl.model.state import Draft, MonitorConfig


def configs_by_name(configs):
    return {c.name: c for c in configs}


def test_initial_configs_from_users_file(monitors, user_lua):
    rules = parse_source(user_lua).rules
    configs = configs_by_name(drafts.initial_configs(monitors, rules))
    edp, dp = configs["eDP-1"], configs["DP-1"]
    assert (edp.output, edp.scale, edp.rule_index) == ("eDP-1", 1.2, 0)
    # No rule matches DP-1: mode/position follow Hyprland's defaults, scale is what's on screen.
    assert (dp.output, dp.mode, dp.position, dp.scale, dp.rule_index) == (
        "desc:Dell Inc. DELL P2725QE FKYZQB4",
        "preferred",
        "auto",
        1.0,
        None,
    )
    assert drafts.owned_rule_indices(monitors, rules) == {0: "eDP-1"}


def test_fallback_and_shared_rules_fork_identifiers(monitors):
    shared = [MonitorRule(output="", scale=2.0, extra={"reserved_area": 5})]
    configs = configs_by_name(drafts.initial_configs(monitors, shared))
    assert configs["DP-1"].output == "desc:Dell Inc. DELL P2725QE FKYZQB4"
    assert configs["DP-1"].scale == 2.0 and configs["DP-1"].rule_index == 0
    rule = drafts.config_to_rule(configs["DP-1"], shared[0])
    assert rule.extra == {"reserved_area": 5}  # inherited from the fallback it derived from


def test_build_rules_orders_and_preserves(monitors, user_lua):
    rules = parse_source(user_lua).rules + [MonitorRule(output="", mode="preferred")]
    configs = drafts.initial_configs(monitors, rules)
    built = drafts.build_rules(Draft(configs, keep_rules=[1, 2]), rules)
    assert [r.output for r in built] == [
        "",
        "desc:Dell Inc. DELL S3422DWG 75Q50M3",
        "eDP-1",
        "desc:Dell Inc. DELL P2725QE FKYZQB4",
    ]
    assert built[1] is rules[1]  # kept rules are written back untouched
    dropped = drafts.build_rules(Draft(configs, keep_rules=[]), rules)
    assert [r.output for r in dropped] == ["eDP-1", "desc:Dell Inc. DELL P2725QE FKYZQB4"]


def test_config_to_rule_keeps_extras_and_disables():
    base = MonitorRule(output="DP-1", transform=0, extra={"reserved_area": LuaTable([("top", 4)])})
    config = MonitorConfig(name="DP-1", output="DP-1", enabled=False, scale=1.5)
    rule = drafts.config_to_rule(config, base)
    assert rule.disabled is True
    assert rule.transform == 0  # base declared it, so it stays explicit
    assert rule.extra == base.extra
    assert drafts.config_to_rule(config, None).transform is None


def test_changed_configs(monitors, user_lua):
    rules = parse_source(user_lua).rules
    configs = drafts.initial_configs(monitors, rules)
    assert drafts.changed_configs(Draft(configs), monitors, rules) == []
    configs[1] = dataclasses.replace(configs[1], position="-1920x0")
    assert [c.name for c in drafts.changed_configs(Draft(configs), monitors, rules)] == ["DP-1"]


def test_restore_rules_redeclare_preview_outputs(monitors, user_lua):
    rules = parse_source(user_lua).rules
    outputs = {"eDP-1": {"eDP-1"}, "DP-1": {"DP-1", "desc:Dell Inc. DELL P2725QE"}}
    restored = drafts.restore_rules(outputs, monitors, rules)
    assert [(r.output, r.scale) for r in restored] == [
        ("eDP-1", "1.2"),
        ("DP-1", 1.0),  # DP-1 had no rule: Hyprland's defaults
        ("desc:Dell Inc. DELL P2725QE", 1.0),
    ]


def test_restore_rules_pin_to_state_before_preview(monitors, user_lua):
    # A monitor with no rule can show a scale that "auto" would not reproduce (Hyprland
    # gives headless outputs scale 1 by default but 2 under "auto"): restore what was shown.
    rules = parse_source(user_lua).rules
    before = {m.name: dataclasses.replace(m, scale=1.5, x=1600, y=-200) for m in monitors}
    (rule,) = drafts.restore_rules({"DP-1": {"DP-1"}}, monitors, rules, before)
    assert (rule.output, rule.mode, rule.position, rule.scale, rule.transform) == ("DP-1", "1920x1080@100.00", "1600x-200", 1.5, 0)
    (edp,) = drafts.restore_rules({"eDP-1": {"eDP-1"}}, monitors, rules, before)
    assert edp.position == "1600x-200" and edp.scale == 1.5


def test_validate_current_layout_is_clean(monitors, user_lua):
    configs = drafts.initial_configs(monitors, parse_source(user_lua).rules)
    result = drafts.validate(Draft(configs), monitors)
    assert result.issues == []
    placements = {p.name: (p.x, p.y, p.width, p.height) for p in result.placements}
    assert placements == {"eDP-1": (0, 0, 1600, 1000), "DP-1": (1600, 0, 1920, 1080)}


def test_validate_reports_problems(monitors, user_lua):
    configs = configs_by_name(drafts.initial_configs(monitors, parse_source(user_lua).rules))
    bad = Draft(
        [
            dataclasses.replace(configs["eDP-1"], scale=1.4),
            dataclasses.replace(configs["DP-1"], position="1000x0", output="desc:Samsung"),
        ]
    )
    codes = {i.code for i in drafts.validate(bad, monitors).issues}
    assert {"invalid-scale", "overlap", "output-mismatch"} <= codes

    detached = Draft([configs["eDP-1"], dataclasses.replace(configs["DP-1"], position="4000x0")])
    assert {i.code for i in drafts.validate(detached, monitors).issues} == {"detached"}

    duplicate = Draft([configs["eDP-1"], dataclasses.replace(configs["DP-1"], output="eDP-1")])
    assert "duplicate-output" in {i.code for i in drafts.validate(duplicate, monitors).issues}

    none_enabled = Draft([dataclasses.replace(c, enabled=False) for c in configs.values()])
    assert "all-disabled" in {i.code for i in drafts.validate(none_enabled, monitors).issues}


def test_live_configs_capture_layout(monitors, user_lua):
    configs = configs_by_name(drafts.live_configs(monitors, parse_source(user_lua).rules))
    assert (configs["DP-1"].mode, configs["DP-1"].position, configs["DP-1"].scale) == ("1920x1080@100.00", "1600x0", 1.0)
    assert configs["eDP-1"].output == "eDP-1"
