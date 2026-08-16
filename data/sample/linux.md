# Linux admin basics

## Users
`whoami` prints the current user. `id` shows uid/gid. `usermod -aG sudo alice` grants sudo.

## Disk
`df -h` is filesystem usage. `du -sh *` is directory size. `find /var -name '*.log'` finds files.

## Services
On systemd: `systemctl status nginx`, `journalctl -u nginx -n 100`.
