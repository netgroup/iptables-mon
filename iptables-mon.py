import subprocess
import re
import sys
import argparse
import time
import curses
import csv
import os
from datetime import datetime

def get_rules_with_counters(chain):
    result = subprocess.run(['iptables', '-S', chain, '-v', '-t', 'mangle'],
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

def human_readable_number(num, suffix=""):
    units = ['', 'K', 'M', 'G']
    units_len = len(units)
    unit_index = 0
    size = num

    while size >= 1024 and unit_index < units_len - 1:
        size /= 1024
        unit_index += 1

    # Format with 2 decimal places
    return f"{size:.2f} {units[unit_index]}{suffix}"

def main(stdscr, args, rule_command):
    # Clear and setup screen
    stdscr.clear()
    # Hide cursor
    curses.curs_set(0)

    stdscr.addstr(0, 0, f"Monitoring chain '{args.chain}', rule index {args.number}, refresh rate {args.refresh}s")
    stdscr.addstr(1, 0, f"Rule command: {rule_command}")
    if args.file:
        stdscr.addstr(2, 0, f"CSV logging to: {args.file}")
    display_row = "Throughput: "
    row = 4 if args.file else 3

    initial_packets, initial_bytes, _ = get_counters(args.chain, args.number)
    if initial_bytes is None:
        stdscr.addstr(row + 2, 0, "Failed to retrieve counters.")
        stdscr.refresh()
        time.sleep(2)
        return

    # Initialize CSV file if specified
    csv_file = None
    csv_writer = None
    if args.file:
        try:
            csv_file = open(args.file, 'w', newline='')
            csv_writer = csv.writer(csv_file)
            # Write CSV header
            csv_writer.writerow(['timestamp', 'throughput_bps', 'total_bytes', 'packets_diff', 'total_packets'])
            csv_file.flush()  # Ensure header is written immediately
        except IOError as e:
            stdscr.addstr(row + 2, 0, f"Error creating CSV file: {e}")
            stdscr.refresh()
            time.sleep(2)
            return

    # Start from 0 for this measurement session
    total_bytes = 0
    total_packets = 0
    initial_packets_count = initial_packets

    try:
        while True:
            packets, bytes_count, _ = get_counters(args.chain, args.number)
            if bytes_count is None:
                continue

            # Calculate differences
            bytes_diff = bytes_count - initial_bytes
            packets_diff = packets - initial_packets

            # Update totals
            total_bytes += bytes_diff
            total_packets += packets_diff

            # Calculate throughput in bytes per second
            bytes_per_sec = bytes_diff / args.refresh

            # Convert to bits/sec for display
            bits_per_sec = bytes_per_sec * 8
            human_readable_throughput = human_readable_number(bits_per_sec, "bps")
            human_readable_tot_amount = human_readable_number(total_bytes, "B")

            # Display throughput and total bytes
            stdscr.addstr(row, 0, f"{display_row}{human_readable_throughput}   |   Total Bytes: {human_readable_tot_amount}    ")
            stdscr.refresh()

            # Write to CSV if enabled
            if csv_writer:
                timestamp = datetime.now().isoformat()
                csv_writer.writerow([
                    timestamp,
                    bytes_per_sec,  # Throughput in Bps (raw)
                    total_bytes,    # Total bytes (raw)
                    packets_diff,   # Packets difference
                    total_packets   # Total packets
                ])
                csv_file.flush()  # Ensure data is written immediately

            # Update for next iteration
            initial_bytes = bytes_count
            initial_packets = packets

            time.sleep(args.refresh)

    except KeyboardInterrupt:
        pass
    finally:
        # Close CSV file if it was opened
        if csv_file:
            csv_file.close()

if __name__ == "__main__":
    # Argument parsing outside curses to handle help display properly
    parser = argparse.ArgumentParser(description='Monitor iptables rule counters by index.')
    parser.add_argument('-c', '--chain', type=str, default='INPUT',
                        help='Name of the iptables chain (default: INPUT).')
    parser.add_argument('-n', '--number', type=int, required=True,
                        help='Rule number (index) in the chain to monitor.')
    parser.add_argument('-r', '--refresh', type=float, default=1.0,
                        help='Refresh interval in seconds.')
    parser.add_argument('-f', '--file', type=str,
                        help='CSV file path for logging measurements (created in current directory).')
    args = parser.parse_args()

    # Validate refresh interval
    if args.refresh <= 0:
        print("Error: Refresh interval must be greater than zero.")
        sys.exit(1)

    # Validate CSV file path if provided
    if args.file:
        # Ensure we're writing to current directory
        csv_path = os.path.basename(args.file)
        if csv_path != args.file:
            print(f"Warning: File will be created in current directory as '{csv_path}'")
        args.file = csv_path

        # Check if file already exists
        if os.path.exists(args.file):
            response = input(f"File '{args.file}' already exists. Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
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
    if args.file:
        print(f"CSV logging enabled: {args.file}")

    # Run curses wrapper with args and rule_command
    curses.wrapper(main, args, rule_command)
