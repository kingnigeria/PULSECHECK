#!/usr/bin/env python3
"""
PulseCheck Demo Reset Script

Resets all configurations back to defaults for testing.
Useful for resetting between demo runs.

Usage: python reset_demo.py
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def reset_configs():
    """Reset all config files to default state."""
    print("\n" + "="*60)
    print("   PulseCheck Demo Reset")
    print("="*60 + "\n")
    
    default_manager_config = {
        "host": "0.0.0.0",
        "handshake_port": 8001,
        "data_port": 8002,
        "alert_port": 8003,
        "web_port": 5000,
        "heartbeat_timeout_seconds": 15,
        "task_interval_seconds": 5,
        "fernet_key": "02M_AD7g3DfI3QR71Y07peXFo3EJD2lL5j5Im8W4AFU=",
        "tasks_file": "../tasks/tasks.txt",
        "allowed_workers": [
            {"worker_id": "*", "ip": "*"}
        ]
    }
    
    default_worker_1_config = {
        "worker_id": "worker-1",
        "manager_host": "192.168.1.100",
        "handshake_port": 8001,
        "data_port": 8002,
        "alert_port": 8003,
        "heartbeat_interval_seconds": 10,
        "fernet_key": "02M_AD7g3DfI3QR71Y07peXFo3EJD2lL5j5Im8W4AFU=",
        "allow_commands": ["hostname", "whoami"],
        "alert_thresholds": {
            "cpu_percent": 85.0,
            "memory_percent": 90.0,
            "disk_percent": 95.0
        }
    }
    
    default_worker_2_config = {
        "worker_id": "worker-2",
        "manager_host": "192.168.1.100",
        "handshake_port": 8001,
        "data_port": 8002,
        "alert_port": 8003,
        "heartbeat_interval_seconds": 10,
        "fernet_key": "02M_AD7g3DfI3QR71Y07peXFo3EJD2lL5j5Im8W4AFU=",
        "allow_commands": ["hostname", "whoami"],
        "alert_thresholds": {
            "cpu_percent": 85.0,
            "memory_percent": 90.0,
            "disk_percent": 95.0
        }
    }
    
    configs = {
        ROOT / "config" / "manager.json": default_manager_config,
        ROOT / "dist" / "config" / "manager.json": default_manager_config,
        ROOT / "config" / "worker.json": default_worker_1_config,
        ROOT / "dist" / "config" / "worker.json": default_worker_1_config,
        ROOT / "config" / "worker-2.json": default_worker_2_config,
        ROOT / "dist" / "config" / "worker-2.json": default_worker_2_config,
    }
    
    reset_count = 0
    for config_path, config_data in configs.items():
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            print("OK: " + str(config_path.relative_to(ROOT)))
            reset_count += 1
        except Exception as e:
            print("Error resetting " + str(config_path) + ": " + str(e))
    
    print("\nReset " + str(reset_count) + " config files to defaults\n")
    print("="*60)
    print("\nNext Steps:")
    print("   1. Run: python setup_demo.py")
    print("   2. This will auto-detect your IP and start everything")
    print("   3. Open http://YOUR_IP:5000 in your browser\n")


if __name__ == "__main__":
    reset_configs()
