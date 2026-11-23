"""Read-only Linux diagnostics helpers. Commands are invoked with fixed argument lists."""
from __future__ import annotations
import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path

def run_cmd(args: list[str], timeout: int = 5) -> str:
    if not args or not shutil.which(args[0]):
        return f"Not available: {args[0] if args else 'command'}"
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        output = (p.stdout or p.stderr).strip()
        return output if output else f"Command exited with code {p.returncode} (no output)"
    except subprocess.TimeoutExpired:
        return "Timed out"
    except Exception as exc:
        return f"Error: {exc}"

def system_info() -> dict:
    info = {
        "Hostname": socket.gethostname(),
        "Distribution": platform.platform(),
        "Architecture": platform.machine(),
        "Kernel": platform.release(),
        "CPU": run_cmd(["bash", "-lc", "lscpu | grep -m1 'Model name' | cut -d: -f2-"]).strip(),
        "Memory": "See CPU / Memory panel",
        "LinuxCNC": run_cmd(["linuxcnc", "-v"], timeout=3),
        "HAL utility": shutil.which("halcmd") or "Not installed / not in PATH",
        "EtherCAT utility": shutil.which("ethercat") or "Not installed / not in PATH",
    }
    if Path("/etc/os-release").exists():
        try:
            for line in Path("/etc/os-release").read_text().splitlines():
                if line.startswith("PRETTY_NAME="):
                    info["Distribution"] = line.split("=",1)[1].strip().strip('"')
                    break
        except OSError:
            pass
    return info

def network_info() -> str:
    return run_cmd(["ip", "-brief", "address"], timeout=4)

def routes_info() -> str:
    return run_cmd(["ip", "route"], timeout=4)

def ethernet_details() -> str:
    return run_cmd(["ip", "-details", "-statistics", "link"], timeout=4)

def hardware_info() -> str:
    sections = []
    for title, cmd in [
        ("CPU", ["lscpu"]),
        ("PCI devices", ["lspci", "-nn"]),
        ("USB devices", ["lsusb"]),
        ("Block devices", ["lsblk", "-o", "NAME,SIZE,TYPE,MODEL"]),
    ]:
        sections.append(f"===== {title} =====\n{run_cmd(cmd, timeout=8)}")
    return "\n\n".join(sections)

def hal_info() -> str:
    return run_cmd(["halcmd", "show"], timeout=8)

def ethercat_info() -> str:
    return "\n\n".join([
        "===== EtherCAT master =====\n" + run_cmd(["ethercat", "master"], timeout=5),
        "===== EtherCAT slaves =====\n" + run_cmd(["ethercat", "slaves"], timeout=5),
    ])

def rt_info() -> str:
    lines = []
    lines.append(f"Kernel: {platform.release()}")
    rt_files = ["/sys/kernel/realtime", "/proc/sys/kernel/ostype"]
    for name in rt_files:
        p = Path(name)
        if p.exists():
            try:
                lines.append(f"{name}: {p.read_text().strip()}")
            except OSError as exc:
                lines.append(f"{name}: {exc}")
    if "PREEMPT_RT" in platform.release() or "-rt" in platform.release():
        lines.append("Kernel string suggests PREEMPT_RT / RT kernel; verify with your distribution documentation.")
    else:
        lines.append("RT kernel not confirmed from kernel release string. This is not a definitive real-time test.")
    lines.append("Latency values are intentionally not fabricated. Use LinuxCNC latency-histogram / latency-test for measured jitter.")
    return "\n".join(lines)

def ping_host(host: str, count: int = 4) -> str:
    if not host.strip():
        return "Enter a hostname or IP address."
    # No shell: user input is passed as a single ping target argument.
    return run_cmd(["ping", "-c", str(max(1, min(count, 20))), "-W", "2", host.strip()], timeout=55)

def launch_latency_histogram() -> tuple[bool, str]:
    executable = shutil.which("latency-histogram")
    if not executable:
        return False, "latency-histogram was not found. Install/use the LinuxCNC tools package for this system."
    try:
        subprocess.Popen([executable], start_new_session=True)
        return True, "Started LinuxCNC latency-histogram in a separate window."
    except Exception as exc:
        return False, f"Could not start latency-histogram: {exc}"


def cpu_temperature() -> str:
    """Read hwmon temperature sensors when exposed by the kernel."""
    values = []
    for path in Path("/sys/class/hwmon").glob("hwmon*/temp*_input"):
        try:
            raw = int(path.read_text().strip())
            label_path = path.with_name(path.name.replace("_input", "_label"))
            label = label_path.read_text().strip() if label_path.exists() else path.name
            values.append(f"{label}: {raw/1000:.1f} °C")
        except (OSError, ValueError):
            continue
    return "\n".join(values) if values else "Not available (no readable hwmon temperature sensors)."
