<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { isConnected, latencyMs, currentState } from "../stores/eveState";

    // ── Bar canvases ─────────────────────────────────────────────────
    let cpuBar: HTMLCanvasElement;
    let ramBar: HTMLCanvasElement;
    let gpuBar: HTMLCanvasElement;
    let vramBar: HTMLCanvasElement;
    let cpuSpark: HTMLCanvasElement;
    let ramSpark: HTMLCanvasElement;
    let gpuSpark: HTMLCanvasElement;
    let vramSpark: HTMLCanvasElement;

    // ── Animated values (lerped for smooth transitions) ───────────────
    let cpuVal = 0;
    let ramVal = 0;
    let gpuVal = 0;
    let vramVal = 0;
    let cpuTarget = 0;
    let ramTarget = 0;
    let gpuTarget: number | null = 0;
    let vramTarget: number | null = 0;
    let gpuName = "GPU";
    let ramUsedGb = 0;
    let ramTotalGb = 0;
    let vramUsedGb = 0;
    let vramTotalGb = 0;
    let ramInfo = "";
    let vramInfo = "";

    // ── History for sparklines ────────────────────────────────────────
    const MAX_HISTORY = 40;
    let cpuHist: number[] = new Array(MAX_HISTORY).fill(0);
    let ramHist: number[] = new Array(MAX_HISTORY).fill(0);
    let gpuHist: number[] = new Array(MAX_HISTORY).fill(0);
    let vramHist: number[] = new Array(MAX_HISTORY).fill(0);

    // ── Uptime ────────────────────────────────────────────────────────
    let bootTimestamp = 0;
    let uptimeStr = "—";

    let animId: number;
    let pollId: number;
    let hasGpu = true;

    // ── btop metric colors ───────────────────────────────────────────
    const COLORS = {
        cpu: "#e8643b",
        ram: "#d4943a",
        gpu: "#a85d66",
        vram: "#7a8a55",
    };

    // ── Pixel-block bar constants ─────────────────────────────────────
    const PIXEL_COLS = 20;
    const PIXEL_GAP = 1;
    const BAR_X = 34;
    const BAR_W = 186;
    const BAR_Y = 8;
    const BAR_H = 12;
    const cellW = Math.floor(
        (BAR_W - PIXEL_GAP * (PIXEL_COLS - 1)) / PIXEL_COLS,
    );

    function drawBar(
        canvas: HTMLCanvasElement,
        pct: number,
        color: string,
        label: string,
        info = "",
    ) {
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const isNa = pct === -1;
        const displayPct = isNa ? 0 : pct;
        const pctTxt = isNa ? "N/A" : `${Math.round(displayPct)}%`;

        // Pixel-block bar
        const filled = Math.round((displayPct / 100) * PIXEL_COLS);
        for (let i = 0; i < PIXEL_COLS; i++) {
            const x = BAR_X + i * (cellW + PIXEL_GAP);
            ctx.fillStyle = i < filled ? color : "rgba(255,255,255,0.12)";
            ctx.fillRect(x, BAR_Y, cellW, BAR_H);
        }

        // Label
        ctx.fillStyle = color;
        ctx.font = 'bold 11px "JetBrains Mono", monospace';
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText(label, 4, 14);

        // Percentage
        ctx.fillStyle = isNa ? "rgba(255,255,255,0.5)" : "#f0f4ff";
        ctx.font = 'bold 12px "JetBrains Mono", monospace';
        ctx.textAlign = "right";
        ctx.fillText(pctTxt, w - 4, 14);

        // Info text
        if (info) {
            ctx.fillStyle = "rgba(255,255,255,0.55)";
            ctx.font = '9px "JetBrains Mono", monospace';
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            ctx.fillText(info, BAR_X, 29);
        }
    }

    function drawSparkline(
        canvas: HTMLCanvasElement,
        values: number[],
        color: string,
    ) {
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const valid = values.filter((v) => v > 0);
        if (valid.length < 2) return;

        const len = values.length;
        const max = Math.max(100, ...values);
        const colW = Math.floor(w / len);

        // Background grid dots
        for (let i = 0; i < len; i += 4) {
            ctx.fillStyle = "rgba(255,255,255,0.05)";
            ctx.fillRect(i * colW, 0, colW, h - 1);
        }

        // Pixel columns
        for (let i = 0; i < len; i++) {
            const colH = Math.round((values[i] / max) * h);
            if (colH < 1) continue;
            ctx.fillStyle = color;
            ctx.fillRect(i * colW, h - colH, colW, colH);
        }
    }

    // ── Polling ───────────────────────────────────────────────────────
    async function pollStats() {
        try {
            const res = await fetch("http://127.0.0.1:8766/system-stats");
            if (!res.ok) return;
            const d = await res.json();

            cpuTarget = d.cpu_percent ?? 0;
            ramTarget = d.ram_percent ?? 0;
            gpuTarget = d.gpu_percent;
            vramTarget = d.vram_percent;

            if (d.ram_used_gb != null) ramUsedGb = d.ram_used_gb;
            if (d.ram_total_gb != null) ramTotalGb = d.ram_total_gb;
            if (d.vram_used_gb != null) vramUsedGb = d.vram_used_gb;
            if (d.vram_total_gb != null) vramTotalGb = d.vram_total_gb;

            if (d.uptime_seconds) bootTimestamp = d.uptime_seconds;

            if (d.gpu_name) {
                const short = d.gpu_name
                    .replace("NVIDIA ", "")
                    .replace("GeForce ", "");
                gpuName =
                    short.length > 18
                        ? short.substring(0, 16) + "\u2026"
                        : short;
            }

            if (d.gpu_percent === null || d.gpu_percent === undefined) {
                hasGpu = false;
                gpuTarget = -1;
                vramTarget = -1;
            } else {
                hasGpu = true;
            }

            cpuHist = [...cpuHist.slice(1), cpuTarget];
            ramHist = [...ramHist.slice(1), ramTarget];
            gpuHist = [
                ...gpuHist.slice(1),
                gpuTarget === -1 ? 0 : (gpuTarget ?? 0),
            ];
            vramHist = [
                ...vramHist.slice(1),
                vramTarget === -1 ? 0 : (vramTarget ?? 0),
            ];
        } catch {
            // server not running
        }
    }

    function updateUptime() {
        if (!bootTimestamp) return;
        const secs = Math.floor(Date.now() / 1000 - bootTimestamp);
        const h = Math.floor(secs / 3600);
        const m = Math.floor((secs % 3600) / 60);
        uptimeStr = `${h}h ${m.toString().padStart(2, "0")}m`;
    }

    // ── Animation loop ────────────────────────────────────────────────
    function animate() {
        const lerp = 0.12;
        cpuVal += (cpuTarget - cpuVal) * lerp;
        ramVal += (ramTarget - ramVal) * lerp;
        if (gpuTarget !== null) gpuVal += (gpuTarget - gpuVal) * lerp;
        if (vramTarget !== null) vramVal += (vramTarget - vramVal) * lerp;

        updateUptime();

        ramInfo =
            ramTotalGb > 0
                ? `${ramUsedGb.toFixed(1)}G / ${ramTotalGb.toFixed(1)}G`
                : "";
        vramInfo =
            vramTotalGb > 0
                ? `${vramUsedGb.toFixed(1)}G / ${vramTotalGb.toFixed(1)}G`
                : "";

        drawBar(cpuBar, cpuVal, COLORS.cpu, "CPU");
        drawBar(ramBar, ramVal, COLORS.ram, "RAM", ramInfo);
        drawBar(
            gpuBar,
            hasGpu ? gpuVal : -1,
            COLORS.gpu,
            hasGpu ? "GPU" : gpuName,
            hasGpu ? gpuName : "",
        );
        drawBar(vramBar, hasGpu ? vramVal : -1, COLORS.vram, "VRAM", vramInfo);

        drawSparkline(cpuSpark, cpuHist, COLORS.cpu);
        drawSparkline(ramSpark, ramHist, COLORS.ram);
        drawSparkline(gpuSpark, gpuHist, COLORS.gpu);
        drawSparkline(vramSpark, vramHist, COLORS.vram);

        animId = requestAnimationFrame(animate);
    }

    onMount(() => {
        pollStats();
        pollId = window.setInterval(pollStats, 2000);
        animId = requestAnimationFrame(animate);
    });

    onDestroy(() => {
        if (animId) cancelAnimationFrame(animId);
        if (pollId) clearInterval(pollId);
    });
</script>

<div class="telemetry">
    <div class="section-header">SYSTEM RESOURCES</div>

    <div class="metrics">
        <div class="metric">
            <canvas bind:this={cpuBar} width={258} height={38}></canvas>
            <canvas bind:this={cpuSpark} width={258} height={24} class="spark"
            ></canvas>
        </div>
        <div class="metric">
            <canvas bind:this={ramBar} width={258} height={38}></canvas>
            <canvas bind:this={ramSpark} width={258} height={24} class="spark"
            ></canvas>
        </div>
        <div class="metric">
            <canvas bind:this={gpuBar} width={258} height={38}></canvas>
            <canvas bind:this={gpuSpark} width={258} height={24} class="spark"
            ></canvas>
        </div>
        <div class="metric">
            <canvas bind:this={vramBar} width={258} height={38}></canvas>
            <canvas bind:this={vramSpark} width={258} height={24} class="spark"
            ></canvas>
        </div>
    </div>

    <div class="section-header" style="margin-top: 6px;">RUNTIME</div>

    <div class="runtime">
        <div class="metric-row">
            <span class="label">State</span>
            <span class="value state-val">{$currentState.toUpperCase()}</span>
        </div>
        <div class="metric-row">
            <span class="label">Latency</span>
            <span
                class="value"
                class:good={$latencyMs < 400}
                class:warn={$latencyMs >= 400 && $latencyMs < 900}
                class:bad={$latencyMs >= 900}
            >
                {$latencyMs} ms
            </span>
        </div>
        <div class="metric-row">
            <span class="label">Status</span>
            <span
                class="value"
                class:connected={$isConnected}
                class:disconnected={!$isConnected}
            >
                {$isConnected ? "ONLINE" : "OFFLINE"}
            </span>
        </div>
        <div class="metric-row">
            <span class="label">Uptime</span>
            <span class="value">{uptimeStr}</span>
        </div>
    </div>
</div>

<style>
    .telemetry {
        background: rgba(5, 10, 21, 0.65);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(var(--tr), var(--tg), var(--tb), 0.25);
        border-radius: 14px;
        padding: 14px 16px;
        width: clamp(200px, 20vw, 320px);
        box-shadow:
            0 10px 40px rgba(0, 0, 0, 0.5),
            inset 0 1px 0 rgba(255, 255, 255, 0.04);
        font-family:
            "Inter",
            -apple-system,
            sans-serif;
        color: #fff;
        transition:
            border-color 0.3s ease,
            box-shadow 0.3s ease;
    }

    .section-header {
        font-size: 0.7rem;
        letter-spacing: 2.5px;
        color: rgba(255, 255, 255, 0.55);
        font-weight: 700;
        margin-bottom: 8px;
        padding-bottom: 5px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    .metrics {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .metric {
        display: flex;
        flex-direction: column;
    }

    .metric canvas:first-child {
        display: block;
        width: 100%;
        height: auto;
    }
    .metric canvas.spark {
        display: block;
        width: 100%;
        height: auto;
    }

    .spark {
        margin-top: -2px;
    }

    .runtime {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .metric-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
    }

    .label {
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.75rem;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .value {
        font-family: "JetBrains Mono", monospace;
        font-weight: 500;
        font-size: 0.8rem;
        color: #e2e8f0;
    }

    .state-val {
        color: #f59e0b;
    }

    .connected {
        color: #22c55e;
    }
    .disconnected {
        color: #ef4444;
    }
    .good {
        color: #22c55e;
    }
    .warn {
        color: #eab308;
    }
    .bad {
        color: #ef4444;
    }
</style>
