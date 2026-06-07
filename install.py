#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import getpass
from collections import OrderedDict


# ─── TUI Helpers ─────────────────────────────────────────────────────────

BOX_W = 66
_last_box = 0


def inner():
    return BOX_W - 4


def box_top(title=""):
    global _last_box
    _last_box = 0
    w = BOX_W - 2
    if title:
        n = len(title)
        print("┌─ " + title + " " + "─" * (w - n - 3) + "┐")
    else:
        print("┌" + "─" * w + "┐")
    _last_box += 1


def box_line(text="", c="center"):
    global _last_box
    iw = inner()
    if c == "center":
        t = text.center(iw)
    elif c == "left":
        t = text.ljust(iw)
    else:
        t = text.rjust(iw)
    print("│ " + t + " │")
    _last_box += 1


def box_input(prompt, hidden=False):
    global _last_box
    iw = inner()
    p = prompt.ljust(iw)
    print("│ " + p + " │")
    sys.stdout.write("│ ")
    _last_box += 2
    if hidden:
        val = getpass.getpass("")
    else:
        val = input("")
    sys.stdout.write("\033[2K\033[1A\033[2K\r")  # clear both lines, return to col 0
    _last_box -= 2
    return val.strip()


def box_bot():
    global _last_box
    w = BOX_W - 2
    print("└" + "─" * w + "┘")
    _last_box += 1


def box_puts(lines):
    global _last_box
    if _last_box:
        sys.stdout.write(f"\033[{_last_box}A\033[J")
        _last_box = 0
    box_top("Arch Linux Quick Installer")
    box_line()
    for line in lines:
        if isinstance(line, tuple):
            box_line(line[0], line[1])
        else:
            box_line(str(line))
    box_line()
    box_bot()


def box_status(msg, detail=None):
    lines = [("\033[33m" + msg + "\033[0m", "center")]
    if detail:
        lines.append(("\033[90m" + detail + "\033[0m", "center"))
    box_puts(lines)


def box_fail(msg, stdout="", stderr=""):
    w = BOX_W - 2
    print("\033[31m┌" + "─" * w + "┐\033[0m")
    iw = inner()
    t = msg.center(iw)
    print("\033[31m│ " + t + " │\033[0m")
    print("\033[31m└" + "─" * w + "┘\033[0m")
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)
    sys.exit(1)


def run(cmd, check=True, capture=True, **kwargs):
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
        kwargs["text"] = True
    result = subprocess.run(cmd, **kwargs)
    if check and result.returncode != 0:
        box_fail(
            f"Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}",
            result.stdout if capture else "",
            result.stderr if capture else "",
        )
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


# ─── Menu data ──────────────────────────────────────────────────────────

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
    # ── X11 Stacking ──
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
    # ── X11 Tiling ──
    ("bspwm",        ["bspwm", "sxhkd", "polybar"]),
    ("Herbstluftwm", ["herbstluftwm"]),
    ("i3",           ["i3-wm", "i3status", "i3lock", "dmenu"]),
    ("LeftWM",       ["leftwm"]),
    ("Notion",       ["notion"]),
    ("Ratpoison",    ["ratpoison"]),
    ("StumpWM",      ["stumpwm"]),
    # ── X11 Dynamic ──
    ("awesome",      ["awesome"]),
    ("Qtile",        ["qtile"]),
    ("spectrwm",     ["spectrwm"]),
    ("xmonad",       ["xmonad", "xmonad-contrib"]),
    # ── Wayland Stacking ──
    ("labwc",        ["labwc"]),
    ("wayfire",      ["wayfire", "wf-config", "wlogout"]),
    ("Weston",       ["weston"]),
    # ── Wayland Tiling ──
    ("niri",         ["niri"]),
    ("Sway",         ["sway", "swaybg", "waybar", "wofi", "alacritty", "mako"]),
    # ── Wayland Dynamic ──
    ("Hyprland",     ["hyprland", "hyprpaper", "hyprlock", "noto-fonts", "kitty"]),
    ("river",        ["river"]),
    # ── Other Wayland ──
    ("Cage",         ["cage"]),
])

# ─── Menu helper ────────────────────────────────────────────────────────

def show_menu(items, selected, title):
    while True:
        lines = []
        lines.append(("\033[33m" + title + "\033[0m", "center"))
        lines.append("")
        keys = list(items.keys())
        for i, name in enumerate(keys, 1):
            mark = "\033[32m[*]\033[0m" if selected.get(name) else "\033[90m[ ]\033[0m"
            lines.append(f"  {i:2d}. {mark} \033[0m{name}")
        lines.append("")
        lines.append(("\033[90m(b) Back  (a) All  (n) None  (d) Done\033[0m", "center"))
        box_puts(lines)
        val = box_input("Choice:")
        if val == "b":
            return "back"
        if val == "a":
            for k in keys:
                selected[k] = True
            continue
        if val == "n":
            for k in keys:
                selected[k] = False
            continue
        if val == "d":
            return "done"
        try:
            idx = int(val) - 1
            if 0 <= idx < len(keys):
                name = keys[idx]
                selected[name] = not selected.get(name)
            else:
                pass
        except ValueError:
            pass


def main_menu(categories):
    selected = {}
    cat_keys = list(categories.keys())

    while True:
        lines = []
        lines.append(("\033[33mDesktop / Window Manager Selection\033[0m", "center"))
        lines.append("")
        for i, cat in enumerate(cat_keys, 1):
            count = sum(1 for name in categories[cat] if selected.get(name))
            lines.append(f"  {i}. \033[36m{cat}\033[0m ({count} selected)")
        lines.append("")
        lines.append(("\033[90m(d) Done / Install  (q) Quit\033[0m", "center"))
        box_puts(lines)
        val = box_input("Choice:")
        if val == "q":
            print("Aborted.")
            sys.exit(0)
        if val == "d":
            break
        try:
            idx = int(val) - 1
            if 0 <= idx < len(cat_keys):
                cat = cat_keys[idx]
                result = show_menu(categories[cat], selected, cat)
                if result == "done":
                    break
            else:
                pass
        except ValueError:
            pass

    # Gather selected packages
    pkgs = []
    for cat in categories:
        for name, pkg_list in categories[cat].items():
            if selected.get(name):
                pkgs.extend(pkg_list)
    return list(set(pkgs))  # deduplicate


# ─── Main installer ────────────────────────────────────────────────────

def main():
    if os.geteuid() != 0:
        box_fail("This script must be run as root.")

    if not os.path.isfile("/etc/arch-release"):
        box_fail("This script must be run from the Arch ISO.")

    # ── Disk ──
    box_status("Detecting disk...")
    disk = find_disk()
    if not disk:
        box_fail("No suitable disk found.")

    box_puts([
        ("\033[33mPre-installation Setup\033[0m", "center"),
        "",
        f"Disk detected: \033[36m{disk}\033[0m",
        ("\033[31mALL DATA on this disk will be DESTROYED!\033[0m", "center"),
        "",
    ])
    if box_input("Type 'yes' to continue:") != "yes":
        box_fail("Aborted.")

    # ── User info ──
    box_puts([
        ("\033[33mUser Setup\033[0m", "center"),
        "",
    ])
    username = ""
    while not username:
        username = box_input("Username:")
    password = box_input("Password:", hidden=True)
    password2 = box_input("Confirm password:", hidden=True)
    if password != password2:
        box_fail("Passwords do not match!")

    # ── DE/WM selection ──
    extra_pkgs = main_menu(CATEGORIES)
    if extra_pkgs:
        box_puts([f"Selected {len(extra_pkgs)} packages."])
    else:
        box_puts(["No desktop/WM selected. Only base system will be installed."])

    p = "" if "nvme" not in disk and "mmc" not in disk else "p"
    root_part = f"{disk}{p}2"
    efi_part = f"{disk}{p}1"

    # ── Partitioning ──
    box_status("Wiping disk and creating partitions")
    run(["sgdisk", "--zap-all", disk])
    run(["sgdisk", "--clear", disk])
    run(["sgdisk", "-n1:0:+1G", "-t1:ef00", disk])
    run(["sgdisk", "-n2:0:0", "-t2:8300", disk])

    box_status("Formatting EFI partition (FAT32)")
    run(["mkfs.fat", "-F32", efi_part])

    box_status("Formatting root partition (Btrfs)")
    run(["mkfs.btrfs", "-f", root_part])

    # ── Subvolume ──
    box_status("Creating btrfs subvolume")
    tmp = "/mnt/tmp_btrfs"
    os.makedirs(tmp, exist_ok=True)
    run(["mount", root_part, tmp])
    run(["btrfs", "subvolume", "create", f"{tmp}/@"])
    run(["umount", tmp])
    os.rmdir(tmp)

    # ── Mount ──
    box_status("Mounting partitions")
    run(["mount", "-o", "subvol=@", root_part, "/mnt"])
    os.makedirs("/mnt/boot", exist_ok=True)
    run(["mount", efi_part, "/mnt/boot"])

    # ── Base install ──
    base_pkgs = [
        "base", "linux", "linux-firmware",
        "btrfs-progs", "sudo", "networkmanager",
        "python", "python-pip",
        "grub", "efibootmgr",
        "amd-ucode", "intel-ucode",
        "ly", "git", "xorg-server", "xorg-xinit", "xorg-xauth", "mesa",
        # Audio (PipeWire)
        "pipewire", "pipewire-pulse", "pipewire-alsa", "pipewire-jack",
        "wireplumber", "alsa-utils", "sof-firmware",
        # Bluetooth
        "bluez", "bluez-utils", "bluez-libs", "bluez-obex",
        "libspa-bluetooth",
        # Fonts
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

    box_status("Installing base system", f"{len(all_pkgs)} packages")
    run(["pacstrap", "/mnt"] + all_pkgs)

    # ── Configure ──
    box_status("Configuring system")

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

# CachyOS repositories (official method: https://wiki.cachyos.org/features/optimized_repos)
pacman-key --recv-keys F3B607488DB35A47 --keyserver keyserver.ubuntu.com || true
pacman-key --lsign-key F3B607488DB35A47 || true

# Install keyring + mirrorlists directly (repos not yet available)
pacman -U --noconfirm \
  'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-keyring-20240331-1-any.pkg.tar.zst' \
  'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-mirrorlist-27-1-any.pkg.tar.zst' \
  'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v3-mirrorlist-27-1-any.pkg.tar.zst' \
  'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v4-mirrorlist-27-1-any.pkg.tar.zst' || true

# Auto-detect CPU level and add the right repos
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

# Install CachyOS kernel + NVIDIA
pacman -S --noconfirm linux-cachyos linux-cachyos-headers
pacman -S --noconfirm nvidia-open-dkms nvidia-utils nvidia-settings \
  lib32-nvidia-utils nvidia-prime opencl-nvidia egl-wayland

# Remove stock linux kernel, keep only CachyOS
pacman -Rdd --noconfirm linux 2>/dev/null || true

# Add NVIDIA modules to initramfs for early loading
sed -i 's/^MODULES=()/MODULES=(nvidia nvidia_modeset nvidia_uvm nvidia_drm)/' /etc/mkinitcpio.conf

# Regenerate initramfs for the new kernel
mkinitcpio -P

# yay (AUR helper) - reinstall after kernel switch
rm -rf /tmp/yay 2>/dev/null || true
su - {username} -c "cd /tmp && git clone https://aur.archlinux.org/yay.git /tmp/yay && cd /tmp/yay && makepkg -si --noconfirm"
rm -rf /tmp/yay

# Disable any other display managers that may have been pulled in
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

# Cleanup
rm -rf /var/cache/pacman/pkg/*
rm -rf /home/{username}/.cache/*
rm -rf /tmp/*
pacman -Sc --noconfirm
"""

    with open("/mnt/setup.sh", "w") as f:
        f.write(setup_script)
    box_status("Running chroot configuration")
    result = subprocess.run(
        ["arch-chroot", "/mnt", "bash", "/setup.sh"],
        capture_output=True, text=True
    )
    os.remove("/mnt/setup.sh")
    if result.returncode != 0:
        box_fail(
            "Chroot configuration failed",
            result.stdout,
            result.stderr
        )

    # ── Fstab ──
    box_status("Generating fstab")
    result = subprocess.run(
        ["genfstab", "-U", "/mnt"],
        capture_output=True, text=True, check=True
    )
    with open("/mnt/etc/fstab", "w") as f:
        f.write(result.stdout)

    box_status("Unmounting partitions")
    run(["umount", "-R", "/mnt"])

    box_puts([
        ("\033[32mInstallation complete!\033[0m", "center"),
        "",
        f"User: \033[36m{username}\033[0m",
        ("\033[33mRebooting in 5 seconds...\033[0m", "center"),
    ])
    time.sleep(5)
    run(["reboot"], check=False)


if __name__ == "__main__":
    main()
