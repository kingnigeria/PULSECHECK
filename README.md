# PulseCheck

PulseCheck is a lightweight socket-based remote task manager built from the project documentation in this folder. It uses a Manager/Worker architecture with:

- TCP handshake authentication
- TCP task and telemetry channel
- UDP alert channel
- Fernet encryption
- `psutil` system metrics
- Heartbeat-based timeout detection

## Project Layout

- `server.py`: starts the manager process
- `client.py`: starts the worker process
- `pulsecheck/`: shared implementation modules
- `config/`: sample manager and worker configuration
- `tasks/tasks.txt`: sample tasks sent by the manager

## Quick Start

If you want the easiest path on Windows:

1. Double-click `install_pulsecheck.bat`
2. Double-click `run_manager.bat` on the manager computer
3. Double-click `run_worker.bat` on the worker computer

Optional helpers:

- `run_smoke_test.bat`: verifies the system can connect locally
- `build_exe.bat`: packages the manager and worker into `.exe` files using PyInstaller

## Environment Setup

```powershell
cd C:\Users\harus\OneDrive\Documents\PULSECHECK
.\install_pulsecheck.bat
```

If Python is not already installed on the machine, install Python 3.12 or newer first and make sure it is available on `PATH`.

## Running Locally

Start the manager:

Double-click `run_manager.bat`

or run:

```powershell
.\.venv\Scripts\python.exe server.py --config config\manager.json
```

Start one worker in a second terminal:

Double-click `run_worker.bat`

or run:

```powershell
.\.venv\Scripts\python.exe client.py --config config\worker.json
```

Run the quick smoke test:

Double-click `run_smoke_test.bat`

or run:

```powershell
.\.venv\Scripts\python.exe smoke_test.py
```

## Sharing With Partners

1. Zip the entire `PULSECHECK` folder.
2. My partner extracts it anywhere on their Windows machine.
3. They run `install_pulsecheck.bat`.
4. They edit `config\worker.json` if the manager IP address changes.
5. They launch `run_worker.bat`.

For the manager machine, edit `config\manager.json` to include each worker ID and IP in `allowed_workers`.

## Single-Computer Demo

The current sample config is already set up for one computer:

- `config\manager.json` uses `127.0.0.1`
- `config\worker.json` uses `127.0.0.1`

That means you can test everything locally without changing the configs:

1. Run `install_pulsecheck.bat`
2. Run `run_manager.bat`
3. Open a second terminal and run `run_worker.bat`

## Two-Computer Demo

If the manager and worker will run on different computers on the same network:

1. On the manager machine, change `config\manager.json`:
   - set `host` to `0.0.0.0` or the manager machine's LAN IP
   - update `allowed_workers` with the worker machine's IP
2. On the worker machine, change `config\worker.json`:
   - set `manager_host` to the manager machine's LAN IP
   - keep a unique `worker_id`
3. Allow Windows Firewall access for ports `8001`, `8002`, and `8003`
4. Start the manager first, then start the worker

## Building Executables

If you want standalone `.exe` files:

1. Run `install_pulsecheck.bat`
2. Run `build_exe.bat`
3. The generated files will appear in `dist\`

Those executables still need the matching `config` and `tasks` folders beside them unless we later decide to bundle config into the app.

## Tasks

The manager reads `tasks/tasks.txt` and sends supported tasks over the encrypted data channel.

Supported task formats:

- `collect_metrics`
- `run_command:hostname`
- `run_command:whoami`

Workers only execute commands listed in `allow_commands` inside `config/worker.json`.

## Default Ports

- Handshake TCP: `8001`
- Data TCP: `8002`
- Alert UDP: `8003`

## Notes

- The sample configs are set up for local testing on `127.0.0.1`.
- To add more workers, copy `config/worker.json`, change the `worker_id`, and add that worker to the manager allowlist.
- If CPU, memory, or disk usage crosses the configured threshold, the worker sends a UDP alert to the manager.
