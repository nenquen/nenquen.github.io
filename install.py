#!/usr/bin/env python3
"""
Nen's Arch Linux Installer — Optimized Edition
CachyOS kernel · KDE Plasma · NVIDIA-aware · Dual-boot support
"""

import subprocess
import sys
import os
import time
import shutil
import getpass
import threading
import itertools
import signal
import logging
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ─── UI Theme ──────────────────────────────────────────────────────────────────

class C:
    BLUE   = "\033[34m"
    CYAN   = "\033[36m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    RED    = "\033[31m"
    LILAC  = "\033[95m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"
    CLEAR  = "\033[H\033[2J"

class Sym:
    OK      = f"{C.GREEN}[ OK ]{C.RESET}"
    FAIL    = f"{C.RED}[ FAIL ]{C.RESET}"
    INFO    = f"{C.CYAN}[ INFO ]{C.RESET}"
    WARN    = f"{C.YELLOW}[ WARN ]{C.RESET}"
    SPINNER = ["|", "/", "-", "\\"]

# ASCII HEADER REMOVED AS REQUESTED

# ─── Configuration ─────────────────────────────────────────────────────────────

LOG_FILE       = Path("/tmp/nen-install.log")
TOTAL_STEPS    = 8   # welcome · disk · partition · mount · base · configure · finish
HOSTNAME       = "archlinux"
TIMEZONE       = "Europe/Istanbul"
LOCALE         = "en_US.UTF-8"
KEYMAP         = "trq"
EFI_SIZE_MIB   = 1024
BTRFS_COMPRESS = "zstd:3"
SWAP_SIZE      = "16G"
MIN_DISK_BYTES = 30 * 1024 ** 3
MIN_FREE_BYTES = 30 * 1024 ** 3

# Valid Linux username: starts with letter/underscore, then letters/digits/underscore/hyphen
USERNAME_RE = re.compile(r'^[a-z_][a-z0-9_-]{0,31}$')

BASE_PACKAGES = [
    "base", "linux-cachyos", "linux-cachyos-headers", "linux-firmware",
    "intel-ucode", "btrfs-progs", "sudo", "base-devel", "git", "go",
    "networkmanager", "bluez", "bluez-utils",
    "pipewire", "pipewire-pulse", "wireplumber",
    "ly",
    "plasma-desktop", "plasma-nm", "powerdevil", "kinfocenter",
    "spectacle", "bluedevil", "plasma-pa", "plasma-systemmonitor",
    "xorg-xwayland", "breeze-gtk",
    "kitty", "dolphin", "ark", "unzip", "unrar", "gwenview", "kate",
    "noto-fonts", "noto-fonts-emoji", "ttf-jetbrains-mono-nerd",
    "sof-firmware", "alsa-ucm-conf",
    "bash-completion",
    "xorg-xauth",   # required by ly for Xorg session support
]

# Dual-boot: GRUB is mandatory (it can chain-load Windows; systemd-boot cannot)
GRUB_PACKAGES = ["grub", "efibootmgr", "os-prober", "ntfs-3g"]

NVIDIA_PACKAGES = [
    "nvidia-open",
    "nvidia-utils",
    "lib32-nvidia-utils",
    "libvdpau",
    "libva-nvidia-driver",
    "vulkan-icd-loader",
    "lib32-vulkan-icd-loader",
]

# ─── Data types ────────────────────────────────────────────────────────────────

@dataclass
class DiskInfo:
    name:        str
    size_bytes:  int
    size_str:    str
    partitions:  list = field(default_factory=list)
    removable:   bool = False

@dataclass
class PartInfo:
    name:        str
    size_bytes:  int
    size_str:    str
    fs_type:     str
    label:       str
    is_free:     bool = False
    mountpoint:  str = ""
    # Filled only for is_free entries:
    _free_start: int = 0
    _free_end:   int = 0

# ─── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("installer")

# ─── Helpers ───────────────────────────────────────────────────────────────────

def typewriter(text: str, delay: float = 0.015, color: str = C.RESET) -> None:
    sys.stdout.write(color)
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(C.RESET + "\n")

def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


class Spinner:
    def __init__(self, message: str = "Working..."):
        self.message = message
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        for frame in itertools.cycle(Sym.SPINNER):
            if self._stop.is_set():
                break
            sys.stdout.write(f"\r  {C.CYAN}{frame}{C.RESET}  {self.message}  ")
            sys.stdout.flush()
            time.sleep(0.08)
        sys.stdout.write("\r" + " " * (len(self.message) + 12) + "\r")

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()


class InstallError(Exception):
    pass


# ─── Core Installer ────────────────────────────────────────────────────────────

class Installer:
    def __init__(self):
        self.step        = 0
        self.in_progress = False
        self.bootloader  = "systemd-boot"
        self.username    = ""
        self.password    = ""
        self.nvidia_gpu  = False
        self.has_igpu    = False

        self.install_mode  = "clean"
        self.disk          = ""
        self.p_efi         = ""
        self.p_swap        = ""
        self.p_root        = ""
        self.root_uuid     = ""
        self.win_efi_part  = ""
        self.free_start    = 0    # int, not str
        self.free_end      = 0    # int, not str
        # DiskInfo holding Windows; used to collect NTFS parts for os-prober
        self._win_disk_obj = None

    # ── Shell helpers ────────────────────────────────────────────────────────

    def run(self, cmd: str, *, check: bool = True, capture: bool = False):
        log.debug("EXEC: %s", cmd)
        try:
            if capture:
                r = subprocess.run(cmd, shell=True, check=check,
                                   text=True, capture_output=True)
                return r.stdout.strip()
            with LOG_FILE.open("a") as fh:
                subprocess.run(cmd, shell=True, check=check,
                               stdout=fh, stderr=fh)
            return True
        except subprocess.CalledProcessError as exc:
            raise InstallError(
                f"Command exited with code {exc.returncode}\n→ {cmd}"
            ) from exc

    def chroot_run(self, script: str) -> None:
        tmp = Path("/mnt/_nen_setup.sh")
        tmp.write_text(script)
        try:
            self.run("arch-chroot /mnt /bin/bash /_nen_setup.sh")
        finally:
            tmp.unlink(missing_ok=True)

    def _teardown_mounts(self) -> None:
        """
        Aggressively unmount everything under /mnt and release swap.
        Called before any partitioning step to ensure a clean slate even if
        a previous install attempt left mounts behind.
        """
        # Release bind-mounts created by setup_cachyos on the live host
        for mp in ("/var/cache/pacman/pkg", "/var/lib/pacman"):
            os.system(f"umount -l {mp} 2>/dev/null || true")

        # Swapoff before touching swap partitions
        os.system("swapoff -a 2>/dev/null || true")

        # Lazy-unmount the whole /mnt tree (handles nested mounts)
        os.system("umount -l /mnt 2>/dev/null || true")
        # Follow up with recursive unmount for any stragglers
        os.system("umount -R /mnt 2>/dev/null || true")

        # Give the kernel a moment to process the unmounts
        time.sleep(1)

    # ── Input ────────────────────────────────────────────────────────────────

    def prompt(self, msg: str) -> str:
        os.system("tput cnorm")
        try:
            val = input(msg)
        except EOFError:
            with open("/dev/tty") as tty:
                sys.stdout.write(msg)
                sys.stdout.flush()
                val = tty.readline().strip()
        finally:
            if self.in_progress:
                os.system("tput civis")
        return val

    # ── Rendering ────────────────────────────────────────────────────────────

    def _header(self) -> None:
        sys.stdout.write(C.CLEAR)
        print()

    def render(self) -> None:
        self._header()
        if not self.in_progress:
            print(f"\n  {C.BOLD}SYSTEM READY.{C.RESET}")
            return
        width  = 42
        pct    = int(self.step * 100 / TOTAL_STEPS)
        filled = int(self.step * width / TOTAL_STEPS)
        color  = C.BLUE if pct < 40 else (C.CYAN if pct < 80 else C.GREEN)
        bar    = f"{color}{'█' * filled}{C.DIM}{'░' * (width - filled)}{C.RESET}"
        print(f"\n  {C.DIM}Progress:{C.RESET}")
        print(f"  [{bar}] {C.BOLD}{pct}%{C.RESET}  ({self.step}/{TOTAL_STEPS})")
        print(f"  {C.DIM}Log → {LOG_FILE}{C.RESET}\n")

    def tick(self, msg: str) -> None:
        log.info(msg)
        print(f"  {Sym.OK}  {msg}")
        self.step += 1
        time.sleep(0.3)
        self.render()

    def abort(self, msg: str) -> None:
        self.render()
        print(f"\n  {Sym.FAIL}  {C.BOLD}FATAL:{C.RESET} {C.RED}{msg}{C.RESET}")
        print(f"\n  {Sym.INFO}  Last log lines:\n")
        subprocess.run(f"tail -n 15 {LOG_FILE}", shell=True)
        print(f"\n  Press Enter to exit…")
        try:
            self.prompt("")
        except Exception:
            pass

    # ── CachyOS repo ─────────────────────────────────────────────────────────

    def _cachyos_script(self) -> str:
        return """set -euo pipefail
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
cd "$tmpdir"
curl -sLO https://mirror.cachyos.org/cachyos-repo.tar.xz
tar xf cachyos-repo.tar.xz
cd cachyos-repo
set +e
yes | ./cachyos-repo.sh
set -e
# Syncing is crucial after adding the repo
pacman -Sy --noconfirm
command -v cachyos-rate-mirrors &>/dev/null && cachyos-rate-mirrors || true
"""

    def setup_cachyos(self, target: Optional[str] = None) -> None:
        label = f"into {target}" if target else "on live host"
        with Spinner(f"Injecting CachyOS repositories {label}…"):
            script = self._cachyos_script()
            if target:
                self.chroot_run(script)
            else:
                # If target is None, we are on the live host.
                # We need to make sure pacman on the live host can see the new repos.
                # The cachyos-repo.sh script modifies /etc/pacman.conf.
                
                # Grow the live tmpfs so repo scripts have room to work
                os.system("mount -o remount,size=75% / 2>/dev/null || true")

                # If /mnt is mounted, we can redirect cache/db to save space
                if os.path.ismount("/mnt"):
                    Path("/mnt/var/cache/pacman/pkg").mkdir(parents=True, exist_ok=True)
                    Path("/mnt/var/lib/pacman").mkdir(parents=True, exist_ok=True)

                    # Bind-mount both dirs so pacman on the live host writes to /mnt
                    self.run(
                        "mount --bind /mnt/var/cache/pacman/pkg /var/cache/pacman/pkg",
                        check=False,
                    )
                    self.run(
                        "mount --bind /mnt/var/lib/pacman /var/lib/pacman",
                        check=False,
                    )

                with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
                    f.write(script)
                    tmp_path = f.name
                try:
                    self.run(f"bash {tmp_path}")
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
                
                # Verify repo was added
                try:
                    conf_content = Path("/etc/pacman.conf").read_text()
                    if "[cachyos]" not in conf_content:
                        log.warning("CachyOS repository header [cachyos] not found in /etc/pacman.conf")
                except Exception as e:
                    log.error(f"Failed to verify /etc/pacman.conf: {e}")

                # After running the script, we MUST ensure the host's pacman is synced
                self.run("pacman -Sy --noconfirm")

    # ── Pre-flight checks ────────────────────────────────────────────────────

    def _check_uefi(self) -> None:
        if not Path("/sys/firmware/efi/efivars").is_dir():
            raise InstallError("EFI vars not found — please boot in UEFI mode.")

    def _check_internet(self) -> None:
        with Spinner("Checking internet connection…"):
            r = subprocess.run(
                "curl -fsSL --max-time 5 https://archlinux.org/",
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        if r.returncode != 0:
            raise InstallError("No internet connection detected.")
        print(f"  {Sym.OK}  Internet available.")

    def _check_nvidia(self) -> None:
        with Spinner("Detecting GPU(s)…"):
            lspci = subprocess.run(
                "lspci -nn", shell=True, capture_output=True, text=True
            ).stdout

        def is_display(line: str) -> bool:
            return any(c in line for c in ["VGA", "3D", "Display"])

        nvidia_lines = [l for l in lspci.splitlines()
                        if "NVIDIA" in l and is_display(l)]
        igpu_lines   = [l for l in lspci.splitlines()
                        if any(v in l for v in ["Intel", "AMD", "ATI"])
                        and is_display(l)]

        self.nvidia_gpu = bool(nvidia_lines)
        self.has_igpu   = bool(igpu_lines)

        if self.nvidia_gpu:
            gpu_name = nvidia_lines[0].split(":")[-1].strip()
            print(f"  {Sym.OK}  NVIDIA GPU  → {C.YELLOW}{gpu_name}{C.RESET}")
            if self.has_igpu:
                igpu_name = igpu_lines[0].split(":")[-1].strip()
                print(f"  {Sym.INFO}  iGPU        → {C.DIM}{igpu_name}{C.RESET}")
                print(f"  {Sym.INFO}  Hybrid graphics — PRIME will be configured.")
        else:
            print(f"  {Sym.INFO}  No NVIDIA GPU found — skipping NVIDIA setup.")

    # ── Disk scanning ────────────────────────────────────────────────────────

    def _scan_disks(self) -> list:
        raw = subprocess.run(
            "lsblk -dpno NAME,SIZE,RM,TYPE",
            shell=True, capture_output=True, text=True
        ).stdout.strip()

        disks = []
        for line in raw.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            name, size_str, removable, dtype = parts[0], parts[1], parts[2], parts[3]
            if dtype != "disk" or removable == "1":
                continue
            size_bytes = int(subprocess.run(
                f"lsblk -bdno SIZE {name}",
                shell=True, capture_output=True, text=True
            ).stdout.strip() or 0)
            d = DiskInfo(name=name, size_bytes=size_bytes, size_str=size_str)
            d.partitions = self._scan_partitions(d)
            disks.append(d)

        return sorted(disks, key=lambda d: d.size_bytes, reverse=True)

    def _scan_partitions(self, disk: DiskInfo) -> list:
        parts = []

        # ── Existing partitions via lsblk ────────────────────────────────────
        raw = subprocess.run(
            f"lsblk -pno NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT {disk.name}",
            shell=True, capture_output=True, text=True
        ).stdout.strip()

        for line in raw.splitlines():
            cols = line.split(None, 4)
            pname = cols[0] if len(cols) > 0 else ""
            if pname == disk.name:
                continue
            psize_str  = cols[1] if len(cols) > 1 else "?"
            fs_type    = cols[2] if len(cols) > 2 else ""
            label      = cols[3] if len(cols) > 3 else ""
            mountpoint = cols[4] if len(cols) > 4 else ""
            psize_bytes = int(subprocess.run(
                f"lsblk -bdno SIZE {pname}",
                shell=True, capture_output=True, text=True
            ).stdout.strip() or 0)
            parts.append(PartInfo(
                name=pname, size_bytes=psize_bytes, size_str=psize_str,
                fs_type=fs_type, label=label, mountpoint=mountpoint.strip()
            ))

        # ── Unallocated regions via sgdisk ────────────────────────────────────
        sgdisk_out = subprocess.run(
            f"sgdisk -p {disk.name} 2>/dev/null",
            shell=True, capture_output=True, text=True
        ).stdout

        sector_size = 512
        for line in sgdisk_out.splitlines():
            if "Logical sector size:" in line:
                try:
                    sector_size = int(line.split()[-2])
                except (IndexError, ValueError):
                    pass

        first_usable = last_usable = 0
        for line in sgdisk_out.splitlines():
            if "First usable sector" in line:
                try: first_usable = int(line.split()[-1])
                except ValueError: pass
            if "Last usable sector" in line:
                try: last_usable = int(line.split()[-1])
                except ValueError: pass

        ranges = []
        in_table = False
        for line in sgdisk_out.splitlines():
            if line.strip().startswith("Number"):
                in_table = True
                continue
            if in_table and line.strip():
                cols = line.split()
                if len(cols) >= 3:
                    try:
                        start = int(cols[1])
                        end   = int(cols[2])
                        ranges.append((start, end))
                    except ValueError:
                        pass

        ranges.sort()
        cursor = first_usable
        for (start, end) in ranges:
            if start > cursor + 2048:
                gap_start = cursor
                gap_end   = start - 1
                free_bytes = (gap_end - gap_start + 1) * sector_size
                if free_bytes >= 5 * 1024 ** 3:
                    parts.append(PartInfo(
                        name="", size_bytes=free_bytes,
                        size_str=fmt_bytes(free_bytes),
                        fs_type="", label="Unallocated",
                        is_free=True,
                        _free_start=gap_start,
                        _free_end=gap_end,
                    ))
            cursor = end + 1

        # Trailing free space after the last partition
        if last_usable > cursor + 2048:
            free_bytes = (last_usable - cursor + 1) * sector_size
            if free_bytes >= 5 * 1024 ** 3:
                parts.append(PartInfo(
                    name="", size_bytes=free_bytes,
                    size_str=fmt_bytes(free_bytes),
                    fs_type="", label="Unallocated",
                    is_free=True,
                    _free_start=cursor,
                    _free_end=last_usable,
                ))

        return parts

    def _has_windows(self, disk: DiskInfo) -> bool:
        """True if any partition on this disk looks like a Windows install."""
        for p in disk.partitions:
            if p.is_free:
                continue
            # NTFS/exFAT data partition → Windows data drive (not conclusive alone)
            if p.fs_type in ("ntfs", "exfat"):
                return True
            # FAT32 EFI partition: check for \EFI\Microsoft directory
            if p.fs_type in ("vfat",):
                tmp_mp = "/tmp/_nen_win_check"
                os.makedirs(tmp_mp, exist_ok=True)
                r = subprocess.run(
                    f"mount -o ro {p.name} {tmp_mp} 2>/dev/null",
                    shell=True
                )
                if r.returncode == 0:
                    has_ms = os.path.isdir(f"{tmp_mp}/EFI/Microsoft")
                    subprocess.run(f"umount {tmp_mp}", shell=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if has_ms:
                        return True
        return False

    def _find_efi_partition(self, disk: DiskInfo) -> str:
        """
        Return the path of the existing EFI system partition on this disk.
        We probe each vfat partition (by temporarily mounting it) and look
        for an /EFI directory.  The Windows EFI partition will always have
        /EFI/Microsoft; any other ESP will have /EFI/<vendor>.
        Returns "" if none found.
        """
        tmp_mp = "/tmp/_nen_efi_find"
        os.makedirs(tmp_mp, exist_ok=True)

        for p in disk.partitions:
            if p.is_free or p.fs_type not in ("vfat", ""):
                continue
            # If already mounted, check in-place
            if p.mountpoint:
                if os.path.isdir(f"{p.mountpoint}/EFI"):
                    return p.name
                continue
            # Try mounting read-only
            r = subprocess.run(
                f"mount -o ro {p.name} {tmp_mp} 2>/dev/null",
                shell=True
            )
            if r.returncode != 0:
                continue
            has_efi = os.path.isdir(f"{tmp_mp}/EFI")
            subprocess.run(f"umount {tmp_mp}", shell=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if has_efi:
                return p.name

        return ""

    # ── Disk selection UI ────────────────────────────────────────────────────

    def _print_disk_map(self, disks: list) -> None:
        print(f"\n  {C.BOLD}DETECTED STORAGE{C.RESET}\n")
        for i, disk in enumerate(disks):
            win_tag = (f"  {C.YELLOW}[Windows detected]{C.RESET}"
                       if self._has_windows(disk) else "")
            print(f"  {C.BOLD}{C.CYAN}[{i+1}]{C.RESET}  {C.BOLD}{disk.name}{C.RESET}  "
                  f"({disk.size_str}){win_tag}")
            for p in disk.partitions:
                if p.is_free:
                    icon  = f"{C.GREEN}◈{C.RESET}"
                    label = f"{C.GREEN}Free space  ← available for Arch{C.RESET}"
                    fsstr = ""
                else:
                    icon  = f"{C.DIM}▪{C.RESET}"
                    label = p.label or p.name
                    fsstr = f"  {C.DIM}[{p.fs_type}]{C.RESET}" if p.fs_type else ""
                print(f"         {icon}  {label}  {p.size_str}{fsstr}")
            print()

    def step_detect_disk(self) -> None:
        self.render()

        with Spinner("Scanning all storage devices…"):
            disks = self._scan_disks()

        if not disks:
            raise InstallError("No physical disks found.")

        self._print_disk_map(disks)

        # ── Detect dual-boot candidates ─────────────────────────────────────
        # A dual-boot candidate is a disk that has Windows AND at least one
        # unallocated region >= 30 GB (the user already ran Shrink Volume).
        dualboot_candidates = []
        for disk in disks:
            if not self._has_windows(disk):
                continue
            free_parts = [p for p in disk.partitions
                          if p.is_free and p.size_bytes >= MIN_FREE_BYTES]
            if free_parts:
                dualboot_candidates.append((disk, free_parts))

        # ── Present mode options ────────────────────────────────────────────
        print(f"  {C.BOLD}INSTALLATION MODE{C.RESET}\n")

        if dualboot_candidates:
            print(f"  {C.GREEN}Dual-boot candidate(s) detected!{C.RESET}")
            for disk, fparts in dualboot_candidates:
                for fp in fparts:
                    print(f"  {Sym.INFO}  {disk.name} → "
                          f"{C.GREEN}{fp.size_str}{C.RESET} unallocated "
                          f"— ready for Arch alongside Windows.")
            print()

        print(f"  {C.DIM}1){C.RESET}  {C.BOLD}Clean install{C.RESET}  "
              f"— wipe a whole disk and install Arch")
        if dualboot_candidates:
            print(f"  {C.DIM}2){C.RESET}  {C.BOLD}Dual-boot{C.RESET}  "
                  f"— install Arch into the unallocated space (keeps Windows)")
        print()

        valid_choices = ["1", "2"] if dualboot_candidates else ["1"]
        while True:
            choice = self.prompt(
                f"  {C.CYAN}› Select mode [{'/'.join(valid_choices)}]:{C.RESET} "
            ).strip()
            if choice in valid_choices:
                break
            print(f"  {Sym.WARN}  Invalid choice.")

        if choice == "1":
            self._select_clean_disk(disks)
        else:
            self._select_dualboot(dualboot_candidates)

        self.tick("Storage target confirmed")

    def _select_clean_disk(self, disks: list) -> None:
        self.install_mode = "clean"

        if len(disks) == 1:
            target = disks[0]
        else:
            print(f"\n  {C.BOLD}SELECT TARGET DISK{C.RESET} (will be completely wiped)\n")
            for i, d in enumerate(disks):
                print(f"  {C.DIM}{i+1}){C.RESET}  {d.name}  ({d.size_str})")
            while True:
                raw = self.prompt(f"\n  {C.CYAN}› Disk number:{C.RESET} ").strip()
                if raw.isdigit() and 1 <= int(raw) <= len(disks):
                    target = disks[int(raw) - 1]
                    break
                print(f"  {Sym.WARN}  Invalid selection.")

        if target.size_bytes < MIN_DISK_BYTES:
            raise InstallError(
                f"{target.name} is too small ({target.size_str}). Need ≥ 30 GB."
            )

        self.disk = target.name
        typewriter(f"\n  ⚠  ALL DATA ON {self.disk} WILL BE ERASED.", 0.02, C.RED)
        print(f"  Continuing in 5 seconds… (Ctrl+C to abort)\n")
        time.sleep(5)

    def _select_dualboot(self, candidates: list) -> None:
        """
        Pick the disk + free region for dual-boot.
        Reuses the existing Windows EFI partition — never creates a new one
        unless none is found.
        """
        self.install_mode = "dualboot"
        self.bootloader   = "grub"   # GRUB required for Windows chain-loading
        print(f"\n  {Sym.INFO}  Dual-boot mode forces {C.BOLD}GRUB{C.RESET} "
              f"(required for Windows chain-loading).")

        # Flatten candidates into a numbered list
        options = []
        for disk, fparts in candidates:
            for fp in fparts:
                options.append((disk, fp))

        if len(options) == 1:
            chosen_disk, chosen_free = options[0]
        else:
            print(f"\n  {C.BOLD}SELECT UNALLOCATED REGION{C.RESET}\n")
            for i, (d, fp) in enumerate(options):
                print(f"  {C.DIM}{i+1}){C.RESET}  {d.name}  → "
                      f"{C.GREEN}{fp.size_str}{C.RESET} free space")
            while True:
                raw = self.prompt(f"\n  {C.CYAN}› Region number:{C.RESET} ").strip()
                if raw.isdigit() and 1 <= int(raw) <= len(options):
                    chosen_disk, chosen_free = options[int(raw) - 1]
                    break
                print(f"  {Sym.WARN}  Invalid selection.")

        self.disk       = chosen_disk.name
        self.free_start = chosen_free._free_start   # int
        self.free_end   = chosen_free._free_end     # int
        self._win_disk_obj = chosen_disk

        self.win_efi_part = self._find_efi_partition(chosen_disk)
        if self.win_efi_part:
            print(f"  {Sym.OK}  Reusing existing EFI partition: "
                  f"{C.YELLOW}{self.win_efi_part}{C.RESET}")
        else:
            print(f"  {Sym.WARN}  No existing EFI partition found. "
                  f"A small one will be created inside the free space.")

        print(f"\n  {Sym.INFO}  Arch will be installed into "
              f"{C.GREEN}{chosen_free.size_str}{C.RESET} of unallocated space on "
              f"{C.YELLOW}{self.disk}{C.RESET}.")
        print(f"  {C.DIM}Windows and all existing data will not be touched.{C.RESET}")
        print(f"\n  Continuing in 5 seconds… (Ctrl+C to abort)")
        time.sleep(5)

    # ── Partitioning ─────────────────────────────────────────────────────────

    def step_partition(self) -> None:
        if self.install_mode == "clean":
            self._partition_clean()
        else:
            self._partition_dualboot()

    def _part_suffix(self) -> str:
        """NVMe/MMC partitions use a 'p' separator: nvme0n1p1, mmcblk0p1."""
        return "p" if any(x in self.disk for x in ("nvme", "mmcblk")) else ""

    def _next_part_num(self) -> int:
        """Return the next available partition number on self.disk."""
        raw = subprocess.run(
            f"lsblk -pno NAME {self.disk}",
            shell=True, capture_output=True, text=True
        ).stdout.strip()
        nums = []
        for line in raw.splitlines():
            line = line.strip()
            if line == self.disk:
                continue
            tail = line.replace(self.disk, "").lstrip("p")
            if tail.isdigit():
                nums.append(int(tail))
        return max(nums, default=0) + 1

    def _partition_clean(self) -> None:
        suffix = self._part_suffix()
        self.p_efi  = f"{self.disk}{suffix}1"
        self.p_swap = f"{self.disk}{suffix}2"
        self.p_root = f"{self.disk}{suffix}3"

        self._teardown_mounts()

        with Spinner("Partitioning disk (clean)…"):

            self.run(f"sgdisk --zap-all {self.disk}")
            self.run(f"sgdisk -o {self.disk}")
            self.run(f"sgdisk -n 1:0:+{EFI_SIZE_MIB}M -t 1:ef00 -c 1:EFI  {self.disk}")
            self.run(f"sgdisk -n 2:0:+{SWAP_SIZE}     -t 2:8200 -c 2:SWAP {self.disk}")
            self.run(f"sgdisk -n 3:0:0                -t 3:8300 -c 3:ARCH {self.disk}")
            self.run(f"partprobe {self.disk}", check=False)
            time.sleep(2)

            self.run(f"mkfs.fat -F32 -n EFI  {self.p_efi}")
            self.run(f"mkswap   -L   SWAP     {self.p_swap}")
            self.run(f"swapon                 {self.p_swap}", check=False)
            self.run(f"mkfs.btrfs -f -L ARCH  {self.p_root}")

        self.tick("Disk partitioned (clean)")

    def _partition_dualboot(self) -> None:
        """
        Carve partitions out of the pre-shrunk free space.

        Layout (existing EFI reused):
          free_start → free_start+SWAP_SIZE   → Linux swap
          (swap_end) → free_end               → Btrfs root

        If no EFI exists, a 512 MiB EFI is carved first, then swap + root.
        The Windows EFI partition is NEVER reformatted.
        """
        self._teardown_mounts()

        suffix   = self._part_suffix()
        next_num = self._next_part_num()

        with Spinner("Carving Arch partitions into free space…"):
            if self.win_efi_part:
                # ── Reuse existing EFI: create only Swap + Root ───────────────
                self.p_efi  = self.win_efi_part
                swap_num    = next_num
                root_num    = next_num + 1

                # Swap: from free_start for SWAP_SIZE
                self.run(
                    f"sgdisk -n {swap_num}:{self.free_start}:+{SWAP_SIZE} "
                    f"-t {swap_num}:8200 -c {swap_num}:SWAP {self.disk}"
                )
                # Root: from after swap to free_end (0 = relative start)
                self.run(
                    f"sgdisk -n {root_num}:0:{self.free_end} "
                    f"-t {root_num}:8300 -c {root_num}:ARCH {self.disk}"
                )
            else:
                # ── No existing EFI: carve EFI + Swap + Root ─────────────────
                efi_num  = next_num
                swap_num = next_num + 1
                root_num = next_num + 2

                self.run(
                    f"sgdisk -n {efi_num}:{self.free_start}:+512M "
                    f"-t {efi_num}:ef00 -c {efi_num}:EFI {self.disk}"
                )
                self.run(
                    f"sgdisk -n {swap_num}:0:+{SWAP_SIZE} "
                    f"-t {swap_num}:8200 -c {swap_num}:SWAP {self.disk}"
                )
                self.run(
                    f"sgdisk -n {root_num}:0:{self.free_end} "
                    f"-t {root_num}:8300 -c {root_num}:ARCH {self.disk}"
                )
                self.p_efi = f"{self.disk}{suffix}{efi_num}"
                self.run(f"mkfs.fat -F32 -n EFI {self.p_efi}")

            self.run(f"partprobe {self.disk}", check=False)
            time.sleep(2)

            self.p_swap = f"{self.disk}{suffix}{swap_num}"
            self.p_root = f"{self.disk}{suffix}{root_num}"

            self.run(f"mkswap   -L SWAP      {self.p_swap}")
            self.run(f"swapon               {self.p_swap}", check=False)
            self.run(f"mkfs.btrfs -f -L ARCH {self.p_root}")

        self.tick("Partitions created (dual-boot)")

    def step_mount(self) -> None:
        with Spinner("Mounting filesystems…"):
            opts = f"noatime,compress={BTRFS_COMPRESS},space_cache=v2"
            self.run(f"mount -o {opts} {self.p_root} /mnt")

            # EFI mount point:
            #   GRUB uses --efi-directory=/boot/efi
            #   systemd-boot uses /boot directly
            if self.bootloader == "grub":
                efi_mp = "/mnt/boot/efi"
            else:
                efi_mp = "/mnt/boot"

            Path(efi_mp).mkdir(parents=True, exist_ok=True)
            self.run(f"mount -o umask=0077 {self.p_efi} {efi_mp}")

        self.tick("Filesystems mounted")

    # ── Base install ─────────────────────────────────────────────────────────

    def step_install_base(self) -> None:
        # First, ensure repositories are set up on the LIVE host.
        # This is critical so that 'pacstrap' and 'pacman -Si' can find CachyOS packages.
        self.setup_cachyos()

        # We use a custom PM command for validation on the live host.
        # It MUST use the host's /etc/pacman.conf (which setup_cachyos modified).
        # We also point it to /mnt for DB and Cache to avoid tmpfs overflow.
        PM = ("pacman --config /etc/pacman.conf "
              "--dbpath /mnt/var/lib/pacman "
              "--cachedir /mnt/var/cache/pacman/pkg")

        with Spinner("Refreshing keyrings…"):
            self.run(f"{PM} -Sy --noconfirm archlinux-keyring", check=False)
        self.tick("Keyrings updated")

        with Spinner("Syncing package databases…"):
            # This syncs the databases at /mnt/var/lib/pacman
            self.run(f"{PM} -Sy")
        self.tick("Repositories synced")

        pkgs = list(BASE_PACKAGES)

        if self.install_mode == "dualboot" or self.bootloader == "grub":
            pkgs.extend(GRUB_PACKAGES)
            self.bootloader = "grub"

        if self.nvidia_gpu:
            pkgs.extend(NVIDIA_PACKAGES)
            if self.has_igpu:
                pkgs.append("nvidia-prime")

        with Spinner("Validating package list…"):
            # Validate packages using the databases we just synced
            valid = []
            skipped = []
            mandatory = ["base", "linux-cachyos", "btrfs-progs", "sudo"]
            
            for p in pkgs:
                r = subprocess.run(
                    f"{PM} -Si {p}",
                    shell=True, capture_output=True
                )
                if r.returncode == 0:
                    valid.append(p)
                else:
                    if p in mandatory:
                        # CRITICAL: Do not skip the kernel or base system!
                        raise InstallError(
                            f"CRITICAL PACKAGE NOT FOUND: {p}\n"
                            "This usually means the CachyOS repositories failed to initialize.\n"
                            "Please check your internet connection or the logs."
                        )
                    skipped.append(p)
                    log.warning("Optional package not found, skipping: %s", p)

        if skipped:
            print(f"  {Sym.WARN}  Skipped {len(skipped)} unavailable package(s): "
                  f"{C.DIM}{', '.join(sorted(skipped))}{C.RESET}")

        # pacstrap must use the live host's pacman.conf (which now includes
        # CachyOS repos added by setup_cachyos) so it can find linux-cachyos.
        print(f"  {Sym.INFO}  Installing {len(valid)} packages via pacstrap…")
        # We don't need -C here if we already modified /etc/pacman.conf, 
        # but being explicit is safer.
        self.run(
            f"pacstrap -C /etc/pacman.conf /mnt {' '.join(valid)}"
        )
        self.tick("Base system installed")

    # ── NVIDIA chroot block ───────────────────────────────────────────────────

    def _build_nvidia_chroot_block(self) -> str:
        if not self.nvidia_gpu:
            return "# No NVIDIA GPU — nothing to configure.\n"

        kparams = (
            "nvidia-drm.modeset=1 "
            "nvidia-drm.fbdev=1 "
            "nvidia.NVreg_PreserveVideoMemoryAllocations=1"
        )

        if self.bootloader == "systemd-boot":
            bootloader_patch = (
                f'sed -i "s|^options .*|& {kparams}|" '
                f'/boot/loader/entries/arch.conf'
            )
        else:
            bootloader_patch = (
                f'sed -i \'s|^GRUB_CMDLINE_LINUX_DEFAULT="\\(.*\\)"|'
                f'GRUB_CMDLINE_LINUX_DEFAULT="\\1 {kparams}"|\' /etc/default/grub\n'
                f'grub-mkconfig -o /boot/grub/grub.cfg'
            )

        prime_block = ""
        if self.has_igpu:
            prime_block = f"""
# ── PRIME render offload ──────────────────────────────────────────────────────
cat >> /etc/environment.d/10-nvidia.conf << 'EOF_PRIME'
__NV_PRIME_RENDER_OFFLOAD=1
__VK_LAYER_NV_optimus=NVIDIA_only
EOF_PRIME
mkdir -p /home/{self.username}/.local/share/applications
cp /usr/share/applications/kitty.desktop \\
   /home/{self.username}/.local/share/applications/kitty-nvidia.desktop 2>/dev/null || true
sed -i \\
    "s|^Exec=kitty|Exec=prime-run kitty|;s|^Name=kitty|Name=kitty (NVIDIA)|" \\
    /home/{self.username}/.local/share/applications/kitty-nvidia.desktop 2>/dev/null || true
chown -R {self.username}:{self.username} /home/{self.username}/.local
"""

        return f"""
# ── NVIDIA (linux-cachyos · nvidia-open pre-built) ────────────────────────────
sed -i '/^MODULES=/{{s/)$/ nvidia nvidia_modeset nvidia_uvm nvidia_drm)/}}' \\
    /etc/mkinitcpio.conf
mkinitcpio -P linux-cachyos

{bootloader_patch}

cat > /etc/modprobe.d/blacklist-nouveau.conf << 'EOF_NOUVEAU'
blacklist nouveau
options nouveau modeset=0
EOF_NOUVEAU

systemctl enable nvidia-suspend nvidia-resume nvidia-hibernate 2>/dev/null || true

mkdir -p /etc/environment.d
cat > /etc/environment.d/10-nvidia.conf << 'EOF_ENV'
GBM_BACKEND=nvidia-drm
__GLX_VENDOR_LIBRARY_NAME=nvidia
LIBVA_DRIVER_NAME=nvidia
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json
NVD_BACKEND=direct
EOF_ENV
{prime_block}
"""

    # ── Configure ────────────────────────────────────────────────────────────

    def step_configure(self) -> None:
        with Spinner("Generating fstab…"):
            self.run("genfstab -U /mnt >> /mnt/etc/fstab")
        self.tick("fstab written")

        self.root_uuid = self.run(
            f"blkid -s UUID -o value {self.p_root}", capture=True
        )
        shutil.copy("/etc/resolv.conf", "/mnt/etc/resolv.conf")

        # ── Bootloader snippet ──────────────────────────────────────────────
        if self.bootloader == "systemd-boot":
            # EFI is mounted at /boot for systemd-boot
            bootloader_cmds = f"""
bootctl install
cat > /boot/loader/loader.conf << 'EOF'
default arch
timeout 3
editor no
EOF
UCODE=""
[ -f /boot/intel-ucode.img ] && UCODE="\\ninitrd /intel-ucode.img"
printf 'title   Arch Linux (CachyOS)\\nlinux   /vmlinuz-linux-cachyos%s\\ninitrd  /initramfs-linux-cachyos.img\\noptions root=UUID={self.root_uuid} rw quiet splash\\n' \\
    "$UCODE" > /boot/loader/entries/arch.conf
"""
        else:
            # GRUB — EFI is mounted at /boot/efi
            # os-prober needs to see the Windows partition from inside the chroot.
            # We pre-mount Windows NTFS partitions under /mnt/windows_probe before
            # entering the chroot, and pass their paths via /etc/os-prober-mounts.
            # The chroot script reads that file and mounts them before running
            # grub-mkconfig, then cleans up.
            bootloader_cmds = f"""
grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=GRUB --recheck

# ── /etc/default/grub ────────────────────────────────────────────────────────
sed -i '/GRUB_DISABLE_OS_PROBER/d' /etc/default/grub
echo 'GRUB_DISABLE_OS_PROBER=false' >> /etc/default/grub

sed -i 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=10/' /etc/default/grub
grep -q '^GRUB_TIMEOUT=' /etc/default/grub || echo 'GRUB_TIMEOUT=10' >> /etc/default/grub

# Make sure GRUB shows the menu (not hidden)
sed -i 's/^GRUB_TIMEOUT_STYLE=.*/GRUB_TIMEOUT_STYLE=menu/' /etc/default/grub
grep -q '^GRUB_TIMEOUT_STYLE=' /etc/default/grub || echo 'GRUB_TIMEOUT_STYLE=menu' >> /etc/default/grub

# ── Explicit custom entry for linux-cachyos at the TOP ───────────────────────
ROOT_UUID=$(blkid -s UUID -o value {self.p_root})
UCODE=""
[ -f /boot/intel-ucode.img ] && UCODE="initrd /boot/intel-ucode.img"

cat > /etc/grub.d/09_custom << GRUBEOF
#!/bin/sh
exec tail -n +3 \$0
menuentry "Arch Linux (CachyOS kernel)" --class arch --class gnu-linux --class gnu --class os {{
    search --no-floppy --fs-uuid --set=root $ROOT_UUID
    linux /boot/vmlinuz-linux-cachyos root=UUID=$ROOT_UUID rw quiet splash
    $UCODE
    initrd /boot/initramfs-linux-cachyos.img
}}
GRUBEOF
chmod +x /etc/grub.d/09_custom

# Set Arch as default
sed -i 's/^GRUB_DEFAULT=.*/GRUB_DEFAULT="Arch Linux (CachyOS kernel)"/' /etc/default/grub
grep -q '^GRUB_DEFAULT=' /etc/default/grub || echo 'GRUB_DEFAULT="Arch Linux (CachyOS kernel)"' >> /etc/default/grub

# ── Probe for Windows ─────────────────────────────────────────────────────────
PROBE_LIST="/etc/nen-probe-mounts"
if [ -f "$PROBE_LIST" ]; then
    while IFS= read -r dev; do
        mp="/mnt/probe_$(basename "$dev")"
        mkdir -p "$mp"
        mount -o ro,noatime "$dev" "$mp" 2>/dev/null || true
    done < "$PROBE_LIST"
fi

os-prober

grub-mkconfig -o /boot/grub/grub.cfg

# ── Cleanup probe mounts ──────────────────────────────────────────────────────
if [ -f "$PROBE_LIST" ]; then
    while IFS= read -r dev; do
        mp="/mnt/probe_$(basename "$dev")"
        umount "$mp" 2>/dev/null || true
        rmdir  "$mp" 2>/dev/null || true
    done < "$PROBE_LIST"
    rm -f "$PROBE_LIST"
fi
"""

        nvidia_block = self._build_nvidia_chroot_block()

        chroot_script = f"""#!/bin/bash
set -euo pipefail

# ── Locale & clock ────────────────────────────────────────────────────────────
ln -sf /usr/share/zoneinfo/{TIMEZONE} /etc/localtime
hwclock --systohc
sed -i 's/^#\\({LOCALE}\\)/\\1/' /etc/locale.gen
locale-gen
echo "LANG={LOCALE}"   > /etc/locale.conf
echo "KEYMAP={KEYMAP}" > /etc/vconsole.conf

# ── Hostname ──────────────────────────────────────────────────────────────────
echo "{HOSTNAME}" > /etc/hostname
cat > /etc/hosts << 'EOF'
127.0.0.1   localhost
::1         localhost
127.0.1.1   {HOSTNAME}.localdomain {HOSTNAME}
EOF

# ── Users & sudo ──────────────────────────────────────────────────────────────
useradd -m -G wheel,audio,video,storage -s /bin/bash "{self.username}"
echo "{self.username}:{self.password}" | chpasswd
echo "root:{self.password}"            | chpasswd
sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers

# ── Services ──────────────────────────────────────────────────────────────────
systemctl enable NetworkManager bluetooth
systemctl disable getty@tty2.service 2>/dev/null || true
systemctl enable ly@tty2.service

# ── X11 Turkish keyboard ──────────────────────────────────────────────────────
mkdir -p /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/00-keyboard.conf << 'EOF'
Section "InputClass"
    Identifier "system-keyboard"
    MatchIsKeyboard "on"
    Option "XkbLayout" "tr"
EndSection
EOF

# ── KDE: default terminal + Ctrl+Alt+T ───────────────────────────────────────
CFG="/home/{self.username}/.config"
mkdir -p "$CFG"
cat > "$CFG/kdeglobals" << 'EOF'
[General]
TerminalApplication=kitty
TerminalService=kitty.desktop
EOF
cat > "$CFG/kglobalshortcutsrc" << 'EOF'
[kitty.desktop]
_k_friendly_name=kitty
_launch=Ctrl+Alt+T,none,kitty
EOF
chown -R "{self.username}:{self.username}" "$CFG"

# ── AUR helper: yay ───────────────────────────────────────────────────────────
echo "{self.username} ALL=(ALL) NOPASSWD: /usr/bin/pacman" > /etc/sudoers.d/99-yay
chmod 440 /etc/sudoers.d/99-yay
runuser -u "{self.username}" -- bash -c "
    cd /tmp
    git clone https://aur.archlinux.org/yay.git
    cd yay && makepkg -si --noconfirm
    rm -rf /tmp/yay
"
rm -f /etc/sudoers.d/99-yay

# ── NVIDIA ────────────────────────────────────────────────────────────────────
{nvidia_block}

# ── Bootloader ────────────────────────────────────────────────────────────────
{bootloader_cmds}
"""

        print(f"  {Sym.INFO}  Injecting CachyOS repos into target system…")
        # Ensure CachyOS repos are also injected into the target CHROOT
        self.setup_cachyos(target="/mnt")

        if self.bootloader == "grub" and self._win_disk_obj is not None:
            ntfs_parts = [
                p.name for p in self._win_disk_obj.partitions
                if not p.is_free and p.fs_type in ("ntfs", "exfat") and p.name
            ]
            if ntfs_parts:
                probe_file = Path("/mnt/etc/nen-probe-mounts")
                probe_file.write_text("\n".join(ntfs_parts) + "\n")
                log.info("os-prober probe list: %s", ntfs_parts)
                print(f"  {Sym.INFO}  Registered {len(ntfs_parts)} Windows partition(s) "
                      f"for GRUB os-prober: "
                      f"{C.DIM}{', '.join(ntfs_parts)}{C.RESET}")

        print(f"  {Sym.INFO}  Configuring system inside chroot…")
        self.chroot_run(chroot_script)

        note = " + NVIDIA" + (" PRIME" if self.has_igpu else "") if self.nvidia_gpu else ""
        mode = " [dual-boot/GRUB]" if self.install_mode == "dualboot" else ""
        self.tick(f"System configured{note}{mode}")

    # ── Finish ───────────────────────────────────────────────────────────────

    def step_finish(self) -> None:
        self.step = TOTAL_STEPS
        self.render()
        typewriter(f"\n  {C.GREEN}{C.BOLD}INSTALLATION COMPLETE.{C.RESET}", 0.04)

        if self.install_mode == "dualboot":
            print(f"\n  {Sym.INFO}  {C.BOLD}Dual-boot tip:{C.RESET} On next boot, "
                  f"GRUB will show both Arch Linux and Windows.")
            print(f"         If Windows doesn't appear, boot into Arch and run:")
            print(f"         {C.DIM}sudo os-prober && sudo grub-mkconfig -o /boot/grub/grub.cfg{C.RESET}")

        print(f"\n  {C.BOLD}CLEANUP{C.RESET}")
        ans = self.prompt(
            f"  {C.CYAN}?{C.RESET}  Delete install log ({LOG_FILE})? [Y/n]: "
        ).strip().lower()
        keep_log = (ans == "n")

        with Spinner("Unmounting and cleaning up…"):
            self._teardown_mounts()
            if not keep_log and LOG_FILE.exists():
                LOG_FILE.unlink(missing_ok=True)
            try:
                Path(sys.argv[0]).unlink()
            except Exception:
                pass

        print(f"  {Sym.OK}  All clean.")
        print(f"\n  {C.YELLOW}⚠{C.RESET}  Remove installation media, then press Enter to reboot.")
        try:
            self.prompt("")
        except Exception:
            pass

        os.system("tput cnorm")
        print(f"\n  {C.GREEN}Rebooting…{C.RESET}")
        os.system("reboot")

    # ── Orchestrator ─────────────────────────────────────────────────────────

    def step_welcome(self) -> None:
        os.system("tput civis")
        self.render()
        typewriter("  Welcome to the installer…", color=C.CYAN)
        time.sleep(0.5)

        self._check_uefi()
        self._check_internet()
        self._check_nvidia()

        print(f"\n  {C.BOLD}USER CONFIGURATION{C.RESET}")

        while True:
            self.username = self.prompt(f"  {C.CYAN}› Username:{C.RESET} ").strip()
            if USERNAME_RE.match(self.username):
                break
            print(f"  {Sym.WARN}  Invalid username. "
                  f"Use lowercase letters, digits, underscore or hyphen; "
                  f"must start with a letter or underscore.")

        while True:
            os.system("tput cnorm")
            pw1 = getpass.getpass(f"  {C.CYAN}› Password:{C.RESET} ")
            pw2 = getpass.getpass(f"  {C.CYAN}› Confirm password:{C.RESET} ")
            if pw1 and pw1 == pw2:
                self.password = pw1
                break
            print(f"  {Sym.WARN}  Passwords don't match — try again.")

        print(f"\n  {C.BOLD}BOOTLOADER{C.RESET}  {C.DIM}(dual-boot always uses GRUB){C.RESET}")
        print(f"  {C.DIM}1) systemd-boot  (recommended for single-boot){C.RESET}")
        print(f"  {C.DIM}2) GRUB{C.RESET}")
        choice = self.prompt(f"  {C.CYAN}› Select [1/2] (default 1):{C.RESET} ").strip()
        self.bootloader = "grub" if choice == "2" else "systemd-boot"

        self.in_progress = True

    def run_all(self) -> None:
        self.step_welcome()
        self.step_detect_disk()
        self.step_partition()
        self.step_mount()
        self.step_install_base()
        self.step_configure()
        self.step_finish()


# ─── Signal & entry ────────────────────────────────────────────────────────────

def _on_sigint(sig, frame):
    print(f"\n\n  {C.YELLOW}Interrupted — cleaning up…{C.RESET}")
    os.system("swapoff -a 2>/dev/null")
    os.system("umount -l /mnt 2>/dev/null")
    os.system("umount -R /mnt 2>/dev/null")
    os.system("tput cnorm")
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGINT, _on_sigint)
    installer = Installer()
    try:
        installer.run_all()
    except InstallError as exc:
        installer.abort(str(exc))
        sys.exit(1)
    except Exception as exc:
        installer.abort(f"Unexpected error: {exc}")
        log.exception("Unhandled exception")
        sys.exit(1)
    finally:
        os.system("tput cnorm")


if __name__ == "__main__":
    main()
