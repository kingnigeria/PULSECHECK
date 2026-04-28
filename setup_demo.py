#!/usr/bin/env python3
"""
PulseCheck Demo Setup Script

Automates the entire setup for a quick demo:
1. Detects the local machine IP
2. Updates all config files with correct IP
3. Sets up firewall rules (Windows)
4. Starts manager and workers
5. Opens web dashboard in browser

Usage: python setup_demo.py
"""

import json
import os
import platform
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path


def get_local_ip():
    """Get the local machine IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_header():
    """Print welcome banner."""
    print("\n" + "="*60)
    print("   PulseCheck Demo Setup - Automated Configuration")
    print("="*60 + "\n")


def update_config_files(manager_ip):
    """Update all config files with the manager IP."""
    print("Updating config files with IP: " + manager_ip)
    
    config_files = [
        "config/manager.json",
        "config/worker.json",
        "config/worker-2.json",
        "dist/config/manager.json",
        "dist/config/worker.json",
        "dist/config/worker-2.json",
    ]
    
    updated = 0
    for config_file in config_files:
        if not os.path.exists(config_file):
            continue
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            if "worker" in config_file:
                config["manager_host"] = manager_ip
            elif "manager" in config_file:
                config["host"] = "0.0.0.0"
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print("   OK: " + config_file)
            updated += 1
        except Exception as e:
            print("   Error " + config_file + ": " + str(e))
    
    print("\nUpdated " + str(updated) + " config files\n")


def setup_firewall():
    """Configure Windows Firewall (if Windows)."""
    if platform.system() != "Windows":
        print("Skipping firewall setup (not Windows)\n")
        return
    
    print("Setting up Windows Firewall rules...")
    print("   You may be prompted for Administrator permission\n")
    
    rules = [
        ('netsh advfirewall firewall add rule name="PulseCheck TCP" dir=in action=allow protocol=tcp localport=8001,8002,5000 enable=yes', "TCP ports"),
        ('netsh advfirewall firewall add rule name="PulseCheck UDP" dir=in action=allow protocol=udp localport=8003 enable=yes', "UDP port"),
    ]
    
    for rule, desc in rules:
        try:
            subprocess.run(rule, shell=True, check=False, capture_output=True)
            print("   OK: " + desc)
        except Exception as e:
            print("   Warning " + desc + ": " + str(e))
    
    print()


def start_manager():
    """Start the manager in a separate thread."""
    print("Starting Manager Server...")
    
    def run_manager():
        try:
            from pulsecheck.manager import main
            main()
        except Exception as e:
            print("Manager error: " + str(e))
    
    thread = threading.Thread(target=run_manager, daemon=True)
    thread.start()
    print("   OK: Manager started (background)\n")
    time.sleep(2)


def start_worker(config_path, worker_name):
    """Start a worker in a separate thread."""
    print("Starting " + worker_name + "...")
    
    def run_worker():
        try:
            from pulsecheck.worker import WorkerClient
            from pulsecheck.config import load_json
            config = load_json(config_path)
            WorkerClient(config).run()
        except Exception as e:
            print(worker_name + " error: " + str(e))
    
    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()
    print("   OK: " + worker_name + " started (background)\n")
    time.sleep(1)


def open_dashboard(manager_ip):
    """Open the web dashboard in default browser."""
    url = "http://" + manager_ip + ":5000"
    print("Opening dashboard at " + url)
    print("   Waiting for manager to start (5 seconds)...\n")
    time.sleep(5)
    
    try:
        if platform.system() == "Windows":
            os.startfile(url)
        elif platform.system() == "Darwin":
            subprocess.run(["open", url])
        else:
            subprocess.run(["xdg-open", url])
        print("   OK: Dashboard opened in browser\n")
    except Exception as e:
        print("   Warning: Could not open browser: " + str(e))
        print("   Visit manually: " + url + "\n")


def show_instructions(manager_ip):
    """Display final instructions."""
    print("="*60)
    print("   SETUP COMPLETE - DEMO IS RUNNING")
    print("="*60)
    print("""
Manager IP: %s
Dashboard: http://%s:5000

Running:
   - Manager Server (port 8001, 8002, 8003, 5000)
   - Worker 1 (connecting...)
   - Worker 2 (connecting...)
   - Web Dashboard (ready)

Timeline:
   - 0-5 sec: Workers authenticate
   - 5-10 sec: First metrics appear
   - 10+ sec: Live updates every 2 seconds

For video recording:
   1. Open browser: http://%s:5000
   2. Refresh to see workers connect
   3. Show real-time metrics updating

To stop: Press Ctrl+C in this terminal

""" % (manager_ip, manager_ip, manager_ip))
    print("="*60)


def main():
    """Main setup flow."""
    print_header()
    
    manager_ip = get_local_ip()
    print("Detected Local IP: " + manager_ip + "\n")
    
    update_config_files(manager_ip)
    setup_firewall()
    
    start_manager()
    start_worker("config/worker.json", "Worker 1")
    start_worker("config/worker-2.json", "Worker 2")
    
    open_dashboard(manager_ip)
    show_instructions(manager_ip)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
