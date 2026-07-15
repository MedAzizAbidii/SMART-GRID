"""Background CPU/RAM/GPU/disk sampler used by every Phase 7 benchmark.

Read-only: samples the OS and the target process; never touches
application code or state.
"""
from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field

import psutil


@dataclass
class ResourceSample:
    t: float
    cpu_percent: float          # whole-machine
    proc_cpu_percent: float     # target process only
    mem_used_mb: float          # whole-machine used RAM
    proc_mem_mb: float          # target process RSS
    disk_read_mb: float         # cumulative since boot
    disk_write_mb: float
    gpu_util_percent: float | None
    gpu_mem_mb: float | None


def _query_gpu() -> tuple[float | None, float | None]:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None, None
        util, mem = out.stdout.strip().split(",")
        return float(util.strip()), float(mem.strip())
    except Exception:
        return None, None


@dataclass
class ResourceMonitor:
    """Samples system + target-process resource usage on a background thread.

    Usage:
        mon = ResourceMonitor(pid=os.getpid())
        mon.start()
        ... do work ...
        samples = mon.stop()
    """
    pid: int | None = None
    interval_sec: float = 0.5
    _samples: list[ResourceSample] = field(default_factory=list)
    _thread: threading.Thread | None = field(default=None, repr=False)
    _stop_evt: threading.Event = field(default_factory=threading.Event, repr=False)

    def __post_init__(self) -> None:
        self._proc = psutil.Process(self.pid) if self.pid else psutil.Process()
        self._proc.cpu_percent()  # prime the internal counter
        psutil.cpu_percent()

    def _loop(self) -> None:
        while not self._stop_evt.is_set():
            gpu_util, gpu_mem = _query_gpu()
            disk = psutil.disk_io_counters()
            vm = psutil.virtual_memory()
            try:
                proc_mem = self._proc.memory_info().rss / 1024 / 1024
                proc_cpu = self._proc.cpu_percent()
            except psutil.NoSuchProcess:
                proc_mem, proc_cpu = 0.0, 0.0
            self._samples.append(ResourceSample(
                t=time.time(),
                cpu_percent=psutil.cpu_percent(),
                proc_cpu_percent=proc_cpu,
                mem_used_mb=vm.used / 1024 / 1024,
                proc_mem_mb=proc_mem,
                disk_read_mb=(disk.read_bytes / 1024 / 1024) if disk else 0.0,
                disk_write_mb=(disk.write_bytes / 1024 / 1024) if disk else 0.0,
                gpu_util_percent=gpu_util,
                gpu_mem_mb=gpu_mem,
            ))
            self._stop_evt.wait(self.interval_sec)

    def start(self) -> None:
        self._samples = []
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> list[ResourceSample]:
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=5)
        return list(self._samples)

    def snapshot(self) -> ResourceSample:
        """One-off sample without starting the background thread."""
        gpu_util, gpu_mem = _query_gpu()
        disk = psutil.disk_io_counters()
        vm = psutil.virtual_memory()
        return ResourceSample(
            t=time.time(), cpu_percent=psutil.cpu_percent(0.1),
            proc_cpu_percent=self._proc.cpu_percent(),
            mem_used_mb=vm.used / 1024 / 1024,
            proc_mem_mb=self._proc.memory_info().rss / 1024 / 1024,
            disk_read_mb=(disk.read_bytes / 1024 / 1024) if disk else 0.0,
            disk_write_mb=(disk.write_bytes / 1024 / 1024) if disk else 0.0,
            gpu_util_percent=gpu_util, gpu_mem_mb=gpu_mem,
        )


def samples_to_dicts(samples: list[ResourceSample]) -> list[dict]:
    return [s.__dict__ for s in samples]


def summarize(samples: list[ResourceSample]) -> dict:
    if not samples:
        return {}
    cpu = [s.proc_cpu_percent for s in samples]
    mem = [s.proc_mem_mb for s in samples]
    sys_cpu = [s.cpu_percent for s in samples]
    return {
        "n_samples": len(samples),
        "duration_sec": round(samples[-1].t - samples[0].t, 2),
        "proc_cpu_avg": round(sum(cpu) / len(cpu), 2),
        "proc_cpu_peak": round(max(cpu), 2),
        "sys_cpu_avg": round(sum(sys_cpu) / len(sys_cpu), 2),
        "sys_cpu_peak": round(max(sys_cpu), 2),
        "proc_mem_avg_mb": round(sum(mem) / len(mem), 2),
        "proc_mem_peak_mb": round(max(mem), 2),
        "proc_mem_start_mb": round(mem[0], 2),
        "proc_mem_end_mb": round(mem[-1], 2),
        "proc_mem_growth_mb": round(mem[-1] - mem[0], 2),
    }
