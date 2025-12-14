import queue
import pytest

from app.core.message_router import MessageRouter
from app.core.plugin_manager import PluginManager
from app.core.media_manager import MediaManager
from app.core.url_extractor import URLExtractor

pytestmark = pytest.mark.unit


# Helpers -------------------------------------------------------------


def process_once(router: MessageRouter):
    """Process exactly one message from the router queue (no infinite loop)."""
    if router.queue.empty():
        return

    message, user_id, incoming_media, thread_history, aux = router.queue.get()
    message = message.strip()

    inf_response = ""
    outgoing_media_filename = None

    try:
        if message.startswith("/"):
            plugin_name = message.split(" ")[0][1:]
            inf_response, outgoing_media_filename, _ = (
                router.plugin_manager.execute_plugin(
                    plugin_name=plugin_name,
                    message=message,
                    user_id=user_id,
                    media=incoming_media,
                )
            )
        else:
            inf_response, tool_images = router.process_text_callback(
                message=message,
                user_id=user_id,
                incoming_media=incoming_media,
                aux=aux,
            )
            outgoing_media_filename = tool_images[0] if tool_images else None
    finally:
        router.cleanup_media_callback(incoming_media)

    router.egest_callback(
        message=inf_response,
        media=[outgoing_media_filename] if outgoing_media_filename else [None],
        aux=aux,
    )


# URLExtractor -------------------------------------------------------


def test_url_extractor_basic(mock_console):
    extractor = URLExtractor(console=mock_console)
    url = extractor.extract_url("see https://example.com please")
    assert url == "https://example.com"


def test_url_extractor_trailing_punct(mock_console):
    extractor = URLExtractor(console=mock_console)
    url = extractor.extract_url("check https://example.com/test?x=1,")
    assert url == "https://example.com/test?x=1"


def test_url_extractor_augment(monkeypatch, mock_console):
    extractor = URLExtractor(console=mock_console)

    def fake_fetch(url, text_only=True, use_js=True):
        assert url == "https://example.com"
        return "PAGE CONTENT"

    monkeypatch.setattr("app.lib.network.fetchHtml", fake_fetch, raising=True)
    msg = extractor.augment_message_with_url("hello https://example.com world")
    assert "PAGE CONTENT" in msg
    assert "hello https://example.com world" in msg


# MediaManager -------------------------------------------------------


def test_media_manager_validate_and_exists(tmp_path, mock_console):
    mgr = MediaManager(console=mock_console, media_dir=str(tmp_path))
    existing = tmp_path / "ok.txt"
    existing.write_text("hi")

    valid = mgr.validate_media_files([str(existing), "/nope/missing.txt", None])
    assert valid == [str(existing)]
    assert mgr.media_exists(str(existing)) is True
    assert mgr.media_exists("/nope/missing.txt") is False


def test_media_manager_cleanup(tmp_path, mock_console):
    mgr = MediaManager(console=mock_console, media_dir=str(tmp_path))
    file_path = tmp_path / "delete_me.txt"
    file_path.write_text("bye")

    mgr.cleanup_media_files([str(file_path)])
    assert file_path.exists() is False


# PluginManager ------------------------------------------------------


def test_plugin_manager_execute(
    clean_plugin_registry, mock_plugin, mock_console, mock_backend
):
    clean_plugin_registry["test"] = mock_plugin
    mgr = PluginManager(
        console=mock_console, backend=mock_backend, imagegen=None, debug=True
    )
    mgr.plugins = clean_plugin_registry

    resp, media, skip = mgr.execute_plugin("test", "/test hello", "user1")
    assert resp == "Test response"
    assert media == ""
    assert skip is True
    mock_plugin.execute.assert_called_once()
    args, kwargs = mock_plugin.execute.call_args
    assert kwargs["query"] == "hello"


def test_plugin_manager_not_found(mock_console, mock_backend):
    mgr = PluginManager(
        console=mock_console, backend=mock_backend, imagegen=None, debug=True
    )
    mgr.plugins = {}
    resp, media, skip = mgr.execute_plugin("missing", "/missing hi", "user")
    assert resp == "Plugin missing not found."
    assert media is None
    assert skip is True


def test_plugin_manager_has_and_get(
    clean_plugin_registry, mock_plugin, mock_console, mock_backend
):
    clean_plugin_registry["plug"] = mock_plugin
    mgr = PluginManager(
        console=mock_console, backend=mock_backend, imagegen=None, debug=False
    )
    mgr.plugins = clean_plugin_registry

    assert mgr.has_plugin("plug") is True
    assert mgr.has_plugin("nope") is False
    assert mgr.get_plugin("plug") is mock_plugin


# MessageRouter ------------------------------------------------------


def test_message_router_text_path(mock_console, mock_backend):
    responses = []
    cleaned = []

    def process_text(message, user_id, incoming_media, aux):
        cleaned.append((message, user_id, incoming_media, aux))
        return "ok", []

    def egest(message, media, aux):
        responses.append((message, media, aux))

    def cleanup(media_paths):
        cleaned.append(tuple(media_paths))

    plugin_mgr = PluginManager(console=mock_console, backend=mock_backend, debug=False)
    plugin_mgr.plugins = {}

    router = MessageRouter(
        console=mock_console,
        process_text_callback=process_text,
        plugin_manager=plugin_mgr,
        egest_callback=egest,
        cleanup_media_callback=cleanup,
        config={"thread_sleep": 0},
        debug=False,
    )
    router.queue = queue.Queue()
    router.queue.put((" hello ", "user1", [], None, {"aux": 1}))

    process_once(router)

    assert responses == [("ok", [None], {"aux": 1})]
    assert cleaned[0][0] == "hello"  # stripped


def test_message_router_plugin_path(
    mock_console, mock_plugin, clean_plugin_registry, mock_backend
):
    responses = []

    def process_text(**kwargs):
        raise AssertionError("should not hit text path")

    def egest(message, media, aux):
        responses.append((message, media, aux))

    def cleanup(media_paths):
        assert media_paths == []

    clean_plugin_registry["plug"] = mock_plugin
    plugin_mgr = PluginManager(console=mock_console, backend=mock_backend, debug=False)
    plugin_mgr.plugins = clean_plugin_registry

    router = MessageRouter(
        console=mock_console,
        process_text_callback=process_text,
        plugin_manager=plugin_mgr,
        egest_callback=egest,
        cleanup_media_callback=cleanup,
        config={"thread_sleep": 0},
        debug=False,
    )
    router.queue = queue.Queue()
    router.queue.put(("/plug hi", "u1", [], None, None))

    process_once(router)

    assert responses == [("Test response", [None], None)]
