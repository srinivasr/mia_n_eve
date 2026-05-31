<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { currentState } from "../stores/eveState";
    import { rmsLevel, captureRunning } from "../stores/audioStore";

    let canvas: HTMLCanvasElement;
    let animationId: number;
    let scanLinePos = 0;

    const stateColors: Record<string, string> = {
        Idle: "#4ae5ff",
        Listening: "#00ffff",
        Thinking: "#b34aff",
        Speaking: "#ffffff",
        Searching: "#00ff88",
        ExecutingTool: "#ffaa00",
        Error: "#ff3333",
    };

    let displayColor = "#4ae5ff";
    let targetDisplayColor = "#4ae5ff";

    onMount(() => {
        tick();
    });

    onDestroy(() => {
        if (animationId) cancelAnimationFrame(animationId);
    });

    function lerpColor(a: string, b: string, t: number): string {
        const ca = parseInt(a.slice(1), 16);
        const cb = parseInt(b.slice(1), 16);
        const r = ((ca >> 16) & 0xff) * (1 - t) + ((cb >> 16) & 0xff) * t;
        const g = ((ca >> 8) & 0xff) * (1 - t) + ((cb >> 8) & 0xff) * t;
        const bv = (ca & 0xff) * (1 - t) + (cb & 0xff) * t;
        return `rgb(${r | 0},${g | 0},${bv | 0})`;
    }

    function draw(data: number[]) {
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        targetDisplayColor =
            stateColors[$currentState as keyof typeof stateColors] ||
            stateColors.Idle;
        displayColor = lerpColor(displayColor, targetDisplayColor, 0.15);

        const center = w / 2;
        const midY = h / 2;

        const numBars = 28;
        const barWidth = 4;
        const gap = 5;
        const totalWidth = numBars * (barWidth + gap);
        const startX = center - totalWidth / 2 + barWidth / 2;

        // ── Scan line overlay ──────────────────────────────────────────
        scanLinePos = (scanLinePos + 0.6) % h;
        ctx.save();
        ctx.globalAlpha = 0.08;
        ctx.strokeStyle = displayColor;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, scanLinePos);
        ctx.lineTo(w, scanLinePos);
        ctx.stroke();
        ctx.restore();

        // ── Draw bars ──────────────────────────────────────────────────
        for (let i = 0; i < numBars; i++) {
            const binIndex = Math.floor((i / numBars) * (data.length * 0.8));
            const raw = data[binIndex] || 0;
            const percent = Math.min(1, raw / 255);

            const barHeight = 8 + percent * (h - 16);
            const x = startX + i * (barWidth + gap);

            // Center bars are brighter, edges are dimmer
            const centerT = 1 - Math.abs(i - numBars / 2) / (numBars / 2);
            const brightness = 0.3 + centerT * 0.7;
            const alpha = 0.2 + percent * 0.6;

            // Glow for louder bars
            ctx.shadowColor = displayColor;
            ctx.shadowBlur = percent > 0.3 ? 8 + percent * 12 : 0;

            ctx.lineCap = "round";
            ctx.lineWidth = barWidth;

            // Gradient from top to bottom of bar
            const topY = midY - barHeight / 2;
            const botY = midY + barHeight / 2;
            const gradient = ctx.createLinearGradient(0, topY, 0, botY);
            gradient.addColorStop(0, `${displayColor}${alpha * brightness * 0.6})`);
            gradient.addColorStop(0.5, `${displayColor}${alpha * brightness})`);
            gradient.addColorStop(1, `${displayColor}${alpha * brightness * 0.4})`);

            ctx.strokeStyle = gradient;

            ctx.beginPath();
            ctx.moveTo(x, topY);
            ctx.lineTo(x, botY);
            ctx.stroke();
        }

        // ── Center indicator dot ───────────────────────────────────────
        ctx.shadowBlur = 10;
        ctx.shadowColor = displayColor;
        ctx.fillStyle = displayColor;
        ctx.globalAlpha = 0.4;
        ctx.beginPath();
        ctx.arc(center, midY, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.shadowBlur = 0;
    }

    function tick() {
        const t = Date.now() * 0.003;
        let data: number[];

        if ($captureRunning) {
            const val = $rmsLevel;
            if (val > 0) {
                data = Array.from({ length: 32 }, (_, i) => {
                    const variance = Math.sin(t + i) * 20;
                    return Math.max(0, Math.min(255, val + variance));
                });
            } else {
                data = Array.from({ length: 32 }, (_, i) => {
                    const noise = Math.random() * 12;
                    return Math.max(0, Math.sin(t + i * 0.4) * 8 + noise);
                });
            }
        } else if ($currentState === "Speaking") {
            data = Array.from({ length: 32 }, (_, i) => {
                const wave = Math.sin(t + i * 0.5) * Math.cos(t * 0.3);
                return Math.max(0, Math.abs(wave) * 220);
            });
        } else if ($currentState === "Thinking") {
            data = Array.from({ length: 32 }, (_, i) => {
                const pulse = Math.sin(t * 2.5 - (i / 32) * Math.PI * 6);
                return Math.max(0, pulse > 0.7 ? 180 : 8);
            });
        } else if ($currentState === "Listening") {
            data = Array.from({ length: 32 }, (_, i) => {
                const noise = Math.random() * 80;
                return Math.max(0, Math.sin(t + i * 0.3) * 50 + noise);
            });
        } else {
            data = Array.from({ length: 32 }, (_, i) => {
                const breathe = Math.sin(t * 0.5) * 0.3 + 0.7;
                return Math.max(0, Math.sin(t + i * 0.2) * 8 * breathe + 2);
            });
        }

        draw(data);
        animationId = requestAnimationFrame(tick);
    }
</script>

<div class="audio-bar-wrap">
    <canvas bind:this={canvas} width={500} height={70} class="top-audio-bar"></canvas>
    <div class="bar-label">AUDIO</div>
</div>

<style>
    .audio-bar-wrap {
        position: absolute;
        top: 8px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 100;
        pointer-events: none;
        border: 1px solid rgba(var(--tr), var(--tg), var(--tb), 0.08);
        border-radius: 4px;
        padding: 2px;
        transition: border-color 0.3s ease;
    }

    .top-audio-bar {
        display: block;
        border-radius: 2px;
        background: rgba(var(--tr), var(--tg), var(--tb), 0.03);
        will-change: transform;
        filter: drop-shadow(0 0 6px rgba(var(--tr), var(--tg), var(--tb), 0.15));
        transition: background 0.3s ease, filter 0.3s ease;
    }

    .bar-label {
        position: absolute;
        top: -4px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 101;
        pointer-events: none;
        font-family: "JetBrains Mono", monospace;
        font-size: 0.55rem;
        letter-spacing: 3px;
        color: rgba(var(--tr), var(--tg), var(--tb), 0.25);
        transition: color 0.3s ease;
    }
</style>
