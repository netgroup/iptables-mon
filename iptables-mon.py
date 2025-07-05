import subprocess
import re
import sys
import argparse
import time
import curses

def get_rules_with_counters(chain):
    result = subprocess.run(['iptables', '-S', chain, '-v'],
                            capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    rules = []

    for idx, line in enumerate(lines):
        c_match = re.search(r"\-c\s+(\d+)\s+(\d+)", line)
        if c_match:
            packets = int(c_match.group(1))
            bytes_count = int(c_match.group(2))
            rules.append({
                'index': idx + 1,
                'line': line,
                'packets': packets,
                'bytes': bytes_count,
                'rule_str': line
            })

    return rules

def get_counters(chain, rule_index):
    rules = get_rules_with_counters(chain)

    if 1 <= rule_index <= len(rules):
        rule = rules[rule_index - 1]
        return rule['packets'], rule['bytes'], rule['line']

    return None, None, None

def human_readable_bytes_per_sec(bytes_per_sec):
    units = ['bps', 'kbps', 'mbps', 'gbps']
    units_len = len(units)
    size = bytes_per_sec
    unit_index = 0

    while size >= 1024 and unit_index < units_len - 1:
        size /= 1024
        unit_index += 1

    # Format with 2 decimal places
    return f"{size:.2f} {units[unit_index]}"

def main(stdscr, args, rule_command):
    # Clear and setup screen
    stdscr.clear()
    # Hide cursor
    curses.curs_set(0) 

    stdscr.addstr(0, 0, f"Monitoring chain '{args.chain}', rule index {args.number}, refresh rate {args.refresh}s")
    stdscr.addstr(1, 0, f"Rule command: {rule_command}")
    display_row = "Throughput: "
    stdscr.addstr(3, 0, f"{display_row}")
    row = 3

    initial_packets, initial_bytes, _ = get_counters(args.chain, args.number)
    if initial_bytes is None:
        stdscr.addstr(5, 0, "Failed to retrieve counters.")
        stdscr.refresh()
        time.sleep(2)
        return

    try:
        while True: 
            packets, bytes_count, _ = get_counters(args.chain, args.number)
            if bytes_count is None:
                continue

            # Convert bytes difference to bits
            bytes_diff = bytes_count - initial_bytes
            bits_per_sec = (bytes_diff * 8) / args.refresh
            human_readable = human_readable_bytes_per_sec(bits_per_sec)

            # overwrite previous value
            stdscr.addstr(row, len(display_row), f"{human_readable}   ")
            stdscr.refresh()

            # Update for next iteration
            initial_bytes = bytes_count
            initial_packets = packets

            time.sleep(args.refresh)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    # Argument parsing outside curses to handle help display properly
    parser = argparse.ArgumentParser(description='Monitor iptables rule counters by index.')
    parser.add_argument('-c', '--chain', type=str, default='INPUT',
                        help='Name of the iptables chain (default: INPUT).')
    parser.add_argument('-n', '--number', type=int, required=True,
                        help='Rule number (index) in the chain to monitor.')
    parser.add_argument('-r', '--refresh', type=float, default=1.0,
                        help='Refresh interval in seconds.')
    args = parser.parse_args()

    # Validate refresh interval
    if args.refresh <= 0:
        print("Error: Refresh interval must be greater than zero.")
        sys.exit(1)

    # Verify that rule number is valid before starting curses
    rules = get_rules_with_counters(args.chain)
    if not rules:
        print(f"No rules found in chain '{args.chain}'.")
        sys.exit(1)
    if args.number < 1 or args.number > len(rules):
        parser.print_help()
        print(f"\nError: Rule number {args.number} is invalid. Must be between 1 and {len(rules)}.")
        sys.exit(1)

    # Get the specific rule command
    rule_command = rules[args.number - 1]['line']
    print(f"Selected Rule {args.number}: {rule_command}")

    # Run curses wrapper with args and rule_command
    curses.wrapper(main, args, rule_command)
