# Installation and Setup Guide

This guide covers the installation and running of a Python script designed to fetch and analyze data from an API, then plot the results in various formats. The script also bundles all output files into a single ZIP archive for easy distribution and archiving.

## Prerequisites

Before running the script, ensure that you have Python installed on your Mac. Python comes pre-installed on macOS, but you may want to update to the latest version or manage multiple versions using a tool like `pyenv`.

## Required Libraries

The script uses several third-party libraries that may not be included with the standard Python installation. Here’s how to install them:

1. **Open Terminal**: You can find it in the `Applications/Utilities` folder or search for it using Spotlight.
2. **Check Python Version**: Run `python3 --version` to ensure Python 3 is installed. The output should be something like `Python 3.x.x`.
3. **Install Required Packages**: Run the following command to install all required libraries:

   ```bash
   pip3 install pandas seaborn matplotlib requests
    ```
    These commands install:
    - `pandas`: For data manipulation and analysis.
    - `seaborn` and `matplotlib`: For data visualization.
    - `requests`: For making HTTP requests to APIs.

## Running the Script

1. **Download the Script:** Ensure `autoqbr.py` is downloaded to a known directory on your Mac.
2. **Navigate to the Script Directory:** In Terminal, change the directory to where the script is located:

   ```bash
   cd path/to/script_directory
   ```
3. **Run the Script:** Execute the script using the following command:
   ```bash
   python3 autoqbr.py
   ```

## How to Use the Script

Upon running the script, you will be prompted to enter several pieces of information:

- **API Token:** This is your authentication token required by the API.
- **App(s) Token(s):** Enter the app tokens separated by space. Type all if you want to include `all` available tokens.
- **Timezone Offset:** Specify the timezone for the data query (e.g., `+00:00, -03:00`).
- **Time Range:** Define the start and end date for the data query (format: `YYYY-MM-DD/YYYY-MM-DD`).

## Outputs

After successful execution, the script will:

- Fetch data based on the provided criteria.
- Generate various plots as PNG files.
- Save all files (CSVs and PNGs) in a ZIP archive named `qbr_outputs.zip`.

## Troubleshooting

- `ModuleNotFoundError:` Ensure all libraries are installed correctly.
- `Permission Issues:` Run `sudo pip3 install [package]` if you encounter permission errors during installation.
- `API Errors:` Check the API token and parameters if you encounter HTTP errors.

## Additional Information

For further assistance or to report issues, contact the artur.barbosa@adjust.com or refer to the internal documentation related to the API used by this script.
