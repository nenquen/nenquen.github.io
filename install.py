#!/usr/bin/env python3

import os, sys, time, subprocess, getpass
from collections import OrderedDict

def box(text, title=None):
    lines = text.split("\n")
    cw = max(len(l) for l in lines)
    if title is not None:
        cw = max(cw, len(title))
        out = ["\u250c\u2500\u2500 " + title + " " + "\u2500" * (cw - len(title)) + "\u2510"]
    else:
        out = ["\u250c" + "\u2500" * (cw + 4) + "\u2510"]
    for l in lines:
        out.append("\u2502" + "  " + l.ljust(cw) + "  " + "\u2502")
    out.append("\u2514" + "\u2500" * (cw + 4) + "\u2518")
    return "\n" + "\n".join(out)

def run(cmd, check=True, capture=True, **kw):
    if capture:
        kw["stdout"] = subprocess.PIPE
        kw["stderr"] = subprocess.PIPE
        kw["text"] = True
    r = subprocess.run(cmd, **kw)
    if check and r.returncode != 0:
        print("")
        print("  " + "-" * 40)
        print("  [ERROR]  " + (" ".join(cmd) if isinstance(cmd, list) else cmd))
        if capture:
            if r.stdout: print(r.stdout)
            if r.stderr: print(r.stderr)
        sys.exit(1)
    return r


def step(title, cmds):
    """Run labeled commands and show summary box with OK/FAIL status.
    cmds: list of (label, cmd_list, allow_fail)
    """
    logs = ""
    for label, cmd, allow_fail in cmds:
        r = run(cmd, check=False, capture=True)
        if r.returncode == 0:
            logs += "  %-25s  OK\n" % label
        else:
            logs += "  %-25s  FAIL\n" % label
            if r.stderr:
                logs += "  " + r.stderr.strip() + "\n"
            if not allow_fail:
                logs += "\n  Aborting."
                print(box(logs, title=title))
                sys.exit(1)
    print(box(logs + "\n  Done!", title=title))


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

DNS_SERVERS = [
    ("Cloudflare",    "1.1.1.1"),
    ("Cloudflare 2",  "1.0.0.1"),
    ("Google",        "8.8.8.8"),
    ("Google 2",      "8.8.4.4"),
    ("Quad9",         "9.9.9.9"),
    ("Quad9 2",       "149.112.112.112"),
    ("OpenDNS",       "208.67.222.222"),
    ("OpenDNS 2",     "208.67.220.220"),
    ("AdGuard",       "94.140.14.14"),
    ("AdGuard 2",     "94.140.15.15"),
    ("DNS.WATCH",     "84.200.69.80"),
    ("Comodo",        "8.26.56.26"),
    ("CleanBrowsing", "185.228.168.9"),
]

def dns_menu():
    print(box("  Configure DNS"))
    print("  Do you want to set a DNS server?")
    c = input("  [y/N]: ").strip().lower()
    if c != "y":
        return None
    while True:
        os.system("clear")
        content = ""
        for i, (name, ip) in enumerate(DNS_SERVERS, 1):
            content += "  %2d.  %-15s %s\n" % (i, name, ip)
        content += "\n"
        content += "  [q] Quit (skip)"
        print(box(content, title="DNS Servers"))
        try:
            c = input("  > ").strip().lower()
            if c == "q":
                return None
            idx = int(c) - 1
            if 0 <= idx < len(DNS_SERVERS):
                return DNS_SERVERS[idx][1]
            print(box("  Invalid number."))
        except ValueError:
            print(box("  Invalid input."))

def show_menu(items, selected, title):
    while True:
        os.system("clear")
        content = ""
        keys = list(items.keys())
        max_nlen = max(len(k) for k in keys)
        for i, name in enumerate(keys, 1):
            m = "(+)" if selected.get(name) else "( )"
            content += "  %2d.  %-*s  %s\n" % (i, max_nlen, name, m)
        content += "\n"
        content += "  [b] Back  [a] All  [n] None  [d] Done"
        print(box(content, title=title))
        c = input("  > ").strip().lower()
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
            else: print(box("  Invalid number."))
        except ValueError: print(box("  Invalid input."))

def main_menu(cat):
    selected = {}
    keys = list(cat.keys())
    max_nlen = max(len(k) for k in keys)
    while True:
        os.system("clear")
        content = ""
        for i, c in enumerate(keys, 1):
            n = sum(1 for name in cat[c] if selected.get(name))
            content += "  %2d.  %-*s  (%d selected)\n" % (i, max_nlen, c, n)
        content += "\n"
        content += "  [d] Done  [q] Quit"
        print(box(content, title="DESKTOP / WM SELECTION"))
        c = input("  > ").strip().lower()
        if c == "q": print(box("  Aborted.")); sys.exit(0)
        if c == "d": break
        try:
            idx = int(c) - 1
            if 0 <= idx < len(keys):
                r = show_menu(cat[keys[idx]], selected, keys[idx])
                if r == "done": break
            else: print(box("  Invalid number."))
        except ValueError: print(box("  Invalid input."))
    pkgs = []
    for c in cat:
        for name, pkg_list in cat[c].items():
            if selected.get(name): pkgs.extend(pkg_list)
    return list(set(pkgs))

def main():
    os.system("clear")
    if os.geteuid() != 0: print(box("  FATAL: must be root")); sys.exit(1)
    if not os.path.isfile("/etc/arch-release"): print(box("  FATAL: must run from Arch ISO")); sys.exit(1)

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
        print(box("  FATAL: no disk found")); sys.exit(1)

    dlist = []
    for i, (d, s, m) in enumerate(disks, 1):
        dlist.append("  %d.  %-12s %8s  %s" % (i, d, s, m))
    print(box("  Available disks\n\n" + "\n".join(dlist) + "\n\n"
               "  Select disk [1-%d]:" % len(disks)))
    while True:
        try:
            c = int(input("  > "))
            if 1 <= c <= len(disks):
                disk = disks[c-1][0]
                break
            print(box("  Invalid number."))
        except ValueError:
            print(box("  Invalid input."))

    print(box("  ALL DATA on this disk will be DESTROYED!\n\n"
               "  Type 'yes' to continue:", title="SELECTED:  " + disk))
    if input("  > ").strip().lower() != "yes": print(box("  Aborted.")); sys.exit(0)

    print("")
    print(box("  User setup"))
    username = ""
    while not username:
        print("  Username:")
        username = input("  > ").strip()
    print("  Password:")
    pw = getpass.getpass("  > ")
    print("  Confirm password:")
    pw2 = getpass.getpass("  > ")
    if pw != pw2: print(box("  Passwords dont match!")); sys.exit(1)

    extra = main_menu(CAT)
    dns_ip = dns_menu()
    os.system("clear")

    p = "" if "nvme" not in disk and "mmc" not in disk else "p"
    rootp = disk + p + "2"
    efip = disk + p + "1"

    step("[1/7]  Partitioning", [
        ("unmount /mnt",        ["umount", "-R", "/mnt"], True),
        ("swapoff",             ["swapoff", "-a"], True),
        ("unmount efi",         ["umount", efip], True),
        ("unmount root",        ["umount", rootp], True),
        ("wipefs",              ["wipefs", "-a", disk], True),
        ("sgdisk --zap-all",    ["sgdisk", "--zap-all", disk], False),
        ("sgdisk --clear",      ["sgdisk", "--clear", disk], False),
        ("sgdisk efi part",     ["sgdisk", "-n1:0:+1G", "-t1:ef00", disk], False),
        ("sgdisk root part",    ["sgdisk", "-n2:0:0", "-t2:8300", disk], False),
    ])
    time.sleep(2)

    step("[2/7]  Formatting", [
        ("mkfs.fat  (EFI)",     ["mkfs.fat", "-F32", efip], False),
        ("mkfs.btrfs  (root)",  ["mkfs.btrfs", "-f", rootp], False),
    ])

    os.makedirs("/mnt/tmp_btrfs", exist_ok=True)
    step("[3/7]  Creating subvolume", [
        ("mount root",          ["mount", rootp, "/mnt/tmp_btrfs"], False),
        ("btrfs subvol @",      ["btrfs", "subvolume", "create", "/mnt/tmp_btrfs/@"], False),
        ("unmount tmp",         ["umount", "/mnt/tmp_btrfs"], False),
    ])
    os.rmdir("/mnt/tmp_btrfs")

    os.makedirs("/mnt/boot", exist_ok=True)
    step("[4/7]  Mounting", [
        ("mount subvol @",      ["mount", "-o", "subvol=@", rootp, "/mnt"], False),
        ("mount /boot",         ["mount", efip, "/mnt/boot"], False),
    ])

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

    n_pkgs = len(all_pkgs)
    print(box("  Installing  %d packages..." % n_pkgs, title="[5/7]  Installing"))
    run(["pacstrap", "/mnt"] + all_pkgs, capture=False)
    print(box("  Done!", title="[5/7]  Installing  %d packages" % n_pkgs))

    print(box("  Running chroot script...", title="[6/7]  Configuring"))

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
    if dns_ip:
        script += "mkdir -p /etc/NetworkManager/conf.d\n"
        script += ("cat > /etc/NetworkManager/conf.d/dns.conf <<EOF\n"
                   "[main]\ndns=none\nEOF\n")
        script += "echo 'nameserver %s' > /etc/resolv.conf\n" % dns_ip
        script += "chattr +i /etc/resolv.conf 2>/dev/null || true\n"
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
        err = r.stderr if r.stderr else ""
        if r.stdout: err += "\n" + r.stdout
        print(box(err, title="[ERROR]  Chroot failed"))
        sys.exit(1)
    print(box("  Done!", title="[6/7]  Configuring"))

    print(box("", title="[7/7]  Generating fstab"))
    r = subprocess.run(["genfstab", "-U", "/mnt"], capture_output=True, text=True, check=True)
    with open("/mnt/etc/fstab", "w") as f:
        f.write(r.stdout)
    print(box("  Done!", title="[7/7]  Generating fstab"))

    step("Unmounting", [
        ("swapoff",             ["swapoff", "-a"], True),
        ("umount -R /mnt",      ["umount", "-R", "/mnt"], False),
    ])

    print(box("  User: " + username, title="Done  (rebooting in 5s)"))
    time.sleep(5)
    run(["reboot"], check=False)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(box("  Installation aborted."))
        sys.exit(0)
