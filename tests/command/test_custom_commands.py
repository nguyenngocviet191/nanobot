import pytest
from pathlib import Path
from nanobot.command.custom_commands import CustomCommandsLoader


@pytest.fixture
def commands_dir(tmp_path):
    """Create a commands directory in tmp_path."""
    cmd_dir = tmp_path / "commands"
    cmd_dir.mkdir()
    return cmd_dir


def test_load_command_from_file(commands_dir):
    # Create a test command file
    cmd_file = commands_dir / "weather.md"
    cmd_file.write_text("""---
name: weather
description: Get weather
---
Use wttr.in to get weather for {args}
""")

    loader = CustomCommandsLoader(commands_dir.parent)
    content = loader.get_command_content("weather")

    assert content is not None
    assert "Use wttr.in" in content
    assert "{args}" in content


def test_command_not_found(tmp_path):
    loader = CustomCommandsLoader(tmp_path)
    content = loader.get_command_content("nonexistent")
    assert content is None


def test_get_commands_for_telegram(commands_dir):
    # Create test commands
    (commands_dir / "weather.md").write_text("""---
name: weather
description: Get weather info
---
Weather command
""")
    (commands_dir / "translate.md").write_text("""---
name: translate
description: Translate text
---
Translate command
""")

    loader = CustomCommandsLoader(commands_dir.parent)
    commands = loader.get_bot_commands()

    assert len(commands) == 2
    assert {"command": "weather", "description": "Get weather info"} in commands
    assert {"command": "translate", "description": "Translate text"} in commands


def test_command_case_insensitive(commands_dir):
    # Create a test command file
    cmd_file = commands_dir / "hello.md"
    cmd_file.write_text("""---
name: hello
description: Say hello
---
Hello world!
""")

    loader = CustomCommandsLoader(commands_dir.parent)

    # Should work with exact case
    assert loader.get_command_content("hello") is not None
    # Should work with different case
    assert loader.get_command_content("HELLO") is not None
    assert loader.get_command_content("Hello") is not None


def test_list_commands(commands_dir):
    (commands_dir / "weather.md").write_text("""---
name: weather
description: Get weather info
---
Weather command
""")
    (commands_dir / "translate.md").write_text("""---
name: translate
description: Translate text
---
Translate command
""")

    loader = CustomCommandsLoader(commands_dir.parent)
    commands = loader.list_commands()

    assert len(commands) == 2
    names = [c["name"] for c in commands]
    assert "weather" in names
    assert "translate" in names


def test_command_exists(commands_dir):
    (commands_dir / "weather.md").write_text("""---
name: weather
description: Get weather info
---
Weather command
""")

    loader = CustomCommandsLoader(commands_dir.parent)

    assert loader.command_exists("weather") is True
    assert loader.command_exists("nonexistent") is False