#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import getpass
from collections import OrderedDict


def run(cmd, check=True, capture=True, **kwargs):
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
        kwargs["text"] = True
    result = subprocess.run(cmd, **kwargs)
    if check and result.returncode != 0:
        print("\n[ERROR] Command failed:", " ".join(cmd) if isinstance(cmd, list) else cmd)
        if capture:
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
        sys.exit(1)
    return result


def find_disk():
    for pattern in ["/dev/sda", "/dev/nvme0n1", "/dev/vda", "/dev/mmcblk0"]:
        if os.path.exists(pattern):
            return pattern
    result = subprocess.run(
        ["lsblk", "-dno", "NAME", "-e", "7,11,1,2"],
        capture_output=True, text=True, check=True
    )
    for d in result.stdout.strip().split():
        full = f"/dev/{d}"
        if os.path.exists(full) and "loop" not in d and "ram" not in d:
            return full
    return None


CATEGORIES = OrderedDict()

CATEGORIES["X11 Desktops"] = OrderedDict([
    ("Budgie",       ["budgie-desktop"]),
    ("Cinnamon",     ["cinnamon"]),
    ("Deepin",       ["deepin", "deepin-extra"]),
    ("Enlightenment",["enlightenment", "terminology"]),
    ("GNOME Flashback", ["gnome-flashback"]),
    ("LXDE",         ["lxde"]),
    ("LXQt",         ["lxqt"]),
    ("MATE",         ["mate", "mate-extra"]),
    ("Pantheon",     ["pantheon"]),
    ("Sugar",        ["sugar", "sugar-fructose"]),
    ("Xfce",         ["xfce4", "xfce4-goodies"]),
])

CATEGORIES["Wayland Desktops"] = OrderedDict([
    ("COSMIC",       ["cosmic"]),
    ("GNOME",        ["gnome", "gnome-tweaks"]),
    ("KDE Plasma",   ["plasma-meta", "kde-applications-meta"]),
])

CATEGORIES["Window Managers"] = OrderedDict([
    ("Blackbox",     ["blackbox"]),
    ("Fluxbox",      ["fluxbox"]),
    ("FVWM3",        ["fvwm3"]),
    ("IceWM",        ["icewm", "icewm-utils"]),
    ("JWM",          ["jwm"]),
    ("KWin (X11)",   ["kwin-x11"]),
    ("Marco",        ["marco"]),
    ("Metacity",     ["metacity"]),
    ("Muffin",       ["muffin"]),
    ("Openbox",      ["openbox", "obconf", "lxappearance"]),
    ("PekWM",        ["pekwm"]),
    ("twm",          ["xorg-twm"]),
    ("Window Maker", ["windowmaker"]),
    ("Xfwm",         ["xfwm4"]),
    ("bspwm",        ["bspwm", "sxhkd", "polybar"]),
    ("Herbstluftwm", ["herbstluftwm"]),
    ("i3",           ["i3-wm", "i3status", "i3lock", "dmenu"]),
    ("LeftWM",       ["leftwm"]),
    ("Notion",       ["notion"]),
    ("Ratpoison",    ["ratpoison"]),
    ("StumpWM",      ["stumpwm"]),
    ("awesome",      ["awesome"]),
    ("Qtile",        ["qtile"]),
    ("spectrwm",     ["spectrwm"]),
    ("xmonad",       ["xmonad", "xmonad-contrib"]),
    ("labwc",        ["labwc"]),
    ("wayfire",      ["wayfire", "wf-config", "wlogout"]),
    ("Weston",       ["weston"]),
    ("niri",         ["niri"]),
    ("Sway",         ["sway", "swaybg", "waybar", "wofi", "alacritty", "mako"]),
    ("Hyprland",     ["hyprland", "hyprpaper", "hyprlock", "noto-fonts", "kitty"]),
    ("river",        ["river"]),
    ("Cage",         ["cage"]),
])


def show_menu(items, selected, title):
    while True:
        print(f"\n── {title} ──")
        keys = list(items.keys())
        for i, name in enumerate(keys, 1):
            mark = "[*]" if selected.get(name) else "[ ]"
            print(f"  {i:2d}. {mark} {name}")
        print("  (b) Back  (a) All  (n) None  (d) Done")

        choice = input("> ").strip().lower()

        if choice == "b":
            return "back"
        if choice == "a":
            for k in keys:
                selected[k] = True
            continue
        if choice == "n":
            for k in keys:
                selected[k] = False
            continue
        if choice == "d":
            return "done"

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                name = keys[idx]
                selected[name] = not selected.get(name)
            else:
                print("Invalid number.")
        except ValueError:
            print("Invalid input.")


def main_menu(categories):
    selected = {}
    cat_keys = list(categories.keys())

    while True:
        print("\n═══════════════════════════════════")
        print("       DESKTOP / WM SELECTION")
        print("═══════════════════════════════════")
        for i, cat in enumerate(cat_keys, 1):
            count = sum(1 for name in categories[cat] if selected.get(name))
            print(f"  {i}. {cat} ({count} selected)")
        print("  d. Done / Install")
        print("  q. Quit")

        choice = input("> ").strip().lower()

        if choice == "q":
            print("Aborted.")
            sys.exit(0)
        if choice == "d":
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(cat_keys):
                cat = cat_keys[idx]
                result = show_menu(categories[cat], selected, cat)
                if result == "done":
                    break
            else:
                print("Invalid number.")
        except ValueError:
            print("Invalid input.")

    pkgs = []
    for cat in categories:
        for name, pkg_list in categories[cat].items():
            if selected.get(name):
                pkgs.extend(pkg_list)
    return list(set(pkgs))


def main():
    if os.geteuid() != 0:
        print("FATAL: This script must be run as root.")
        sys.exit(1)

    if not os.path.isfile("/etc/arch-release"):
        print("FATAL: This script must be run from the Arch ISO.")
        sys.exit(1)

    disk = find_disk()
    if not disk:
        print("FATAL: No suitable disk found.")
        sys.exit(1)

    print(f"\nDisk: {disk}")
    print("WARNING: ALL DATA on this disk will be DESTROYED!")
    print("Type 'yes' to continue:", end=" ")
    if input().strip().lower() != "yes":
        print("Aborted.")
        sys.exit(0)

    username = ""
    while not username:
        username = input("Username: ").strip()

    password = getpass.getpass("Password: ")
    password2 = getpass.getpass("Confirm password: ")
    if password != password2:
        print("Passwords do not match!")
        sys.exit(1)

    extra_pkgs = main_menu(CATEGORIES)
    if extra_pkgs:
        print(f"\nSelected {len(extra_pkgs)} packages.")
    else:
        print("\nNo desktop/WM selected. Only base system will be installed.")

    p = "" if "nvme" not in disk and "mmc" not in disk else "p"
    root_part = f"{disk}{p}2"
    efi_part = f"{disk}{p}1"

    print("\n[1/7] Partitioning disk...")
    run(["sgdisk", "--zap-all", disk])
    run(["sgdisk", "--clear", disk])
    run(["sgdisk", "-n1:0:+1G", "-t1:ef00", disk])
    run(["sgdisk", "-n2:0:0", "-t2:8300", disk])

    print("[2/7] Formatting partitions...")
    run(["mkfs.fat", "-F32", efi_part])
    run(["mkfs.btrfs", "-f", root_part])

    print("[3/7] Creating btrfs subvolume...")
    tmp = "/mnt/tmp_btrfs"
    os.makedirs(tmp, exist_ok=True)
    run(["mount", root_part, tmp])
    run(["btrfs", "subvolume", "create", f"{tmp}/@"])
    run(["umount", tmp])
    os.rmdir(tmp)

    print("[4/7] Mounting partitions...")
    run(["mount", "-o", "subvol=@", root_part, "/mnt"])
    os.makedirs("/mnt/boot", exist_ok=True)
    run(["mount", efi_part, "/mnt/boot"])

    base_pkgs = [
        "base", "linux", "linux-firmware",
        "btrfs-progs", "sudo", "networkmanager",
        "python", "python-pip",
        "grub", "efibootmgr",
        "amd-ucode", "intel-ucode",
        "ly", "git", "xorg-server", "xorg-xinit", "xorg-xauth", "mesa",
        "pipewire", "pipewire-pulse", "pipewire-alsa", "pipewire-jack",
        "wireplumber", "alsa-utils", "sof-firmware",
        "bluez", "bluez-utils", "bluez-libs", "bluez-obex",
        "libspa-bluetooth",
        "noto-fonts", "noto-fonts-emoji", "noto-fonts-cjk", "noto-fonts-extra",
        "ttf-dejavu", "ttf-liberation", "ttf-ubuntu-font-family",
        "ttf-roboto", "ttf-opensans", "ttf-fira-code",
        "ttf-hack", "ttf-jetbrains-mono", "ttf-inconsolata",
        "ttf-font-awesome", "ttf-material-design-icons",
        "ttf-croscore", "ttf-caladea", "ttf-carlito",
        "adobe-source-code-pro-fonts",
    ]
    base_pkgs = [p for p in base_pkgs if p]
    all_pkgs = base_pkgs + extra_pkgs

    print(f"[5/7] Installing base system ({len(all_pkgs)} packages)...")
    run(["pacstrap", "/mnt"] + all_pkgs)

    print("[6/7] Configuring system...")
    setup_script = f"""#!/bin/bash
set -e
ln -sf /usr/share/zoneinfo/Europe/Istanbul /etc/localtime
hwclock --systohc
sed -i 's/#en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen
locale-gen
echo 'LANG=en_US.UTF-8' > /etc/locale.conf
echo 'archlinux' > /etc/hostname
cat > /etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   archlinux.localdomain archlinux
EOF
echo -e 'root\\nroot' | passwd
useradd -m -G wheel {username}
echo -e '{password}\\n{password}' | passwd {username}
echo '%wheel ALL=(ALL:ALL) NOPASSWD: ALL' >> /etc/sudoers
systemctl enable NetworkManager
systemctl enable bluetooth
systemctl enable ly@tty2.service
systemctl disable getty@tty2.service 2>/dev/null || true
systemctl --global enable pipewire pipewire-pulse wireplumber
pacman-key --recv-keys F3B607488DB35A47 --keyserver keyserver.ubuntu.com || true
pacman-key --lsign-key F3B607488DB35A47 || true
pacman -U --noconfirm \
  'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-keyring-20240331-1-any.pkg.tar.zst' \
  'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-mirrorlist-27-1-any.pkg.tar.zst' \
  'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v3-mirrorlist-27-1-any.pkg.tar.zst' \
  'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v4-mirrorlist-27-1-any.pkg.tar.zst' || true
if /lib/ld-linux-x86-64.so.2 --help 2>/dev/null | grep -q "x86-64-v4 (supported, searched)"; then
  cat >> /etc/pacman.conf << 'REPOEOF'

[cachyos-v4]
Include = /etc/pacman.d/cachyos-v4-mirrorlist
[cachyos-core-v4]
Include = /etc/pacman.d/cachyos-v4-mirrorlist
[cachyos-extra-v4]
Include = /etc/pacman.d/cachyos-v4-mirrorlist
[cachyos]
Include = /etc/pacman.d/cachyos-mirrorlist
REPOEOF
elif /lib/ld-linux-x86-64.so.2 --help 2>/dev/null | grep -q "x86-64-v3 (supported, searched)"; then
  cat >> /etc/pacman.conf << 'REPOEOF'

[cachyos-v3]
Include = /etc/pacman.d/cachyos-v3-mirrorlist
[cachyos-core-v3]
Include = /etc/pacman.d/cachyos-v3-mirrorlist
[cachyos-extra-v3]
Include = /etc/pacman.d/cachyos-v3-mirrorlist
[cachyos]
Include = /etc/pacman.d/cachyos-mirrorlist
REPOEOF
else
  cat >> /etc/pacman.conf << 'REPOEOF'

[cachyos]
Include = /etc/pacman.d/cachyos-mirrorlist
REPOEOF
fi
pacman -Sy --noconfirm
pacman -S --noconfirm linux-cachyos linux-cachyos-headers
pacman -S --noconfirm nvidia-open-dkms nvidia-utils nvidia-settings \
  lib32-nvidia-utils nvidia-prime opencl-nvidia egl-wayland
pacman -Rdd --noconfirm linux 2>/dev/null || true
sed -i 's/^MODULES=()/MODULES=(nvidia nvidia_modeset nvidia_uvm nvidia_drm)/' /etc/mkinitcpio.conf
mkinitcpio -P
rm -rf /tmp/yay 2>/dev/null || true
su - {username} -c "cd /tmp && git clone https://aur.archlinux.org/yay.git /tmp/yay && cd /tmp/yay && makepkg -si --noconfirm"
rm -rf /tmp/yay
for dm in gdm sddm lightdm lxdm; do
    if systemctl list-unit-files --type=service 2>/dev/null | grep -q "$dm"; then
        systemctl disable "$dm" 2>/dev/null || true
    fi
done
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg
truncate -s 0 /swapfile
chattr +C /swapfile
btrfs property set /swapfile compression none
dd if=/dev/zero of=/swapfile bs=1M count=16384 2>/dev/null
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap defaults 0 0' >> /etc/fstab
rm -rf /var/cache/pacman/pkg/*
rm -rf /home/{username}/.cache/*
rm -rf /tmp/*
pacman -Sc --noconfirm
"""

    with open("/mnt/setup.sh", "w") as f:
        f.write(setup_script)
    result = subprocess.run(
        ["arch-chroot", "/mnt", "bash", "/setup.sh"],
        capture_output=True, text=True
    )
    os.remove("/mnt/setup.sh")
    if result.returncode != 0:
        print("\n[ERROR] Chroot configuration failed")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        sys.exit(1)

    print("[7/7] Generating fstab...")
    result = subprocess.run(
        ["genfstab", "-U", "/mnt"],
        capture_output=True, text=True, check=True
    )
    with open("/mnt/etc/fstab", "w") as f:
        f.write(result.stdout)

    print("Unmounting...")
    run(["umount", "-R", "/mnt"])

    print("\nDone! Rebooting in 5 seconds...")
    print(f"User: {username}")
    time.sleep(5)
    run(["reboot"], check=False)


if __name__ == "__main__":
    main()
​
