```
 __
|__|_______   ____  _____  __  _  ________
|  |\_  __ \_/ ___\ \__  \ \ \/ \/ /\____ \
|  | |  | \/\  \___  / __ \_\     / |  |_) )
|__| |__|    \___  )(____  / \/\_/  |   __/
                 \/      \/         |__|
```

# ircawp

An easy to setup Llama.cpp-based IRC bot with easily extensible functionality.

## Why "ircawp"? (or "I want a the golden goose now!")

It's the name of an old bot we had on IRC in the late 1990s. Back then it was a more straightforward bot that would handle channel operations, bans, etc. Then it
became a fun Markov chain based babbler that would actually learn from the inputs people would feed it.

Eventually it's "brain" would get corrupted and we'd
have to reset it.

Hopefully down the line this LLM-based bot will, too, be able to do something similar where the bot will learn from our bizarre shit and regurgitate even weirder stuff.

But for now, the standard LLM weirdness is good enough for me! ;)

# Requirements

-   Tested with Python 3.11
-   Deployed on a small box with 32gb of RAM but that was apparently overkill.

## Installation

-   Run `setup.sh` to setup a venv, install dependencies, create config files, and download models.

-   You will be prompted before the ~11 gig download begins.

    -   Or bring your own GGML-format model and add it to the `config.json` file.

-   Modify .env with your Slack API credentials

## Usage

-   Run `bot.py` to start the bot. If all your configs and models are in place, and your creds are in `.env`, it should just work.

## Functions

The bot responds to `/command` style slash commands, if the first character is a slash. These are defined in the config.json file, with the appropriate Python modules implementing them placed in the `functions` directory.

Execute commands like so: `@ircawp /mycommand query value`.

A couple are included just to get you started:

-   `/?` and `/help` - dumps all the registered slash commands
-   `/reverse` - reverses the text you give it; a trivial demo
-   `/summary` - uses langchain and a smaller, faster model to summarize the website you give it (e.g. `@ircawp /summary https://www.example.com`)

### Adding New Functions

-   Follow the examples in the `functions` directory as a template for rolling your own.
-   Add the function to the `config.json` file, and restart the bot.

## Notes

-   You will need to judge for yourself whether your hardware available is good enough to run an LLM a chat bot. By default this runs on the CPU, and I get some reasonable speeds. But you have to understand that this is a very computationally expensive process and it is not _streaming_ the response. So you have to wait for the entire inference to complete before the bot posts it back to the channel. This can be between a few seconds, or a few minutes, depending on your hardware and the size of the model you're using.

-   This bot was designed for **small-scale** use by a handful of people. It will queue up requests and respond to them in order. If you have a large channel with a lot of people eager to talk to the bot, you may want to consider a different solution. Or maybe not. I don't know. I'm not your dad. (Unless you're my kid, in which case, I'm going out for a pack of cigs. Don't wait up.)

- This software could probably be written much more efficiently, faster, etc. Feel free to fork; maybe ping me if you do and maybe I'll steal some of your ideas.

-   This software is provided as-is, with no warranty or guarantee of any kind. Use at your own risk.

## Contributing

-   Bug tickets are fine, but this project is not currently accepting outside contributions.

## License

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

&copy; Network47.org, 2023
