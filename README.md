# Control Freak Edidio Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom%20Repository-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
## Overview

The Control Freak Edidio Integration for Home Assistant brings seamless control of your DALI and DMX lighting systems connected via a Control Freak Edidio Gateway/Controller directly into your Home Assistant instance. This integration supports a wide range of lighting protocols, allowing you to manage various light types, from simple white lights to complex RGBW and tunable white fixtures.

## Features

* **Broad Protocol Support:**
    * DALI (Digital Addressable Lighting Interface):
        * DALI (Dimming/White)
        * DALI RGB
        * DALI RGBW
        * DALI DT8 Color Temperature (CCT)
        * DALI DT8 XY Color
    * DMX (Digital Multiplex):
        * DMX White
        * DMX RGB
        * DMX RGBW
* **TLS Support:** Optionally connect to your eDIDIO controller over a secure TLS connection (port 443) in addition to the standard plain TCP connection (port 23).
* **Individual Light Control:** Map individual DALI addresses or DMX channels to Home Assistant light entities.
* **Brightness Control:** Adjust brightness for all supported light types.
* **Color Control:** Full RGB, RGBW, and XY color control for compatible lights.
* **Color Temperature Control:** Adjust color temperature for DALI DT8 CCT lights (2000K–6500K).
* **Line Support:** Specify the DALI/DMX line for multi-line Edidio controllers.
* **Stable Entity IDs:** Each light is assigned a stable UUID at creation time, so entities persist correctly across restarts and reconfiguration.
* **Auto-Reconnect:** If the connection to the controller is lost, the integration will automatically attempt to reconnect on the next update cycle.
* **Seamless Integration:** Lights appear as standard Home Assistant light entities, usable in automations, scenes, and dashboards.

## Prerequisites

Before you begin, ensure you have the following:

1.  **Home Assistant:** A running Home Assistant instance (version X.Y.Z or later is recommended).
2.  **Control Freak Edidio Gateway/Controller:** An Edidio controller (e.g., eDS10, eDMX Gateway, etc.) connected to your network.
3.  **Network Access:** Your Home Assistant instance must be on the same network as your Edidio controller and able to reach its IP address and port.
4.  **Edidio Configuration:** Your DALI/DMX lights must be properly wired and configured on your Edidio controller, with their addresses and lines known.
5.  **Python Library:** The `edidio-control-py` library (v0.2.0+) is used internally. It will be installed automatically by Home Assistant.

## Installation

### A. Via HACS (Recommended)

HACS (Home Assistant Community Store) simplifies the installation and updates of custom components.

1.  **Add this repository to HACS:**
    * In Home Assistant, navigate to **HACS** (if you don't have HACS, follow [these instructions](https://hacs.xyz/docs/setup/download)).
    * Go to **Integrations**.
    * Click the three dots in the top right corner and select **Custom repositories**.
    * In the "Repository" field, paste the GitHub repository URL: `https://github.com/CreativeLightingAdmin/home-assistant-control-freak-edidio`.
    * Select "Integration" as the "Category".
    * Click **Add**.
2.  **Install the Integration:**
    * Search for "Control Freak Edidio" in the HACS Integrations section.
    * Click on the "Control Freak Edidio" integration.
    * Click **Download** and select the latest version.
    * Restart your Home Assistant instance.

### B. Manual Installation (Advanced)

1.  **Download the Integration:**
    * Go to the `https://github.com/CreativeLightingAdmin/home-assistant-control-freak-edidio` of this repository.
    * Download the source code archive (e.g., `Source code (zip)`).
    * Extract the contents.
    * Locate the `custom_components/control_freak_edidio` folder.
2.  **Copy to Home Assistant:**
    * Copy the entire `control_freak_edidio` folder into your Home Assistant's `config/custom_components/` directory.
    * The final path should look like: `your_ha_config_dir/custom_components/control_freak_edidio/`.
3.  **Restart Home Assistant:**
    * Restart your Home Assistant instance for the changes to take effect.

## Configuration

The Control Freak Edidio integration is configured entirely via the Home Assistant UI.

### Initial Setup

1.  **Add the Integration:**
    * After restarting Home Assistant, go to **Settings** > **Devices & Services** > **Integrations**.
    * Click the **+ ADD INTEGRATION** button.
    * Search for "Control Freak Edidio" and select it.

2.  **Enter Controller Details:**
    * You will be prompted to enter the connection details for your Control Freak Edidio Gateway:
        * **Host:** The IP address of your controller (e.g., `192.168.1.10`).
        * **Use TLS:** Enable this to connect over a secure TLS connection. Leave disabled for a plain TCP connection.
        * **Port:** The port to connect on. Default is `23` (plain TCP) or `443` (TLS). Change this only if your controller is configured to use a non-standard port.
    * Click **Submit**.

3.  **Define Your Lights:**
    * You will be presented with a menu to add lights or finish setup.
    * Click **Add a light** for each light you want to add. For each light, provide:
        * **Name:** The friendly name that will appear in Home Assistant (e.g., `Living Room Spot 1`).
        * **DALI/DMX Address:** The primary address of the light on the DALI/DMX bus. For multi-channel lights (RGB, RGBW), this is the address of the first channel; subsequent channels are addressed sequentially.
        * **Protocol:** Select the correct protocol for your light from the dropdown:
            * `DALI White` — DALI DT0/DT6 dimmable white
            * `DALI RGB` — 3-channel DALI RGB (uses 3 consecutive addresses)
            * `DALI RGBW` — 4-channel DALI RGBW (uses 4 consecutive addresses)
            * `DALI DT8 CCT` — DALI DT8 Tunable White / Color Temperature
            * `DALI DT8 XY` — DALI DT8 XY Color
            * `DMX White` — Single-channel DMX dimmable white
            * `DMX RGB` — 3-channel DMX RGB (uses 3 consecutive channels)
            * `DMX RGBW` — 4-channel DMX RGBW (uses 4 consecutive channels)
        * **Line:** The DALI/DMX line number (defaults to `1`).
    * When you are finished adding lights, click **Finish setup**.

Your lights will now appear in Home Assistant under **Settings** > **Devices & Services** > **Entities**.

### Reconfiguring After Setup (Options Flow)

You can modify the integration at any time without re-adding it:

1.  Go to **Settings** > **Devices & Services** > **Integrations**.
2.  Find the **Control Freak Edidio** integration and click **Configure**.
3.  You will see a menu with two options:
    * **Reconfigure connection (IP / Port / TLS):** Update the host address, port, or toggle TLS on/off.
    * **Manage lights:** Add new lights, edit existing lights (name, address, protocol, line), or remove lights. Removing a light here will also clean up its entity from the Home Assistant entity registry.

### Example Configuration (YAML - for reference only)

*(**Note:** The primary configuration method is via the UI. This YAML snippet represents the data structure the UI config flow creates internally — do NOT add this directly to `configuration.yaml`.)*

```yaml
# Example of the data structure created by the UI config flow
control_freak_edidio:
  - host: 192.168.1.10
    port: 23
    tls: false
    lights:
      - name: Living Room Main Light
        address: 1
        line: 1
        protocol: DALI White
      - name: Kitchen RGB Strip
        address: 10  # Starting address for R channel
        line: 1
        protocol: DALI RGB
      - name: Bedroom CCT Downlight
        address: 5
        line: 2
        protocol: DALI DT8 CCT
      - name: Outdoor DMX Flood
        address: 1  # Starting DMX channel
        line: 1
        protocol: DMX RGBW
```

## Troubleshooting

* **Integration Not Found:**
    * Ensure you have restarted Home Assistant after installation.
    * Check that the `control_freak_edidio` folder is directly under `custom_components`.

* **Lights Not Appearing/Working:**
    * **Check Controller Connectivity:** Verify your Edidio controller's IP address and port are correct and that Home Assistant can reach it. Try pinging the IP from your Home Assistant server.
    * **Check TLS Setting:** If you enabled TLS, ensure your controller supports TLS on the configured port (default `443`). If using plain TCP, ensure TLS is disabled and port is set to `23`.
    * **Verify Edidio Configuration:** Double-check that your lights are correctly configured and working on the Edidio controller itself. Ensure the addresses, lines, and protocols you entered match your Edidio setup.
    * **Enable Debug Logging:** Add the following to your `configuration.yaml` to get more detailed logs:
        ```yaml
        logger:
          default: info
          logs:
            custom_components.control_freak_edidio: debug
            edidio_control_py: debug  # For verbose communication library logs
        ```
        Then restart Home Assistant and check the logs (**Settings** > **System** > **Logs**).

* **Entity Unavailable After Restart:**
    * The integration will attempt to reconnect automatically on the next polling cycle. If the controller is unreachable, entities will show as unavailable until connectivity is restored.

## Known Issues / Limitations

* The integration assumes sequential addressing for multi-channel lights (RGB, RGBW) starting from the base address.
* TLS connections currently do not validate the server certificate (suitable for self-signed certificates on local network controllers).
* *(List any other known bugs, limitations, or features not yet implemented.)*

## Contributing

Contributions are welcome! If you find a bug, have a feature request, or want to contribute code, please:

1.  **Open an Issue:** Describe the bug or feature request in detail.
2.  **Fork the Repository:** Create a fork of this repository.
3.  **Create a Branch:** Create a new branch for your changes (e.g., `feature/my-new-feature` or `fix/bug-description`).
4.  **Make Changes:** Implement your changes and write tests.
5.  **Submit a Pull Request:** Open a pull request to the `main` branch of this repository.

## Acknowledgements

This integration relies on the [`edidio-control-py`](https://github.com/your-username/edidio-control-py-repo) Python library for communication with the Control Freak Edidio Gateway.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
