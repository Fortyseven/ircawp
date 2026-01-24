# Architecture After Phase 3 Refactoring

## Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        Ircawp (Coordinator)                      │
│  - Wires dependencies                                            │
│  - Initializes components                                        │
│  - Provides public API                                           │
└────────┬───────┬─────────┬──────────┬────────┬───────────────────┘
         │       │         │          │        │
         │       │         │          │        │
    ┌────▼───┐ ┌─▼──────┐ ┌▼───────┐ ┌▼────────▼┐ ┌──────────┐
    │Frontend│ │Backend │ │ImageGen│ │ Services │ │  Config  │
    │(Slack) │ │(OpenAI)│ │ (SDXL) │ └──────────┘ │   (YAML) │
    └────────┘ └────────┘ └────────┘      │       └──────────┘
                                          │
                     ┌────────────────────┼───────────────────┐
                     │                    │                   │
               ┌─────▼──────┐      ┌──────▼──────┐    ┌───────▼────────┐
               │ Message    │      │   Plugin    │    │     Media      │
               │  Router    │      │   Manager   │    │    Manager     │
               │            │      │             │    │                │
               │ • Queue    │      │ • Discovery │    │ • Validation   │
               │ • Dispatch │      │ • Execution │    │ • Cleanup      │
               │ • Thread   │      │ • Commands  │    │ • Paths        │
               └────────────┘      └─────────────┘    └────────────────┘
                                           │
                                           │
                                   ┌───────▼────────┐
                                   │      URL       │
                                   │   Extractor    │
                                   │                │
                                   │ • Extract      │
                                   │ • Fetch        │
                                   │ • Augment      │
                                   └────────────────┘
```

## Message Flow (Text Message)

```
1. Frontend receives message
         │
         ▼
2. Frontend.ingestEvent()
         │
         ▼
3. Ircawp.ingestMessage()
         │
         ▼
4. MessageRouter.ingest() → adds to queue
         │
         ▼
5. MessageRouter._message_queue_loop()
         │
         ▼
6. Is plugin?  ─── Yes ──→  PluginManager.execute_plugin()
         │                           │
         No                          │
         │                           │
         ▼                           │
7. URLExtractor.augment_message()    │
         │                           │
         ▼                           │
8. Backend.runInference()            │
         │                           │
         └───────────┬───────────────┘
                     │
                     ▼
9. MediaManager.cleanup_media_files()
                     │
                     ▼
10. Ircawp._egest_message()
                     │
                     ▼
11. Frontend.egestEvent()
                     │
                     ▼
12. User sees response
```

## Plugin Flow

```
User sends: /weather Seattle

         │
         ▼
PluginManager.is_plugin_command() → true
         │
         ▼
PluginManager.execute_plugin("weather", "Seattle", user_id, media)
         │
         ▼
PLUGINS["weather"].execute(
    query="Seattle",
    backend=backend,
    media=[],
    media_backend=imagegen
)
         │
         ▼
Returns: (response_text, media_file, skip_imagegen)
         │
         ▼
Back to MessageRouter for egestion
```

## Service Dependencies

```
MessageRouter
  ├─→ process_text_callback: Ircawp._process_text_message
  ├─→ process_plugin_callback: Ircawp._process_plugin_message
  ├─→ egest_callback: Ircawp._egest_message
  └─→ cleanup_media_callback: MediaManager.cleanup_media_files

PluginManager
  ├─→ Backend (for plugin execution)
  ├─→ ImageGen (optional, for plugins that generate images)
  └─→ Console (for logging)

MediaManager
  └─→ Console (for logging)

URLExtractor
  └─→ Console (for logging)

Ircawp
  ├─→ Frontend (Slack, Discord, etc.)
  ├─→ Backend (OpenAI, Ollama, etc.)
  ├─→ ImageGen (SDXL, etc.) [optional]
  ├─→ MessageRouter
  ├─→ PluginManager
  ├─→ MediaManager
  └─→ URLExtractor
```

## Directory Structure

```
app/
├── __init__.py
├── __main__.py
├── ircawp.py                 # Refactored coordinator (300 lines, was 472)
├── types.py
│
├── core/                     # NEW: Core services
│   ├── __init__.py
│   ├── message_router.py     # Queue & dispatch logic
│   ├── plugin_manager.py     # Plugin lifecycle
│   ├── media_manager.py      # Media file handling
│   └── url_extractor.py      # URL extraction & fetching
│
├── backends/
│   ├── Ircawp_Backend.py     # Base class
│   ├── openai.py             # OpenAI implementation
│   └── tools_manager.py      # Tool calling system
│
├── frontends/
│   ├── Ircawp_Frontend.py    # Base class
│   └── slack.py              # Slack implementation
│
├── plugins/
│   ├── __PluginBase.py
│   ├── __PluginCharacter.py
│   └── [individual plugins]
│
├── media_backends/
│   └── [image generation backends]
│
└── lib/
    ├── config.py
    ├── network.py            # Used by URLExtractor
    ├── thread_history.py
    └── [other utilities]
```

## Key Design Decisions

### 1. Callback Architecture
- Services don't depend on `Ircawp` directly
- `Ircawp` provides callbacks to services during initialization
- Loose coupling enables easier testing

### 2. Single Responsibility
- Each service has ONE clear purpose
- Related functionality grouped together
- Easy to understand and modify

### 3. Dependency Injection
- Services receive their dependencies via constructor
- No global state or singletons
- Facilitates testing with mocks

### 4. Backward Compatibility
- Public API unchanged
- `ingestMessage()` still works the same way
- Frontends and plugins unaffected

### 5. Error Isolation
- Each service handles its own errors
- Queue thread protected from crashes
- Graceful degradation

## Comparison: Before vs After

### Before (God Object)
```python
class Ircawp:
    def __init__(self):
        # Initialize everything
        self.queue = Queue()
        self.plugins = load_plugins()
        # ... 50+ more lines

    def extractUrl(self, text):
        # URL extraction logic
        pass

    def processMessagePlugin(self, plugin, message, user_id, media):
        # Plugin execution logic
        pass

    def processMessageText(self, message, user_id, media, aux):
        # Text processing logic
        pass

    def messageQueueLoop(self):
        # 100+ lines of queue processing
        pass

    # ... many more methods
```

### After (Coordinator)
```python
class Ircawp:
    def __init__(self, config):
        # Initialize services
        self.media_manager = MediaManager(...)
        self.url_extractor = URLExtractor(...)
        self.plugin_manager = PluginManager(...)
        self.message_router = MessageRouter(...)

    # Public API (thin wrappers)
    def ingestMessage(self, ...):
        self.message_router.ingest(...)

    def start(self):
        self.message_router.start()
        self.frontend.start()

    # Private callbacks (delegate to services)
    def _process_plugin_message(self, ...):
        return self.plugin_manager.execute_plugin(...)

    def _process_text_message(self, ...):
        message = self.url_extractor.augment_message_with_url(message)
        return self.backend.runInference(...)
```

## Testing Strategy

### Unit Tests (New)
```python
# test_plugin_manager.py
def test_plugin_discovery():
    manager = PluginManager(console, backend, imagegen)
    manager.load_plugins()
    assert manager.has_plugin("weather")

def test_plugin_execution():
    manager = PluginManager(console, backend, imagegen)
    response, media, skip = manager.execute_plugin("weather", "Seattle", "user123")
    assert response is not None
```

### Integration Tests (New)
```python
# test_message_flow.py
def test_full_message_flow():
    # Mock frontend, backend, etc.
    ircawp = Ircawp(test_config)
    ircawp.ingestMessage("Hello", "user123")
    # Assert message processed correctly
```

## Performance Notes

- **No performance degradation**: Callback overhead is negligible
- **Memory**: Slightly more objects, but still minimal
- **Threading**: Same single-threaded queue model
- **Startup**: Slightly faster (cleaner initialization)

## Future Enhancements

Now that services are separated, we can:
1. Add caching to URLExtractor
2. Implement plugin lifecycle hooks in PluginManager
3. Add metrics/monitoring to MessageRouter
4. Make MediaManager async
5. Add plugin sandboxing to PluginManager

Each enhancement can be done in isolation without affecting other services.
