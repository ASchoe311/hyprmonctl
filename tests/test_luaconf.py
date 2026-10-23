from hyprmonctl.luaconf.discovery import default_lua_path, is_required, module_name
from hyprmonctl.luaconf.lexer import Tok, tokenize
from hyprmonctl.luaconf.parser import parse_source
from hyprmonctl.luaconf.writer import render_call, render_file, render_rule, write_atomic
from hyprmonctl.model.rule import LuaRaw, LuaTable, MonitorRule


def test_parses_users_file(user_lua):
    parsed = parse_source(user_lua)
    assert parsed.error is None
    assert parsed.foreign_lines == []
    assert [r.output for r in parsed.rules] == ["eDP-1", "desc:Dell Inc. DELL S3422DWG 75Q50M3"]
    edp = parsed.rules[0]
    assert (edp.mode, edp.position, edp.scale) == ("preferred", "auto", "1.2")  # scale given as a string


def test_lexer_handles_comments_and_strings():
    tokens = tokenize('--[==[ block ]==] x = "a\\"b" -- tail\n y = [[long\nstr]] z = 0x10 w = 1e2')
    values = [t.value for t in tokens if t.kind is not Tok.EOF]
    assert values == ["x", "=", 'a"b', "y", "=", "long\nstr", "z", "=", 16, "w", "=", 100.0]


def test_parses_call_sugar_nested_tables_and_raw_values():
    parsed = parse_source(
        """
        local s = 1.5
        hl.monitor{ output = "DP-2", scale = s * 2, reserved_area = { top = 10, bottom = 0 }, transform = -1 }
        hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })
        """
    )
    assert parsed.error is None
    assert parsed.foreign_lines == [2]
    dp2, fallback = parsed.rules
    assert dp2.scale == LuaRaw("s * 2")
    assert dp2.transform == -1
    assert dp2.extra == {"reserved_area": LuaTable([("top", 10), ("bottom", 0)])}
    assert fallback.is_fallback


def test_nested_monitor_calls_are_foreign():
    parsed = parse_source('if x then\n  hl.monitor({ output = "DP-1" })\nend\nhl.monitor({ output = "DP-2" })')
    assert [r.output for r in parsed.rules] == ["DP-2"]
    assert parsed.foreign_lines == [1]


def test_syntax_error_is_reported():
    parsed = parse_source('hl.monitor({ output = "DP-1" ')
    assert parsed.error is not None and parsed.rules == []


def test_render_roundtrip_preserves_values():
    rule = MonitorRule(
        output="desc:Dell Inc. \"Quoted\"",
        mode="1920x1080@100.00",
        position="-1920x0",
        scale=4 / 3,
        transform=1,
        extra={"reserved_area": LuaTable([("top", 10)]), "icc": LuaRaw('HOME .. "/x.icc"')},
    )
    text = render_file([rule])
    parsed = parse_source(text)
    assert parsed.error is None and parsed.foreign_lines == []
    (back,) = parsed.rules
    assert back.output == rule.output
    assert back.scale == 1.333333
    assert back.extra["icc"] == LuaRaw('HOME .. "/x.icc"')
    assert back.extra["reserved_area"] == LuaTable([("top", 10)])


def test_render_rule_style_matches_hand_written_files():
    rule = MonitorRule(output="eDP-1", mode="preferred", position="auto", scale=1.2)
    assert render_rule(rule) == (
        'hl.monitor({\n    output   = "eDP-1",\n    mode     = "preferred",\n'
        '    position = "auto",\n    scale    = 1.2,\n})\n'
    )
    assert render_call(rule) == 'hl.monitor({ output = "eDP-1", mode = "preferred", position = "auto", scale = 1.2 })'


def test_write_atomic_keeps_backup(tmp_path):
    target = tmp_path / "monitors.lua"
    target.write_text("old")
    backup = write_atomic(target, "new")
    assert target.read_text() == "new"
    assert backup is not None and backup.read_text() == "old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["monitors.lua", "monitors.lua.bak"]


def test_discovery(tmp_path):
    main = tmp_path / "hyprland.lua"
    main.write_text('require("hyprland.general")\nif x then require("config.monitors") end\n')
    assert default_lua_path(main) == tmp_path / "config" / "monitors.lua"
    assert is_required(tmp_path / "config" / "monitors.lua", main) is True
    assert is_required(tmp_path / "other.lua", main) is False
    assert module_name(tmp_path / "config" / "monitors.lua", tmp_path) == "config.monitors"
    assert is_required(tmp_path / "x.lua", tmp_path / "missing.lua") is None


def test_discovery_default_without_monitor_module(tmp_path):
    main = tmp_path / "hyprland.lua"
    main.write_text('require("general")\n')
    assert default_lua_path(main) == tmp_path / "monitors.lua"
