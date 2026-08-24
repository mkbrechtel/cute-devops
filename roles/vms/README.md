<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# vms

Really simple virtual machines: one instanced `vm@.service` template
unit that starts qemu directly. systemd *is* the hypervisor manager —
no libvirt, no XML, no extra daemon. A VM is a unit instance
(`vm@webtest.service`) plus one qemu config file
(`/etc/vms/webtest.cfg`, qemu's native `-readconfig` format).

Everything you already know about units applies to VMs unchanged:

```bash
systemctl status vm@webtest
journalctl -u vm@webtest
socat - UNIX-CONNECT:/run/vms/webtest/console   # serial console
```

See [the feature documentation](../../docs/features/vms.md) for the
design and its rationale.

## Requirements

- Debian 13/trixie with KVM (`/dev/kvm`)
- For `vms_with_bridge`: the bridges must already exist
- For `vms_configure_caddy`: a Caddy that includes
  `/etc/caddy/conf.d/*`

## Role Variables

See `defaults/main.yml` for all variables and defaults.

- `vms_instances` (default: `{}`) - The VMs, one entry per name. Keys
  per VM (all optional): `memory` (`"1G"`), `cpus` (`1`), `disk_size`
  (`"10G"`), `networks` (list of bridge names; absent → user-mode
  NIC), `mac` (first NIC; default derived from the name), `autostart`
  (`true`), `extra_config` (raw lines appended to the config file).
  Removing an entry stops and disables the VM and removes its config;
  disk images are never deleted.
- `vms_disk_dir` (default: `/var/lib/vms`) - qcow2 images, created if
  missing
- `vms_run_user` (default: `vm-run`) - system user qemu runs as,
  member of `kvm`
- `vms_admin_group` (default: `vm-admin`) - members get the console
  and QMP sockets and may start/stop/restart `vm@*.service` via
  polkit
- `vms_with_bridge` (default: `false`) - bridged NICs via
  `qemu-bridge-helper`: setuid `4750 root:vm-run` via
  `dpkg-statoverride`, ACL in `/etc/qemu/bridge.conf`
- `vms_bridge_allow` (default: `["all"]`) - bridges the helper may
  attach to
- `vms_with_web_console` (default: `false`) - per-VM VNC unix socket,
  `websockify@` bridge, noVNC client behind a Caddy vhost. Unix
  sockets only, all in the VM's run dir
- `vms_https_socket_group` (default: `https-socket-access`) - group
  the reverse proxy uses to reach the websocket sockets
- `vms_configure_caddy` (default: `true`) - deploy the vhost fragment
  to `/etc/caddy/conf.d/` (only acts with the web console on)
- `vms_web_console_vhost` (default: `vms.<hostname>.<domain>`) - the
  web console vhost
- `vms_caddy_extra` (default: `""`) - raw lines at the top of the
  vhost, e.g. a `forward_auth` block for oauth2-proxy

## Notes

- The unit is policy (`-nodefaults -display none -cpu host
  -readconfig`), the config file is the VM. Per-instance overrides —
  resource limits, extra qemu args — go in a `vm@<name>.service.d/`
  drop-in.
- Config changes apply on the VM's next restart; the role never
  restarts a running guest.
- Stopping a VM sends ACPI `system_powerdown` over QMP;
  `TimeoutStopSec=120` is the backstop.
- A hand-written `/etc/vms/<name>.cfg` works identically:
  `systemctl start vm@<name>` just runs it.
- Installing an OS is not this role's job: boot an installer ISO via
  `extra_config` (a `[drive]` with `media = "cdrom"`), or provision
  images externally.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: vmhosts
  become: yes
  roles:
    - role: osahris.cute_devops.vms
      vars:
        vms_with_bridge: true
        vms_bridge_allow: [br-lan]
        vms_instances:
          webtest:
            memory: "2G"
            cpus: 2
            disk_size: "20G"
            networks: [br-lan]
          scratch: {}
```
