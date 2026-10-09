from typer.testing import CliRunner

from multimodal_ai.main import app

runner = CliRunner()


def test_greet():
    result = runner.invoke(app, ["hello", "greet", "Ken"])
    assert result.exit_code == 0
    assert "Hello, Ken!" in result.stdout


def test_greet_shout():
    result = runner.invoke(app, ["hello", "greet", "Ken", "--shout"])
    assert result.exit_code == 0
    assert "HELLO, KEN!" in result.stdout


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"
