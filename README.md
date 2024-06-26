```
 __
|__|_______   ____  _____  __  _  ________
|  |\_  __ \_/ ___\ \__  \ \ \/ \/ /\____ \
|  | |  | \/\  \___  / __ \_\     / |  |_) )
|__| |__|    \___  )(____  / \/\_/  |   __/
                 \/      \/         |__|
```

# ircawp

An easy to setup Llama.cpp-based IRC bot with easily extensible plugin functionality.

Ircawp is under _heavy development_ and may undergo significant changes. I'm already planning a refactor to make it easier to port to other services, like Discord.

## Why "ircawp"? (or "I want a the golden goose now!")

It's the name of an old bot we had on IRC in the late 1990s. Back then it was a more straightforward bot that would handle channel operations, bans, etc. Then it
became a fun Markov chain based babbler that would actually learn from the inputs people would feed it.

Eventually it's "brain" would get corrupted and we'd
have to reset it.

Hopefully down the line this LLM-based bot will, too, be able to do something similar where the bot will learn from our bizarre shit and regurgitate even weirder stuff.

But for now, the standard LLM weirdness is good enough for me! ;)

# Features

-   Designed to work on lower-end hardware first. (I personally deploy this on a small AMD Ryzen 5 5625U based media box that sits on a shelf.)
-   Llamacpp (gguf models) and Ollama (preferred) backends
-   Easy plugin support to add new `/slash` commands with arguments; return images and text.
    -   Includes weather and a host of chatbot 'personalities' to ask the advice of.
-   Request queue that processes requests in the order received
-   SDXS image generation (insanely fast!); renders on the CPU by default, but even on that meager Ryzen 5 CPU it can generate about _an image a second_. Sure, they're not fantastic and they're 512x512, but c'mon, man, they're practically free. 😉

# Requirements

-   Tested with Python 3.11
-   Deployed on a small box with 32gb of RAM but that was apparently overkill.

## Installation

-   Run `setup.sh` to setup a venv, install dependencies, create config files, and download models.

-   You will be prompted before the ~11 gig download begins.

    -   Or bring your own GGML-format model and add it to the `config.json` file.

-   You'll need to setup a Slack application. Doing that is beyond the scope of this meager README.

-   Modify .env with your Slack API credentials.

## Config

-   The `prompt` string in the config has some interpolated variables available for dynamic prompt content, including `{today}` for today's date. Add your own as needed.

## Usage

-   Run `bot.py` to start the bot. If all your configs and models are in place, and your creds are in `.env`, it should just work.
-   Use `cli.py` to query the bot from the command line. This is useful for debugging and manually testing plugins.

## Plugins

The bot responds to `/command` style slash commands, if the first character is a slash. These are defined in the config.json file, with the appropriate Python modules implementing them placed in the `plugins` directory.

Execute commands like so: `@ircawp /mycommand query value`.

A base set of plugins are included, including but not limited to:

-   `/?` and `/help` - dumps all the registered slash commands
-   `/reverse` - reverses the text you give it (a trivial demo!)
-   `/weather` - queries [wttr.in](https://wttr.in) for the weather in the location you give it (e.g. `@ircawp /weather 90210`)
-   `/askjesus` - ask Jesus for advice (e.g. `@ircawp /askjesus should I buy a new car?`) -- and other characters!
-   ~~`/summary` - uses langchain and a smaller, faster model to summarize the website you give it (e.g. `@ircawp /summary https://www.example.com`)~~ (Disabled for now.)

### Authoring New Plugins

#### This section is outdated -- check the examples; it's easier than ever.
-   Follow the examples in the `/plugins` directory as a template for rolling your own.
    -   `triggers` are a list of `/cmd` triggers (without the slash) that will cause it to be called.
    -   The `description` is what it will show up as in the `/help` output.
    -   ~~The primary entry point is a method called `execute` that takes signature of `(query: str, backend: BaseBackend)` and returns a string that is passed back to the channel.~~
    -   Everything else is up to you.
-   All of the `*.py` files in the `/plugins` directory will be loaded and registered at runtime.

## Notes

-   You will need to judge for yourself whether your hardware available is good enough to run an LLM chat bot. By default this runs on the CPU, and I get some reasonable speeds. But you have to understand that this is a very computationally expensive process and it is not _streaming_ the response. So you have to wait for the **entire inference** to complete before the bot posts it back to the channel. This can be between a few seconds, or a few minutes, depending on your hardware and the size of the model you're using.

-   This bot was designed for **small-scale** use by a handful of people. It will queue up requests and respond to them in order. If you have a large channel with a lot of people eager to talk to the bot, you may want to consider a different solution. Or maybe not. I don't know. I'm not your dad. (Unless you're my kid, in which case, I'm going out for a pack of cigs. Don't wait up.)

-   This software could probably be written much more efficiently, faster, etc. Feel free to fork; maybe ping me if you do and maybe I'll steal some of your ideas.

-   This software is provided as-is, with no warranty or guarantee of any kind. Use at your own risk.

## Contributing

-   Bug tickets are fine, but this project is not currently accepting outside contributions. Ideas are fine to run by me, as long as you don't expect me to agree and implement it. I mean, if it's good, I might. I already implemented some surprise ideas last night. Who knows?

## License

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

&copy; Network47.org, 2024
