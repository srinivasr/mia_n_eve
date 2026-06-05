"""
Mia Brain — main entry point for mia_n_mia.

Core entry point for the Mia AI Backend. Uses Ollama local models, faster-whisper, and pyttsx3.
"""

import asyncio
import sys
import threading
import json
import traceback
from pathlib import Path
import warnings

# Suppress harmless multiprocessing leaked semaphore warning on exit (from faster-whisper/ctranslate2)
warnings.filterwarnings("ignore", category=UserWarning, module="multiprocessing.resource_tracker")

from RealtimeSTT import AudioToTextRecorder
from piper_tts import PiperTTS, SentenceBuffer
import ollama

from ui_bridge import UIBridge
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
)
from memory.config_manager import get_ollama_url, get_ollama_model

from actions.file_processor import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater

from utils.logger import setup_logger
logger = setup_logger(__name__)


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR            = get_base_dir()
PROMPT_PATH         = BASE_DIR / "core" / "prompt.txt"

CHANNELS            = 1
SAMPLE_RATE         = 16000

def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "Your name is Mia (pronounced Mee-ah). Always refer to yourself as Mia. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

# Tool Declarations verbatim
TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Opens any application on the computer. Use this whenever the user asks to open, launch, or start any app, website, or program. Always call this tool — never just say you opened it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": "Controls YouTube. Use for: playing videos, summarizing a video's content, getting video info, or showing trending videos.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": "Captures and analyzes the screen or webcam image. MUST be called when user asks what is on screen, what you see, analyze my screen, look at camera, etc. You have NO visual ability without this tool. After calling this tool, stay SILENT — the vision module speaks directly.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": "Controls the computer: volume, brightness, window management, keyboard shortcuts, typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. Use for ANY single computer control command. NEVER route to agent_task.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": "Controls any web browser. Use for: opening websites, searching the web, clicking elements, filling forms, scrolling, screenshots, navigation, any web-based task. Always pass the 'browser' parameter when the user specifies a browser (e.g. 'open in Edge', 'use Firefox', 'open Chrome'). Multiple browsers can run simultaneously.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | get_url | press | new_tab | close_tab | screenshot | back | forward | reload | switch | list_browsers | close | close_all"},
                "browser":     {"type": "STRING", "description": "Target browser: chrome | edge | firefox | opera | operagx | brave | vivaldi | safari. Omit to use the currently active browser."},
                "url":         {"type": "STRING", "description": "URL for go_to / new_tab action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "engine":      {"type": "STRING", "description": "Search engine: google | bing | duckduckgo | yandex (default: google)"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up | down for scroll"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount in pixels (default: 500)"},
                "key":         {"type": "STRING", "description": "Key name for press action (e.g. Enter, Escape, F5)"},
                "path":        {"type": "STRING", "description": "Save path for screenshot"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": "Executes complex multi-step tasks requiring multiple different tools. Examples: 'research X and save to file', 'find and organize files'. DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": "THE ONLY tool for ANY Steam or Epic Games request. Use for: installing, downloading, updating games, listing installed games, checking download status, scheduling updates. ALWAYS call directly for any Steam/Epic/game request. NEVER use agent_task, browser_control, or web_search for Steam/Epic.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "shutdown_mia",
        "description": "Shuts down the assistant completely. Call this when the user expresses intent to end the conversation, close the assistant, say goodbye, or stop Mia. The user can say this in ANY language.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "file_processor",
        "description": "Processes any file that the user has uploaded or dropped onto the interface. Use this when the user refers to an uploaded file and wants an action on it. Supports: images, PDFs, Word docs & text files, CSV/Excel, JSON/XML, code files, audio, video, archives, presentations. ALWAYS call this tool when a file has been uploaded and the user gives a command about it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
                },
                "action": {
                    "type": "STRING",
                    "description": "What to do with the file. Examples: describe | ocr | resize | compress | convert | info | summarize | extract_text | analyze | stats | filter | sort | run | document | test | transcribe | trim | extract_audio | extract_frame | list | extract"
                },
                "instruction": {
                    "type": "STRING",
                    "description": "Free-form instruction if action doesn't cover it."
                },
                "format":    {"type": "STRING",  "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"},
                "width":     {"type": "INTEGER", "description": "Target width for image resize"},
                "height":    {"type": "INTEGER", "description": "Target height for image resize"},
                "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
                "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
                "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
                "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
                "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
                "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
                "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
                "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
                "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
                "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
                "destination": {"type": "STRING", "description": "Output folder for archive extract"},
            },
            "required": []
        }
    },
    {
        "name": "save_memory",
        "description": "Save an important personal fact about the user to long-term memory. Call this silently whenever the user reveals something worth remembering. Do NOT call for: weather, reminders, searches, or one-time commands. Do NOT announce that you are saving — just call it silently. Values must be in English regardless of the conversation language.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "identity | preferences | projects | relationships | wishes | notes"
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. John, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
]

def convert_to_openai_schema(schema):
    if isinstance(schema, list):
        return [convert_to_openai_schema(x) for x in schema]
    elif isinstance(schema, dict):
        new_schema = {}
        for k, v in schema.items():
            if k == "type" and isinstance(v, str):
                new_schema[k] = v.lower()
            else:
                new_schema[k] = convert_to_openai_schema(v)
        return new_schema
    return schema

OLLAMA_TOOLS = []
for tool in TOOL_DECLARATIONS:
    params = tool.get("parameters")
    if params:
        params = convert_to_openai_schema(params)
    else:
        params = {"type": "object", "properties": {}}
    OLLAMA_TOOLS.append({
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": params
        }
    })

class MiaLocal:
    def __init__(self, ui: UIBridge):
        self.ui = ui
        self.client = ollama.Client(host=get_ollama_url())
        self.model = get_ollama_model()
        self._loop = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self._speech_overlap = False
        self._llm_interrupted = False
        self._speak_end_time = 0.0  # timestamp when speaking ended (for cooldown)
        self._recent_mia_sentences = []  # echo detection: what Mia recently said
        self._recent_mia_lock = threading.Lock()
        self._process_lock = None  # initialized in run() as asyncio.Lock
        self.ui.on_text_command = self._on_text_command
        self.chat_history = []
        
        # Audio TTS
        self.tts = PiperTTS()
        self.tts.initialize()
        self.tts.enabled = True
                
        self._stop_event = threading.Event()

    def _on_text_command(self, text: str):
        if not self._loop: return
        self.ui.write_log(f"You: {text}")
        asyncio.run_coroutine_threadsafe(
            self._process_text_async(text),
            self._loop
        )

    def set_speaking(self, value: bool):
        import time as _time
        with self._speaking_lock:
            self._is_speaking = value
            if value:
                self._speech_overlap = True
                if hasattr(self, 'recorder'):
                    try:
                        self.recorder.abort()
                    except Exception:
                        pass
            else:
                # Record when speaking ended so we can apply a cooldown
                self._speak_end_time = _time.monotonic()
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    @staticmethod
    def _strip_punct(word: str) -> str:
        """Remove leading/trailing punctuation from a word for echo comparison."""
        import string
        return word.strip(string.punctuation)

    def _record_mia_sentence(self, sentence: str):
        """Track a sentence Mia spoke for echo detection."""
        import time as _time
        words = set(self._strip_punct(w) for w in sentence.lower().split() if self._strip_punct(w))
        if not words:
            return
        with self._recent_mia_lock:
            self._recent_mia_sentences.append((_time.monotonic(), words, sentence))
            # Keep only the last 30 seconds of sentences
            cutoff = _time.monotonic() - 30.0
            self._recent_mia_sentences = [
                (t, w, s) for t, w, s in self._recent_mia_sentences if t > cutoff
            ]

    def _is_echo(self, text: str) -> bool:
        """Check if transcribed text matches something Mia recently said."""
        import time as _time
        if not text or not text.strip():
            return False
        incoming_words = set(self._strip_punct(w) for w in text.lower().split() if self._strip_punct(w))
        if not incoming_words:
            return False
        with self._recent_mia_lock:
            cutoff = _time.monotonic() - 30.0
            for t, mia_words, mia_sent in self._recent_mia_sentences:
                if t < cutoff:
                    continue
                if not mia_words:
                    continue
                overlap = len(incoming_words & mia_words)
                # If >=50% of incoming words match what Mia said, it's echo
                ratio = overlap / len(incoming_words) if incoming_words else 0
                if ratio >= 0.5:
                    logger.info(f"Echo detected: '{text}' matches Mia's '{mia_sent}' (overlap={ratio:.0%})")
                    return True
        return False

    def speak(self, text: str):
        if not text: return
        self.ui.write_log(f"MIA: {text}")
        self._record_mia_sentence(text)
        self.set_speaking(True)
        try:
            self.tts.queue_sentence(text)
            self.tts.wait_for_completion()
        finally:
            self.set_speaking(False)

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_system_message(self) -> dict:
        from datetime import datetime
        memory = load_memory()
        mem_str = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()
        now = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )
        parts = [time_ctx]
        if mem_str: parts.append(mem_str)
        parts.append(sys_prompt)
        return {"role": "system", "content": "\n".join(parts)}
        
    async def _execute_tool(self, name: str, args: dict) -> dict:
        logger.info(f"{name}  {args}")
        self.ui.set_state("THINKING")

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                logger.info(f"save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return {"result": "ok", "silent": True}

        loop   = asyncio.get_event_loop()
        result = "Done."
        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."
            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."
            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."
            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."
            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None, "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."
            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result   = f"Task started (ID: {task_id})."
            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(None, lambda: file_processor(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "shutdown_mia":
                self.ui.write_log("SYS: Shutdown requested.")
                self.speak("Goodbye, sir.")
                def _shutdown():
                    import time
                    import os
                    time.sleep(1)
                    os._exit(0)
                threading.Thread(target=_shutdown, daemon=True).start()
            else:
                result = f"Unknown tool: {name}"
        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")
        logger.info(f"{name} → {str(result)[:80]}")
        return {"result": result}
        
    async def _process_text_async(self, text: str):
        # Serialize LLM processing — only one request at a time
        if not self._process_lock:
            return
        async with self._process_lock:
            await self._process_text_impl(text)

    async def _process_text_impl(self, text: str):
        if text.strip():
            self.chat_history.append({"role": "user", "content": text})
            
        self._llm_interrupted = False
        self.ui.set_state("THINKING")
        
        try:
            loop = asyncio.get_event_loop()
            
            async def run_streamed_chat(msg_list):
                q = asyncio.Queue()
                
                def _stream_reader():
                    try:
                        for chunk in self.client.chat(
                            model=self.model,
                            messages=msg_list,
                            tools=OLLAMA_TOOLS,
                            stream=True
                        ):
                            # chunk received OK
                            if self._llm_interrupted:
                                break
                            loop.call_soon_threadsafe(q.put_nowait, (chunk, None))
                    except Exception as e:
                        logger.error(f"DEBUG EXCEPTION: {e}")
                        loop.call_soon_threadsafe(q.put_nowait, (None, e))
                    finally:
                        loop.call_soon_threadsafe(q.put_nowait, (None, None))
                        
                threading.Thread(target=_stream_reader, daemon=True).start()
                
                full_content = ""
                tool_calls_map = {}
                sentence_buffer = SentenceBuffer()
                speaking_started = False
                
                while True:
                    if self._llm_interrupted:
                        break
                        
                    chunk, err = await q.get()
                    if err:
                        raise err
                    if chunk is None:
                        break
                        
                    # Force chunk into a standard dictionary to avoid Pydantic bugs
                    if hasattr(chunk, 'model_dump'):
                        try:
                            chunk = chunk.model_dump()
                        except:
                            chunk = dict(chunk)
                    elif not isinstance(chunk, dict):
                        try:
                            chunk = dict(chunk)
                        except:
                            pass
                            
                    msg = chunk.get("message", {}) if isinstance(chunk, dict) else {}
                    
                    # Accumulate tool calls
                    tcs = msg.get("tool_calls")
                    if tcs:
                        for tc in tcs:
                            idx = tc.get("index", 0) if isinstance(tc, dict) else 0
                            if idx not in tool_calls_map:
                                tool_calls_map[idx] = {
                                    "id": tc.get("id", "") if isinstance(tc, dict) else "",
                                    "type": "function",
                                    "function": {
                                        "name": tc.get("function", {}).get("name", "") if isinstance(tc, dict) else "",
                                        "arguments": tc.get("function", {}).get("arguments", "") if isinstance(tc, dict) else ""
                                    }
                                }
                            else:
                                fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                                if fn.get("name"):
                                    tool_calls_map[idx]["function"]["name"] = fn["name"]
                                if fn.get("arguments"):
                                    existing_args = tool_calls_map[idx]["function"]["arguments"]
                                    new_args = fn["arguments"]
                                    if isinstance(existing_args, str) and isinstance(new_args, str):
                                        tool_calls_map[idx]["function"]["arguments"] += new_args
                                    elif isinstance(new_args, dict):
                                        if not isinstance(existing_args, dict):
                                            tool_calls_map[idx]["function"]["arguments"] = {}
                                        tool_calls_map[idx]["function"]["arguments"].update(new_args)
                                        
                    # Accumulate and stream text content
                    content = msg.get("content", "")
                    if content:
                        full_content += str(content)
                        sentences = sentence_buffer.add(str(content))
                        for sentence in sentences:
                            if self._llm_interrupted:
                                break
                            if not speaking_started:
                                self.set_speaking(True)
                                speaking_started = True
                            self.tts.queue_sentence(sentence)
                            self._record_mia_sentence(sentence)
                            self.ui.write_log(f"MIA: {sentence}")
                            
                # Flush final sentences
                if not self._llm_interrupted:
                    remaining = sentence_buffer.flush()
                    if remaining:
                        if not speaking_started:
                            self.set_speaking(True)
                            speaking_started = True
                        self.tts.queue_sentence(remaining)
                        self._record_mia_sentence(remaining)
                        self.ui.write_log(f"MIA: {remaining}")
                        
                # Wait for speaking to complete
                if speaking_started and not self._llm_interrupted:
                    logger.info("Waiting for TTS to finish...")
                    await loop.run_in_executor(None, self.tts.wait_for_completion)
                    logger.info("TTS finished.")
                    self.set_speaking(False)
                elif speaking_started:
                    self.set_speaking(False)
                    
                # Convert tool calls map to list
                tool_calls = []
                if tool_calls_map:
                    tool_calls = list(tool_calls_map.values())
                    for tc in tool_calls:
                        fn = tc["function"]
                        if isinstance(fn["arguments"], str) and fn["arguments"].strip():
                            try:
                                fn["arguments"] = json.loads(fn["arguments"])
                            except Exception:
                                pass
                                
                return full_content, tool_calls
                
            messages = [self._build_system_message()] + self.chat_history
            full_content, tool_calls = await run_streamed_chat(messages)
            
            if tool_calls and not self._llm_interrupted:
                self.chat_history.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": tool_calls
                })
                
                for tc in tool_calls:
                    if self._llm_interrupted:
                        break
                    name = tc["function"]["name"]
                    args = tc["function"]["arguments"]
                    res = await self._execute_tool(name, args)
                    self.chat_history.append({
                        "role": "tool",
                        "content": json.dumps(res),
                        "name": name
                    })
                    
                if not self._llm_interrupted:
                    logger.info("Calling LLM again with tool results...")
                    messages = [self._build_system_message()] + self.chat_history
                    final_content, _ = await run_streamed_chat(messages)
                    logger.info(f"Follow-up LLM response done, content length: {len(final_content) if final_content else 0}")
                    if final_content and not self._llm_interrupted:
                        self.chat_history.append({"role": "assistant", "content": final_content})
            elif full_content and not self._llm_interrupted:
                self.chat_history.append({"role": "assistant", "content": full_content})
                
        except Exception as e:
            logger.error(f"Error communicating with Ollama: {e}")
            traceback.print_exc()
            if not self._llm_interrupted:
                await loop.run_in_executor(None, self.speak, "I encountered an error reaching the local model.")
            
        if not self.ui.muted:
            self.ui.set_state("LISTENING")

    def _in_speaking_cooldown(self) -> bool:
        """Return True if we recently stopped speaking (echo suppression window)."""
        import time as _time
        COOLDOWN_SECS = 4.0  # Whisper takes several seconds to process echo audio
        return (_time.monotonic() - self._speak_end_time) < COOLDOWN_SECS

    def _audio_listen_loop(self):
        logger.info("Starting audio listen loop")
        
        def on_rec_start():
            with self._speaking_lock:
                if self._is_speaking:
                    # Check if we should truly interrupt.
                    # Only allow interruption if user has been speaking for a
                    # sustained period (not just an echo blip). We handle the
                    # actual interrupt decision in the text callback instead,
                    # because VAD triggers too eagerly on speaker echo.
                    logger.info("VAD detected speech while Mia speaking — deferring to text callback.")
                    return
                elif self._in_speaking_cooldown():
                    # Still within the echo cooldown window after Mia finished
                    logger.info("VAD triggered during post-speech cooldown — ignoring.")
                    return
                else:
                    self._speech_overlap = False
                    if not self.ui.muted:
                        self.ui.set_state("LISTENING")
                    
        def on_rec_stop():
            with self._speaking_lock:
                if not self.ui.muted and not self._is_speaking:
                    self.ui.set_state("THINKING")

        import silero_vad
        silero_model_path = str(Path(silero_vad.__file__).resolve().parent / "data" / "silero_vad.onnx")

        self.recorder = AudioToTextRecorder(
            model="base.en",
            language="en",
            device="cpu",
            compute_type="int8",
            spinner=False,
            silero_sensitivity=0.4,
            post_speech_silence_duration=0.7,
            silero_onnx_model_path=silero_model_path,
            on_recording_start=on_rec_start,
            on_recording_stop=on_rec_stop
        )
        
        while not self._stop_event.is_set():
            try:
                text = self.recorder.text()
                
                with self._speaking_lock:
                    is_speaking_now = self._is_speaking
                    is_muted = self.ui.muted
                    is_overlap = self._speech_overlap
                
                # If we got text while Mia was speaking, check if it's
                # an echo of Mia's own words before treating as interruption.
                if is_speaking_now and text and text.strip():
                    if self._is_echo(text):
                        continue
                    logger.info(f"User interrupted with real speech: {text}")
                    self.tts.stop()
                    self._llm_interrupted = True
                    with self._speaking_lock:
                        self._is_speaking = False
                        self._speech_overlap = False
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("MIA: (interrupted)")
                    self.ui.write_log(f"You: {text}")
                    asyncio.run_coroutine_threadsafe(self._process_text_async(text), self._loop)
                    continue
                
                # Skip if still speaking, muted, overlap flag, or in cooldown
                if is_speaking_now or is_muted or is_overlap:
                    continue
                    
                if self._in_speaking_cooldown():
                    # Whisper may have transcribed echo — discard
                    if text and text.strip():
                        logger.info(f"Discarding likely echo during cooldown: {text}")
                    continue
                
                # Final echo check even outside cooldown — Whisper can be slow
                if text and text.strip() and self._is_echo(text):
                    continue
                        
                if text and text.strip():
                    self.ui.write_log(f"You: {text}")
                    asyncio.run_coroutine_threadsafe(self._process_text_async(text), self._loop)
            except Exception as e:
                logger.error(f"Whisper STT error: {e}")
                
        self.recorder.shutdown()

    async def run(self):
        self._loop = asyncio.get_event_loop()
        self._process_lock = asyncio.Lock()  # Must be created in async context
        self.ui.set_state("INITIALIZING")
        
        threading.Thread(target=self._audio_listen_loop, daemon=True).start()

        self.ui.set_state("LISTENING")
        self.ui.write_log("SYS: MIA online (Local Mode).")
        
        await asyncio.sleep(0.5)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.speak, "System Initialization Complete. Running on local Ollama.")
        
        while not self._stop_event.is_set():
            await asyncio.sleep(1)

async def _run_all():
    ui  = UIBridge()
    mia = MiaLocal(ui)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(ui.serve())
        await ui.wait_for_config()
        tg.create_task(mia.run())

def main():
    try:
        asyncio.run(_run_all())
    except KeyboardInterrupt:
        logger.info("\n Shutting down Mia Brain...")

if __name__ == "__main__":
    main()
