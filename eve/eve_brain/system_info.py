#!/usr/bin/env python3
"""
Tiny HTTP server that exposes system hardware info to the frontend.
Runs on port 8766 as a sidecar process.
"""
import json
import platform
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

def get_system_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {}

    info["os"] = f"{platform.system()} {platform.release()}"

    # CPU name — linux gives us /proc/cpuinfo, mac needs sysctl
    cpu_name = platform.processor() or "Unknown"
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_name = line.split(":")[1].strip()
                        break
        except Exception:
            pass
    elif platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, check=True
            )
            cpu_name = result.stdout.strip()
        except Exception:
            pass

    info["cpu"] = cpu_name
    info["cpu_cores"] = os.cpu_count() or 0

    # RAM — parse meminfo on linux, sysctl on mac
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        info["ram_gb"] = round(kb / 1048576, 1)
                        break
        elif platform.system() == "Darwin":
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, check=True
            )
            info["ram_gb"] = round(int(result.stdout.strip()) / (1024 ** 3), 1)
        else:
            info["ram_gb"] = 0
    except Exception:
        info["ram_gb"] = 0

    # GPU — nvidia-smi first, then fall back to lspci
    gpu_name = "No dedicated GPU"
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, check=True
        )
        gpu_name = result.stdout.strip().split("\n")[0]
    except (FileNotFoundError, subprocess.CalledProcessError):
        if platform.system() == "Linux":
            try:
                result = subprocess.run(
                    ["lspci"], capture_output=True, text=True, check=True
                )
                for line in result.stdout.split("\n"):
                    if "VGA" in line or "3D" in line or "Display" in line:
                        gpu_name = line.split(": ", 1)[-1].strip()
                        break
            except Exception:
                pass
    info["gpu"] = gpu_name

    info["kernel"] = platform.release()
    info["arch"] = platform.machine()
    info["hostname"] = platform.node()

    return info


class CORSRequestHandler(BaseHTTPRequestHandler):
    """Simple handler so the frontend can fetch system info without CORS issues."""

    def do_GET(self) -> None:
        if self.path == "/system-info":
            data = get_system_info()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass  # silence the default access logs


def main() -> None:
    port = 8766
    server = HTTPServer(("127.0.0.1", port), CORSRequestHandler)
    print(f"Eve System Info server running at http://127.0.0.1:{port}/system-info")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
