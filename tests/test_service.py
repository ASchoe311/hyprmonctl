import dataclasses

import pytest

from hyprmonctl.luaconf.parser import parse_source
from hyprmonctl.model.state import Draft
from hyprmonctl.service import ConflictError, InvalidDraftError, NoPreviewError


def current_draft(env) -> Draft:
    state = env.service.state()
    return Draft([m.config for m in state.monitors], [r.index for r in state.saved_rules], state.file_hash)


def moved(draft: Draft, name: str, position: str) -> Draft:
    monitors = [dataclasses.replace(c, position=position) if c.name == name else c for c in draft.monitors]
    return dataclasses.replace(draft, monitors=monitors)


def test_state_summarizes_file_and_monitors(env):
    state = env.service.state()
    assert [m.name for m in state.monitors] == ["eDP-1", "DP-1"]
    assert [(r.index, r.status) for r in state.saved_rules] == [(1, "disconnected")]
    assert state.diagnostics == []
    assert state.lua_module == "config.monitors"
    assert state.file_hash


def test_state_diagnostics(env):
    env.lua_path.write_text('local x = 1\nhl.monitor({ output = "eDP-1", scale = x })\n')
    env.main_config.write_text("-- nothing required\n")
    codes = {d.code for d in env.service.state().diagnostics}
    assert codes == {"foreign-code", "raw-values", "not-loaded"}
    env.lua_path.unlink()
    assert "file-missing" in {d.code for d in env.service.state().diagnostics}


def test_preview_only_applies_changes_and_reverts_on_timeout(env):
    draft = moved(current_draft(env), "DP-1", "-1920x0")
    info = env.service.preview(draft)
    assert info.timeout == 15 and info.deadline == env.clock.now + 15
    assert env.compositor.evals == [
        'hl.monitor({ output = "desc:Dell Inc. DELL P2725QE FKYZQB4", mode = "preferred", position = "-1920x0", scale = 1 })'
    ]
    assert env.events[-1][0] == "preview.started"

    env.clock.now += 15
    env.timers[-1].fire()
    # Restored to exactly what was on screen before the preview.
    assert env.compositor.evals[-1] == (
        'hl.monitor({ output = "desc:Dell Inc. DELL P2725QE FKYZQB4", mode = "1920x1080@100.00", position = "1600x0", scale = 1, transform = 0 })'
    )
    assert env.events[-1] == ("preview.reverted", {"reason": "timeout", "error": None})
    assert env.service.state().preview is None


def test_confirm_writes_file_with_backup_and_reloads(env):
    original = env.lua_path.read_text()
    env.service.preview(moved(current_draft(env), "DP-1", "-1920x0"))
    result = env.service.confirm()
    assert env.compositor.reloads == 1
    assert env.timers[-1].cancelled
    assert (env.lua_path.parent / "monitors.lua.bak").read_text() == original
    rules = parse_source(env.lua_path.read_text()).rules
    assert [(r.output, r.position) for r in rules] == [
        ("desc:Dell Inc. DELL S3422DWG 75Q50M3", "-3440x-440"),
        ("eDP-1", "auto"),
        ("desc:Dell Inc. DELL P2725QE FKYZQB4", "-1920x0"),
    ]
    assert result.backup_path.endswith("monitors.lua.bak")
    with pytest.raises(NoPreviewError):
        env.service.confirm()


def test_user_revert_and_stacked_previews(env):
    base = current_draft(env)
    env.service.preview(moved(base, "DP-1", "-1920x0"))
    # Second preview puts DP-1 back where the file has it: it must still be re-applied.
    env.service.preview(moved(base, "eDP-1", "1600x1080"))
    assert 'output = "desc:Dell Inc. DELL P2725QE FKYZQB4", mode = "preferred", position = "auto", scale = 1' in env.compositor.evals[-1]
    assert 'output = "eDP-1", mode = "preferred", position = "1600x1080"' in env.compositor.evals[-1]
    assert env.timers[0].cancelled
    assert env.service.revert() is True
    assert env.events[-1][1]["reason"] == "user"
    assert env.service.revert() is False


def test_preview_rejects_invalid_drafts_and_conflicts(env):
    with pytest.raises(InvalidDraftError):
        env.service.preview(moved(current_draft(env), "DP-1", "100x0"))  # overlaps eDP-1
    draft = current_draft(env)
    env.lua_path.write_text(env.lua_path.read_text() + "\n-- edited elsewhere\n")
    with pytest.raises(ConflictError):
        env.service.preview(draft)
    assert env.compositor.evals == []


def test_failed_eval_restores(env):
    env.compositor.fail_eval = True
    with pytest.raises(Exception):
        env.service.preview(moved(current_draft(env), "DP-1", "-1920x0"))
    assert env.service.state().preview is None


def test_close_reverts_pending_preview(env):
    env.service.preview(moved(current_draft(env), "DP-1", "-1920x0"))
    env.service.close()
    assert env.events[-1][1]["reason"] == "closed"


def test_save_skips_reload_when_file_is_not_loaded(env):
    env.main_config.write_text("-- monitors live elsewhere\n")
    env.service.save(current_draft(env))
    assert env.compositor.reloads == 0


def test_render_live_and_settings(env):
    lua = env.service.render_live()
    assert 'position = "1600x0"' in lua and "S3422DWG" in lua
    settings = env.service.update_settings({"confirmTimeout": 30})
    assert settings.confirm_timeout == 30
    with pytest.raises(ValueError):
        env.service.update_settings({"confirmTimeout": 1})
    with pytest.raises(ValueError):
        env.service.update_settings({"bogus": 1})
