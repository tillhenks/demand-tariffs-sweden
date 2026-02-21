# kWh Consumption Analyzer

A lightweight Python utility designed to parse hourly power consumption data, calculate costs based on custom tariffs, and generate both visual and document-based reports.

## Overview

This program processes CSV files containing hourly energy readings. It calculates the total energy usage and tariff cost, then provides a breakdown via a text table, a PDF report, and an interactive plot.

### Data Format
The script expects a CSV file using a semicolon (`;`) separator with the following structure:
`YYYY-MM-DD HH:MM;Usage`

**Example:**
```
2026-01-01 00:00;2,008
2026-01-01 01:00;1,63
2026-01-01 02:00;1,321
2026-01-01 03:00;1,291
2026-01-01 04:00;1,486
2026-01-01 05:00;1,381
```

* **Timestamp:** The date and the start of the hour.
* **Value:** The mean power consumption (kW) for that hour. Since the interval is exactly one hour, 1 kW x 1 h = 1 kWh.

---

## Features

* **CSV Parsing:** Automatically handles date-time formatting and decimal conversions.
* **Custom Tariffs:** Easily adjustable pricing logic to match your specific utility provider.
* **Multi-format Output:**
    * **CLI Table:** A quick summary printed directly to your terminal.
    * **PDF Export:** A professional, portable report of your consumption data.
    * **Data Visualization:** An interactive Matplotlib plot (if running in a non-headless environment).

---

## Getting Started

### Prerequisites
Ensure you have Python installed, along with the necessary libraries:
```bash
pip install pandas matplotlib
```

#### Consumption file
The csv file that contains the values, make sure to match the filename as in the Python script

### Usage
With the files in place and Python 3 installed with the pre reqs above just issue:
`python3 tariff-from-file.py`

