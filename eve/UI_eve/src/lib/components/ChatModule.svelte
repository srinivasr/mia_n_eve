<script lang="ts">
    import { onMount, afterUpdate, onDestroy } from "svelte";
    import { invoke } from "@tauri-apps/api/core";
    import { currentState } from "../stores/eveState";
    import {
        sttResult,
        captureRunning,
        vadActive,
        rmsLevel,
    } from "../stores/audioStore";
    import AudioDevicePanel from "./AudioDevicePanel.svelte";

    export let messages: Array<{ time: string; sender: string; text: string }> =
        [];
    export let inputValue = "";
    export let onsend: (detail: { text: string }) => void = () => {};

    let messageContainer: HTMLDivElement;
    let showDevices = false;

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === "Enter") {
            if (inputValue.trim()) {
                onsend({ text: inputValue });
                inputValue = "";
            }
        }
    }

    function scrollToBottom() {
        if (messageContainer) {
            messageContainer.scrollTo({
                top: messageContainer.scrollHeight,
                behavior: "smooth",
            });
        }
    }

    afterUpdate(() => {
        scrollToBottom();
    });

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

    let unsubscribeStt: () => void;

    onMount(() => {
        scrollToBottom();
        unsubscribeStt = sttResult.subscribe((val) => {
            if (val) {
                inputValue = (inputValue + " " + val).trim();
                sttResult.set("");
            }
        });
    });

    onDestroy(() => {
        if (unsubscribeStt) unsubscribeStt();
    });
</script>

<div class="terminal">
    <div class="term-header">
        <div class="term-dots">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
        </div>
        <span class="term-title">E.V.E. TERMINAL — {getStateLabel($currentState)}</span>
        <button class="term-gear" onclick={() => (showDevices = !showDevices)} aria-label="Settings">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
        </button>
    </div>

    <AudioDevicePanel visible={showDevices} />

    <div bind:this={messageContainer} class="term-body">
        {#each messages as msg}
            <div class="term-line {msg.sender === 'USER' ? 'line-user' : msg.sender === 'SYSTEM' ? 'line-sys' : 'line-eve'}">
                <span class="line-time">{msg.time}</span>
                <span class="line-sender">{formatSender(msg.sender)}</span>
                <span class="line-sep">▸</span>
                <span class="line-text">{msg.text}</span>
            </div>
        {/each}
    </div>

    <div class="term-input-row">
        <button
            class="term-mic"
            class:recording={$captureRunning && $vadActive}
            class:active={$captureRunning}
            onclick={toggleCapture}
            aria-label="Toggle mic"
        >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="22"/>
            </svg>
        </button>
        <span class="term-prompt">></span>
        <input
            type="text"
            bind:value={inputValue}
            onkeydown={handleKeyDown}
            placeholder="type a command..."
            class="term-input"
        />
    </div>

    <div class="term-status">
        <span class="status-indicator" class:alive={$captureRunning}></span>
        <span class="status-text">
            {#if $captureRunning}
                {$vadActive ? "LISTENING" : "STANDBY"}
            {:else}
                IDLE
            {/if}
        </span>
        <span
            class="status-rms"
            style="width: {Math.min(100, ($rmsLevel / 255) * 100)}%;"
        ></span>
    </div>
</div>

<script context="module" lang="ts">
    function getStateLabel(s: string): string {
        const map: Record<string, string> = {
            Idle: "IDLE",
            Listening: "CAPTURE",
            Thinking: "PROCESS",
            Speaking: "OUTPUT",
            Searching: "SEARCH",
            ExecutingTool: "EXEC",
            Error: "ERR",
        };
        return map[s] || "IDLE";
    }

    function formatSender(s: string): string {
        const map: Record<string, string> = {
            USER: "USER",
            EVE: "EVE",
            SYSTEM: "SYS",
        };
        return (map[s] || s).padEnd(4);
    }
</script>

<style>
    .terminal {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        width: clamp(300px, 30vw, 480px);
        display: flex;
        flex-direction: column;
        pointer-events: auto;
        background: #0a0a0a;
        border-left: 1px solid #1a1a1a;
        z-index: 90;
        overflow: hidden;
        font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
        font-size: 0.75rem;
        color: #c0c0c0;
    }

    /* ── Header ─────────────────────────────────── */
    .term-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        border-bottom: 1px solid #181818;
        flex-shrink: 0;
        user-select: none;
    }

    .term-dots {
        display: flex;
        gap: 5px;
        flex-shrink: 0;
    }

    .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }

    .dot-red { background: #ff5f56; }
    .dot-yellow { background: #ffbd2e; }
    .dot-green { background: #27c93f; }

    .term-title {
        flex: 1;
        font-size: 0.6rem;
        color: #555;
        letter-spacing: 0.5px;
        text-align: center;
    }

    .term-gear {
        flex-shrink: 0;
        background: none;
        border: none;
        color: #333;
        cursor: pointer;
        padding: 2px;
        transition: color 0.15s;
    }

    .term-gear:hover { color: #666; }

    /* ── Message body ────────────────────────────── */
    .term-body {
        flex: 1;
        overflow-y: auto;
        padding: 10px 12px;
        scrollbar-width: none;
    }

    .term-body::-webkit-scrollbar { display: none; }

    .term-line {
        display: flex;
        gap: 6px;
        margin-bottom: 4px;
        opacity: 0;
        animation: fade-in 0.15s ease forwards;
        line-height: 1.6;
    }

    @keyframes fade-in {
        to { opacity: 1; }
    }

    .line-time {
        color: #444;
        flex-shrink: 0;
    }

    .line-sender {
        flex-shrink: 0;
        width: 4ch;
    }

    .line-user .line-sender { color: #ffcc00; }
    .line-eve .line-sender { color: #4ae5ff; }
    .line-sys .line-sender { color: #555; }

    .line-sep {
        color: #444;
        flex-shrink: 0;
        margin-right: 2px;
    }

    .line-text {
        color: #bbb;
        word-break: break-word;
    }

    .line-user .line-text { color: #e0d090; }
    .line-eve .line-text { color: #4ae5ff; }

    /* ── Input row ───────────────────────────────── */
    .term-input-row {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        border-top: 1px solid #181818;
        flex-shrink: 0;
    }

    .term-mic {
        flex-shrink: 0;
        width: 26px;
        height: 26px;
        border-radius: 3px;
        border: 1px solid #222;
        background: transparent;
        color: #555;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.15s;
    }

    .term-mic:hover { border-color: #444; color: #888; }
    .term-mic.active { border-color: #2a5; color: #2a5; }
    .term-mic.recording {
        border-color: #2a5;
        color: #2a5;
        background: rgba(34, 170, 85, 0.08);
        box-shadow: 0 0 10px rgba(34, 170, 85, 0.2);
    }

    .term-prompt {
        color: #2a5;
        flex-shrink: 0;
        font-weight: 700;
    }

    .term-input {
        flex: 1;
        background: transparent;
        border: none;
        outline: none;
        color: #c0c0c0;
        font-family: inherit;
        font-size: inherit;
        padding: 0;
        caret-color: #c0c0c0;
    }

    .term-input::placeholder { color: #333; }

    /* ── Status bar ──────────────────────────────── */
    .term-status {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-top: 1px solid #181818;
        flex-shrink: 0;
    }

    .status-indicator {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: #333;
        flex-shrink: 0;
    }

    .status-indicator.alive {
        background: #2a5;
        box-shadow: 0 0 6px #2a5;
    }

    .status-text {
        font-size: 0.6rem;
        color: #555;
        letter-spacing: 1px;
        flex-shrink: 0;
    }

    .status-rms {
        height: 2px;
        background: #2a5;
        border-radius: 1px;
        transition: width 0.05s;
        opacity: 0.6;
    }
</style>
