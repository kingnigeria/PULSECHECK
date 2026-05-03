# PulseCheck Multi-Computer Expo Setup

This version of PulseCheck is built for a live CS381 expo:

- Real Python workers use TCP and UDP sockets
- Browser visitors open the dashboard and appear as web visitors
- The dashboard explains what students should do when they arrive

## Manager Machine

1. Connect to the expo Wi-Fi
2. Run:

```powershell
cd C:\Users\harus\OneDrive\Documents\PULSECHECK
python setup_demo.py
```

3. Keep the dashboard open
4. Note the manager IP shown in the script output

## Worker Machine

1. Connect to the same Wi-Fi
2. Open `config\worker.json`
3. Set `manager_host` to the manager machine IP
4. Run:

```powershell
python client.py --config config\worker.json
```

If you want a second worker machine, use `config\worker-2.json` or copy the worker config and give it a different `worker_id`.

## Visitor Devices

Students do not need Python installed just to watch the demo.

They should:

1. Join the same Wi-Fi
2. Open `http://MANAGER-IP:5000`
3. Watch the live dashboard

The page will automatically register them as web visitors.

## Firewall Ports

Allow these ports on the manager machine:

- `8001` TCP
- `8002` TCP
- `8003` UDP
- `5000` TCP

## If You See ConnectionRefusedError

That almost always means one of these:

1. The manager is not actually running
2. `manager_host` in the worker config points to the wrong IP
3. Windows Firewall is blocking the ports
4. The manager and worker are not on the same network

## Recommended Expo Demo Flow

1. Start the manager
2. Open the dashboard on the manager laptop
3. Start one real worker on another laptop
4. Let student visitors open the dashboard URL from phones or laptops
5. Show that:
   browser visitors appear on the page
6. Show that:
   real workers appear in the Socket Workers section and send live metrics over sockets
