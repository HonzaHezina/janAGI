import requests

def run(task):
    prompt = task.get("prompt", "a cat in a hat")
    response = requests.post("https://api-inference.huggingface.co/models/CompVis/stable-diffusion-v1-4",
                             headers={"Authorization": f"Bearer YOUR_HF_TOKEN"},
                             json={"inputs": prompt})
    return {"image_url": response.json().get("generated_image_url", "N/A")}
