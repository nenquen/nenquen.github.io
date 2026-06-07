#!/usr/bin/env python3

import os, sys, time, subprocess, getpass
from collections import OrderedDict
from shutil import get_terminal_size

def tw():
    return get_terminal_size().columns

def center(text):
    w = tw()
    return "\n".join(line.center(w) for line in text.split("\n"))

def box(text):
    lines = text.split("\n")
    cw = max(len(l) for l in lines)
    aw = cw + 4
    tl = "\u250c" + "\u2500" * aw + "\u2510"
    bl = "\u2514" + "\u2500" * aw + "\u2518"
    out = [tl]
    for l in lines:
        out.append("\u2502 " + l.ljust(aw - 2) + " \u2502")
    out.append(bl)
    return "\n".join(out)

def cbox(text):
    return center(box(text))

def run(cmd, check=True, capture=True, **kw):
    if capture:
        kw["stdout"] = subprocess.PIPE
        kw["stderr"] = subprocess.PIPE
        kw["text"] = True
    r = subprocess.run(cmd, **kw)
    if check and r.returncode != 0:
        print(center("  \u2500" * 30))
        print(center("  [ERROR]  " + (" ".join(cmd) if isinstance(cmd, list) else cmd)))
        if capture:
            if r.stdout: print(r.stdout)
            if r.stderr: print(r.stderr)
        sys.exit(1)
    return r


CAT = OrderedDict()
CAT["X11 Desktops"] = OrderedDict([
    ("Budgie", ["budgie-desktop"]), ("Cinnamon", ["cinnamon"]),
    ("Deepin", ["deepin"]), ("Enlightenment", ["enlightenment", "terminology"]),
    ("GNOME Flashback", ["gnome-flashback"]), ("LXDE", ["lxde"]),
    ("LXQt", ["lxqt-session", "lxqt-panel", "pcmanfm-qt", "qterminal", "lxqt-config"]),
    ("MATE", ["mate-session-manager", "mate-panel", "caja", "marco", "mate-terminal", "mate-control-center"]),
    ("Pantheon", ["pantheon-session", "pantheon-files", "pantheon-terminal", "switchboard", "pantheon-settings-daemon", "gala", "wingpanel"]),
    ("Sugar", ["sugar"]),
    ("Xfce", ["xfce4-session", "xfwm4", "xfce4-panel", "thunar", "xfce4-terminal", "xfce4-power-manager"]),
])
CAT["Wayland Desktops"] = OrderedDict([
    ("COSMIC", ["cosmic-session", "cosmic-comp", "cosmic-panel", "cosmic-files", "cosmic-terminal", "cosmic-settings", "cosmic-settings-daemon"]),
    ("GNOME", ["gnome-shell", "gnome-session", "nautilus", "gnome-terminal", "gnome-control-center", "gnome-tweaks", "gvfs"]),
    ("KDE Plasma", ["plasma-desktop", "dolphin", "konsole", "systemsettings", "plasma-nm", "plasma-pa", "powerdevil", "bluedevil", "kde-gtk-config", "breeze"]),
])
CAT["Window Managers"] = OrderedDict([
    ("Blackbox", ["blackbox"]), ("Fluxbox", ["fluxbox"]), ("FVWM3", ["fvwm3"]),
    ("IceWM", ["icewm"]), ("JWM", ["jwm"]), ("KWin (X11)", ["kwin-x11"]),
    ("Marco", ["marco"]), ("Metacity", ["metacity"]), ("Muffin", ["muffin"]),
    ("Openbox", ["openbox", "obconf"]), ("PekWM", ["pekwm"]),
    ("twm", ["xorg-twm"]), ("Window Maker", ["windowmaker"]), ("Xfwm", ["xfwm4"]),
    ("bspwm", ["bspwm", "sxhkd"]), ("Herbstluftwm", ["herbstluftwm"]),
    ("i3", ["i3-wm", "i3status", "i3lock"]),
    ("Notion", ["notion"]), ("Ratpoison", ["ratpoison"]), ("StumpWM", ["stumpwm"]),
    ("awesome", ["awesome"]), ("Qtile", ["qtile"]),
    ("xmonad", ["xmonad", "xmonad-contrib"]), ("labwc", ["labwc"]),
    ("wayfire", ["wayfire", "wf-config"]), ("Weston", ["weston"]),
    ("niri", ["niri"]), ("Sway", ["sway", "swaybg", "mako"]),
    ("Hyprland", ["hyprland", "hyprpaper", "hyprlock"]),
    ("river", ["river"]), ("Cage", ["cage"]),
])

def show_menu(items, selected, title):
    while True:
        os.system("clear")
        content = "  " + title + "\n"
        keys = list(items.keys())
        for i, name in enumerate(keys, 1):
            m = "(+)" if selected.get(name) else "( )"
            content += "  %2d. %s %s\n" % (i, m, name)
        content += "\n"
        content += "  [b] Back  [a] All  [n] None  [d] Done"
        print(cbox(content))
        c = input(" > ").strip().lower()
        if c == "b": return "back"
        if c == "a":
            for k in keys: selected[k] = True
            continue
        if c == "n":
            for k in keys: selected[k] = False
            continue
        if c == "d": return "done"
        try:
            idx = int(c) - 1
            if 0 <= idx < len(keys): selected[keys[idx]] = not selected.get(keys[idx])
            else: print(cbox("  Invalid number."))
        except ValueError: print(cbox("  Invalid input."))

def main_menu(cat):
    selected = {}
    keys = list(cat.keys())
    while True:
        os.system("clear")
        content = "  DESKTOP / WM SELECTION\n"
        for i, c in enumerate(keys, 1):
            n = sum(1 for name in cat[c] if selected.get(name))
            content += "  %2d. %s (%d selected)\n" % (i, c, n)
        content += "\n"
        content += "  [d] Done  [q] Quit"
        print(cbox(content))
        c = input(" > ").strip().lower()
        if c == "q": print(cbox("  Aborted.")); sys.exit(0)
        if c == "d": break
        try:
            idx = int(c) - 1
            if 0 <= idx < len(keys):
                r = show_menu(cat[keys[idx]], selected, keys[idx])
                if r == "done": break
            else: print(cbox("  Invalid number."))
        except ValueError: print(cbox("  Invalid input."))
    pkgs = []
    for c in cat:
        for name, pkg_list in cat[c].items():
            if selected.get(name): pkgs.extend(pkg_list)
    return list(set(pkgs))

def main():
    os.system("clear")
    if os.geteuid() != 0: print(cbox("  FATAL: must be root")); sys.exit(1)
    if not os.path.isfile("/etc/arch-release"): print(cbox("  FATAL: must run from Arch ISO")); sys.exit(1)

    disks = []
    r = subprocess.run(["lsblk", "-dno", "NAME,SIZE,MODEL", "-e", "7,11,1,2"], capture_output=True, text=True)
    for line in r.stdout.strip().split("\n"):
        parts = line.strip().split(None, 2)
        if parts:
            name = parts[0]
            size = parts[1] if len(parts) > 1 else ""
            model = parts[2] if len(parts) > 2 else ""
            disks.append(("/dev/" + name, size, model))

    if not disks:
        print(cbox("  FATAL: no disk found")); sys.exit(1)

    dlist = []
    for i, (d, s, m) in enumerate(disks, 1):
        dlist.append("  %d.  %-12s %8s  %s" % (i, d, s, m))
    print(cbox("  Available disks\n\n" + "\n".join(dlist) + "\n\n"
               "  Select disk [1-%d]:" % len(disks)))
    while True:
        try:
            c = int(input(" > "))
            if 1 <= c <= len(disks):
                disk = disks[c-1][0]
                break
            print(cbox("  Invalid number."))
        except ValueError:
            print(cbox("  Invalid input."))

    print(cbox("SELECTED:  " + disk + "\n\n"
               "\u2500\u2500\u2500\u2500 WARNING \u2500\u2500\u2500\u2500\n"
               "ALL DATA on this disk\nwill be DESTROYED!\n"
               "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\n"
               "Type 'yes' to continue:  "))
    if input().strip().lower() != "yes": print(cbox("  Aborted.")); sys.exit(0)

    print("")
    print(cbox("  User setup"))
    username = ""
    while not username:
        print(center("  Username:"))
        username = input("  > ").strip()
    print(center("  Password:"))
    pw = getpass.getpass("  > ")
    print(center("  Confirm password:"))
    pw2 = getpass.getpass("  > ")
    if pw != pw2: print(cbox("  Passwords dont match!")); sys.exit(1)

    extra = main_menu(CAT)
    os.system("clear")

    p = "" if "nvme" not in disk and "mmc" not in disk else "p"
    rootp = disk + p + "2"
    efip = disk + p + "1"

    print(center("\u2500" * tw()))
    print(center("  [1/7]  Partitioning"))
    run(["umount", "-R", "/mnt"], check=False)
    run(["swapoff", "-a"], check=False)
    run(["umount", disk + p + "1"], check=False)
    run(["umount", disk + p + "2"], check=False)
    run(["wipefs", "-a", disk], check=False)
    run(["sgdisk", "--zap-all", disk])
    run(["sgdisk", "--clear", disk])
    run(["sgdisk", "-n1:0:+1G", "-t1:ef00", disk])
    run(["sgdisk", "-n2:0:0", "-t2:8300", disk])
    time.sleep(2)

    print(center("  [2/7]  Formatting"))
    run(["mkfs.fat", "-F32", efip])
    run(["mkfs.btrfs", "-f", rootp])

    print(center("  [3/7]  Creating subvolume"))
    os.makedirs("/mnt/tmp_btrfs", exist_ok=True)
    run(["mount", rootp, "/mnt/tmp_btrfs"])
    run(["btrfs", "subvolume", "create", "/mnt/tmp_btrfs/@"])
    run(["umount", "/mnt/tmp_btrfs"])
    os.rmdir("/mnt/tmp_btrfs")

    print(center("  [4/7]  Mounting"))
    run(["mount", "-o", "subvol=@", rootp, "/mnt"])
    os.makedirs("/mnt/boot", exist_ok=True)
    run(["mount", efip, "/mnt/boot"])

    base = [
        "base", "linux", "linux-firmware", "btrfs-progs", "sudo", "networkmanager",
        "python", "python-pip", "grub", "efibootmgr", "amd-ucode", "intel-ucode",
        "ly", "git", "xorg-server", "xorg-xinit", "xorg-xauth", "mesa",
        "pipewire", "pipewire-pulse", "pipewire-alsa", "pipewire-jack",
        "wireplumber", "alsa-utils", "sof-firmware",
        "bluez", "bluez-utils", "bluez-libs", "bluez-obex",
        "noto-fonts", "noto-fonts-emoji", "noto-fonts-cjk", "noto-fonts-extra",
        "ttf-dejavu", "ttf-liberation", "ttf-ubuntu-font-family",
        "ttf-roboto", "ttf-opensans", "ttf-fira-code",
        "ttf-hack", "ttf-jetbrains-mono", "ttf-inconsolata",
        "ttf-croscore", "ttf-caladea", "ttf-carlito", "adobe-source-code-pro-fonts",
        "fakeroot", "debugedit", "brightnessctl", "power-profiles-daemon",
    ]
    all_pkgs = base + extra

    print(center("  [5/7]  Installing %d packages" % len(all_pkgs)))
    run(["pacstrap", "/mnt"] + all_pkgs)

    print(center("  [6/7]  Configuring"))

    r = subprocess.run(["curl", "-s", "http://ip-api.com/line?fields=timezone"], capture_output=True, text=True)
    tz = r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "Europe/Istanbul"

    script = "#!/bin/bash\nset -e\n"
    script += "ln -sf /usr/share/zoneinfo/%s /etc/localtime\n" % tz
    script += "hwclock --systohc\n"
    script += "sed -i 's/#en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen\n"
    script += "locale-gen\n"
    script += "echo 'LANG=en_US.UTF-8' > /etc/locale.conf\n"
    script += "echo 'archlinux' > /etc/hostname\n"
    script += "cat > /etc/hosts <<EOF\n127.0.0.1   localhost\n::1         localhost\n127.0.1.1   archlinux.localdomain archlinux\nEOF\n"
    script += "echo -e 'root\\nroot' | passwd 2>/dev/null\n"
    script += "useradd -m -G wheel %s\n" % username
    script += "echo -e '%s\\n%s' | passwd %s 2>/dev/null\n" % (pw, pw, username)
    script += "echo '%%wheel ALL=(ALL:ALL) NOPASSWD: ALL' >> /etc/sudoers\n"
    script += "echo 'Defaults !requiretty' >> /etc/sudoers\n"
    script += "systemctl enable NetworkManager\n"
    script += "systemctl enable bluetooth\n"
    script += "systemctl enable ly@tty2.service\n"
    script += "systemctl disable getty@tty2.service 2>/dev/null || true\n"
    script += "systemctl --global enable pipewire pipewire-pulse wireplumber\n"
    script += "systemctl enable fstrim.timer\n"
    script += "systemctl enable paccache.timer 2>/dev/null || true\n"
    script += "systemctl enable power-profiles-daemon\n"
    script += "pacman-key --recv-keys F3B607488DB35A47 --keyserver keyserver.ubuntu.com 2>/dev/null || true\n"
    script += "pacman-key --lsign-key F3B607488DB35A47 2>/dev/null || true\n"
    script += "pacman -U --noconfirm "
    script += "'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-keyring-20240331-1-any.pkg.tar.zst' "
    script += "'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-mirrorlist-27-1-any.pkg.tar.zst' "
    script += "'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v3-mirrorlist-27-1-any.pkg.tar.zst' "
    script += "'https://mirror.cachyos.org/repo/x86_64/cachyos/cachyos-v4-mirrorlist-27-1-any.pkg.tar.zst' || true\n"
    script += "if /lib/ld-linux-x86-64.so.2 --help 2>/dev/null | grep -q 'x86-64-v4 (supported, searched)'; then\n"
    script += "  cat >> /etc/pacman.conf << 'R'\n[cachyos-v4]\nInclude = /etc/pacman.d/cachyos-v4-mirrorlist\n"
    script += "[cachyos-core-v4]\nInclude = /etc/pacman.d/cachyos-v4-mirrorlist\n"
    script += "[cachyos-extra-v4]\nInclude = /etc/pacman.d/cachyos-v4-mirrorlist\n"
    script += "[cachyos]\nInclude = /etc/pacman.d/cachyos-mirrorlist\nR\n"
    script += "elif /lib/ld-linux-x86-64.so.2 --help 2>/dev/null | grep -q 'x86-64-v3 (supported, searched)'; then\n"
    script += "  cat >> /etc/pacman.conf << 'R'\n[cachyos-v3]\nInclude = /etc/pacman.d/cachyos-v3-mirrorlist\n"
    script += "[cachyos-core-v3]\nInclude = /etc/pacman.d/cachyos-v3-mirrorlist\n"
    script += "[cachyos-extra-v3]\nInclude = /etc/pacman.d/cachyos-v3-mirrorlist\n"
    script += "[cachyos]\nInclude = /etc/pacman.d/cachyos-mirrorlist\nR\n"
    script += "else\n  cat >> /etc/pacman.conf << 'R'\n[cachyos]\nInclude = /etc/pacman.d/cachyos-mirrorlist\nR\nfi\n"
    script += "sed -i '/^#\\[multilib\\]/,/^#Include/{s/^#//}' /etc/pacman.conf\n"
    script += "pacman -Sy --noconfirm\n"
    script += "pacman -S --noconfirm linux-cachyos linux-cachyos-headers\n"
    script += "pacman -S --noconfirm nvidia-open-dkms nvidia-utils lib32-nvidia-utils nvidia-prime opencl-nvidia egl-wayland\n"
    script += "pacman -Rdd --noconfirm linux 2>/dev/null || true\n"
    script += "sed -i 's/^MODULES=()/MODULES=(nvidia nvidia_modeset nvidia_uvm nvidia_drm)/' /etc/mkinitcpio.conf\n"
    script += "mkinitcpio -P\n"
    script += "rm -rf /tmp/yay 2>/dev/null || true\n"
    script += "pacman -S --noconfirm go\n"
    script += ("su - %s -c 'cd /tmp && git clone https://aur.archlinux.org/yay.git /tmp/yay && "
               "cd /tmp/yay && makepkg'\n") % username
    script += "pacman -U --noconfirm /tmp/yay/*.pkg.tar.zst\n"
    script += "rm -rf /tmp/yay\n"
    script += "for dm in gdm sddm lightdm lxdm; do\n"
    script += "  if systemctl list-unit-files --type=service 2>/dev/null | grep -q \"$dm\"; then\n"
    script += "    systemctl disable \"$dm\" 2>/dev/null || true\n  fi\ndone\n"
    script += "grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB\n"
    script += "grub-mkconfig -o /boot/grub/grub.cfg\n"
    script += "truncate -s 0 /swapfile\nchattr +C /swapfile\n"
    script += "dd if=/dev/zero of=/swapfile bs=1M count=16384 2>/dev/null\n"
    script += "chmod 600 /swapfile\nmkswap /swapfile\nswapon /swapfile\n"
    script += "echo '/swapfile none swap defaults 0 0' >> /etc/fstab\n"
    script += "rm -rf /var/cache/pacman/pkg/*\n"
    script += ("rm -rf /home/%s/.cache/*\n" % username)
    script += "rm -rf /tmp/*\npacman -Sc --noconfirm\n"

    with open("/mnt/setup.sh", "w") as f:
        f.write(script)
    r = subprocess.run(["arch-chroot", "/mnt", "bash", "/setup.sh"], capture_output=True, text=True)
    os.remove("/mnt/setup.sh")
    if r.returncode != 0:
        print(center("  \u2500" * 30))
        print(center("  [ERROR]  Chroot failed"))
        if r.stdout: print(r.stdout)
        if r.stderr: print(r.stderr)
        sys.exit(1)

    print(center("  [7/7]  Generating fstab"))
    r = subprocess.run(["genfstab", "-U", "/mnt"], capture_output=True, text=True, check=True)
    with open("/mnt/etc/fstab", "w") as f:
        f.write(r.stdout)

    print(center("\u2500" * tw()))
    print(center("  Unmounting"))
    run(["swapoff", "-a"], check=False)
    run(["umount", "-R", "/mnt"])

    print(center("\u2500" * tw()))
    print(center("  Done! Rebooting in 5 seconds"))
    print(center("  User: " + username))
    time.sleep(5)
    run(["reboot"], check=False)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(cbox("  Installation aborted."))
        sys.exit(0)
