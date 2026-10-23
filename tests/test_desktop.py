from hyprmonctl import desktop


def test_install_writes_entry_matching_app_id(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(desktop, "launch_command", lambda: "/opt/bin/hyprmonctl gui")
    path = desktop.install()
    assert path == tmp_path / "applications" / "hyprmonctl.desktop"
    text = path.read_text()
    assert "Exec=/opt/bin/hyprmonctl gui\n" in text
    assert f"StartupWMClass={desktop.APP_ID}\n" in text  # matches the Wayland app id the GUI sets
