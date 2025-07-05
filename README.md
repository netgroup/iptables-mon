# iptables Rule Monitor

A command-line tool to monitor iptables rules by index, displaying real-time throughput and total bytes transferred.

---

## Overview

This script allows you to monitor specific iptables rules within a chain (default: `INPUT`) by specifying the rule's index. It dynamically fetches packet and byte counters for the chosen rule and displays throughput and total bytes transferred in real-time, updating at a user-defined interval.

---

## Usage

```bash
python3 iptables_monitor.py [options]
```

## Arguments

### Required Arguments

- `-n`, `--number` **(int)**  
  **Rule number (index)** in the specified chain to monitor.  
  **(Mandatory)**

### Optional Arguments

- `-c`, `--chain` **(str)**  
  **Name of the iptables chain** to monitor (default: `INPUT`).  
  **Example:** `FORWARD`, `OUTPUT`, or custom chain name.

- `-r`, `--refresh` **(float)**  
  **Refresh interval in seconds** between updates (default: `1.0`).  
  Must be a positive number.

---

## Example

Monitor the 3rd rule in the `FORWARD` chain, refreshing every 2 seconds:

```bash
python3 iptables_monitor.py -c FORWARD -n 3 -r 2
```

---

## Notes

- Make sure you have appropriate permissions to run `iptables` commands (typically root or with sudo).
- The script uses `curses` for a terminal-based UI.
- Press `Ctrl+C` to exit the monitor gracefully.

---

## Validation of Arguments

- The script checks that:

  - The refresh interval (`-r`) is greater than zero.
  - The specified rule number (`-n`) exists within the chain.

- If invalid, it will display an error message and exit.

---

## Dependencies

- Python 3
- Standard libraries: `subprocess`, `re`, `sys`, `argparse`, `time`, `curses`

---

## License

This project is provided as-is. Ensure you have the necessary permissions to run `iptables` commands on your system.

---

*Note:* For detailed usage, run:

```bash
python3 iptables_monitor.py --help
```
