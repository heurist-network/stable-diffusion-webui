import os
import re
import html
import json
import gradio as gr
from threading import Thread
from io import BytesIO
import base64
from dotenv import load_dotenv
import requests
import json
import random
import string
import gradio as gr
from modules.constants import css

model_list_url = "https://raw.githubusercontent.com/heurist-network/heurist-models/main/models.json"

def fetch_model_list(url):
    response = requests.get(url)
    return response.json() if response.status_code == 200 else []
models = fetch_model_list(model_list_url)

def fetch_model_defaults(model_name):
    url = f"https://raw.githubusercontent.com/heurist-network/heurist-models/main/examples/{model_name}.json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {}

def random_job_id():
    letters = string.ascii_lowercase + string.digits
    return 'sd-webui' + ''.join(random.choice(letters) for i in range(10))

def txt2img(prompt, neg_prompt, model_id, num_iterations, guidance_scale, width, height, seed):
    data = {
        "job_id": random_job_id(),
        "model_input": {
            "SD": {
                "prompt": prompt,
                "neg_prompt": neg_prompt,
                "num_iterations": num_iterations,
                "width": width,
                "height": height,
                "guidance_scale": guidance_scale,
                "seed": seed
            }
        },
        "model_type": "SD",
        "model_id": model_id,
        "deadline": 30,
        "priority": 1
    }
    response = requests.post("http://70.23.102.189:3030/submit_job", headers={"Content-Type": "application/json"}, data=json.dumps(data))
    image_url = response.json()  
    return gr.update(value=[image_url])

def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def update_btn_start():
    return [
        gr.update(visible=False),
        gr.update(visible=True, value="Generating... Please wait.")
    ]

def create_default():
    with gr.Blocks():
        first_model_name = models[0]['name'] if models else None
        defaults = fetch_model_defaults(first_model_name) if first_model_name else {}
        model_dropdown = gr.Dropdown(label="Select Model", choices=[model['name'] for model in models], value=first_model_name)

        with gr.Row():
            with gr.Column(scale=6, min_width=600):
                prompt = gr.Textbox(defaults.get("prompt", ""), placeholder="Prompt", show_label=False, lines=3)
                negative_prompt = gr.Textbox(defaults.get("neg_prompt", ""), placeholder="Negative Prompt", show_label=False, lines=3)
            with gr.Row():
                generate_btn = gr.Button("Generate", variant='primary', elem_id="generate")
                loading_text = gr.Text(value="", visible=False)

        with gr.Row():
            with gr.Column():
                with gr.Tab("Generation"):
                    with gr.Row():
                        steps = gr.Slider(label="Sampling Steps", minimum=1, maximum=50, value=defaults.get("num_inference_steps", 25), step=1)
        
                    with gr.Row():
                        with gr.Column(scale=8):
                            width = gr.Slider(label="Width", maximum=1024, value=defaults.get("width", 512), step=8)
                            height = gr.Slider(label="Height", maximum=1024, value=defaults.get("height", 768), step=8)
        
                    guidance_scale = gr.Slider(label="Guidance Scale", minimum=1, maximum=20, value=defaults.get("guidance_scale", 7), step=0.5)
                    seed = gr.Number(label="Seed", value=defaults.get("seed", -1))
        

            with gr.Column():
                initial_image_url = f"https://raw.githubusercontent.com/heurist-network/heurist-models/main/examples/{first_model_name}.png" if first_model_name else ""
                image_output = gr.Gallery(columns=1, height=1024, value=[initial_image_url] if initial_image_url else [], label="Output Image", allow_preview=False, object_fit='scale-down')

    return (model_dropdown, prompt, negative_prompt, steps, width, height, guidance_scale, seed, image_output, loading_text, generate_btn)

def create_ui():
    with gr.Blocks(css=css) as ui:
        with gr.Tabs():
            with gr.Tab("Text to Image"):
                (model_dropdown, prompt, negative_prompt, steps, width, height, guidance_scale, seed, image_output, loading_text, generate_btn) = create_default()

                def on_model_change(selected_model):
                    defaults = fetch_model_defaults(selected_model)
                    new_image_url = f"https://raw.githubusercontent.com/heurist-network/heurist-models/main/examples/{selected_model}.png"
                    return [defaults.get("prompt", ""), defaults.get("neg_prompt", ""), defaults.get("num_inference_steps", 25), defaults.get("width", 512), defaults.get("height", 768), defaults.get("guidance_scale", 7), defaults.get("seed", -1), [new_image_url]]

                model_dropdown.change(on_model_change, inputs=[model_dropdown], outputs=[prompt, negative_prompt, steps, width, height, guidance_scale, seed, image_output])
                
                event_start = generate_btn.click(
                    update_btn_start,
                    outputs=[generate_btn, loading_text], 
                    queue=False
                )
                event = event_start.then(
                    txt2img,
                    inputs=[prompt, negative_prompt, model_dropdown, steps, guidance_scale, width, height, seed],
                    outputs=[image_output]
                )
                event_end = event.then(
                    lambda: [gr.update(visible=True), gr.update(visible=False)],
                    outputs=[generate_btn, loading_text],
                    queue=False
                )

    return ui


def main():
    demo = create_ui()
    demo.queue(default_concurrency_limit=2)
    demo.launch(share=True)

if __name__ == "__main__":
    main()
