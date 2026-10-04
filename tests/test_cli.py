from wowforever.__main__ import main


def test_cli_without_command_prints_help(capsys):
    assert main([]) == 0
    assert "usage: wowforever" in capsys.readouterr().out
