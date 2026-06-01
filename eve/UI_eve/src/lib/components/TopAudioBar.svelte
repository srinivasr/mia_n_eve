<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { currentState } from "../stores/eveState";
    import { captureRunning, audioBars } from "../stores/audioStore";

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

    let displayR = 74,
        displayG = 229,
        displayB = 255;
    let displayColor = "#4ae5ff";
    let targetDisplayColor = "#4ae5ff";

    function lerpColor(a: string, b: string, t: number): void {
        const ca = parseInt(a.slice(1), 16);
        const cb = parseInt(b.slice(1), 16);
        displayR =
            (((ca >> 16) & 0xff) * (1 - t) + ((cb >> 16) & 0xff) * t) | 0;
        displayG = (((ca >> 8) & 0xff) * (1 - t) + ((cb >> 8) & 0xff) * t) | 0;
        displayB = ((ca & 0xff) * (1 - t) + (cb & 0xff) * t) | 0;
    }

    function rgba(a: number): string {
        return `rgba(${displayR},${displayG},${displayB},${a})`;
    }

    onMount(() => {
        tick();
    });
    onDestroy(() => {
        if (animationId) cancelAnimationFrame(animationId);
    });

    function draw(data: number[]) {
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const w = canvas.width,
            h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        targetDisplayColor =
            stateColors[$currentState as keyof typeof stateColors] ||
            stateColors.Idle;
        lerpColor(displayColor, targetDisplayColor, 0.12);
        displayColor = targetDisplayColor;

        // ── HUD frame outline ──────────────────────────────────────────
        ctx.save();
        ctx.strokeStyle = rgba(0.15);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(1.5, 1.5);
        ctx.lineTo(w - 1.5, 1.5);
        ctx.lineTo(w - 1.5, h - 1.5);
        ctx.lineTo(1.5, h - 1.5);
        ctx.closePath();
        ctx.stroke();
        ctx.restore();

        const midY = h / 2;
        const numBars = 28;
        const barW = 6;
        const gap = 2;
        const totalW = numBars * (barW + gap);
        const startX = (w - totalW) / 2 + barW / 2;
        ctx.lineCap = "round";

        // ── Bars ───────────────────────────────────────────────────────
        for (let i = 0; i < numBars; i++) {
            const raw = data[Math.floor((i / numBars) * data.length)] || 0;
            const percent = Math.min(1, raw / 255);
            const barH = 4 + percent * (h - 28);
            const x = startX + i * (barW + gap);

            const centerT = 1 - Math.abs(i - numBars / 2) / (numBars / 2);
            const dim = 0.5 + centerT * 0.5;
            const a = Math.min(0.95, 0.3 + percent * 0.7);

            ctx.shadowColor = rgba(0.8 * dim);
            ctx.shadowBlur = percent > 0.15 ? 3 + percent * 16 : 0;
            ctx.lineWidth = barW;
            ctx.strokeStyle = rgba(a * dim);

            const topY = midY - barH / 2;
            ctx.beginPath();
            ctx.moveTo(x, topY);
            ctx.lineTo(x, midY + barH / 2);
            ctx.stroke();
        }

        // ── Scan line ──────────────────────────────────────────────────
        scanLinePos = (scanLinePos + 0.5) % h;
        ctx.save();
        ctx.globalAlpha = 0.06;
        ctx.strokeStyle = rgba(1);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, scanLinePos);
        ctx.lineTo(w, scanLinePos);
        ctx.stroke();
        ctx.restore();
    }

    function tick() {
        const t = Date.now() * 0.003;
        const N = 28;
        let data: number[];

        if ($captureRunning) {
            data = $audioBars;
        } else if ($currentState === "Speaking") {
            data = Array.from(
                { length: N },
                (_, i) =>
                    Math.abs(Math.sin(t + i * 0.5) * Math.cos(t * 0.3)) * 220,
            );
        } else if ($currentState === "Thinking") {
            data = Array.from({ length: N }, (_, i) =>
                Math.sin(t * 2.5 - (i / N) * Math.PI * 6) > 0.7 ? 200 : 10,
            );
        } else if ($currentState === "Listening") {
            data = Array.from({ length: N }, (_, i) =>
                Math.max(0, Math.sin(t + i * 0.3) * 60 + Math.random() * 60),
            );
        } else {
            data = Array.from({ length: N }, (_, i) =>
                Math.max(
                    0,
                    (Math.sin(t * 0.5) * 0.3 + 0.7) *
                        (Math.sin(t + i * 0.25) * 12 + 6),
                ),
            );
        }

        draw(data);
        animationId = requestAnimationFrame(tick);
    }
</script>

<canvas bind:this={canvas} width={400} height={50} class="hud-audio"></canvas>

<style>
    .hud-audio {
        display: block;
        position: absolute;
        top: 8px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 100;
        pointer-events: none;
        background: rgba(0, 0, 0, 0.3);
        border-radius: 3px;
        filter: drop-shadow(0 0 6px rgba(var(--tr), var(--tg), var(--tb), 0.2));
    }
</style>
