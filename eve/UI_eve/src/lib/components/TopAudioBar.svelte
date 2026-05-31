<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { listen } from "@tauri-apps/api/event";
    import type { UnlistenFn } from "@tauri-apps/api/event";
    import { currentState } from "../stores/eveState";
    import { rmsLevel, captureRunning } from "../stores/audioStore";

    export let audioData: number[] = [];

    let canvas: HTMLCanvasElement;
    let animationId: number;
    let unlistenAudio: UnlistenFn | null = null;
    let hasMicAccess = false;
    let micData: number[] = [];
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

    onMount(async () => {
        try {
            unlistenAudio = await listen<number[]>("audio-stream", (event) => {
                hasMicAccess = true;
                micData = event.payload;
            });
        } catch (e) {
            // Tauri event not available (browser dev), that's okay
        }

        tick();
    });

    onDestroy(() => {
        if (animationId) {
            cancelAnimationFrame(animationId);
        }
        if (unlistenAudio) {
            unlistenAudio();
        }
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
        if (hasMicAccess && micData.length > 0) {
            draw(micData);
        } else if (audioData && audioData.length > 0) {
            draw(audioData);
        } else if ($captureRunning) {
            const val = $rmsLevel;
            const t = Date.now() * 0.003;
            const nativeData = Array.from({ length: 32 }, (_, i) => {
                const variance = Math.sin(t + i) * 15;
                return Math.max(0, val + variance);
            });
            draw(nativeData);
        } else {
            const t = Date.now() * 0.005;
            let mockData: number[] = [];

            if ($currentState === "Speaking") {
                mockData = Array.from({ length: 32 }, (_, i) => {
                    const wave = Math.sin(t + i * 0.5) * Math.cos(t * 0.2);
                    return Math.max(0, Math.abs(wave) * 200);
                });
            } else if ($currentState === "Thinking") {
                mockData = Array.from({ length: 32 }, (_, i) => {
                    const pulse = Math.sin(t * 2 - (i / 32) * Math.PI * 4);
                    return Math.max(0, pulse > 0.8 ? 150 : 10);
                });
            } else if ($currentState === "Listening") {
                mockData = Array.from({ length: 32 }, (_, i) => {
                    const noise = Math.random() * 60;
                    return Math.max(0, Math.sin(t + i * 0.3) * 40 + noise);
                });
            } else {
                mockData = Array.from({ length: 32 }, (_, i) => {
                    return Math.max(0, Math.sin(t + i * 0.15) * 6 + 4);
                });
            }
            draw(mockData);
        }
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
        will-change: transform;
        filter: drop-shadow(0 0 6px rgba(var(--tr), var(--tg), var(--tb), 0.15));
        transition: filter 0.3s ease;
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
