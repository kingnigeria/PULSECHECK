# PulseCheck Multi-Computer Network Setup Guide

## 🚀 Quick Start for Expo Tomorrow

Your PulseCheck manager/worker system is now configured to run across multiple computers on the same network!

### Step 1: Find Your Manager's IP Address

**On the Manager Computer (Windows):**
1. Open Command Prompt (Win + R, type `cmd`)
2. Run: `ipconfig`
3. Look for "IPv4 Address" under your network adapter
   - Example: `192.168.1.100`

**Make note of this IP!** You'll need it for all worker configs.

---

### Step 2: Update Configuration Files

You need to replace `192.168.1.100` with your actual manager IP in:

- `config/manager.json` - Already set to `"host": "0.0.0.0"` ✅
- `config/worker.json` - Change `"manager_host"` to your manager IP
- `config/worker-2.json` - Already configured, just change `"manager_host"`

**Example for manager IP `192.168.1.50`:**
```json
{
  "manager_host": "192.168.1.50",
  ...
}
```

---

### Step 3: Configure Windows Firewall (REQUIRED!)

Run Command Prompt **as Administrator** and execute:

```powershell
# Allow TCP ports for handshake, data, and web dashboard
netsh advfirewall firewall add rule name="PulseCheck TCP" dir=in action=allow protocol=tcp localport=8001,8002,5000 enable=yes

# Allow UDP port for alerts
netsh advfirewall firewall add rule name="PulseCheck UDP" dir=in action=allow protocol=udp localport=8003 enable=yes
```

Or use the GUI:
1. Settings → Privacy & Security → Windows Defender Firewall → Allow an app
2. Add Python and allow for "Private" networks
3. Manually add ports: 8001, 8002, 8003, 5000

---

### Step 4: Start the System

**On Manager Computer:**
```bash
# Terminal 1: Start the manager
python server.py

# Terminal 2: Start first worker
python client.py --config config/worker.json
```

**On Second Computer:**
```bash
python client.py --config config/worker-2.json
```

---

### Step 5: View Live Dashboard

Open your browser and navigate to:
```
http://<manager-ip>:5000
```

**Example:** `http://192.168.1.100:5000`

You'll see a beautiful real-time dashboard showing:
- ✅ All connected workers
- 📍 Their IP addresses
- 💚 Online/Offline status
- ⏰ Last heartbeat time

**Perfect for your expo demo!**

---

## 📊 How It Works

1. **Manager (`server.py`)** runs on the central computer
   - Listens on all network interfaces (`0.0.0.0`)
   - Distributes tasks to workers
   - Collects metrics (CPU, RAM, Disk)
   - Serves web dashboard

2. **Workers (`client.py`)** run on any computer
   - Connect back to manager via network
   - Authenticate with encryption
   - Report system metrics
   - Execute approved commands

3. **Web Dashboard** shows real-time stats
   - Auto-refreshes every 2 seconds
   - Shows worker status
   - Perfect for monitoring during expo

---

## 🔧 Troubleshooting

### "Connection Refused" Error?
- ✅ Check manager IP is correct
- ✅ Verify firewall rules are applied
- ✅ Ensure manager is running on `server.py`
- ✅ Check both computers are on same WiFi

### Worker not showing in dashboard?
- ✅ Verify worker config has correct `manager_host`
- ✅ Check worker output for auth errors
- ✅ Ensure Fernet key matches in both configs (it should)

### Can't access dashboard from other computer?
- ✅ Try `http://<manager-ip>:5000` (use actual IP, not localhost)
- ✅ Firewall port 5000 must be allowed
- ✅ Both computers must be on same network

---

## 🎯 Demo Script for Expo

1. **Setup Phase:**
   - Manager running on laptop
   - 1-2 workers on other computers

2. **Demo Flow:**
   - Open dashboard (`http://ip:5000`)
   - Show live worker connections
   - Watch real-time CPU/RAM/Disk updates
   - Mention encryption & authentication

3. **Interactive Demo:**
   - Run commands via manager
   - Show alert system when thresholds exceeded
   - Explain TCP handshake & heartbeat mechanism

---

## ✅ What Changed

- ✅ `config/manager.json` - Network access enabled (`0.0.0.0`), web dashboard added
- ✅ `config/worker.json` - Updated for network (change IP to yours!)
- ✅ `config/worker-2.json` - New config for second worker
- ✅ Same changes in `dist/config/` for distribution

---

## 📝 Default Ports

- **8001** - TCP Handshake (authentication)
- **8002** - TCP Data Channel (tasks & metrics)
- **8003** - UDP Alert Channel (threshold alerts)
- **5000** - HTTP Web Dashboard

All must be open in firewall for network operation.

---

Good luck at the expo! 🚀
