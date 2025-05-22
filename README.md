# Utility scripts for creating instances on Vast.ai for Ollama, ComfyUI and Fooocus

## How to create an instance with Ollama and pulling models

``` bash
# Create a virtual environment
python3 -m venv venv
source ./venv/bin/activate

# Install dependencies
pip install vastai
pip install ollama

# Set your vast.ai api key
export VASTAI_API_KEY="12345"
# Start, Destroy or get ollama url of a running instance:
python Ollama_CreateInstance.py

```
