# settings.py
import json

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

# Globalna varijabla koju svi uvoze
cfg = load_config()