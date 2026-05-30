<script lang="ts">
    import { onMount, afterUpdate, onDestroy } from "svelte";
    import { currentState } from "../stores/eveState";
    import { sttResult } from "../stores/audioStore";

    export let messages: Array<{ time: string; sender: string; text: string }> =
        [];
    export let inputValue = "";
    export let isModularMode = false;
    export let activeDragElement = "";
    export let position = { x: 0, y: 0 };
    export let width = 672;
    export let height: number | null = null;

    export let onsend: (detail: { text: string }) => void = () => {};
    let messageContainer: HTMLDivElement;

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

    let unsubscribeStt: () => void;

    onMount(() => {
        scrollToBottom();
        // wire up the STT result stream so voice input fills the text box
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

<div
    id="chat"
    class="chat-module {isModularMode
        ? activeDragElement === 'chat'
            ? 'ring-active'
            : 'ring-inactive'
        : ''}"
    style="
        left: {position.x ? position.x + 'px' : '50%'};
        top: {position.y ? position.y + 'px' : 'auto'};
        width: {width}px;
        height: {height ? height + 'px' : 'auto'};
    "
>
    <div class="noise-overlay"></div>

    <div
        bind:this={messageContainer}
        class="messages-container"
        style="height: {height ? `calc(${height}px - 70px)` : '15rem'};"
    >
        {#each messages as msg}
            <div
                class="message-wrapper {msg.sender === 'USER'
                    ? 'user-msg'
                    : 'system-msg'}"
            >
                {#if msg.sender !== "USER"}
                    <div
                        class="avatar-dot {msg.sender === 'SYSTEM'
                            ? 'system-dot'
                            : 'eve-dot'}"
                    ></div>
                {/if}
                <div class="bubble-container">
                    <div class="message-bubble">
                        <div class="message-text">{msg.text}</div>
                    </div>
                    <span class="message-time">{msg.time}</span>
                </div>
            </div>
        {/each}
    </div>

    <div class="input-container">
        <input
            type="text"
            bind:value={inputValue}
            onkeydown={handleKeyDown}
            placeholder="What would you like to do today...!!"
            class="command-input"
        />
    </div>

    {#if isModularMode}
        <div
            class="modular-label {activeDragElement === 'chat'
                ? 'text-active'
                : 'text-inactive'}"
        >
            CHAT MODULE
        </div>
    {/if}
</div>

<style>
    .chat-module {
        position: absolute;
        bottom: 40px;
        left: 50%;
        transform: translateX(-50%);
        padding: 24px;
        pointer-events: auto;
        transition: all 0.2s cubic-bezier(0.25, 1, 0.5, 1);
        backdrop-filter: blur(20px);
        background: rgba(5, 10, 20, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow:
            0 20px 50px rgba(0, 0, 0, 0.6),
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        z-index: 90;
        overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            Helvetica, Arial, sans-serif;
    }

    .noise-overlay {
        position: absolute;
        inset: 0;
        background-image: url("https://grainy-gradients.vercel.app/noise.svg");
        opacity: 0.03;
        pointer-events: none;
        mix-blend-mode: overlay;
    }

    .messages-container {
        display: flex;
        flex-direction: column;
        gap: 16px;
        overflow-y: auto;
        margin-bottom: 16px;
        position: relative;
        z-index: 10;
        scrollbar-width: none;
        mask-image: linear-gradient(to bottom, transparent 0%, black 15%);
        padding-right: 4px;
        padding-left: 4px;
    }

    .messages-container::-webkit-scrollbar {
        display: none;
    }

    .message-wrapper {
        display: flex;
        align-items: flex-end;
        gap: 10px;
        max-width: 85%;
        opacity: 0;
        transform: translateY(10px);
        animation: bubble-appear 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)
            forwards;
    }

    @keyframes bubble-appear {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .user-msg {
        align-self: flex-end;
        flex-direction: row-reverse;
    }

    .system-msg {
        align-self: flex-start;
    }

    .avatar-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-bottom: 14px;
        flex-shrink: 0;
    }

    .eve-dot {
        background: #22d3ee;
        box-shadow: 0 0 8px #22d3ee;
    }

    .system-dot {
        background: rgba(255, 255, 255, 0.4);
    }

    .bubble-container {
        display: flex;
        flex-direction: column;
    }

    .user-msg .bubble-container {
        align-items: flex-end;
    }

    .system-msg .bubble-container {
        align-items: flex-start;
    }

    .message-bubble {
        padding: 10px 16px;
        border-radius: 18px;
        font-size: 0.9rem;
        line-height: 1.5;
        font-weight: 300;
    }

    .user-msg .message-bubble {
        background: linear-gradient(
            135deg,
            rgba(34, 211, 238, 0.15) 0%,
            rgba(34, 211, 238, 0.05) 100%
        );
        border: 1px solid rgba(34, 211, 238, 0.25);
        color: #e2e8f0;
        border-bottom-right-radius: 4px;
        box-shadow: 0 4px 15px rgba(34, 211, 238, 0.05);
    }

    .system-msg .message-bubble {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.06);
        color: #cbd5e1;
        border-bottom-left-radius: 4px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
    }

    .message-time {
        font-size: 0.65rem;
        color: rgba(255, 255, 255, 0.25);
        margin-top: 4px;
        font-family: monospace;
        letter-spacing: 0.5px;
    }

    .message-text {
        word-break: break-word;
    }

    .input-container {
        position: relative;
        z-index: 10;
        margin-top: 8px;
    }

    .command-input {
        width: 100%;
        background: rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px 18px;
        color: #f8fafc;
        font-size: 0.9rem;
        backdrop-filter: blur(5px);
        transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1);
        box-sizing: border-box;
    }

    .command-input::placeholder {
        color: rgba(255, 255, 255, 0.3);
    }

    .command-input:focus {
        outline: none;
        border-color: rgba(34, 211, 238, 0.4);
        box-shadow:
            0 0 20px rgba(34, 211, 238, 0.15),
            inset 0 0 5px rgba(34, 211, 238, 0.05);
        background: rgba(0, 0, 0, 0.55);
    }

    .modular-label {
        position: absolute;
        top: -24px;
        left: 0;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 2px;
    }

    .ring-active {
        box-shadow:
            0 0 0 2px #22c55e,
            0 20px 50px rgba(0, 0, 0, 0.6);
    }

    .ring-inactive {
        box-shadow:
            0 0 0 1px rgba(234, 179, 8, 0.3),
            0 20px 50px rgba(0, 0, 0, 0.6);
    }

    .text-active {
        color: #22c55e;
    }

    .text-inactive {
        color: rgba(234, 179, 8, 0.5);
    }
</style>
