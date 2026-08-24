---
status: draft
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# vms

## Goal

A `vms` role for really simple virtual machines: one instanced
`vm@.service` template unit that starts qemu directly. systemd *is* the
hypervisor manager — no libvirt, no XML, no extra daemon. A VM is a
unit instance (`vm@webtest.service`) plus one qemu config file;
everything you already know about units (enable, restart, journal,
resource limits) applies to VMs unchanged.

## Scope

- **Packages.** Install `qemu-system-x86` (and OVMF for UEFI guests).
- **Users & access.** Two principals:
  - `vm-run` — system user qemu runs as, member of `kvm` (a system
    user has no logind seat, so the desktop uaccess ACL on `/dev/kvm`
    does not apply; group membership is the mechanism).
  - `vm-admin` — group for humans operating VMs: read/write on each
    VM's console and QMP sockets, and a polkit rule
    (`/etc/polkit-1/rules.d/`) allowing members to manage
    `vm@*.service` units (start/stop/restart via
    `org.freedesktop.systemd1.manage-units`, matched on the unit
    name) without sudo.
- **Template unit.** Ship `/etc/systemd/system/vm@.service` with the
  managed-file header per [coding conventions](../improve/coding.md).
  `User=vm-run`, `Group=vm-admin`, `UMask=0007`. The unit carries
  *policy*, the config file carries *the VM*:

  ```
  ExecStart=/usr/bin/qemu-system-x86_64 -nodefaults -display none \
      -cpu host -name %i -readconfig /etc/vms/%i.cfg
  ```

- **Per-VM config.** `/etc/vms/<name>.cfg` is qemu's native
  `-readconfig` format: `[machine]` (type, accel), `[memory]`,
  `[smp-opts]`, `[drive]`, `[netdev]`, `[device]`, `[chardev]`. The
  role templates it from an inventory dict `vms_instances`, one entry
  per VM — but a hand-written file works identically, and
  `systemctl start vm@<name>` just runs it. Removing an inventory
  entry stops and disables the instance and removes the config; disk
  images are never deleted.
- **Per-VM run dir.** `RuntimeDirectory=vms/%i`
  (`RuntimeDirectoryMode=0750`) → `/run/vms/<name>/`, owned
  `vm-run:vm-admin`, created and cleaned up by systemd with the
  unit. It holds the QMP socket (`qmp`) and serial console socket
  (`console`) as `[chardev]` entries; with `UMask=0007` the sockets
  come out `0660 vm-run:vm-admin`, so `vm-admin` members can attach
  (`socat - UNIX-CONNECT:/run/vms/<name>/console`).
- **Escape hatch.** qemu merges `-readconfig` with further CLI args,
  so a per-instance drop-in (`vm@<name>.service.d/`) appending args
  covers anything the config format can't express. Resource limits
  (`MemoryMax=`, `CPUQuota=`) go in drop-ins too.
- **Disks.** The role creates a qcow2 of configured size under
  `vms_disk_dir` (default `/var/lib/vms/`, owned `vm-run`) if the
  image doesn't exist yet. Putting an OS on it is out of scope —
  that's [os-bootstrap](os-bootstrap.feature.md) territory.
- **Graceful shutdown.** `ExecStop` sends `system_powerdown` over
  QMP; qemu exits when the guest halts, `TimeoutStopSec` is the
  backstop.
- **Networking.** Default is qemu user-mode networking (zero host
  configuration). `vms_with_bridge` enables bridged NICs via
  `qemu-bridge-helper`:
  - Debian ships the helper inert (`0755 root:root`, no ACL file).
    The role activates it scoped: `dpkg-statoverride` to
    `4750 root:vm-run` — setuid, executable only by the qemu user,
    not a host-wide grant.
  - The role writes `/etc/qemu/bridge.conf` from `vms_bridge_allow`,
    default `["all"]` → `allow all`. Restrictive sites set the list
    to specific bridges (`allow br-lan` …); ACL semantics are
    default-deny with deny-overrides-allow. Bridges themselves are
    assumed to exist — host network config is a different concern.
  - A VM on multiple networks is just multiple `[netdev]`/`[device]`
    pairs naming different bridges. Taps are created with vnet
    headers (`--use-vnet`, added by qemu automatically for virtio) —
    required for GSO/checksum offload throughput.
- **Web console** (`vms_with_web_console: false` default). Browser
  access to each VM's graphical console, same router shape as
  [ttyd](ttyd.feature.md) / [code-server](code-server.feature.md) —
  unix sockets only, no TCP ports anywhere:
  - Each VM's config gains `[vnc]` on a unix socket
    (`/run/vms/<name>/vnc` — `[vnc]` is a verified `-readconfig`
    group), reachable only by `vm-run`/`vm-admin` like the other
    sockets.
  - A `websockify@.service` template instance per VM
    (`PartOf=vm@%i.service`) bridges it to a websocket unix socket:
    `websockify --unix-listen=/run/vms/%i/websock
    --unix-listen-mode=0660 --unix-target=/run/vms/%i/vnc`
    (unix-listen verified in trixie's websockify 0.12.0 — the
    release that added it). The socket is owned
    `vm-run:https-socket-access` so the reverse proxy can connect —
    the same socket-group pattern as ttyd. The run dir
    stays `0750 vm-run:vm-admin`; `https-socket-access` gets a
    traverse-only ACL on it (one `ExecStartPre=+setfacl` line in
    `websockify@`).
  - **Single vhost** `vms.<host>` (configurable): serves the static
    noVNC client (Debian `novnc` package), proxies
    `/<name>/websock` to that VM's socket, oauth2-proxy
    forward_auth in front. One vhost, N VMs — path routing by VM
    name, since any authorized operator may open any console
    (matching the `vm-admin` trust model).
  - Caddy-fragment auto-deploy option like ttyd
    (`vms_configure_caddy`).
- **Lifecycle.** The role enables/starts `vm@<name>` per instance,
  honoring a per-VM `autostart` flag.

## Design notes

### Why `-readconfig` (and not an env-file schema or a wrapper)

Three candidates for feeding qemu its configuration:

1. **EnvironmentFile + arg line in the unit** — invents a role-owned
   schema; every new need means growing the role, and systemd's
   unquoted `$VAR` word-splitting makes the extra-args escape hatch
   fragile.
2. **`-readconfig`** — the per-VM file is qemu's own documented
   format; we invent nothing, and the file is the whole truth about
   the VM.
3. **Wrapper script reading an args file** — fully general, but puts
   glue code between systemd and qemu and invents a format anyway.

Option 2 wins: two native formats (systemd unit + qemu config), zero
glue.

### What `-readconfig` cannot express

Config-file sections only exist for options backed by a registered
`QemuOpts` group (`qemu_config_parse()` in `util/qemu-config.c`,
groups registered in `system/vl.c`). Options implemented outside that
mechanism have no config-file spelling — verified against qemu
10.0.11 (trixie): `[cpu]`, `[display]`, `[nographic]` and
`[nodefaults]` are rejected with `There is no option group '...'`,
while `[machine]`, `[memory]`, `[smp-opts]`, `[drive]`, `[netdev]`,
`[device]`, `[chardev]`, `[vnc]` and `[spice]` are accepted. There is
no upstream document enumerating the groups; coverage is verified
empirically per option.

The gaps align with the unit=policy split, and upstream agrees: the
example configs qemu ships (`/usr/share/doc/qemu-system-common/
config/q35-virtio-serial.cfg`) use exactly this invocation shape —
`-nodefaults -readconfig <file> -display none -serial mon:stdio`,
machine/memory/drives/devices in the file.

QAPI-only options (`-blockdev`, JSON `-object`) also have no
config-file form; a VM that truly needs them uses the drop-in escape
hatch. `[drive]` is not deprecated and covers the simple-VM case.

### Access model

`vm-run` owns the processes, `vm-admin` owns the humans. Console and
QMP arrive via socket group-ownership; unit control arrives via
polkit, matched to `vm@*.service` only — no sudo, no wrapper
scripts. Note QMP access is powerful (device hotplug etc.), but
`vm-admin` members can restart units anyway, so the trust boundary
is consistent: `vm-admin` administers VMs, full stop.

### Networking notes

- **The bridge helper**, precisely: a small setuid C binary
  (`qemu-bridge-helper.c`) that qemu execs per bridged NIC. It
  checks the bridge against the ACL, creates a tap
  (kernel-assigned `tap%d` name), attaches it (`SIOCBRADDIF`),
  passes the open fd back over a unix socket, and exits. Its whole
  config surface: `--use-vnet/--br/--fd` plus
  `allow`/`deny`/`include` in `bridge.conf`.
- **Known limits** (accepted for this role's trusted-guest scope):
  tap names are kernel-picked and never reported, so per-port
  policy — MAC locking (`bridge link set … locked on` + static
  fdb), ARP-spoofing filters, per-port VLANs — cannot be attached;
  and `SIOCBRADDIF` only works on kernel bridges, not OVS. A future
  `vms_with_port_security` would switch to role-created named taps
  (`ip tuntap add vm-<name> … user vm-run vnet_hdr` in
  `ExecStartPre=+`, qemu opens by `ifname=`), which also covers
  OVS/OVN attachment. Same `[netdev]` mechanism, different tap
  provenance — the config format absorbs either.
- **Multi-host VM networks** need no new machinery in the role:
  enslave a kernel VXLAN device into the same bridge on each host
  (over WireGuard when the underlay is untrusted) and the L2 spans
  machines. Host network config, out of scope here. Full SDN (OVN)
  is the scale-up path beyond this role — at that point use incus.
- **Rejected:** qemu's `socket`/`dgram`/`stream`/`hubport` backends
  (hub semantics, no uplink, qemu-main-loop slow path) and vde
  (userspace switch, dormant, still needs a privileged uplink).

### Other notes

- The systemd toolbox is the VM toolbox: `systemctl status
  vm@webtest`, `journalctl -u vm@webtest`, resource control via
  drop-ins instead of hypervisor tunables.
- This deliberately overlaps with libvirt/incus. Those are right for
  fleets, migration, snapshot features; this role is for the host
  that needs two or three long-lived VMs and no new mental model.
  (`test-in-vms.yaml` uses incus for disposable test VMs — a
  different job.)
- qemu's default NIC MAC is identical for every VM — `vms_instances`
  entries carry a fixed `mac`, or the role derives a stable one from
  the VM name.
- The web console uses the same ingredients as Debian's
  `qemu-web-desktop` (DARTS: qemu + websockify + noVNC) but composed
  our way: DARTS is a session-oriented web app spawning ephemeral
  desktop VMs behind its own Apache/Perl/dnsmasq stack; here the VMs
  are declarative systemd services and the console is just another
  group-owned socket behind the existing reverse-proxy +
  oauth2-proxy pattern.

## Open questions

- BIOS or UEFI (OVMF) as default firmware? UEFI adds a per-VM nvram
  vars file — a second stateful file per VM.
- slirp or passt as the user-mode default? passt is the modern slirp
  replacement (unprivileged per-VM process, better security record,
  already in trixie), but needs an `ExecStartPre` companion process
  and a `[netdev] stream` attachment.
- Offer a cloud-init NoCloud seed ISO behind `vms_with_cloud_init`,
  or leave that entirely to [os-bootstrap](os-bootstrap.feature.md)?
- Should the guest console also be logged to the journal, or live
  only on the socket?
- Does the polkit rule need `manage-unit-files` (enable/disable) too,
  or is start/stop/restart enough for `vm-admin`?
