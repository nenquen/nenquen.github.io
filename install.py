#!/usr/bin/env python3
import subprocess
import sys
import os
import time
import shutil
import getpass
import threading
import itertools
import signal

# --- UI Theme & Constants ---
class Colors:
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    PURPLE = "\033[35m"
    LILAC = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    CLEAR = "\033[H\033[2J"

class Symbol:
    BLOCK_FULL = "#"
    BLOCK_DARK = "*"
    BLOCK_MED = "="
    BLOCK_LIGHT = "-"
    SUCCESS = "[  OK  ]"
    ERROR = "[ FAIL ]"
    INFO = "[ INFO ]"
    SPINNER = ["/", "-", "\\", "|"]

# Configuration
LOG_FILE = "/tmp/nen-install.log"
TOTAL_STEPS = 12
HOSTNAME = "archlinux"
TIMEZONE = "Europe/Istanbul"
LOCALE = "en_US.UTF-8"
KEYMAP = "trq"
EFI_SIZE_MIB = 1024
BTRFS_COMPRESS = "zstd:3"
SWAP_SIZE = "16G"

HEADER = r'''
 _____         _                   
|  _  |___ ___| |_ ___ _ _ ___ ___ 
|     |  _|  _|   | . | | | -_|   |
|__|__|_| |___|_|_|_  |___|___|_|_|
                    |_|            
'''

# --- Utility Functions ---
def typewriter_print(text, delay=0.01, color=Colors.RESET):
    sys.stdout.write(color)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(Colors.RESET + "\n")

class Spinner:
    def __init__(self, message="Working..."):
        self.message = message
        self.stop_running = threading.Event()
        self.spin_thread = threading.Thread(target=self._animate)

    def _animate(self):
        for char in itertools.cycle(Symbol.SPINNER):
            if self.stop_running.is_set():
                break
            sys.stdout.write(f"\r  {Colors.CYAN}{char}{Colors.RESET} {self.message}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")

    def __enter__(self):
        self.spin_thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running.set()
        self.spin_thread.join()

# --- Core Installer ---
class Installer:
    def __init__(self):
        self.current_step = 0
        self.ui_mode = "welcome"
        self.bootloader = "systemd-boot"
        self.username = ""
        self.password = ""
        self.disk = ""
        self.p1 = self.p2 = self.p3 = ""
        self.root_uuid = ""

    def log(self, message):
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")

    def run(self, cmd, check=True, capture=False, silent=False):
        self.log(f"EXEC: {cmd}")
        try:
            if capture:
                result = subprocess.run(cmd, shell=True, check=check, text=True, capture_output=True)
                return result.stdout.strip()
            else:
                with open(LOG_FILE, "a") as f:
                    subprocess.run(cmd, shell=True, check=check, stdout=f, stderr=f)
                return True
        except subprocess.CalledProcessError as e:
            self.on_error(f"Hardware/System Error: Command failed with code {e.returncode}\nCMD: {cmd}")
            sys.exit(1)

    def safe_input(self, prompt=""):
        os.system("tput cnorm")
        try:
            user_input = input(prompt)
        except EOFError:
            try:
                with open("/dev/tty", "r") as tty:
                    sys.stdout.write(prompt)
                    sys.stdout.flush()
                    user_input = tty.readline().strip()
            except Exception:
                user_input = ""
        finally:
            if self.ui_mode != "welcome":
                os.system("tput civis")
        return user_input

    def check_pkg(self, pkg_name):
        try:
            res = subprocess.run(f"pacman -Si {pkg_name}", shell=True, capture_output=True, text=True)
            return res.returncode == 0
        except:
            return False

    def setup_cachyos(self, target=None):
        msg = f"Injecting CachyOS optimizations into {'target' if target else 'host'}..."
        with Spinner(msg):
            # If in live host, redirect cache to physical disk to avoid 'disk full' error
            if not target:
                os.system("mount -o remount,size=75% / &>/dev/null")
                os.makedirs("/mnt/var/cache/pacman/pkg", exist_ok=True)
                self.run("mount --bind /mnt/var/cache/pacman/pkg /var/cache/pacman/pkg", check=False)

            script = """
set -e
mkdir -p /mnt/tmp/cachyos-setup
cd /mnt/tmp/cachyos-setup
echo "i Fetching official CachyOS repository package..."
curl -sLO https://mirror.cachyos.org/cachyos-repo.tar.xz
tar xvf cachyos-repo.tar.xz
cd cachyos-repo
echo "i Running official repository configuration (High Resource Step)..."
# Disable 'set -e' temporarily to allow mirror-rating even if initial sync is shaky
set +e
yes | ./cachyos-repo.sh
echo "i Optimizing mirrors for maximum performance..."
if command -v cachyos-rate-mirrors &>/dev/null; then
    cachyos-rate-mirrors
else
    # Fallback to forced full database refresh
    pacman -Syy
fi
set -e
"""
            if target:
                # Inside chroot, move script to root to ensure accessibility
                inner_script = script.replace("/mnt/tmp/cachyos-setup", "/tmp/cachyos-setup")
                with open(f"{target}/cachy_setup.sh", "w") as f: f.write(inner_script)
                self.run(f"arch-chroot {target} bash /cachy_setup.sh")
                self.run(f"rm -f {target}/cachy_setup.sh", check=False)
            else:
                with open("/tmp/cachy.sh", "w") as f: f.write(script)
                self.run("bash /tmp/cachy.sh")

    def render(self):
        sys.stdout.write(Colors.CLEAR)
        # Main Logo (Offset to center)
        for line in HEADER.strip("\n").split("\n"):
            print(f"     {Colors.LILAC}{line}{Colors.RESET}")
        
        # Centered Sub-header
        print(f"        {Colors.DIM}Nen's personal arch installer{Colors.RESET}\n")

        if self.ui_mode == "welcome":
            print(f"\n  {Colors.BOLD}SYSTEM READY.{Colors.RESET}")
            return

        # Progress Section
        print(f"\n  {Colors.DIM}Installation Status:{Colors.RESET}")
        width = 40
        percent = int(self.current_step * 100 / TOTAL_STEPS)
        filled = int(self.current_step * width / TOTAL_STEPS)
        empty = width - filled
        
        # Color transition for bar
        if percent < 40: bar_color = Colors.BLUE
        elif percent < 80: bar_color = Colors.CYAN
        else: bar_color = Colors.GREEN

        bar = f"{bar_color}{Symbol.BLOCK_FULL * filled}{Colors.DIM}{Symbol.BLOCK_LIGHT * empty}{Colors.RESET}"
        print(f"  [{bar}] {Colors.BOLD}{percent}%{Colors.RESET}")
        print(f"  {Colors.DIM}Log: {LOG_FILE}{Colors.RESET}\n")

    def progress_next(self, msg=None):
        if msg:
            self.log(msg)
            print(f"  {Colors.GREEN}{Symbol.SUCCESS}{Colors.RESET} {msg}")
        self.current_step += 1
        time.sleep(0.5)
        self.render()

    def on_error(self, err_msg):
        self.render()
        print(f"\n  {Colors.RED}{Colors.BOLD}{Symbol.ERROR} FATAL ERROR:{Colors.RESET}")
        print(f"  {Colors.RED}{err_msg}{Colors.RESET}")
        print(f"\n  {Colors.YELLOW}{Symbol.INFO} Log snippet:{Colors.RESET}")
        if os.path.exists(LOG_FILE):
            subprocess.run(f"tail -n 10 {LOG_FILE}", shell=True)
        print(f"\n  {Colors.BOLD}Press Enter to exit...{Colors.RESET}")
        try:
            self.safe_input()
        except:
            pass

    def welcome(self):
        os.system("tput civis")
        self.render()
        typewriter_print("  Welcome", delay=0.02, color=Colors.CYAN)
        time.sleep(1)

        # Pre-flight checks
        if not os.path.isdir("/sys/firmware/efi/efivars"):
            self.on_error("EFI Vars not found. Please boot in UEFI mode.")
            sys.exit(1)

        # Check internet
        typewriter_print("  Checking internet connection...", delay=0.01)
        try:
            subprocess.run("curl -fsSL --max-time 3 https://archlinux.org/", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  {Colors.GREEN}{Symbol.SUCCESS} Internet available.{Colors.RESET}")
        except:
            self.on_error("No network detected. Internet is required.")
            sys.exit(1)

        print(f"\n  {Colors.BOLD}USER CONFIGURATION{Colors.RESET}")
        self.username = self.safe_input(f"  {Colors.CYAN}> Username:{Colors.RESET} ").strip()
        while not self.username:
            self.username = self.safe_input(f"  {Colors.RED}! Username cannot be empty:{Colors.RESET} ").strip()
        
        while True:
            os.system("tput cnorm")
            self.password = getpass.getpass(f"  {Colors.CYAN}> Password:{Colors.RESET} ")
            p2 = getpass.getpass(f"  {Colors.CYAN}> Confirm Password:{Colors.RESET} ")
            if self.password and self.password == p2:
                break
            print(f"  {Colors.RED}! Match error. Try again.{Colors.RESET}")

        print(f"\n  {Colors.BOLD}BOOTLOADER SELECTION{Colors.RESET}")
        print(f"  {Colors.DIM}1) Systemd-boot{Colors.RESET}")
        print(f"  {Colors.DIM}2) GRUB{Colors.RESET}")
        bc = self.safe_input(f"  {Colors.CYAN}> Select [1/2] (Default 1):{Colors.RESET} ").strip() or "1"
        self.bootloader = "grub" if bc == "2" else "systemd-boot"

    def detect_disk(self):
        self.ui_mode = "progress"
        self.render()
        print(f"  {Colors.CYAN}{Symbol.INFO} Scanning storage topology...{Colors.RESET}")
        
        cmd = "lsblk -dpno NAME,TYPE,SIZE,RM | awk '$2==\"disk\" && $4==0 {print $1, $3}' | sort -h -k2 | tail -n1 | awk '{print $1}'"
        self.disk = self.run(cmd, capture=True)
        
        if not self.disk:
            self.on_error("No physical disks detected.")
            sys.exit(1)

        size_str = self.run(f"lsblk -dno SIZE {self.disk}", capture=True)
        print(f"  {Colors.BOLD}Target Disk:{Colors.RESET} {Colors.YELLOW}{self.disk}{Colors.RESET} ({size_str})")
        
        # Space check
        bytes = int(self.run(f"lsblk -bdno SIZE {self.disk} | head -n1", capture=True) or 0)
        if bytes < 30 * 1024**3:
            self.on_error("Insufficient storage (< 30GB).")
            sys.exit(1)

        typewriter_print(f"\n  ! WARNING: ALL DATA ON {self.disk} WILL BE WIPED !", 0.02, color=Colors.RED)
        print(f"  Proceeding in 5 seconds... (Ctrl+C to abort)")
        time.sleep(5)
        self.progress_next("Hardware validation complete")

    def partition_and_format(self):
        if "nvme" in self.disk or "mmcblk" in self.disk:
            self.p1, self.p2, self.p3 = f"{self.disk}p1", f"{self.disk}p2", f"{self.disk}p3"
        else:
            self.p1, self.p2, self.p3 = f"{self.disk}1", f"{self.disk}2", f"{self.disk}3"

        with Spinner("Formatting file structures..."):
            # Aggressive cleanup of previous mounts/binds
            os.system("umount -l /var/cache/pacman/pkg 2>/dev/null")
            os.system("umount -R /mnt 2>/dev/null")
            os.system("swapoff -a 2>/dev/null")
            
            self.run(f"sgdisk --zap-all {self.disk}")
            self.run(f"sgdisk -o {self.disk}")
            self.run(f"sgdisk -n 1:0:+{EFI_SIZE_MIB}M -t 1:ef00 -c 1:EFI {self.disk}")
            self.run(f"sgdisk -n 2:0:+{SWAP_SIZE} -t 2:8200 -c 2:SWAP {self.disk}")
            self.run(f"sgdisk -n 3:0:0 -t 3:8300 -c 3:ARCH {self.disk}")
            self.run(f"partprobe {self.disk}", check=False)
            time.sleep(2)

            self.run(f"mkfs.fat -F32 -n EFI {self.p1}")
            self.run(f"mkfs.btrfs -f -L ARCH {self.p3}")
            self.run(f"mkswap -L SWAP {self.p2}")
            self.run(f"swapon {self.p2}", check=False)
        
        self.progress_next("Storage mapping finalized")

        with Spinner("Mounting filesystem tree..."):
            self.run(f"mount -o noatime,compress={BTRFS_COMPRESS},space_cache=v2 {self.p3} /mnt")
            os.makedirs("/mnt/boot", exist_ok=True)
            self.run(f"mount -o umask=0077 {self.p1} /mnt/boot")
        self.progress_next("Hierarchy established")

    def install_base(self):
        self.setup_cachyos()
        
        with Spinner("Updating system keyrings..."):
            self.run("pacman -Sy --noconfirm archlinux-keyring", check=False)
        self.progress_next("Keyrings modernized")

        with Spinner("Synchronizing package databases..."):
            self.run("pacman -Sy")
        self.progress_next("Repositories synchronized")

        all_pkgs = [
            "base", "linux-cachyos", "linux-cachyos-headers", "linux-firmware", 
            "intel-ucode", "btrfs-progs", "sudo", "base-devel", "git", "go", 
            "networkmanager", "bluez", "bluez-utils", "pipewire", 
            "pipewire-pulse", "wireplumber", "ly",
            "plasma-desktop", "plasma-nm", "powerdevil", "kinfocenter",
            "spectacle", "bluedevil", "plasma-pa", "kitty", "dolphin",
            "noto-fonts", "noto-fonts-emoji", "ttf-jetbrains-mono-nerd",
            "ark", "unzip", "unrar", "gwenview", "kate",
            "plasma-systemmonitor", "xorg-xwayland", "breeze-gtk"
        ]
        if self.bootloader == "grub":
            all_pkgs.extend(["grub", "efibootmgr"])

        valid_pkgs = []
        with Spinner("Validating hardware drivers..."):
            for pkg in all_pkgs:
                if self.check_pkg(pkg):
                    valid_pkgs.append(pkg)
                else:
                    self.log(f"SKIPPED: {pkg} (Not found in repos)")

        print(f"  {Colors.CYAN}{Symbol.INFO} Deploying system core...{Colors.RESET}")
        self.run(f"pacstrap /mnt {' '.join(valid_pkgs)}")
        self.progress_next("System core installed")

    def configure(self):
        with Spinner("Writing partition map (fstab)..."):
            self.run("genfstab -U /mnt >> /mnt/etc/fstab")
        self.progress_next("Configuration persistent")

        self.root_uuid = self.run(f"blkid -s UUID -o value {self.p3}", capture=True)
        shutil.copy("/etc/resolv.conf", "/mnt/etc/resolv.conf")

        chroot_cmds = f"""
ln -sf /usr/share/zoneinfo/{TIMEZONE} /etc/localtime
hwclock --systohc
sed -i "s/^#{LOCALE}/{LOCALE}/" /etc/locale.gen
locale-gen
echo "LANG={LOCALE}" > /etc/locale.conf
echo "KEYMAP={KEYMAP}" > /etc/vconsole.conf
echo "{HOSTNAME}" > /etc/hostname
printf "127.0.0.1 localhost\\n::1 localhost\\n127.0.1.1 {HOSTNAME}.localdomain {HOSTNAME}\\n" > /etc/hosts
useradd -m -G wheel -s /bin/bash "{self.username}"
echo "{self.username}:{self.password}" | chpasswd
echo "root:{self.password}" | chpasswd
sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
systemctl enable NetworkManager bluetooth || true
systemctl disable getty@tty2.service || true
systemctl enable ly.service || true
systemctl enable ly@tty2.service || true

# Driver installation (Delayed for kernel compatibility)
pacman -Sy --noconfirm nvidia-dkms nvidia-utils nvidia-settings nvidia-prime

# Nvidia optimizations
if pacman -Q nvidia-utils >/dev/null 2>&1; then
    sed -i 's/^MODULES=(\\(.*\\))/MODULES=(\\1 nvidia nvidia_modeset nvidia_uvm nvidia_drm)/' /etc/mkinitcpio.conf
    sed -i 's/^MODULES=( /MODULES=(/' /etc/mkinitcpio.conf
    mkinitcpio -P
fi

# AUR Helpers (yay)
echo "{self.username} ALL=(ALL) NOPASSWD: /usr/bin/pacman" > /etc/sudoers.d/99-yay
chmod 440 /etc/sudoers.d/99-yay
runuser -u "{self.username}" -- /bin/bash -c "cd /tmp && git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si --noconfirm"
rm -f /etc/sudoers.d/99-yay

# Bootloader deployment
OPTS="root=UUID={self.root_uuid} rw"
if pacman -Q nvidia-utils >/dev/null 2>&1; then OPTS="$OPTS nvidia-drm.modeset=1"; fi

if [[ "{self.bootloader}" == "systemd-boot" ]]; then
    bootctl install
    echo -e "default arch\\ntimeout 2\\neditor no" > /boot/loader/loader.conf
    
    UCODE=""
    if [ -f /boot/intel-ucode.img ]; then UCODE="\\ninitrd /intel-ucode.img"; fi
    
    echo -e "title Arch Linux\\nlinux /vmlinuz-linux-cachyos$UCODE\\ninitrd /initramfs-linux-cachyos.img\\noptions $OPTS" > /boot/loader/entries/arch.conf
else
    if pacman -Q nvidia-utils >/dev/null 2>&1; then
        sed -i 's/^GRUB_CMDLINE_LINUX="\\(.*\\)"/GRUB_CMDLINE_LINUX="\\1 nvidia-drm.modeset=1"/' /etc/default/grub || echo 'GRUB_CMDLINE_LINUX="nvidia-drm.modeset=1"' >> /etc/default/grub
    fi
    grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
    grub-mkconfig -o /boot/grub/grub.cfg
fi
"""
        with open("/mnt/setup_config.sh", "w") as f: f.write(chroot_cmds)
        
        print(f"  {Colors.CYAN}{Symbol.INFO} Optimizing environment...{Colors.RESET}")
        self.setup_cachyos(target="/mnt")
        self.run("arch-chroot /mnt /bin/bash /setup_config.sh")
        self.run("rm -f /mnt/setup_config.sh", check=False)
        self.progress_next("Environment optimized")

    def finish(self):
        self.current_step = TOTAL_STEPS
        self.render()
        typewriter_print(f"\n  {Colors.GREEN}{Colors.BOLD}DEPLOYMENT SUCCESSFUL.{Colors.RESET}", 0.05)
        
        # --- Cleanup Section ---
        print(f"\n  {Colors.BOLD}CLEANUP{Colors.RESET}")
        ans = self.safe_input(f"  {Colors.CYAN}?{Colors.RESET} Delete log file ({LOG_FILE})? [Y/n]: ").strip().lower()
        delete_logs = (ans != 'n')

        with Spinner("Cleaning up temporary files and unmounting..."):
            # Unmount everything safely
            os.system("umount -l /var/cache/pacman/pkg 2>/dev/null")
            os.system("umount -R /mnt 2>/dev/null")
            
            # Remove temporary waste files
            waste_files = ["/tmp/cachy.sh", "/tmp/cachy_setup.sh", "/tmp/setup_config.sh"]
            for f in waste_files:
                if os.path.exists(f):
                    try: os.remove(f)
                    except: pass
            
            if os.path.exists("/tmp/cachyos-setup"):
                shutil.rmtree("/tmp/cachyos-setup", ignore_errors=True)

            # Optional log deletion
            if delete_logs and os.path.exists(LOG_FILE):
                try: os.remove(LOG_FILE)
                except: pass

            # Self-destruct (Remove the installer script itself)
            try:
                os.remove(sys.argv[0])
            except:
                pass

        print(f"  {Colors.GREEN}{Symbol.SUCCESS}{Colors.RESET} Cleanup complete. System is lean.")
        
        print(f"\n  {Colors.YELLOW}!{Colors.RESET} Remove installation media now.")
        for i in range(5, 0, -1):
            sys.stdout.write(f"\r  {Colors.CYAN}{Symbol.INFO}{Colors.RESET} Rebooting in {i} seconds... ")
            sys.stdout.flush()
            time.sleep(1)
        
        os.system("tput cnorm")
        print(f"\n  {Colors.GREEN}Rebooting...{Colors.RESET}")
        os.system("reboot")

def signal_handler(sig, frame):
    print(f"\n\n  {Colors.RED}Process interrupted. Cleaning up...{Colors.RESET}")
    subprocess.run("umount -R /mnt 2>/dev/null", shell=True)
    os.system("tput cnorm")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    installer = Installer()
    try:
        installer.welcome()
        installer.detect_disk()
        installer.partition_and_format()
        installer.install_base()
        installer.configure()
        installer.finish()
    except Exception as e:
        installer.on_error(str(e))
    finally:
        os.system("tput cnorm")

if __name__ == "__main__":
    main()
