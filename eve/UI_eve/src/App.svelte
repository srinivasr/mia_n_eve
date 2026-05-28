<script lang="ts">
  import ThreeOrb from "./lib/components/ThreeOrb.svelte";
  import Telemetry from "./lib/components/Telemetry.svelte";
  import TopAudioBar from "./lib/components/TopAudioBar.svelte";
  import ChatModule from "./lib/components/ChatModule.svelte";
  import { onMount } from "svelte";
  import {
    currentState,
    transcript,
    latencyMs,
    isConnected,
  } from "./lib/stores/eveState";

  interface Message {
    time: string;
    sender: string;
    text: string;
  }

  let messages: Message[] = [
    {
      time: "15:00:00",
      sender: "SYSTEM",
      text: "E.V.E. PROTOCOL INITIALIZED.",
    },
  ];

  let inputValue = "";
  let ws: WebSocket | null = null;

  onMount(() => {
    connectWs();
    setTimeout(() => {
      currentState.set("Listening");
    }, 3000);

    setTimeout(() => {
      currentState.set("Thinking");
    }, 6000);

    setTimeout(() => {
      currentState.set("Speaking");
      transcript.set("Hello! I am Eve. How can I assist you today?");
    }, 9000);

    setTimeout(() => {
      currentState.set("Idle");
    }, 13000);
  });

  transcript.subscribe((value) => {
    if (value) {
      const now = new Date().toTimeString().split(" ")[0];
      if (
        messages.length === 0 ||
        messages[messages.length - 1].text !== value
      ) {
        messages = [...messages, { time: now, sender: "EVE", text: value }];
      }
    }
  });

  function handleSendMessage(detail: { text: string }) {
    const text = detail.text;
    const now = new Date().toTimeString().split(" ")[0];
    messages = [...messages, { time: now, sender: "USER", text }];

    currentState.set("Thinking");

    setTimeout(() => {
      currentState.set("Speaking");
      const responses = [
        "Command sequence accepted. Core systems operational.",
        "Analyzing ambient frequencies. Visualizer is fully active.",
        "Sub-system validation complete. Hardware metrics are nominal.",
        "Establishing neural pathways. Communication link secure.",
      ];
      const reply = responses[Math.floor(Math.random() * responses.length)];
      transcript.set(reply);

      setTimeout(() => {
        currentState.set("Idle");
      }, 3000);
    }, 1500);
  }

  function connectWs() {
    try {
      isConnected.set(true);
      latencyMs.set(45);
    } catch (e) {
      console.error("WS error", e);
    }
  }
</script>

<main data-tauri-drag-region>
  <Telemetry />

  <div class="audio-bar-container">
    <TopAudioBar />
  </div>

  <ThreeOrb />

  <ChatModule {messages} bind:inputValue onsend={handleSendMessage} />
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
  }

  .audio-bar-container {
    position: absolute;
    top: 30px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 100;
    pointer-events: none;
  }
</style>
