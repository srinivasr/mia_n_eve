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
  import { stateColor, hexToRgb } from "./lib/stores/theme";

  let tr = 74, tg = 229, tb = 255;

  $: {
    const c = hexToRgb($stateColor);
    tr = c.r; tg = c.g; tb = c.b;
  }

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
    window.onerror = function(msg, url, lineNo, columnNo, error) {
      alert("Error: " + msg);
      return false;
    };
    // the error overlay was swallowing useful error messages
    // so let's also dump them to console
    const originalError = console.error;
    console.error = function(...args) {
      if (args[0] && args[0].toString().includes("WebGL")) {
        alert("WebGL Error: " + args.join(" "));
      }
      originalError.apply(console, args);
    };

    connectWs();

    // these timeouts are just for demo / testing the state transitions
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
    // TODO: actually wire up real websocket connection
    // for now we just pretend the connection is live
    try {
      isConnected.set(true);
      latencyMs.set(45);
    } catch (e) {
      console.error("WS error", e);
    }
  }
</script>

  <main
    data-tauri-drag-region
    style="--tr: {tr}; --tg: {tg}; --tb: {tb}"
  >
    <TopAudioBar />

    <ThreeOrb />

    <div class="left-dashboard">
      <Telemetry />
    </div>

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

  .left-dashboard {
    position: fixed;
    left: 24px;
    top: 84px;
    z-index: 100;
    pointer-events: none;
  }

  .left-dashboard > :global(*) {
    pointer-events: auto;
  }
</style>
