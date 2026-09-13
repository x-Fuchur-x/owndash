from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .base import SensorProvider
from owndash.hardware.usb_setup import can_offer_graphical_setup, probe_artinchip_usb


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _percent(used: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min(100.0, used * 100.0 / total))


def _format_rate(value: float) -> str:
    value = max(0.0, value)
    units = ("B/s", "KB/s", "MB/s", "GB/s")
    index = 0
    while value >= 1024.0 and index < len(units) - 1:
        value /= 1024.0
        index += 1
    return f"{value:.1f} {units[index]}"


def _os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in _read_text(Path("/etc/os-release")).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


class SystemSensorProvider(SensorProvider):
    """Distribution-neutral Linux telemetry using procfs/sysfs with safe fallbacks.

    Hardware-dependent metrics are discovered at runtime. Missing values are
    represented as ``None`` so unsupported sensors never break the application.
    Optional NVIDIA telemetry uses ``nvidia-smi`` when it is available.
    """

    def __init__(self) -> None:
        self._last_cpu: tuple[int, int] | None = None
        self._last_net: tuple[float, int, int] | None = None
        self._last_energy: dict[str, tuple[float, float]] = {}

    def snapshot(self) -> dict[str, Any]:
        gpu = self._gpu()
        cpu_temp = self._cpu_temperature()
        cpu_w = self._cpu_package_power()
        gpu_w = gpu.get("power_w")
        values = [value for value in (cpu_w, gpu_w) if isinstance(value, (int, float))]
        return {
            "cpu": self._cpu(),
            "gpu": {
                "usage": gpu.get("usage"),
                "name": gpu.get("name", "GPU"),
                "driver": gpu.get("driver", "unknown"),
                "temperature": gpu.get("temperature"),
            },
            "memory": self._memory(),
            "storage": self._storage(),
            "network": self._network(),
            "temperature": cpu_temp,
            "power": {
                "cpu_w": cpu_w,
                "gpu_w": gpu_w,
                "total_w": sum(values) if values else None,
            },
            "uptime_seconds": self._uptime(),
        }

    def diagnostics(self) -> dict[str, Any]:
        """Return human-readable capabilities without assuming a specific distro."""
        snap = self.snapshot()
        release = _os_release()
        gpu = self._gpu()
        return {
            "system": {
                "distribution": release.get("PRETTY_NAME") or release.get("NAME") or "Linux",
                "kernel": platform.release(),
                "desktop": os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "unknown",
                "session": os.environ.get("XDG_SESSION_TYPE") or "unknown",
            },
            "cpu": {
                "name": snap["cpu"].get("name", "CPU"),
                "usage": snap["cpu"].get("usage") is not None,
                "temperature": snap["temperature"].get("value") is not None,
                "power": snap["power"].get("cpu_w") is not None,
            },
            "gpu": {
                "name": gpu.get("name", "GPU"),
                "driver": gpu.get("driver", "unknown"),
                "usage": gpu.get("usage") is not None,
                "temperature": gpu.get("temperature") is not None,
                "power": gpu.get("power_w") is not None,
            },
            "memory": snap["memory"].get("total", 0) > 0,
            "storage": snap["storage"].get("total", 0) > 0,
            "network": True,
        }

    def diagnostics_text(self, language: str = "en") -> str:
        info = self.diagnostics()

        def mark(value: bool) -> str:
            return "✓" if value else "—"

        if language == "de":
            return "\n".join([
                f"Distribution: {info['system']['distribution']}",
                f"Kernel: {info['system']['kernel']}",
                f"Desktop: {info['system']['desktop']}",
                f"Sitzung: {info['system']['session']}",
                "",
                f"CPU: {info['cpu']['name']}",
                f"  Auslastung: {mark(info['cpu']['usage'])}",
                f"  Temperatur: {mark(info['cpu']['temperature'])}",
                f"  Leistung: {mark(info['cpu']['power'])}",
                "",
                f"GPU: {info['gpu']['name']}",
                f"  Treiber: {info['gpu']['driver']}",
                f"  Auslastung: {mark(info['gpu']['usage'])}",
                f"  Temperatur: {mark(info['gpu']['temperature'])}",
                f"  Leistung: {mark(info['gpu']['power'])}",
                "",
                f"Arbeitsspeicher: {mark(info['memory'])}",
                f"Speicher: {mark(info['storage'])}",
                f"Netzwerk: {mark(info['network'])}",
            ])
        return "\n".join([
            f"Distribution: {info['system']['distribution']}",
            f"Kernel: {info['system']['kernel']}",
            f"Desktop: {info['system']['desktop']}",
            f"Session: {info['system']['session']}",
            "",
            f"CPU: {info['cpu']['name']}",
            f"  Usage: {mark(info['cpu']['usage'])}",
            f"  Temperature: {mark(info['cpu']['temperature'])}",
            f"  Power: {mark(info['cpu']['power'])}",
            "",
            f"GPU: {info['gpu']['name']}",
            f"  Driver: {info['gpu']['driver']}",
            f"  Usage: {mark(info['gpu']['usage'])}",
            f"  Temperature: {mark(info['gpu']['temperature'])}",
            f"  Power: {mark(info['gpu']['power'])}",
            "",
            f"Memory: {mark(info['memory'])}",
            f"Storage: {mark(info['storage'])}",
            f"Network: {mark(info['network'])}",
        ])

    def _cpu(self) -> dict[str, Any]:
        usage = 0.0
        text = _read_text(Path("/proc/stat"))
        first = text.splitlines()[0].split() if text else []
        if len(first) >= 5 and first[0] == "cpu":
            try:
                values = [int(value) for value in first[1:]]
                idle = values[3] + (values[4] if len(values) > 4 else 0)
                total = sum(values)
                if self._last_cpu is not None:
                    old_idle, old_total = self._last_cpu
                    total_delta = total - old_total
                    idle_delta = idle - old_idle
                    if total_delta > 0:
                        usage = _percent(total_delta - idle_delta, total_delta)
                self._last_cpu = (idle, total)
            except ValueError:
                pass
        return {
            "usage": usage,
            "load": os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0,
            "name": self._cpu_name(),
        }

    @staticmethod
    def _cpu_name() -> str:
        for line in _read_text(Path("/proc/cpuinfo")).splitlines():
            if line.lower().startswith("model name") and ":" in line:
                return line.split(":", 1)[1].strip()
            if line.lower().startswith("hardware") and ":" in line:
                return line.split(":", 1)[1].strip()
        return platform.processor() or "CPU"

    @staticmethod
    def _memory() -> dict[str, Any]:
        values: dict[str, int] = {}
        for line in _read_text(Path("/proc/meminfo")).splitlines():
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            parts = raw.split()
            if parts:
                try:
                    values[key] = int(parts[0]) * 1024
                except ValueError:
                    pass
        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", values.get("MemFree", 0))
        used = max(0, total - available)
        return {"used": used, "total": total, "percent": _percent(used, total)}

    @staticmethod
    def _storage() -> dict[str, Any]:
        try:
            usage = shutil.disk_usage("/")
        except OSError:
            return {"used": 0, "total": 0, "percent": 0.0, "mount": "/"}
        return {
            "used": usage.used,
            "total": usage.total,
            "percent": _percent(usage.used, usage.total),
            "mount": "/",
        }

    def _network(self) -> dict[str, Any]:
        rx = tx = 0
        for line in _read_text(Path("/proc/net/dev")).splitlines()[2:]:
            if ":" not in line:
                continue
            name, raw = line.split(":", 1)
            if name.strip() == "lo":
                continue
            fields = raw.split()
            if len(fields) >= 9:
                try:
                    rx += int(fields[0])
                    tx += int(fields[8])
                except ValueError:
                    pass
        now = time.monotonic()
        down = up = 0.0
        if self._last_net is not None:
            old_time, old_rx, old_tx = self._last_net
            elapsed = now - old_time
            if elapsed > 0:
                down = max(0, rx - old_rx) / elapsed
                up = max(0, tx - old_tx) / elapsed
        self._last_net = (now, rx, tx)
        return {
            "down_bps": down,
            "up_bps": up,
            "down_text": _format_rate(down),
            "up_text": _format_rate(up),
        }

    @staticmethod
    def _drm_devices() -> list[tuple[Path, str]]:
        devices: list[tuple[Path, str]] = []
        for card in sorted(Path("/sys/class/drm").glob("card[0-9]*")):
            device = card / "device"
            if not device.exists():
                continue
            uevent = _read_text(device / "uevent")
            driver = "unknown"
            for line in uevent.splitlines():
                if line.startswith("DRIVER="):
                    driver = line.split("=", 1)[1].strip()
                    break
            devices.append((device, driver))
        return devices

    def _gpu(self) -> dict[str, Any]:
        # Native sysfs path first: AMD and some Intel drivers expose useful data here.
        candidates: list[dict[str, Any]] = []
        for device, driver in self._drm_devices():
            usage = self._gpu_usage_sysfs(device)
            temp = self._gpu_temp(device)
            power = self._gpu_power_device(device)
            name = self._gpu_name(device, driver)
            candidates.append({
                "usage": usage,
                "name": name,
                "driver": driver,
                "temperature": temp,
                "power_w": power,
            })

        # NVIDIA proprietary telemetry is optional. If available, treat it as
        # another capability-rich candidate instead of requiring it.
        nvidia = self._nvidia_smi_gpu()
        if nvidia is not None:
            candidates.append(nvidia)

        # Prefer a discrete GPU / device with the richest telemetry.
        if candidates:
            candidates.sort(
                key=lambda item: (
                    item["driver"] in {"amdgpu", "nvidia"},
                    sum(item[key] is not None for key in ("usage", "temperature", "power_w")),
                ),
                reverse=True,
            )
            return candidates[0]
        return {"usage": None, "name": "GPU", "driver": "unknown", "temperature": None, "power_w": None}

    @staticmethod
    def _gpu_name(device: Path, driver: str) -> str:
        pci_name = SystemSensorProvider._pci_display_name(device)
        if pci_name:
            return pci_name

        vendor = _read_text(device / "vendor").lower()
        device_id = _read_text(device / "device").lower()
        if driver == "amdgpu" or vendor == "0x1002":
            return f"AMD GPU {device_id}".strip()
        if driver in {"i915", "xe"} or vendor == "0x8086":
            return f"Intel GPU {device_id}".strip()
        if driver == "nouveau" or vendor == "0x10de":
            return f"NVIDIA GPU {device_id}".strip()
        return f"GPU {device_id}".strip() or "GPU"

    @staticmethod
    def _pci_display_name(device: Path) -> str | None:
        """Resolve a friendly PCI GPU name when the standard lspci tool exists."""
        binary = shutil.which("lspci")
        if not binary:
            return None
        try:
            pci_address = device.resolve().name
        except OSError:
            return None
        if ":" not in pci_address or "." not in pci_address:
            return None
        try:
            result = subprocess.run(
                [binary, "-s", pci_address],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.0,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        line = result.stdout.strip()
        if result.returncode != 0 or not line:
            return None
        description = line.split(": ", 1)[1] if ": " in line else line
        # Strip the PCI class prefix, keeping the vendor/model description.
        for marker in ("VGA compatible controller: ", "Display controller: ", "3D controller: "):
            if description.startswith(marker):
                description = description[len(marker):]
                break
        return description.strip() or None

    @staticmethod
    def _gpu_usage_sysfs(device: Path) -> float | None:
        for name in ("gpu_busy_percent", "gt_busy_percent"):
            path = device / name
            if not path.exists():
                continue
            try:
                value = float(_read_text(path))
            except ValueError:
                continue
            if 0 <= value <= 100:
                return value
        return None

    @staticmethod
    def _gpu_temp(device: Path) -> float | None:
        for hwmon in sorted((device / "hwmon").glob("hwmon*")):
            labeled: list[tuple[int, Path]] = []
            fallback: list[Path] = []
            for temp in sorted(hwmon.glob("temp*_input")):
                fallback.append(temp)
                label = _read_text(temp.with_name(temp.name.replace("_input", "_label"))).lower()
                priority = 0 if label in {"edge", "gpu", "junction"} else 1
                labeled.append((priority, temp))
            for _, temp in sorted(labeled, key=lambda item: item[0]) or [(0, p) for p in fallback]:
                try:
                    value = float(_read_text(temp)) / 1000.0
                except ValueError:
                    continue
                if -20 <= value <= 150:
                    return value
        return None

    @staticmethod
    def _gpu_power_device(device: Path) -> float | None:
        for hwmon in sorted((device / "hwmon").glob("hwmon*")):
            for name in ("power1_average", "power1_input"):
                path = hwmon / name
                if not path.exists():
                    continue
                try:
                    microwatts = float(_read_text(path))
                except ValueError:
                    continue
                if microwatts >= 0:
                    return microwatts / 1_000_000.0
        return None

    @staticmethod
    def _nvidia_smi_gpu() -> dict[str, Any] | None:
        binary = shutil.which("nvidia-smi")
        if not binary:
            return None
        try:
            result = subprocess.run(
                [
                    binary,
                    "--query-gpu=name,utilization.gpu,temperature.gpu,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0 or not result.stdout.strip():
            return None
        fields = [part.strip() for part in result.stdout.splitlines()[0].split(",")]
        if len(fields) < 4:
            return None

        def number(value: str) -> float | None:
            try:
                return float(value)
            except ValueError:
                return None

        return {
            "name": fields[0] or "NVIDIA GPU",
            "driver": "nvidia",
            "usage": number(fields[1]),
            "temperature": number(fields[2]),
            "power_w": number(fields[3]),
        }

    @staticmethod
    def _cpu_temperature() -> dict[str, Any]:
        candidates: list[tuple[int, str, float]] = []
        preferred_labels = {
            "tctl": 0,
            "tdie": 0,
            "package id 0": 0,
            "package id 1": 0,
            "cpu package": 0,
            "physical id 0": 1,
        }
        cpu_hwmon_names = {
            "k10temp", "coretemp", "zenpower", "cpu_thermal",
            "soc_thermal", "acpitz",
        }

        for hwmon in sorted(Path("/sys/class/hwmon").glob("hwmon*")):
            hwmon_name = (_read_text(hwmon / "name") or hwmon.name).lower()
            for temp_path in sorted(hwmon.glob("temp*_input")):
                try:
                    value = float(_read_text(temp_path)) / 1000.0
                except ValueError:
                    continue
                if not (-20.0 <= value <= 150.0):
                    continue
                label_path = temp_path.with_name(temp_path.name.replace("_input", "_label"))
                label = _read_text(label_path) or hwmon_name
                label_lower = label.lower()
                if label_lower in preferred_labels:
                    priority = preferred_labels[label_lower]
                elif hwmon_name in cpu_hwmon_names:
                    priority = 2
                else:
                    priority = 10
                candidates.append((priority, label, value))

        if not candidates:
            return {"label": "CPU", "value": None}
        _, label, value = sorted(candidates, key=lambda item: item[0])[0]
        return {"label": label, "value": value}

    def _cpu_package_power(self) -> float | None:
        # AMD zenergy exposes cumulative microjoule counters in hwmon.
        value = self._energy_counter_power_from_hwmon()
        if value is not None:
            return value

        # Intel and some other platforms expose package energy through powercap/RAPL.
        return self._energy_counter_power_from_powercap()

    def _energy_delta_watts(self, key: str, energy_uj: float, now: float) -> float | None:
        previous = self._last_energy.get(key)
        self._last_energy[key] = (now, energy_uj)
        if previous is None:
            return None
        old_time, old_energy = previous
        elapsed = now - old_time
        delta = energy_uj - old_energy
        if elapsed <= 0 or delta < 0:
            return None
        return delta / 1_000_000.0 / elapsed

    def _energy_counter_power_from_hwmon(self) -> float | None:
        now = time.monotonic()
        for hwmon in sorted(Path("/sys/class/hwmon").glob("hwmon*")):
            if _read_text(hwmon / "name").lower() not in {"zenergy", "zenpower"}:
                continue
            for label_path in sorted(hwmon.glob("energy*_label")):
                label = _read_text(label_path).lower()
                if "socket" not in label and "package" not in label:
                    continue
                input_path = label_path.with_name(label_path.name.replace("_label", "_input"))
                try:
                    energy_uj = float(_read_text(input_path))
                except ValueError:
                    continue
                return self._energy_delta_watts(str(input_path), energy_uj, now)
        return None

    def _energy_counter_power_from_powercap(self) -> float | None:
        now = time.monotonic()
        roots = (
            Path("/sys/class/powercap"),
            Path("/sys/devices/virtual/powercap"),
        )
        seen: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for energy_path in sorted(root.glob("**/energy_uj")):
                if energy_path in seen:
                    continue
                seen.add(energy_path)
                name = _read_text(energy_path.parent / "name").lower()
                if name and not any(word in name for word in ("package", "pkg", "socket")):
                    continue
                try:
                    energy_uj = float(_read_text(energy_path))
                except ValueError:
                    continue
                return self._energy_delta_watts(str(energy_path), energy_uj, now)
        return None

    @staticmethod
    def _uptime() -> float:
        try:
            return float(_read_text(Path("/proc/uptime")).split()[0])
        except (ValueError, IndexError):
            return 0.0


def system_capabilities() -> dict[str, Any]:
    """Central compatibility report shared by setup, diagnostics and bug reports."""
    provider = SystemSensorProvider()
    info = provider.diagnostics()
    linux = platform.system().lower() == "linux"
    display_session = bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))
    session_type = (os.environ.get("XDG_SESSION_TYPE") or "").lower()
    nvidia_tool = shutil.which("nvidia-smi") is not None
    lspci_tool = shutil.which("lspci") is not None
    usb = probe_artinchip_usb()
    return {
        "required": {
            "linux": linux,
            "graphical_session": display_session,
            "proc": Path("/proc").is_dir(),
            "sys": Path("/sys").is_dir(),
        },
        "optional": {
            "hwmon": Path("/sys/class/hwmon").is_dir(),
            "powercap": Path("/sys/class/powercap").is_dir() or Path("/sys/devices/virtual/powercap").is_dir(),
            "nvidia_smi": nvidia_tool,
            "lspci": lspci_tool,
        },
        "display": {
            "artinchip_connected": usb.connected,
            "artinchip_accessible": usb.accessible,
            "artinchip_device_node": usb.device_node,
            "graphical_usb_setup": can_offer_graphical_setup(),
        },
        "session_type": session_type or str(info["system"]["session"]),
        "diagnostics": info,
    }
