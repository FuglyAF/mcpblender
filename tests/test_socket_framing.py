"""The socket on both ends: messages are split by one scan over the stream, a Blender-side error
keeps the connection, and a timeout says the command may still be running."""

from __future__ import annotations

import asyncio
import json
import socket

import pytest
from test_server_threading import BlenderMCPServer
from test_socket_unicode import _ScriptedSocket

from blender_mcp import server
from blender_mcp.server import BlenderConnection, BlenderError, JsonFrames

MESSAGES = [
    {"type": "execute_code", "params": {"code": 'print("{not a brace}")\nx = "\\\\"'}},
    {"type": "get_scene_info", "params": {"name": "Café ☕ 椅子", "nested": {"a": [1, {"b": "]"}]}}},
]


def _stream() -> bytes:
    return b"".join(json.dumps(m, ensure_ascii=False).encode("utf-8") for m in MESSAGES)


@pytest.mark.parametrize("frames_class", [JsonFrames, BlenderMCPServer._JsonFrames], ids=["server", "addon"])
def test_back_to_back_messages_split_whatever_the_chunking(frames_class):
    data = _stream()
    for size in (1, 2, 3, 7, len(data)):
        frames, got = frames_class(), []
        for i in range(0, len(data), size):
            got += frames.feed(data[i:i + size])
        assert [json.loads(m.decode("utf-8")) for m in got] == MESSAGES, size
        assert not frames.buffer.strip()


@pytest.mark.parametrize("frames_class", [JsonFrames, BlenderMCPServer._JsonFrames], ids=["server", "addon"])
def test_anything_but_objects_is_refused(frames_class):
    with pytest.raises(ValueError, match="expected a JSON object"):
        frames_class().feed(b'"just a string"')


def test_a_large_reply_arrives_whole():
    big = {"status": "success", "result": {"objects": [{"name": f"SM_Part_{i}", "aabb": [i, i, i]}
                                                       for i in range(40000)]}}
    data = json.dumps(big).encode("utf-8")
    frames, got = JsonFrames(), []
    for i in range(0, len(data), 65536):
        got += frames.feed(data[i:i + 65536])
    assert len(got) == 1 and json.loads(got[0]) == big


def test_two_commands_in_one_recv_are_both_queued():
    blender = BlenderMCPServer(port=0)
    blender.running = True
    sock = _ScriptedSocket([_stream()])
    blender._handle_client(sock)
    queued = []
    while not blender.command_queue.empty():
        queued.append(blender.command_queue.get_nowait()[0])
    assert queued == MESSAGES


def _connected(monkeypatch):
    ours, blenders = socket.socketpair()
    conn = BlenderConnection(host="localhost", port=1)
    conn.sock = ours
    monkeypatch.setattr(server, "_blender_connection", conn)
    return conn, blenders


def test_a_blender_error_is_blenders_and_keeps_the_connection(monkeypatch):
    conn, blenders = _connected(monkeypatch)
    blenders.sendall(json.dumps({"status": "error", "message": "Unknown command type: nope"}).encode())
    with pytest.raises(BlenderError, match="^Unknown command type: nope$"):
        conn.send_command("nope")
    assert conn.sock is not None
    blenders.recv(65536)
    blenders.sendall(json.dumps({"status": "success", "result": {"pong": True}}).encode())
    assert conn.send_command("ping") == {"pong": True}


def test_a_failing_script_shows_its_traceback(monkeypatch):
    conn, blenders = _connected(monkeypatch)
    detail = {"exception_type": "NameError", "message": "name 'cube' is not defined",
              "traceback": 'File "<string>", line 2\nNameError: name \'cube\' is not defined'}
    blenders.sendall(json.dumps({"status": "error", "message": json.dumps(detail)}).encode())
    reply = asyncio.run(server.execute_blender_code(None, code="import bpy\ncube.location.x = 1"))
    assert reply.startswith("Error executing code: NameError: name 'cube' is not defined\n\n")
    assert 'line 2' in reply
    assert conn.sock is not None


def test_a_timeout_says_the_command_may_still_run_and_closes_the_socket(monkeypatch):
    conn, blenders = _connected(monkeypatch)
    ours = conn.sock
    monkeypatch.setattr(server, "RESPONSE_TIMEOUT_S", 0.2)
    with pytest.raises(Exception, match="may still be running") as e:
        conn.send_command("execute_code", {"code": "render()"})
    assert "headless" in str(e.value)
    assert conn.sock is None and ours.fileno() == -1
    blenders.close()
