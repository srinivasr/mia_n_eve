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

    export let visible = false;

    let selectedInput = "";
    let selectedOutput = "";
    let pollingInterval: number;

    onMount(async () => {
        if (window.__TAURI_INTERNALS__) {
            await fetchDevices();
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
        } catch (e) {}
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

{#if visible}
    <div class="device-settings">
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
{/if}

<style>
    .device-settings {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 10px 0;
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 3px;
    }

    label {
        font-size: 0.6rem;
        color: rgba(255, 255, 255, 0.35);
        letter-spacing: 1.5px;
    }

    select {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #e2e8f0;
        padding: 5px 8px;
        border-radius: 5px;
        font-size: 0.75rem;
        outline: none;
    }

    select:focus {
        border-color: rgba(var(--tr), var(--tg), var(--tb), 0.3);
    }
</style>
