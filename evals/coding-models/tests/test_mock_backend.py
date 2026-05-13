"""Mock backend unit tests."""

from harness.backends.mock import MockBackend


def test_default_response() -> None:
    backend = MockBackend(default_response="<html></html>")
    response = backend.generate("anything goes")
    assert response.text == "<html></html>"
    assert response.finish_reason == "stop"


def test_keyed_response_takes_precedence() -> None:
    backend = MockBackend(
        responses={"You are refactoring": '{"files": {}}'},
        default_response="<html></html>",
    )
    response = backend.generate("You are refactoring a small project")
    assert response.text == '{"files": {}}'


def test_fail_on_triggers_error() -> None:
    backend = MockBackend(fail_on=["__BOOM__"])
    response = backend.generate("trigger __BOOM__ now")
    assert response.finish_reason == "error"
    assert response.text == ""


def test_image_propagates_into_raw() -> None:
    backend = MockBackend()
    response = backend.generate("hi", image=b"\x89PNG\r\n")
    assert response.raw["had_image"] is True
