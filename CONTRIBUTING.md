# Contributing to Twitter Monitor Bot

## 🐛 Known Issues & Server Deployment

### ⚠️ Critical: Zombie Processes on Linux/Debian Servers

There is a known issue when running this bot on Linux servers (e.g., Debian, Ubuntu).

**The Problem:**
When the bot script is stopped or when a Playwright session is closed, the underlying browser processes (Chromium) may not terminate correctly.
- PIDs (Process IDs) remain active in the background.
- These "zombie" processes continue to consume memory and CPU.
- Over time, this leads to server resource saturation, causing the script to crash or the server to become unresponsive.

**Current Workarounds:**
1.  **Manual Cleanup:** Regularly check for and kill orphaned Chrome processes.
    ```bash
    pkill -f chrome
    ```
2.  **Docker (Recommended):** Running the bot inside a Docker container can help isolate processes and ensure they are all killed when the container stops.
3.  **Supervisor/Systemd:** Configure your process manager to send `SIGKILL` to the entire process group upon stopping the service.

**Help Needed:**
We are looking for a robust solution to ensure graceful and complete termination of all Playwright browser contexts on Linux environments. If you have experience with `asyncio` signal handling or Playwright process management on Linux, please submit a Pull Request!

## 🛠️ Development Guidelines

1.  **Fork** the repository
2.  **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3.  **Make** your changes
4.  **Test** thoroughly (especially on different OS if possible)
5.  **Commit** your changes (`git commit -m 'Add amazing feature'`)
6.  **Push** to the branch (`git push origin feature/amazing-feature`)
7.  **Open** a Pull Request
