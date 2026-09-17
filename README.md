# Discord Server Bot

# Overview

This is a lightweight, self-hosted Discord bot made for monitoring a Minecraft server and the machine it's running on.

It tracks hardware usage, checks whether the Minecraft server is online or offline, and uploads new Minecraft logs to Discord as `.txt` files.

The bot is mainly made for keeping an eye on a Minecraft server without having to constantly SSH into the machine.

This project is mostly vibe coded. It's my first real Python project since I started learning Python around 1–3 months ago, so don't expect the code to be perfect.

# Features

* Minecraft server online/offline detection
* Server status notifications
* CPU usage monitoring
* Per-core CPU usage monitoring
* CPU temperature monitoring
* RAM usage monitoring
* Storage usage monitoring
* Battery and power status monitoring
* System uptime monitoring
* Automatic Minecraft log checking
* Incremental Minecraft log uploads
* Discord `.txt` log uploads
* Configurable Discord channels
* Configurable Minecraft server address and port
* Configurable Minecraft log location

The bot checks the Minecraft server, hardware, and logs every 5 minutes.

The log system only uploads new log lines instead of repeatedly uploading the entire `latest.log`.

# Requirements

* Linux
* Python 3
* pip
* Python virtual environment support
* `lm-sensors` for hardware temperature monitoring
* A Discord bot
* A Minecraft server for the Minecraft monitoring features

Python dependencies are listed in [`requirements.txt`](requirements.txt) and a installation guide!.

# Confi
