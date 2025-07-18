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
* **Individual Light Control:** Map individual DALI addresses or DMX channels to Home Assistant light entities.
* **Brightness Control:** Adjust brightness for all supported light types.
* **Color Control:** Full RGB, RGBW, and XY color control for compatible lights.
* **Color Temperature Control:** Adjust color temperature for DALI DT8 CCT lights.
* **Line Support:** Specify the DALI/DMX line for multi-line Edidio controllers.
* **Seamless Integration:** Lights appear as standard Home Assistant light entities, usable in automations, scenes, and dashboards.

## Prerequisites

Before you begin, ensure you have the following:

1.  **Home Assistant:** A running Home Assistant instance (version X.Y.Z or later is recommended).
2.  **Control Freak Edidio Gateway/Controller:** An Edidio controller (e.g., eDS10, eDMX Gateway, etc.) connected to your network.
3.  **Network Access:** Your Home Assistant instance must be on the same network as your Edidio controller and able to reach its IP address and port.
4.  **Edidio Configuration:** Your DALI/DMX lights must be properly wired and configured on your Edidio controller, with their addresses and lines known.
5.  **Python Library:** The `edidio-control-py` library is used internally. It will be installed automatically by Home Assistant.

## Installation

### A. Via HACS (Recommended)

HACS (Home Assistant Community Store) simplifies the installation and updates of custom components.

1.  **Add this repository to HACS:**
    * In Home Assistant, navigate to **HACS** (if you don't have HACS, follow [these instructions](https://hacs.xyz/docs/setup/download)).
    * Go to **Integrations**.
    * Click the three dots in the top right corner and select **Custom repositories**.
    * In the "Repository" field, paste your GitHub repository URL: `YOUR_GITHUB_USERNAME/YOUR_REPO_NAME` (e.g., `myusername/control_freak_edidio`).
    * Select "Integration" as the "Category".
    * Click **Add**.
2.  **Install the Integration:**
    * Search for "Control Freak Edidio" in the HACS Integrations section.
    * Click on the "Control Freak Edidio" integration.
    * Click **Download** and select the latest version.
    * Restart your Home Assistant instance.

### B. Manual Installation (Advanced)

1.  **Download the Integration:**
    * Go to the [latest release](YOUR_GITHUB_REPO_URL/releases/latest) of this repository.
    * Download the source code archive (e.g., `Source code (zip)`).
    * Extract the contents.
    * Locate the `custom_components/control_freak_edidio` folder.
2.  **Copy to Home Assistant:**
    * Copy the entire `control_freak_edidio` folder into your Home Assistant's `config/custom_components/` directory.
    * The final path should look like: `your_ha_config_dir/custom_components/control_freak_edidio/`.
3.  **Restart Home Assistant:**
    * Restart your Home Assistant instance for the changes to take effect.

## Configuration

The Control Freak Edidio integration is configured via the Home Assistant UI.

1.  **Add the Integration:**
    * After restarting Home Assistant, go to **Settings** > **Devices & Services** > **Integrations**.
    * Click the **+ ADD INTEGRATION** button.
    * Search for "Control Freak Edidio" and select it.
2.  **Enter Controller Details:**
    * You will be prompted to enter the **IP Address** and **Port** of your Control Freak Edidio Gateway.
    * **IP Address:** `[e.g., 192.168.1.10]`
    * **Port:** `[e.g., 5000]` (default is often 5000)
    * Click **Submit**.
3.  **Define Your Lights:**
    * Next, you will define each light entity. Click **+ ADD LIGHT** for each light you want to add.
    * For each light, you will need to provide:
        * **Light ID:** A unique identifier for this light (e.g., `living_room_spot_1`). This should be unique across all lights for this integration instance.
        * **Light Name:** The friendly name that will appear in Home Assistant (e.g., `Living Room Spot 1`).
        * **DALI/DMX Address (or starting address/channel):** The primary address of the light on the DALI/DMX bus.
        * **Line:** The DALI/DMX line number (defaults to 1 if not specified).
        * **Protocol:** Select the correct protocol for your light from the dropdown. Available options:
            * `DALI_WHITE` (for DALI DT0/DT6 dimmable white lights)
            * `DALI_RGB` (for 3-channel DALI RGB)
            * `DALI_RGBW` (for 4-channel DALI RGBW)
            * `DALI_DT8_CCT` (for DALI DT8 Tunable White / Color Temperature)
            * `DALI_DT8_XY` (for DALI DT8 XY Color)
            * `DMX_WHITE` (for single-channel DMX dimmable white)
            * `DMX_RGB` (for 3-channel DMX RGB)
            * `DMX_RGBW` (for 4-channel DMX RGBW)
    * Click **Submit** after defining each light.
    * When you are finished adding all lights, click **Finish**.

Your lights should now appear in Home Assistant under **Settings** > **Devices & Services** > **Entities**.

### Example Configuration (YAML - for reference, if supported)

*(**Note:** The primary configuration method is via the UI. This YAML example is for advanced users or debugging, and represents the data stored by the UI. Do NOT add this directly to `configuration.yaml` unless you've specifically designed your component to load from YAML alongside the UI config flow, which is typically not recommended for new integrations.)*

```yaml
# This is an example of the data structure the UI config flow creates
# Do NOT place this directly in configuration.yaml unless instructed by advanced documentation
control_freak_edidio:
  - host: 192.168.1.10
    port: 5000
    lights:
      - id: living_room_main
        name: Living Room Main Light
        address: 1
        line: 1
        protocol: DALI_WHITE
      - id: kitchen_rgb_strip
        name: Kitchen RGB Strip
        address: 10 # Starting address for R channel
        line: 1
        protocol: DALI_RGB
      - id: bedroom_cct_downlight
        name: Bedroom CCT Downlight
        address: 5 # DALI Short Address
        line: 2
        protocol: DALI_DT8_CCT
      - id: outdoor_dmx_flood
        name: Outdoor DMX Flood
        address: 1 # Starting DMX channel
        line: 1 # DMX line
        protocol: DMX_RGBW
```
## Troubleshooting

* **Integration Not Found:**
    * Ensure you have restarted Home Assistant after installation.
    * Check that the `control_freak_edidio` folder is directly under `custom_components`.
* **Lights Not Appearing/Working:**
    * **Check Controller Connectivity:** Verify your Edidio controller's IP address and port are correct and that Home Assistant can reach it. Try pinging the IP from your Home Assistant server.
    * **Verify Edidio Configuration:** Double-check that your lights are correctly configured and working on the Edidio controller itself. Ensure the addresses, lines, and protocols you entered match your Edidio setup.
    * **Enable Debug Logging:** Add the following to your `configuration.yaml` to get more detailed logs:
        ```yaml
        logger:
          default: info
          logs:
            custom_components.control_freak_edidio: debug
            edidio_control_py: debug # For verbose communication library logs
        ```
        Then restart Home Assistant and check the Home Assistant logs (`home-assistant.log`).
* **`RuntimeWarning: coroutine was never awaited`:** This is typically an internal development warning and does not affect the functionality of the integration. If it persists, ensure you are on the latest version and report it as a bug.

## Known Issues / Limitations

* *(List any known bugs, limitations, or features not yet implemented. E.g., "Currently does not support DALI Groups," "Scene recall is not yet implemented," etc.)*
* The integration assumes sequential addressing for multi-channel lights (RGB, RGBW) starting from the base address.

## Contributing

Contributions are welcome! If you find a bug, have a feature request, or want to contribute code, please:

1.  **Open an Issue:** Describe the bug or feature request in detail.
2.  **Fork the Repository:** Create a fork of this repository.
3.  **Create a Branch:** Create a new branch for your changes (e.g., `feature/my-new-feature` or `fix/bug-description`).
4.  **Make Changes:** Implement your changes and write tests.
5.  **Submit a Pull Request:** Open a pull request to the `main` branch of this repository.

## Acknowledgements

This integration relies on the excellent [`edidio-control-py`](https://github.com/your-username/edidio-control-py-repo) Python library for communication with the Control Freak Edidio Gateway.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.