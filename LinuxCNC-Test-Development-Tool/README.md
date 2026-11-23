# LinuxCNC Test & Development Tool

**Version:** 1.1.0  
**Purpose:** A generic, read-only diagnostics and system-inventory GUI for LinuxCNC installations.

This project is designed to be independent of a particular CNC machine, controller brand, or fieldbus. It can be used on a LinuxCNC PC to inspect host resources and, where the corresponding utilities are installed and accessible, inspect LinuxCNC HAL and EtherCAT status.

## Features

- Dark Qt desktop interface (PySide6)
- Linux host, kernel, distribution and LinuxCNC utility detection
- CPU, RAM and swap monitoring (psutil)
- Hardware inventory using `lscpu`, `lspci`, `lsusb`, and `lsblk`
- Network interfaces, addresses, routes and link statistics (`ip`)
- Ping test helper
- HAL inspection (`halcmd show`)
- EtherCAT master/slave inspection (`ethercat master`, `ethercat slaves`)
- Launches LinuxCNC `latency-histogram` if installed
- Exports text and PDF system reports
- System Health Check for tool availability and RT-kernel indication
- Real-time details: LinuxCNC thread inspection, kernel command line and interrupt snapshot
- Hardware inventory including available Ethernet link details

## Important limitations and safety

- This is a diagnostics tool, not a machine controller.
- It does **not** issue jog, home, spindle, enable, or other motion/output commands.
- HAL and EtherCAT functions require the relevant LinuxCNC/fieldbus utilities and permissions.
- EtherCAT output depends on the installed master utility and its configuration.
- A kernel release string is not proof of real-time performance.
- The application does not invent latency numbers. Use LinuxCNC `latency-histogram` / `latency-test` and follow the LinuxCNC documentation for a meaningful measurement under representative system load.
- Some hardware commands may require `pciutils`, `usbutils`, and `util-linux`.
- The program is not a safety-rated diagnostic instrument.

## Requirements

- Linux (recommended: the same host on which LinuxCNC is installed)
- Python 3.10+
- PySide6
- psutil
- reportlab
- Optional system tools: `linuxcnc`, `halcmd`, `ethercat`, `ip`, `ping`, `lscpu`, `lspci`, `lsusb`, `lsblk`, `ethtool`, `latency-histogram`

On Debian-based systems, optional system utilities can be installed with:

```bash
sudo apt update
sudo apt install python3-venv python3-pip iproute2 iputils-ping pciutils usbutils util-linux ethtool
```

Install LinuxCNC separately using the official LinuxCNC installation instructions for your distribution.

## Install and run

```bash
git clone https://github.com/YOUR-USERNAME/LinuxCNC-Test-Development-Tool.git
cd LinuxCNC-Test-Development-Tool

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

./run.sh
```

If the distro's Python packaging policy prevents installing PySide6 with pip, use a distro package if available, or create the virtual environment with `--system-site-packages` and install the distro's PySide6 package.

## Running diagnostics

Run the application on the LinuxCNC host for the most complete results. Start with **Run full scan**. If a subsystem is not installed or configured, the output will state that it is unavailable.

For real-time latency, use the **Start latency-histogram** button. This launches the LinuxCNC utility in a separate window when it is installed. Let the test run under representative load and interpret the results using LinuxCNC documentation.

## Project structure

```text
LinuxCNC-Test-Development-Tool/
├── src/linuxcnc_tool/
│   ├── __init__.py
│   ├── diagnostics.py
│   └── main.py
├── assets/
├── requirements.txt
├── pyproject.toml
├── run.sh
├── LICENSE
├── .gitignore
└── README.md
```

## GitHub publishing

Create an empty repository on GitHub, then:

```bash
git init
git add .
git commit -m "Initial release: LinuxCNC Test & Development Tool v1.0.0"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/LinuxCNC-Test-Development-Tool.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username and repository URL.

## Roadmap

- More complete LinuxCNC status integration through the LinuxCNC Python API
- Structured EtherCAT PDO and working-counter monitoring for supported masters
- Configurable network interface selection and repeated ping history
- Export to PDF/HTML
- Plugin interface for vendor-specific drives and I/O
- Automated tests and packaging for Debian

## License

This project is licensed under the **GNU General Public License v3.0 only (GPL-3.0-only)**. See the `LICENSE` file for the complete license text.

If you distribute modified versions or binaries of this program, GPLv3 requires you to provide the corresponding source code under the license terms.
## Version 1.1.0 additions

- **Real-time Analyzer:** displays kernel command line, LinuxCNC HAL thread information and an interrupt snapshot. It deliberately does not claim to calculate latency from these sources; use the actual LinuxCNC latency tools for measured jitter.
- **Hardware Scanner:** inventories CPU, PCI, USB, storage and Ethernet link details when the corresponding Linux utilities are installed.
- **System Health Check:** reports whether key utilities are present and gives an indicative RT-kernel check.
- **PDF report export:** creates a portable PDF report using ReportLab.

These checks are diagnostic hints, not a safety certification. EtherCAT state and LinuxCNC thread details depend on the system being configured and the user having permission to query it.
