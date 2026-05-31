<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { isConnected, latencyMs, currentState } from "../stores/eveState";

    // ── Gauge canvases ────────────────────────────────────────────────
    let cpuCanvas: HTMLCanvasElement;
    let ramCanvas: HTMLCanvasElement;
    let gpuCanvas: HTMLCanvasElement;
    let vramCanvas: HTMLCanvasElement;
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

    // ── History for sparklines ────────────────────────────────────────
    const MAX_HISTORY = 40;
    let cpuHist: number[] = new Array(MAX_HISTORY).fill(0);
    let ramHist: number[] = new Array(MAX_HISTORY).fill(0);
    let gpuHist: number[] = new Array(MAX_HISTORY).fill(0);
    let vramHist: number[] = new Array(MAX_HISTORY).fill(0);

    // ── Uptime ────────────────────────────────────────────────────────
    let bootTimestamp = 0;
    let uptimeStr = "—";

    // ── Gauge constants ───────────────────────────────────────────────
    const ARC_START = Math.PI * 0.75;
    const ARC_END = Math.PI * 0.25;
    const ARC_SWEEP = Math.PI * 1.5;

    let animId: number;
    let pollId: number;
    let hasGpu = true;

    function gaugeColor(pct: number): string {
        const hue = Math.max(0, 180 - (pct / 100) * 200);
        const sat = 90;
        const lit = 55 + (pct / 100) * 10;
        return `hsl(${hue}, ${sat}%, ${lit}%)`;
    }

    function drawGauge(
        canvas: HTMLCanvasElement,
        pct: number,
        label: string,
    ) {
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const cx = w / 2;
        const cy = h / 2 + 2;
        const r = 27;
        const lw = 7;

        const isNa = pct === -1;
        const displayPct = isNa ? 0 : pct;
        const color = isNa ? "rgba(255,255,255,0.12)" : gaugeColor(displayPct);
        const txt = isNa ? "N/A" : `${Math.round(displayPct)}%`;

        // Background arc
        ctx.beginPath();
        ctx.arc(cx, cy, r, ARC_START, ARC_END, false);
        ctx.strokeStyle = "rgba(255,255,255,0.06)";
        ctx.lineWidth = lw;
        ctx.lineCap = "round";
        ctx.stroke();

        // Fill arc
        const fillEnd = (ARC_START + (displayPct / 100) * ARC_SWEEP) % (Math.PI * 2);
        ctx.beginPath();
        ctx.arc(cx, cy, r, ARC_START, fillEnd, false);
        ctx.strokeStyle = color;
        ctx.lineWidth = lw;
        ctx.lineCap = "round";
        ctx.stroke();

        // Inner glow line
        ctx.beginPath();
        ctx.arc(cx, cy, r - lw - 3, ARC_START, fillEnd, false);
        ctx.strokeStyle = color + "20";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Percentage text
        ctx.fillStyle = isNa ? "rgba(255,255,255,0.25)" : "#f0f4ff";
        ctx.font = 'bold 20px "JetBrains Mono", monospace';
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(txt, cx, cy - 3);

        // Label
        ctx.fillStyle = isNa ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.35)";
        ctx.font = '8px "JetBrains Mono", monospace';
        ctx.textBaseline = "top";
        ctx.fillText(label, cx, cy + 18);
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

        ctx.beginPath();
        for (let i = 0; i < len; i++) {
            const x = (i / (len - 1)) * w;
            const y = h - (values[i] / max) * h;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // Subtle fill beneath the line
        ctx.lineTo(w, h);
        ctx.lineTo(0, h);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, 0, 0, h);
        grad.addColorStop(0, color + "30");
        grad.addColorStop(1, color + "02");
        ctx.fillStyle = grad;
        ctx.fill();
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

            if (d.uptime_seconds) bootTimestamp = d.uptime_seconds;

            if (d.gpu_name) {
                const short = d.gpu_name.replace("NVIDIA ", "").replace("GeForce ", "");
                gpuName = short.length > 18 ? short.substring(0, 16) + "…" : short;
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
            gpuHist = [...gpuHist.slice(1), gpuTarget === -1 ? 0 : (gpuTarget ?? 0)];
            vramHist = [...vramHist.slice(1), vramTarget === -1 ? 0 : (vramTarget ?? 0)];
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

        const gpuColor = hasGpu ? gaugeColor(gpuVal) : "rgba(255,255,255,0.12)";
        const vramColor = hasGpu ? gaugeColor(vramVal) : "rgba(255,255,255,0.12)";

        drawGauge(cpuCanvas, cpuVal, "CPU");
        drawGauge(ramCanvas, ramVal, "RAM");
        drawGauge(gpuCanvas, hasGpu ? gpuVal : -1, gpuName);
        drawGauge(vramCanvas, hasGpu ? vramVal : -1, "VRAM");

        drawSparkline(cpuSpark, cpuHist, gaugeColor(cpuVal));
        drawSparkline(ramSpark, ramHist, gaugeColor(ramVal));
        drawSparkline(gpuSpark, gpuHist, gpuColor);
        drawSparkline(vramSpark, vramHist, vramColor);

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

    <div class="gauges">
        <div class="cell">
            <canvas bind:this={cpuCanvas} width={82} height={82}></canvas>
            <canvas bind:this={cpuSpark} width={90} height={20} class="spark"></canvas>
        </div>
        <div class="cell">
            <canvas bind:this={ramCanvas} width={82} height={82}></canvas>
            <canvas bind:this={ramSpark} width={90} height={20} class="spark"></canvas>
        </div>
        <div class="cell">
            <canvas bind:this={gpuCanvas} width={82} height={82}></canvas>
            <canvas bind:this={gpuSpark} width={90} height={20} class="spark"></canvas>
        </div>
        <div class="cell">
            <canvas bind:this={vramCanvas} width={82} height={82}></canvas>
            <canvas bind:this={vramSpark} width={90} height={20} class="spark"></canvas>
        </div>
    </div>

    <div class="section-header" style="margin-top: 8px;">RUNTIME</div>

    <div class="runtime">
        <div class="metric-row">
            <span class="label">State</span>
            <span class="value state-val">{$currentState.toUpperCase()}</span>
        </div>
        <div class="metric-row">
            <span class="label">Latency</span>
            <span class="value" class:good={$latencyMs < 400} class:warn={$latencyMs >= 400 && $latencyMs < 900} class:bad={$latencyMs >= 900}>
                {$latencyMs} ms
            </span>
        </div>
        <div class="metric-row">
            <span class="label">Status</span>
            <span class="value" class:connected={$isConnected} class:disconnected={!$isConnected}>
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
        position: fixed;
        top: 80px;
        right: 16px;
        background: rgba(5, 10, 21, 0.65);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 14px;
        width: 210px;
        z-index: 100;
        box-shadow:
            0 10px 40px rgba(0, 0, 0, 0.5),
            inset 0 1px 0 rgba(255, 255, 255, 0.04);
        font-family: "Inter", -apple-system, sans-serif;
        color: #fff;
    }

    .section-header {
        font-size: 0.6rem;
        letter-spacing: 2.5px;
        color: rgba(255, 255, 255, 0.25);
        font-weight: 600;
        margin-bottom: 8px;
        padding-bottom: 5px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    .gauges {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2px;
        justify-items: center;
    }

    .cell {
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    .spark {
        margin-top: -6px;
        filter: drop-shadow(0 0 3px rgba(0, 180, 255, 0.15));
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
        font-size: 0.75rem;
    }

    .label {
        color: rgba(255, 255, 255, 0.35);
        font-size: 0.65rem;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .value {
        font-family: "JetBrains Mono", monospace;
        font-weight: 500;
        font-size: 0.7rem;
        color: #e2e8f0;
    }

    .state-val {
        color: #22d3ee;
    }

    .connected { color: #22c55e; }
    .disconnected { color: #ef4444; }
    .good { color: #22c55e; }
    .warn { color: #eab308; }
    .bad { color: #ef4444; }
</style>
