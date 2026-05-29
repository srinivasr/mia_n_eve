<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { currentState } from "../stores/eveState";
    import { listen } from "@tauri-apps/api/event";
    import type { UnlistenFn } from "@tauri-apps/api/event";

    export let audioData: number[] = [];

    let canvas: HTMLCanvasElement;
    let animationId: number;
    let unlistenAudio: UnlistenFn | null = null;
    let hasMicAccess = false;
    let micData: number[] = [];

    const stateColors = {
        Idle: "rgba(74, 229, 255, ",
        Listening: "rgba(0, 255, 255, ",
        Thinking: "rgba(179, 74, 255, ",
        Speaking: "rgba(255, 255, 255, ",
        Searching: "rgba(0, 255, 136, ",
        ExecutingTool: "rgba(255, 170, 0, ",
        Error: "rgba(255, 51, 51, )",
    };

    onMount(async () => {
        try {
            unlistenAudio = await listen<number[]>("audio-stream", (event) => {
                hasMicAccess = true;
                micData = event.payload;
            });
        } catch (e) {
            console.error("Failed to listen to audio-stream", e);
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

    function draw(data: any) {
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const width = canvas.width;
        const height = canvas.height;
        ctx.clearRect(0, 0, width, height);

        const center = width / 2;
        const midY = height / 2;

        const baseColor =
            stateColors[$currentState as keyof typeof stateColors] ||
            stateColors.Idle;
        ctx.shadowBlur = 0;
        ctx.lineCap = "round";

        const numBars = 20;
        const barWidth = 6;
        const gap = 8;

        ctx.lineWidth = barWidth;

        for (let i = 0; i < numBars; i++) {
            const binIndex = Math.floor((i / numBars) * (data.length * 0.8));
            const value = data[binIndex] || 0;
            const percent = value / 255;

            const barHeight = 6 + percent * (height - 12);
            const xOffset = i * (barWidth + gap) + gap / 2;

            ctx.strokeStyle = `${baseColor}${0.15 + percent * 0.4})`;

            ctx.beginPath();
            ctx.moveTo(center + xOffset, midY - barHeight / 2);
            ctx.lineTo(center + xOffset, midY + barHeight / 2);
            ctx.stroke();

            ctx.beginPath();
            ctx.moveTo(center - xOffset, midY - barHeight / 2);
            ctx.lineTo(center - xOffset, midY + barHeight / 2);
            ctx.stroke();
        }
    }

    function tick() {
        if (hasMicAccess && micData.length > 0) {
            draw(micData);
        } else if (audioData && audioData.length > 0) {
            draw(audioData);
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
                    const noise = Math.random() * 50;
                    return Math.max(0, Math.sin(t + i * 0.3) * 30 + noise);
                });
            } else {
                mockData = Array.from({ length: 32 }, (_, i) => {
                    return Math.max(0, Math.sin(t + i * 0.1) * 5 + 5);
                });
            }
            draw(mockData);
        }
        animationId = requestAnimationFrame(tick);
    }
</script>

<canvas bind:this={canvas} width={400} height={50} class="top-audio-bar"
></canvas>

<style>
    .top-audio-bar {
        position: absolute;
        top: 15px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 100;
        pointer-events: none;
        will-change: transform;
    }
</style>
