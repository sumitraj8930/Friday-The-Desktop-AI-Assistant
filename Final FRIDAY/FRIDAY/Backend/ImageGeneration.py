# Backend/ImageGeneration.py

from random import randint
from PIL import Image
import requests
from dotenv import dotenv_values
import os
from time import sleep
from typing import Literal
from pathlib import Path
import sys

# === Constants ===
WRITABLE_DATA_DIR = Path.home() / "JarvisData"
WRITABLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

ImageSize = Literal['auto', '1024x1024', '1536x1024', '1024x1536', '256x256', '512x512', '1792x1024', '1024x1792']

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# === Env and A4F Setup ===
env_vars = dotenv_values(resource_path(".env"))
a4f_api_key = ""
a4f_base_url = "https://api.a4f.co/v1"

try:
    from openai import OpenAI
    A4F_AVAILABLE = True
    a4f_client = OpenAI(api_key=a4f_api_key, base_url=a4f_base_url)
except ImportError:
    A4F_AVAILABLE = False
    a4f_client = None
    print("Install A4F using: pip install a4f-local openai")

def open_images(prompt):
    prompt = prompt.replace(" ", "_")
    for i in range(1, 5):
        image_path = WRITABLE_DATA_DIR / f'generated_{prompt}{i}.jpg'
        if image_path.exists():
            Image.open(image_path).show()
            sleep(1)

def generate_image_with_a4f_single(prompt, image_number, size: ImageSize):
    if not a4f_client: return False
    models = [
        "provider-5/gpt-image-1", "provider-5/dall-e-3",
        "provider-1/FLUX.1-schnell", "provider-2/FLUX.1-schnell",
        "provider-3/FLUX.1-schnell", "provider-5/FLUX.1 [schnell]",
        "provider-1/FLUX.1.1-pro"
    ]
    for model in models:
        try:
            response = a4f_client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
                size=size,
                response_format="url"
            )
            image_url = response.data[0].url if response and response.data else None
            if image_url:
                res = requests.get(image_url, timeout=15)
                if res.status_code == 200:
                    filename = f"generated_{prompt.replace(' ', '_')}{image_number}.jpg"
                    with open(WRITABLE_DATA_DIR / filename, "wb") as f:
                        f.write(res.content)
                    return True
        except Exception: continue
    return False

def generate_fallback_images(prompt, start_index=1, size: ImageSize = "1024x1024"):
    width, height = map(int, size.split('x')) if size != "auto" else (1024, 1024)
    for i in range(start_index, 5):
        try:
            url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width={width}&height={height}&seed={randint(0, 100000)}"
            res = requests.get(url, timeout=30)
            if res.status_code == 200:
                filename = f"generated_{prompt.replace(' ', '_')}{i}.jpg"
                with open(WRITABLE_DATA_DIR / filename, "wb") as f:
                    f.write(res.content)
                print(f"Fallback image {i} generated")
            sleep(1)
        except Exception as e:
            print(f"Error in fallback gen {i}: {e}")

def GenerateImages(prompt: str, size: ImageSize = "1024x1024"):
    success = 0
    if a4f_client and a4f_api_key:
        print("Using A4F...")
        if generate_image_with_a4f_single(prompt, 1, size):
            success = 1
            for i in range(2, 5):
                if generate_image_with_a4f_single(f"{prompt}, variation {i}", i, size):
                    success += 1
    if success < 4:
        print(f"Falling back for {4 - success} images")
        generate_fallback_images(prompt, start_index=success+1, size=size)
    open_images(prompt)

def ProcessImageRequestFromDataFile():
    try:
        file_path = resource_path("Frontend/Files/ImageGeneration.data")
        with open(file_path, "r") as f:
            data = f.read().strip()
        if "," not in data:
            print("Invalid ImageGeneration.data format.")
            return
        parts = data.split(",")
        prompt = parts[0].strip()
        status = parts[1].strip()
        size = parts[2].strip() if len(parts) > 2 else "1024x1024"
        if status != "True":
            return
        GenerateImages(prompt, size)
        # Reset to prevent regeneration
        with open(file_path, "w") as f:
            f.write("False,False")
    except Exception as e:
        print(f"[ImageGen Error] {e}")

ProcessImageRequestFromDataFile()