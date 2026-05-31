<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { invoke } from "@tauri-apps/api/core";
    import {
        audioDevices,
        captureRunning,
        vadActive,
        rmsLevel,
        type AudioDeviceInfo,
    } from "../stores/audioStore";
    import { currentState } from "../stores/eveState";

    let selectedInput = "";
    let selectedOutput = "";
    let pollingInterval: number;

    onMount(async () => {
        if (window.__TAURI_INTERNALS__) {
            await fetchDevices();
            // poll every 2s to check if capture is still alive
            pollingInterval = window.setInterval(pollMetrics, 2000);
        }
    });

    onDestroy(() => {
        if (pollingInterval) clearInterval(pollingInterval);
    });

    async function fetchDevices() {
        try {
            const [inputs, outputs] = await invoke<[AudioDeviceInfo[], AudioDeviceInfo[]]>("list_audio_devices");
            audioDevices.set({ inputs, outputs });

            const defaultIn = inputs.find((d) => d.is_default);
            if (defaultIn && !selectedInput) selectedInput = defaultIn.id;

            const defaultOut = outputs.find((d) => d.is_default);
            if (defaultOut && !selectedOutput) selectedOutput = defaultOut.id;
        } catch (e) {
            console.error("could not list audio devices", e);
        }
    }

    async function pollMetrics() {
        try {
            const metrics = await invoke<{ capture_running: boolean; playback_running: boolean }>("get_audio_metrics");
            captureRunning.set(metrics.capture_running);
        } catch (e) {
            // tauri command not available in browser dev mode
        }
    }

    async function onInputChanged() {
        if (window.__TAURI_INTERNALS__) {
            await invoke("set_input_device", { name: selectedInput || null });
        }
    }

    async function onOutputChanged() {
        if (window.__TAURI_INTERNALS__) {
            await invoke("set_output_device", { name: selectedOutput || null });
        }
    }

    async function toggleCapture() {
        if (!window.__TAURI_INTERNALS__) return;

        try {
            if ($captureRunning) {
                await invoke("stop_capture");
                captureRunning.set(false);
                if ($currentState === "Listening") {
                    currentState.set("Idle");
                }
            } else {
                await invoke("start_capture");
                captureRunning.set(true);
            }
        } catch (e) {
            console.error("toggle capture failed", e);
        }
    }

    // VAD state drives the app state when capture is active
    $: {
        if ($captureRunning) {
            if ($vadActive && $currentState === "Idle") {
                currentState.set("Listening");
            } else if (!$vadActive && $currentState === "Listening") {
                currentState.set("Idle");
            }
        }
    }
</script>

<div class="audio-panel">
    <div class="header">
        <span class="title">AUDIO NATIVE RUNTIME</span>
        <div class="status-indicator">
            <span class="vad-dot" class:active={$vadActive}></span>
            <span class="status-text">{$vadActive ? "VAD" : "RDY"}</span>
        </div>
    </div>

    <div class="controls">
        <div class="form-group">
            <label for="input-select">INPUT</label>
            <select id="input-select" bind:value={selectedInput} on:change={onInputChanged}>
                {#each $audioDevices.inputs as device}
                    <option value={device.id}>{device.name}</option>
                {/each}
            </select>
        </div>

        <div class="form-group">
            <label for="output-select">OUTPUT</label>
            <select id="output-select" bind:value={selectedOutput} on:change={onOutputChanged}>
                {#each $audioDevices.outputs as device}
                    <option value={device.id}>{device.name}</option>
                {/each}
            </select>
        </div>
    </div>

    <div class="action-row">
        <button class="capture-btn" class:running={$captureRunning} on:click={toggleCapture}>
            {$captureRunning ? "STOP CAPTURE" : "START CAPTURE"}
        </button>

        <div class="rms-meter-container">
            <div class="rms-meter-fill" style="width: {Math.min(100, ($rmsLevel / 255) * 100)}%;"></div>
        </div>
    </div>
</div>

<style>
    .audio-panel {
        background: rgba(10, 15, 20, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(var(--tr), var(--tg), var(--tb), 0.15);
        border-radius: 12px;
        padding: 16px;
        width: 252px;
        font-family: "Inter", -apple-system, sans-serif;
        color: #fff;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 10px;
        margin-bottom: 12px;
    }

    .title {
        font-size: 0.7rem;
        letter-spacing: 2px;
        color: #8892b0;
        font-weight: 600;
    }

    .status-indicator {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .vad-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #4a5568;
        transition: all 0.1s ease;
    }

    .vad-dot.active {
        background: #00ff88;
        box-shadow: 0 0 8px #00ff88;
    }

    .status-text {
        font-size: 0.6rem;
        font-family: "JetBrains Mono", monospace;
        color: #a8b2d1;
        width: 20px;
    }

    .controls {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin-bottom: 16px;
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    label {
        font-size: 0.65rem;
        color: #a8b2d1;
        letter-spacing: 1px;
    }

    select {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #e2e8f0;
        padding: 6px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        outline: none;
    }

    select:focus {
        border-color: rgba(34, 211, 238, 0.4);
    }

    .action-row {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .capture-btn {
        background: rgba(34, 211, 238, 0.1);
        border: 1px solid rgba(34, 211, 238, 0.3);
        color: #22d3ee;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 1px;
        cursor: pointer;
        transition: all 0.2s ease;
        flex-shrink: 0;
    }

    .capture-btn:hover {
        background: rgba(34, 211, 238, 0.2);
    }

    .capture-btn.running {
        background: rgba(255, 107, 107, 0.1);
        border-color: rgba(255, 107, 107, 0.3);
        color: #ff6b6b;
    }

    .capture-btn.running:hover {
        background: rgba(255, 107, 107, 0.2);
    }

    .rms-meter-container {
        flex-grow: 1;
        height: 6px;
        background: rgba(0, 0, 0, 0.5);
        border-radius: 3px;
        overflow: hidden;
    }

    .rms-meter-fill {
        height: 100%;
        background: linear-gradient(90deg, #22d3ee, #00ff88);
        transition: width 0.05s ease;
    }
</style>
