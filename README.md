```
 __
|__|_______   ____  _____  __  _  ________
|  |\_  __ \_/ ___\ \__  \ \ \/ \/ /\____ \
|  | |  | \/\  \___  / __ \_\     / |  |_) )
|__| |__|    \___  )(____  / \/\_/  |   __/
                 \/      \/         |__|
```

WARNING: This documentation is incomplete, and a constant WIP as new features and changes are rolled in regularly.

# ircawp

An easy to setup OpenAI API (Ollama, Llamacpp, etc) connected IRC bot with easily extensible plugin functionality.

Ircawp is under _heavy development_ and may undergo significant changes. I'm already planning a refactor to make it easier to port to other services, like Discord.

## Why "ircawp"? (or "I want a the golden goose now!")

It's the name of an old bot we had on IRC in the late 1990s. Back then it was a more straightforward bot that would handle channel operations, bans, etc. Then it became a fun Markov chain based babbler that would actually learn from the inputs people would feed it.

Eventually it's "brain" would get corrupted and we'd have to reset it.

Hopefully down the line this LLM-based bot will, too, be able to do something similar where the bot will learn from our bizarre shit and regurgitate even weirder stuff.

But for now, the standard LLM weirdness is good enough for me! ;)

# Features

-   Designed to work on lower-end hardware first. (I personally deploy this on a small AMD Ryzen 5 5625U based media box that sits on a shelf.)
-   Request queue that processes requests in the order received.
-   OpenAI backend (compatiable with Ollama)
-   Easy plugin support to add new `/slash` commands with arguments; return images and text.
    -   Includes weather and a host of chatbot 'personalities' to ask the advice of.
-   Supports media image attachments from Slack for the LLM, or passed to plugins.
-   SDXS image generation (insanely fast!); renders on the CPU by default, but even on that meager Ryzen 5 CPU it can generate about _an image a second_. Sure, they're not fantastic and they're 512x512, but c'mon, man, they're practically free. 😉
-   ZImage Turbo image generation (also fast!), but renders on the GPU -- very high quality.

# Requirements

-   Tested with Python 3.11
-   Deployed on a small box with 64gb of RAM (it's overkill; 32gb is recommended though).

## Installation

-   Run `setup.sh` to setup a venv, install dependencies, create config files, and download models.

-   You'll need to setup a Slack application. Doing that is beyond the scope of this meager README.

-   Modify .env with your Slack API credentials.

## Config

-   The `prompt` string in the config has some interpolated variables available for dynamic prompt content, including `{today}` for today's date. Add your own as needed.

## Usage

-   Run `bot.py` to start the bot. If all your configs and models are in place, and your creds are in `.env`, it should just work.
-   Use `cli.py` to query the bot from the command line. This is useful for debugging and manually testing plugins.

## Message Prefixes

The bot supports several special prefixes at the start of messages to modify behavior:

### `+` - Continue Conversation

Start your message with `+` to continue the previous conversation with full context:

```
user: What's the capital of France?
bot: Paris is the capital of France.

user: +What's its population?
bot: Paris has a population of about 2.1 million people.

user: +Tell me more about it
bot: Paris is known for the Eiffel Tower, the Louvre...
```

**How it works:**
- Every message **without** `+` starts a fresh conversation (the default behavior)
- Messages **with** `+` continue from the previous conversation, maintaining full context
- The conversation is global - anyone in the channel can continue with `+`
- Media attachments (images) are preserved in the conversation history
- Plugin responses are also stored, so you can ask follow-up questions about plugin output

**Examples:**

```
user: Explain quantum physics
bot: [detailed explanation]
user: +Can you simplify that?        [continues - bot remembers the physics topic]
bot: [simpler explanation]

user: What's the weather?             [no + - starts fresh, physics forgotten]
bot: [weather info]
user: +What about tomorrow?           [continues - bot remembers weather context]
bot: [tomorrow's forecast]

user: /weather 06457                  [plugin command]
bot: Weather for Middletown: Broken Clouds at 40F...
user: +What should I wear?            [continues - bot remembers the weather]
bot: I'd recommend layers since it's 40F and cloudy...
```

**Using `+` as a plugin argument:**

You can also use `+` as an argument to a plugin command to use the most recent response as the plugin's input:

```
user: /weather Hartford
bot: Weather for Hartford: Sunny at 72F...

user: /img +                          [generates image using the weather description]
bot: [image of sunny Hartford weather]

user: /summarize https://example.com
bot: [summary of the webpage]

user: /askjesus +                     [asks Jesus about the summary]
bot: [Jesus's perspective on the webpage content]
```

### Other Prefixes

- **`!`** - Skip the system prompt (raw LLM response)
- **`^`** - Prepend the last generated image to your message
- **`@`** - Use an alternate neutral system prompt

## Plugins

The bot responds to `/command` style slash commands, if the first character is a slash. These are defined in the `config.yml` file, with the appropriate Python modules implementing them placed in the `plugins` directory.

Execute commands like so: `@ircawp /mycommand query value`.

A base set of plugins are included, including but not limited to:

-   `/?` and `/help` - dumps all the registered slash commands
-   `/reverse` - reverses the text you give it (a trivial demo!)
-   `/weather` - queries [OpenWeatherMap](https://openweathermap.org) for current weather conditions. Supports ZIP codes, city names, and "City, State" format (e.g. `@ircawp /weather 90210` or `@ircawp /weather Hartford, CT`). Can optionally generate a weather scene image.
-   `/askjesus` - ask Jesus for advice (e.g. `@ircawp /askjesus should I buy a new car?`) -- and other characters!
-   `/summarize` - summarizes a webpage given a URL
-   `/geolocate` - runs rudimentary a geolocation prompt on a provided image

### Authoring New Plugins

Creating a plugin is straightforward. Here's the basic structure:

```python
from app.backends.Ircawp_Backend import Ircawp_Backend
from app.media_backends.MediaBackend import MediaBackend
from .__PluginBase import PluginBase

def my_function(
    prompt: str,
    media: list,
    backend: Ircawp_Backend,
    media_backend: MediaBackend = None,
) -> tuple[str, str, bool, dict]:
    """
    Your plugin logic here.

    Returns:
        tuple: (response_text, media_path, skip_imagegen, metadata_dict)
    """
    response = f"You said: {prompt}"
    return response, "", True, {}

plugin = PluginBase(
    name="My Plugin",
    description="What shows up in /help output",
    triggers=["mycommand", "mycmd"],  # /mycommand or /mycmd will trigger this
    system_prompt="",
    emoji_prefix="🎯",
    msg_empty_query="No input provided",
    msg_exception_prefix="MY PLUGIN ERROR",
    main=my_function,
    use_imagegen=False,
    prompt_required=True,
    media_required=False,
)
```

**Key components:**

- **main function**: Must accept `(prompt, media, backend, media_backend)` and return `(response_text, media_path, skip_imagegen, metadata_dict)`
- **triggers**: List of command names (without the `/`) that invoke your plugin
- **description**: Displayed in `/help` output
- **prompt_required**: Set to `False` if the plugin works without arguments
- **media_required**: Set to `True` if the plugin needs an image attachment
- **use_imagegen**: Set to `True` if you want automatic image generation for the response

All `*.py` files in `/app/plugins/` are automatically loaded at runtime. See [8ball.py](app/plugins/8ball.py), [weather.py](app/plugins/weather.py), or other plugins for complete examples.

## Notes

-   You will need to judge for yourself whether your hardware available is good enough to run an LLM chat bot. By default this runs on the CPU, and I get some reasonable speeds. But you have to understand that this is a very computationally expensive process and it is not _streaming_ the response. So you have to wait for the **entire inference** to complete before the bot posts it back to the channel. This can be between a few seconds, or a few minutes, depending on your hardware and the size of the model you're using.

-   This bot was designed for **small-scale** use by a handful of people. It will queue up requests and respond to them in order. If you have a large channel with a lot of people eager to talk to the bot, you may want to consider a different solution. Or maybe not. I don't know. I'm not your dad. (Unless you're my kid, in which case, I'm going out for a pack of cigs. Don't wait up.)

-   This software could probably be written much more efficiently, faster, etc. Feel free to fork; maybe ping me if you do and maybe I'll steal some of your ideas.

-   This software is provided as-is, with no warranty or guarantee of any kind. Use at your own risk.

## Contributing

-   Bug tickets are fine, but this project is not currently accepting outside contributions. Ideas are fine to run by me, as long as you don't expect me to agree and implement it. I mean, if it's good, I might. I already implemented some surprise ideas last night. Who knows?

## License

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

&copy; Network47.org, 2025, 2026
