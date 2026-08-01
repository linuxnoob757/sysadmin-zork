# Install Guide — Rocky/Alma in VirtualBox

Step-by-step for the guided-but-hands-on prologue. You do the clicks; the engine
verifies the result. (A future release may script this via Kickstart; for now,
doing it by hand is the first RHCSA lesson.)

## 1. Create the VM

In VirtualBox: **New** →
- Name: `sysadmin-zork`
- Type: Linux, Version: **Red Hat (64-bit)**
- Memory: **2048 MB** (or 4096)
- Disk: **Create a virtual hard disk now** → VDI → Dynamically allocated → **20 GB**

Then **Settings** →
- **System → Processor:** 2 CPUs; **Motherboard:** enable EFI.
- **Network → Adapter 1:** NAT. **Adapter 2:** Host-Only Adapter
  (`VirtualBox Host-Only Ethernet Adapter`).
- **Storage:** attach the Rocky/Alma **minimal ISO** to the optical drive.

## 2. Boot & start the installer

Start the VM → at the boot menu choose **Install Rocky Linux** → pick language →
**Continue** → you land on the **Installation Summary** hub.

> Tip: if the mouse gets captured by the VM, press the **right Ctrl** key.

## 3. Work the Installation Summary hub

Clear each item, then **Begin Installation**:

- **Installation Destination:** click in, leave automatic partitioning, **Done**.
  (Custom `/boot` + swap + LVM is a nice RHCSA exercise but not required here.)
- **Root Account:** **Disable root account**.
- **User Creation:**
  - User name: **`student`**
  - ✅ **Make this user administrator**  ← critical: this is your sudo
  - ✅ Require a password; set one you'll remember (e.g. `student123`)
- **Software Selection:** **Minimal Install**.
- **Time & Date:** set your timezone.

## 4. Finish & reboot

Let it install → **Reboot System** → the ISO ejects → it boots your new system →
log in as **`student`**.

## 5. Enable SSH (the door the engine knocks on)

```bash
sudo systemctl enable --now sshd
ip a
```

Find the `inet 192.168.56.x` line under the host-only adapter (`enp0s8` or
similar). That address + port 22 is what you give the prologue at the handshake.

## 6. Hand back to the engine

Return to the prologue and enter the address, port, username (`student`) and the
password you set. The engine installs its key, verifies sudo, confirms sshd,
takes the `clean-baseline` snapshot — and your server is live.
