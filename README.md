# Webcam Surveillance

Use your old webcam as a surveillance camera!

## Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e .

cp config-template.toml config.toml
# Modify config.toml to your needs

# Either
python -m webcam_surveillance

# Or, built thanks to pyproject.toml, saved in your venv's bin folder
webcam-surveillance
```

To stop, you can do a `Ctrl + C` or type `q` in the windows of your webcam
