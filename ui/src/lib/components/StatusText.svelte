<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  export let state: string = "INITIALISING";

  let blink = true;
  let tick = 0;
  let interval: ReturnType<typeof setInterval>;
  let currentHeights = Array(36).fill(3);
  let targetHeights = Array(36).fill(3);
  let waveformHeights = Array(36).fill(3);

  onMount(() => {
    interval = setInterval(() => {
      tick++;
      if (tick % 38 === 0) {
        blink = !blink;
      }
      
      // Update waveform targets based on state
      for (let i = 0; i < 36; i++) {
        if (state === "Speaking") {
          if (tick % 4 === 0) {
            targetHeights[i] = Math.floor(Math.random() * 24) + 4;
          }
        } else if (state === "Error") {
          targetHeights[i] = 2;
        } else if (state === "Listening") {
          // Complex organic wave
          targetHeights[i] = 10 + 6 * Math.sin(tick * 0.1 + i * 0.4) + 4 * Math.cos(tick * 0.15 - i * 0.2);
        } else if (state === "Thinking" || state === "Processing") {
          // Bouncing scanner wave
          let cycle = (tick * 0.7) % 72;
          let focal = cycle < 36 ? cycle : 72 - cycle;
          let distance = Math.abs(i - focal);
          targetHeights[i] = Math.max(3, 16 - distance * 2);
        } else {
          // Idle / Initialising
          targetHeights[i] = 4 + 2 * Math.sin(tick * 0.05 + i * 0.3);
        }
        
        // Smooth interpolation
        currentHeights[i] += (targetHeights[i] - currentHeights[i]) * 0.25;
      }
      
      waveformHeights = [...currentHeights];
    }, 16);
  });

  onDestroy(() => {
    clearInterval(interval);
  });

  $: isSpeaking = state === "Speaking";
  $: isError = state === "Error";
  $: isThinking = state === "Thinking";
  $: isListening = state === "Listening";

  $: symbol = isThinking ? (blink ? "◈" : "◇") :
             (state === "Processing" ? (blink ? "▷" : "") :
             (blink ? "●" : "○"));

  $: textColor = isError ? "var(--muted-c)" :
                (isSpeaking ? "var(--acc)" :
                ((isThinking || state === "Processing") ? "var(--acc2)" :
                (isListening ? "var(--green)" : "var(--pri)")));

  $: textStr = `${symbol}  ${state.toUpperCase()}`;

</script>

<div class="status-container">
  <div class="status-text" style="color: {textColor}; text-shadow: 0 0 10px {textColor}44;">
    {textStr}
  </div>
  <div class="waveform">
    {#each waveformHeights as h}
      <div 
        class="wave-bar" 
        style="
          height: {Math.max(2, h)}px; 
          background-color: {textColor};
          opacity: {Math.min(1, Math.max(0.3, h / 18))};
          border-radius: 4px;
        "
      ></div>
    {/each}
  </div>
</div>

<style>
  .status-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin-top: auto;
    margin-bottom: 40px;
    height: 80px;
  }

  .status-text {
    font-family: "Courier New", Courier, monospace;
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 1px;
    margin-bottom: 20px;
  }

  .waveform {
    display: flex;
    align-items: flex-end;
    justify-content: center;
    height: 20px;
    gap: 7px;
  }

  .wave-bar {
    width: 7px;
    min-height: 2px;
  }
</style>
