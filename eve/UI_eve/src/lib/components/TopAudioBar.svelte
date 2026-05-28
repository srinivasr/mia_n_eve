<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { currentState } from "../stores/eveState";

    export let audioData: number[] = [];

    let canvas: HTMLCanvasElement;
    let animationId: number;
    let audioContext: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let dataArray: any;
    let source: MediaStreamAudioSourceNode | null = null;
    let stream: MediaStream | null = null;
    let hasMicAccess = false;

    const stateColors = {
        Idle: "rgba(74, 229, 255, ",
        Listening: "rgba(0, 255, 255, ",
        Thinking: "rgba(179, 74, 255, ",
        Speaking: "rgba(255, 255, 255, ",
        Searching: "rgba(0, 255, 136, ",
        ExecutingTool: "rgba(255, 170, 0, ",
        Error: "rgba(255, 51, 51, )",
    };

    onMount(() => {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices
                .getUserMedia({ audio: true })
                .then((s) => {
                    stream = s;
                    audioContext = new (window.AudioContext ||
                        (window as any).webkitAudioContext)();
                    analyser = audioContext.createAnalyser();
                    analyser.fftSize = 64;
                    source = audioContext.createMediaStreamSource(stream);
                    source.connect(analyser);
                    const bufferLength = analyser.frequencyBinCount;
                    dataArray = new Uint8Array(bufferLength);
                    hasMicAccess = true;
                    tick();
                })
                .catch(() => {
                    tick();
                });
        } else {
            tick();
        }
    });

    onDestroy(() => {
        if (animationId) {
            cancelAnimationFrame(animationId);
        }
        if (stream) {
            stream.getTracks().forEach((track) => track.stop());
        }
        if (audioContext) {
            audioContext.close();
        }
    });

    function draw(data: any) {
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const width = canvas.width;
        const height = canvas.height;
        ctx.clearRect(0, 0, width, height);

        const barWidth = 4;
        const gap = 2;
        const totalBars = Math.floor(width / (barWidth + gap));
        const center = width / 2;

        const baseColor =
            stateColors[$currentState as keyof typeof stateColors] ||
            stateColors.Idle;

        for (let i = 0; i < totalBars / 2; i++) {
            const value = data[i % data.length] || 0;
            const percent = value / 255;
            const barHeight = Math.max(2, percent * height);

            ctx.fillStyle = `${baseColor}${0.2 + percent * 0.8})`;

            ctx.fillRect(
                center + i * (barWidth + gap),
                (height - barHeight) / 2,
                barWidth,
                barHeight,
            );
            ctx.fillRect(
                center - (i + 1) * (barWidth + gap),
                (height - barHeight) / 2,
                barWidth,
                barHeight,
            );
        }
    }

    function tick() {
        if (hasMicAccess && analyser && dataArray) {
            analyser.getByteFrequencyData(dataArray);
            draw(dataArray);
        } else if (audioData && audioData.length > 0) {
            draw(audioData);
        } else {
            const t = Date.now() * 0.003;
            let mockData: number[] = [];

            if ($currentState === "Listening") {
                mockData = Array.from({ length: 32 }, (_, i) => {
                    const noise = Math.random() * 20;
                    return Math.max(0, Math.sin(t + i * 0.3) * 60 + 80 + noise);
                });
            } else if ($currentState === "Speaking") {
                mockData = Array.from({ length: 32 }, (_, i) => {
                    const wave = Math.sin(t * 2 + i * 0.15) * Math.cos(t * 0.5);
                    return Math.max(0, Math.abs(wave) * 160 + 30);
                });
            } else if ($currentState === "Thinking") {
                mockData = Array.from({ length: 32 }, (_, i) => {
                    const pos = i / 32;
                    const pulse = Math.sin(t * 3 - pos * Math.PI * 4);
                    return Math.max(0, (pulse > 0.7 ? 1 : 0.1) * 80 + 10);
                });
            } else {
                mockData = Array.from({ length: 32 }, (_, i) => {
                    return Math.max(0, Math.sin(t + i * 0.1) * 15 + 20);
                });
            }
            draw(mockData);
        }
        animationId = requestAnimationFrame(tick);
    }
</script>

<canvas bind:this={canvas} width={300} height={40} class="top-audio-bar"
></canvas>

<style>
    .top-audio-bar {
        opacity: 0.85;
        filter: drop-shadow(0 0 8px rgba(34, 211, 238, 0.3));
        transition: filter 0.3s ease;
    }
</style>
