#!/usr/bin/env python3

import os
import sys
import time
import shutil
import subprocess
import getpass
from collections import OrderedDict


# ─── TUI Helpers ─────────────────────────────────────────────────────────

def term_cols():
    return shutil.get_terminal_size((80, 20)).columns


def center(text):
    return text.center(term_cols())


def header():
    cols = term_cols()
    print("\033[1;36m" + "━" * cols + "\033[0m")
    print("\033[1;36m" + center("Arch Linux Quick Installer") + "\033[0m")
    print("\033[1;36m" + "━" * cols + "\033[0m")


def status(msg, detail=None):
    print("\033[2J\033[H", end="")
    header()
    print()
    print(center("\033[33m" + msg + "\033[0m"))
    if detail:
        print(center("\033[90m" + detail + "\033[0m"))
    print()


def status_ok(msg):
    print(center("\033[32m✓ " + msg + "\033[0m"))


def status_fail(msg, stdout="", stderr=""):
    cols = term_cols()
    print("\033[31m" + "━" * cols + "\033[0m")
    print("\033[31m" + center("✗ " + msg) + "\033[0m")
    print("\033[31m" + "━" * cols + "\033[0m")
    if stdout:
        print("\033[31m── stdout ──\033[0m")
        print(stdout)
    if stderr:
        print("\033[31m── stderr ──\033[0m")
        print(stderr)
    sys.exit(1)


def run(cmd, check=True, capture=True, **kwargs):
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
        kwargs["text"] = True
    result = subprocess.run(cmd, **kwargs)
    if check and result.returncode != 0:
        status_fail(
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
        print("\033[2J\033[H", end="")
        header()
        print()
        print(center("\033[33m" + title + "\033[0m"))
        print()
        keys = list(items.keys())
        for i, name in enumerate(keys, 1):
            mark = "\033[32m[*]\033[0m" if selected.get(name) else "\033[90m[ ]\033[0m"
            print(center(f"  {i:2d}. {mark} \033[0m{name}"))
        print()
        print(center("\033[90m(b) Back  (a) All  (n) None  (d) Done\033[0m"))
        print()
        sys.stdout.write(center("Choice: ") + " ")
        sys.stdout.flush()
        choice = input().strip().lower()

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
        print("\033[2J\033[H", end="")
        header()
        print()
        print(center("\033[33mDesktop / Window Manager Selection\033[0m"))
        print()
        for i, cat in enumerate(cat_keys, 1):
            count = sum(1 for name in categories[cat] if selected.get(name))
            print(center(f"  {i}. \033[36m{cat}\033[0m ({count} selected)"))
        print()
        print(center("\033[90m(d) Done / Install  (q) Quit\033[0m"))
        print()
        sys.stdout.write(center("Choice: ") + " ")
        sys.stdout.flush()
        choice = input().strip().lower()

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
        status_fail("This script must be run as root.")

    if not os.path.isfile("/etc/arch-release"):
        status_fail("This script must be run from the Arch ISO.")

    # ── Disk ──
    status("Detecting disk...")
    disk = find_disk()
    if not disk:
        status_fail("No suitable disk found.")

    print("\033[2J\033[H", end="")
    header()
    print()
    print(center("\033[33mPre-installation Setup\033[0m"))
    print()
    print(center(f"Disk detected: \033[36m{disk}\033[0m"))
    print(center("\033[31m⚠  ALL DATA on this disk will be DESTROYED!\033[0m"))
    print()
    print(center("Type \033[1myes\033[0m to continue:"), end=" ")
    sys.stdout.flush()
    if input().strip().lower() != "yes":
        print(center("Aborted."))
        sys.exit(0)

    # ── User info ──
    username = ""
    while not username:
        print(center("Enter username:"), end=" ")
        sys.stdout.flush()
        username = input().strip()

    password = getpass.getpass(center("Password: ") + " ")
    password2 = getpass.getpass(center("Confirm password: ") + " ")
    if password != password2:
        status_fail("Passwords do not match!")

    # ── DE/WM selection ──
    extra_pkgs = main_menu(CATEGORIES)
    if extra_pkgs:
        print(f"\n  Selected {len(extra_pkgs)} packages.")
    else:
        print("\n  No desktop/WM selected. Only base system will be installed.")

    p = "" if "nvme" not in disk and "mmc" not in disk else "p"
    is_uefi = os.path.isdir("/sys/firmware/efi")
    root_part = f"{disk}{p}2"

    # ── Partitioning ──
    status("Wiping disk and creating partitions")
    run(["sgdisk", "--zap-all", disk])
    run(["sgdisk", "--clear", disk])

    if is_uefi:
        run(["sgdisk", "-n1:0:+1G", "-t1:ef00", disk])
        run(["sgdisk", "-n2:0:0", "-t2:8300", disk])
        efi_part = f"{disk}{p}1"
    else:
        run(["sgdisk", "-n1:0:+2M", "-t1:ef02", disk])
        run(["sgdisk", "-n2:0:0", "-t2:8300", disk])

    if is_uefi:
        status("Formatting EFI partition (FAT32)")
        run(["mkfs.fat", "-F32", efi_part])

    status("Formatting root partition (Btrfs)")
    run(["mkfs.btrfs", "-f", root_part])

    # ── Subvolume ──
    status("Creating btrfs subvolume")
    tmp = "/mnt/tmp_btrfs"
    os.makedirs(tmp, exist_ok=True)
    run(["mount", root_part, tmp])
    run(["btrfs", "subvolume", "create", f"{tmp}/@"])
    run(["umount", tmp])
    os.rmdir(tmp)

    # ── Mount ──
    status("Mounting partitions")
    run(["mount", "-o", "subvol=@", root_part, "/mnt"])
    os.makedirs("/mnt/boot", exist_ok=True)
    if is_uefi:
        run(["mount", efi_part, "/mnt/boot"])

    # ── Base install ──
    base_pkgs = [
        "base", "linux", "linux-firmware",
        "btrfs-progs", "sudo", "networkmanager",
        "python", "python-pip",
        "grub", "efibootmgr" if is_uefi else "",
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

    status("Installing base system", f"{len(all_pkgs)} packages")
    run(["pacstrap", "/mnt"] + all_pkgs, timeout=3600000)

    # ── Configure ──
    status("Configuring system")

    # Always use ly, disable any other DMs pulled in by DEs
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

if [ -d /sys/firmware/efi ]; then
    grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
else
    grub-install --target=i386-pc {disk}
fi
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
    status("Running chroot configuration")
    result = subprocess.run(
        ["arch-chroot", "/mnt", "bash", "/setup.sh"],
        capture_output=True, text=True
    )
    os.remove("/mnt/setup.sh")
    if result.returncode != 0:
        status_fail(
            "Chroot configuration failed",
            result.stdout,
            result.stderr
        )

    # ── Fstab ──
    status("Generating fstab")
    result = subprocess.run(
        ["genfstab", "-U", "/mnt"],
        capture_output=True, text=True, check=True
    )
    with open("/mnt/etc/fstab", "w") as f:
        f.write(result.stdout)

    status("Unmounting partitions")
    run(["umount", "-R", "/mnt"])

    print("\033[2J\033[H", end="")
    header()
    print()
    print(center("\033[32m✓ Installation complete!\033[0m"))
    print(center(f"User: \033[36m{username}\033[0m"))
    print()
    print(center("\033[33mRebooting in 5 seconds...\033[0m"))
    time.sleep(5)
    run(["reboot"], check=False)


if __name__ == "__main__":
    main()
