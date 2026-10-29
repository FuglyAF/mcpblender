# MCP for Blender — personal fork

A personal, invite-only fork of [MCP for Blender](https://github.com/ahujasid/blender-mcp) by
Siddharth Ahuja (MIT, see [LICENSE](LICENSE)), kept as the live-Blender front end for
[The Analog Lab](https://github.com/FuglyAF/The-Analog-Lab).

Not affiliated with the Blender Foundation, and not the upstream project: don't report issues here
to upstream.

## What's different from upstream

- **Nothing leaves the machine.** Telemetry, trajectory recording, consent prompts, screenshot
  uploads and the edit recorder are removed, not just switched off.
- **No paid service.** The Premium generation service and every pointer to it are removed. The
  3D generators (Hyper3D, Hunyuan3D, Tripo, Meshy) still work on your own API keys, and stay off
  until you turn them on.
- **No upstream installers.** `setup`, `update`, the install scripts and the Docker image pulled
  upstream's package from PyPI, which would replace this fork. The add-on's update check reads
  this fork's `personal` branch.
- **Port 9877** by default, so it can run beside Blender Lab's own MCP extension on 9876.
- Tools no longer ask the model to repeat your words (`user_prompt`); that only fed telemetry.

## Set up (Windows)

```
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\mcp-for-blender install-addon
```

Then in Blender: Preferences → Add-ons → enable *Interface: MCP for Blender*, open the sidebar
(N) → *MCP for Blender* → *Start MCP Server*.

Register the server with Claude Code (user scope):

```
claude mcp add --scope user blender-live -- C:\path\to\mcpblender\.venv\Scripts\mcp-for-blender.exe
```

Blender must be open with a window: commands run on Blender's main-thread timer, which doesn't run
under `blender -b`. Headless work belongs to The Analog Lab's warm workers.

## Tests

```
.venv\Scripts\python -m pytest -q
```
