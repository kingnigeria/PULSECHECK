# PulseCheck System Monitor

**Created by:** Somtoo and Ahmad

## Project Overview
PulseCheck is a system monitoring tool we built to track computer performance across a network. The system uses a client-server architecture to gather and display hardware data in real time. A central Manager server listens for incoming connections. Individual Worker scripts run on target machines to collect local hardware metrics including CPU usage and RAM utilization. These workers send data payloads back to the manager. The manager aggregates this information and hosts it on a live web dashboard using Flask. 

## Setup and Run Instructions
We automated the configuration process using batch scripts to simplify deployment. 

1. Double-click the `install_pulsecheck.bat` file. This script creates a localized Python virtual environment and installs all necessary dependencies.
2. Wait for the command prompt window to confirm the installation is complete. 
3. Double-click the `run_demo.bat` file. This script launches both the backend manager server and the web dashboard interface simultaneously. 
4. Open a web browser and navigate to `http://localhost:5000` to view the live dashboard.
5. To test the monitoring capabilities on your own machine, double-click `run_worker.bat` to launch a local client. You will see your system appear on the web dashboard.




## Multi-Machine Network Demonstration
We also built the system to support real network deployments across multiple physical devices.

### Manager Machine Configuration
1. Execute `python setup_demo.py` or `python server.py`.
2. Keep the web dashboard running.
3. Verify that the Windows Firewall allows traffic through ports 8001, 8002, 8003, and 5000.

### Worker Machine Configuration (Automated)
1. Double-click the `toggle_worker_config.bat` file.
2. Select option [1] to add a network worker.
3. Input the manager computer's IP address when prompted.
4. Execute `python client.py --config config\worker.json`.

### Worker Machine Configuration (Manual Reversion)
1. Double-click the `toggle_worker_config.bat` file.
2. Select option [1] to revert the configuration back to localhost.

### Web Visitor Access
1. Connect the visitor device to the same Wi-Fi network as the manager machine.
2. Open a web browser and navigate to `http://MANAGER-IP:5000`.
3. The device will appear on the dashboard as an active web visitor.

## Dashboard Features
We programmed the web interface to display several distinct categories of connected devices and activities.

* **Your Visitor Card**: Displays the specific specifications of the device currently viewing the page.
* **Live Visitors**: Displays other devices actively viewing the dashboard on the network.
* **Worker Machines**: Displays the computers actively running the Python PulseCheck client script.
* **Live Activity**: Displays a real-time stream of authentication events, active tasks, system alerts, and heartbeat data.

## File Directory Map
We organized the project into several executable scripts and core Python files to separate the server logic from the client data collection. 

* **`install_pulsecheck.bat`**: Creates the Python virtual environment and installs the required libraries.
* **`requirements.txt`**: Lists the specific Python dependencies needed for the environment.
* **`run_demo.bat`**: Starts the main server and the web interface together for a full system demonstration.
* **`run_manager.bat`**: Starts only the central manager server for listening to incoming worker data.
* **`run_worker.bat`**: Launches the client script to begin collecting local system metrics and sending them to the manager.
* **`setup_demo.py`**: A utility script we wrote to configure the initial network environment and verify port availability.
* **`server.py`**: The main entry point to start the manager server.
* **`client.py`**: The main entry point to start a worker node.
* **`tools/reset_demo.py`**: Resets all configuration files back to their default demo values.
* **`tools/smoke_test.py`**: Executes a quick local health check to verify core functionality.
* **`run_smoke_test.bat`**: A batch wrapper to execute the automated smoke tests easily.
* **`toggle_worker_config.bat`**: Swaps between different worker configuration states to test various network scenarios.
* **`docs/SETUP_MULTICOMPUTER.md`**: Contains our technical notes for deploying across two distinct computers.
* **`pulsecheck/manager.py`**: Contains the core logic for the socket manager and the dashboard server.
* **`pulsecheck/worker.py`**: Contains the hardware polling logic and data transmission protocols for the client.

## Network Port Configuration
We assigned specific ports to handle different types of traffic to prevent data collisions.

* **8001**: Reserved for the initial TCP handshake between the worker and manager.
* **8002**: Reserved for continuous TCP data streaming of hardware metrics.
* **8003**: Reserved for UDP alert transmissions.
* **5000**: Reserved for the HTTP web dashboard interface.

## Architecture Details
The backend utilizes Python socket programming to maintain continuous connections between the worker nodes and the manager. The manager processes incoming JSON payloads and stores the current state in memory. The Flask web server reads this memory state and dynamically updates the HTML frontend. We designed it this way to ensure the web interface remains responsive regardless of how many worker nodes are connected or transmitting data.

