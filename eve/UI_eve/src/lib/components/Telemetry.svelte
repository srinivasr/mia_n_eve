<script lang="ts">
    import { isConnected, latencyMs, currentState } from "../stores/eveState";
    import { onMount } from "svelte";

    // System Specification States
    let sysOs = "Detecting...";
    let sysCpu = "Detecting...";
    let sysMem = "Detecting...";
    let sysGpu = "Detecting...";
    let sysArch = "";
    let sysKernel = "";

    onMount(async () => {
        // Try fetching real system info from the Python server first
        try {
            const res = await fetch("http://127.0.0.1:8765/system-info");
            if (res.ok) {
                const data = await res.json();
                sysOs = data.os || "Unknown";
                // Shorten long CPU names (e.g., "Intel(R) Core(TM) i7-12700H" → "i7-12700H")
                const cpuRaw = data.cpu || "Unknown";
                const cpuShort = cpuRaw
                    .replace(/\(R\)/g, "")
                    .replace(/\(TM\)/g, "")
                    .trim();
                sysCpu = `${cpuShort.length > 22 ? cpuShort.substring(cpuShort.length - 22) : cpuShort}`;
                sysMem = data.ram_gb ? `${data.ram_gb} GB` : "Unknown";
                // Shorten GPU name
                const gpuRaw = data.gpu || "Unknown";
                sysGpu =
                    gpuRaw.length > 24 ? gpuRaw.substring(0, 24) + "…" : gpuRaw;
                sysArch = data.arch || "";
                sysKernel = data.kernel || "";
                return; // Success — skip browser fallback
            }
        } catch (_) {
            // Server not running — fall through to browser APIs
        }

        // Fallback: Browser API detection (limited info)
        const ua = navigator.userAgent;
        if (ua.includes("Win")) sysOs = "Windows";
        else if (ua.includes("Mac")) sysOs = "macOS";
        else if (ua.includes("Linux")) sysOs = "Linux";
        else sysOs = "Unknown OS";

        const cores = navigator.hardwareConcurrency;
        sysCpu = cores ? `${cores} Threads` : "Unknown CPU";

        const memGB = (navigator as any).deviceMemory;
        sysMem = memGB ? `≥ ${memGB} GB` : "Unknown";

        try {
            const canvas = document.createElement("canvas");
            const gl = canvas.getContext("webgl");
            if (gl) {
                const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
                if (debugInfo) {
                    const renderer = gl.getParameter(
                        debugInfo.UNMASKED_RENDERER_WEBGL,
                    );
                    sysGpu = renderer
                        .split(",")[0]
                        .replace("ANGLE (", "")
                        .substring(0, 24);
                } else {
                    sysGpu = "Standard WebGL";
                }
            }
        } catch (_) {
            sysGpu = "Unknown GPU";
        }
    });
</script>

<div class="telemetry">
    <div class="header">SYSTEM SPECIFICATIONS</div>
    <div class="metric">
        <span class="label">CPU</span>
        <span class="value">{sysCpu}</span>
    </div>
    <div class="metric">
        <span class="label">MEM</span>
        <span class="value">{sysMem}</span>
    </div>
    <div class="metric">
        <span class="label">GPU</span>
        <span class="value" title={sysGpu}>{sysGpu}</span>
    </div>
    <div class="metric">
        <span class="label">OS</span>
        <span class="value">{sysOs}</span>
    </div>

    <div class="header" style="margin-top: 15px;">RUNTIME TELEMETRY</div>

    <div class="metric">
        <span class="label">Status</span>
        <span
            class="value"
            class:connected={$isConnected}
            class:disconnected={!$isConnected}
        >
            {$isConnected ? "ONLINE" : "OFFLINE"}
        </span>
    </div>

    <div class="metric">
        <span class="label">State</span>
        <span class="value state-text">{$currentState.toUpperCase()}</span>
    </div>

    <div class="metric">
        <span class="label">Latency</span>
        <span class="value">
            <span
                class:good={$latencyMs < 400}
                class:warn={$latencyMs >= 400 && $latencyMs < 900}
                class:bad={$latencyMs >= 900}
            >
                {$latencyMs}
            </span> ms
        </span>
    </div>
</div>

<style>
    .telemetry {
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(10, 15, 20, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 15px;
        width: 230px;
        font-family:
            "Inter",
            -apple-system,
            sans-serif;
        color: #fff;
        z-index: 100;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }

    .header {
        font-size: 0.7rem;
        letter-spacing: 2px;
        color: #8892b0;
        margin-bottom: 12px;
        font-weight: 600;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 6px;
    }

    .metric {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        font-size: 0.85rem;
    }

    .label {
        color: #a8b2d1;
    }

    .value {
        font-family: "JetBrains Mono", monospace;
        font-weight: 500;
        text-align: right;
    }

    .connected {
        color: #64ffda;
    }
    .disconnected {
        color: #ff6b6b;
    }

    .state-text {
        color: #e6f1ff;
    }

    .good {
        color: #64ffda;
    }
    .warn {
        color: #ffd166;
    }
    .bad {
        color: #ff6b6b;
    }
</style>
