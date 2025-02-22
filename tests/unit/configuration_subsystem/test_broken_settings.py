"""test using broken settings files
"""
import os


def test_broken_settings_file(generate_config):
    """Ensure exit_messages generated for broken settings file"""
    response = generate_config(setting_file_name="ansible-navigator_broken.yml")
    assert len(response.exit_messages) == 3, response.exit_messages
    error = "Errors encountered when loading settings file:"
    assert response.exit_messages[1].message.startswith(error)


def test_garbage_settings_file(generate_config):
    """Ensure exit_messages generated for garbage settings file"""
    response = generate_config(setting_file_name=os.path.abspath(__file__))
    error = "but failed to load it."
    assert response.exit_messages[1].message.endswith(error), response.exit_messages
