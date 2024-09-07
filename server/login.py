import os
from huggingface_hub import login

# Fetch the token from the environment variable
huggingface_token = os.getenv("HUGGINGFACE_TOKEN")
login(huggingface_token)