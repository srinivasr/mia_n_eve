<script lang="ts">
  import ThreeOrb from './lib/components/ThreeOrb.svelte';
  import Telemetry from './lib/components/Telemetry.svelte';
  import { onMount } from 'svelte';
  import { currentState, transcript, latencyMs, isConnected } from './lib/stores/eveState';

  // WebSocket Skeleton
  let ws: WebSocket | null = null;
  
  onMount(() => {
    // For now we just mock the connection since the python backend isn't running yet
    // In the future this will connect to the local python websocket server (ws://127.0.0.1:8080)
    connectWs();
    
    // MOCK DATA for testing UI 
    setTimeout(() => {
      currentState.set('Listening');
    }, 3000);
    
    setTimeout(() => {
      currentState.set('Thinking');
    }, 6000);
    
    setTimeout(() => {
      currentState.set('Speaking');
      transcript.set('Hello! I am Eve. How can I assist you today?');
    }, 9000);
    
    setTimeout(() => {
      currentState.set('Idle');
    }, 13000);
  });
  
  function connectWs() {
    try {
      isConnected.set(true);
      latencyMs.set(45); // Mock latency
    } catch (e) {
      console.error("WS error", e);
    }
  }
</script>

<main data-tauri-drag-region>
  <Telemetry />
  
  <ThreeOrb />
  
  {#if $transcript}
    <div class="transcript-container">
      <div class="transcript">
        {$transcript}
      </div>
    </div>
  {/if}
</main>

<style>
  main {
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    /* This makes the whole background draggable in Tauri */
  }

  .transcript-container {
    position: absolute;
    bottom: 40px;
    left: 0;
    right: 0;
    display: flex;
    justify-content: center;
    padding: 0 40px;
    pointer-events: none;
    z-index: 50;
  }

  .transcript {
    background: rgba(10, 15, 20, 0.75);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(100, 255, 218, 0.2);
    color: #e6f1ff;
    padding: 15px 30px;
    border-radius: 20px;
    font-size: 1.15rem;
    font-weight: 300;
    letter-spacing: 0.5px;
    line-height: 1.5;
    max-width: 70%;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.6), 0 0 15px rgba(100, 255, 218, 0.1);
    animation: fade-in 0.4s cubic-bezier(0.25, 1, 0.5, 1) forwards;
  }

  @keyframes fade-in {
    from { opacity: 0; transform: translateY(15px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
