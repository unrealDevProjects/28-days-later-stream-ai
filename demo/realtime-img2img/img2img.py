import sys
import os
import warnings

sys.path.append(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
    )
)

from utils.wrapper import StreamDiffusionWrapper

import torch
import numpy as np

from config import Args
from pydantic import BaseModel, Field
from PIL import Image

# Suprimir warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="diffusers.image_processor")

base_model = "stabilityai/sd-turbo"
taesd_model = "madebyollin/taesd"

default_prompt = "Portrait of hyperrealistic zombie, decaying flesh, exposed bone, rotting skin, bloodshot eyes, menacing glare, detailed, cinematic lighting, 8k, photorealistic, extreme details, unreal engine 5, masterpiece, professional photography, realistic textures, horror aesthetic, no cartoon, no stylized"
default_negative_prompt = "black and white, blurry, low resolution, pixelated, pixel art, low quality, low fidelity"

page_content = """"""


class Pipeline:
    class Info(BaseModel):
        name: str = "StreamDiffusion img2img"
        input_mode: str = "image"
        page_content: str = page_content

    class InputParams(BaseModel):
        prompt: str = Field(
            default_prompt,
            title="Prompt",
            field="textarea",
            id="prompt",
        )
        denoise_strength: float = Field(
            0.0,  # Empieza en 0 (imagen original), se anima a 1 (máximo efecto)
            min=0.0,
            max=1.0,
            step=0.001,  # Pasos más pequeños para animación más suave
            title="Intensidad del Efecto",
            description="0.0 = imagen original, 1.0 = máxima transformación",
            field="range",
            id="denoise_strength",
        )
        width: int = Field(
            512, min=2, max=15, title="Width", disabled=True, hide=True, id="width"
        )
        height: int = Field(
            512, min=2, max=15, title="Height", disabled=True, hide=True, id="height"
        )

    def __init__(self, args: Args, device: torch.device, torch_dtype: torch.dtype):
        params = self.InputParams()
        
        # t_index_list FIJO - nunca cambia durante la ejecución
        # Esto evita llamadas a prepare() que bloquean la GPU
        # Valores más altos = más transformación (máximo efecto del prompt)
        # Opciones:
        #   [20, 35] = efecto suave
        #   [32, 45] = efecto medio
        #   [40, 49] = efecto alto
        #   [45, 49] = efecto máximo (casi no reconoces la imagen original)
        self.t_index_list = [35, 41]  # Efecto alto - más transformación
        
        self.stream = StreamDiffusionWrapper(
            model_id_or_path=base_model,
            use_tiny_vae=args.taesd,
            device=device,
            dtype=torch_dtype,
            t_index_list=self.t_index_list,
            frame_buffer_size=1,
            width=params.width,
            height=params.height,
            use_lcm_lora=False,
            output_type="pil",
            warmup=10,
            vae_id=None,
            acceleration=args.acceleration,
            mode="img2img",
            use_denoising_batch=True,
            cfg_type="none",
            use_safety_checker=args.safety_checker,
            engine_dir=args.engine_dir,
        )

        self.last_prompt = default_prompt
        
        # Preparar UNA sola vez al inicio
        self.stream.prepare(
            prompt=default_prompt,
            negative_prompt=default_negative_prompt,
            num_inference_steps=50,
            guidance_scale=1.2,
        )

    def predict(self, params: "Pipeline.InputParams") -> Image.Image:
        # Guardar imagen original para el blend
        original_image = params.image
        
        # Si el strength es 0, devolver la imagen original directamente
        if params.denoise_strength <= 0.001:
            return original_image
        
        # Preprocesar imagen
        image_tensor = self.stream.preprocess_image(original_image)
        
        # Solo re-preparar si el PROMPT cambió (no el slider)
        if params.prompt != self.last_prompt:
            self.stream.prepare(
                prompt=params.prompt,
                negative_prompt=default_negative_prompt,
                num_inference_steps=50,
                guidance_scale=1.2,
            )
            self.last_prompt = params.prompt
        
        # Procesar la imagen con el efecto completo
        processed_image = self.stream(image=image_tensor, prompt=params.prompt)
        
        # Si el strength es 1, devolver la imagen procesada directamente
        if params.denoise_strength >= 0.999:
            return processed_image
        
        # BLEND: Mezclar imagen original con procesada según el slider
        # Esto es instantáneo y no requiere GPU adicional
        blend_factor = params.denoise_strength
        
        # Convertir a numpy para el blend
        original_np = np.array(original_image).astype(np.float32)
        processed_np = np.array(processed_image).astype(np.float32)
        
        # Mezcla lineal: resultado = original * (1-factor) + processed * factor
        blended_np = original_np * (1.0 - blend_factor) + processed_np * blend_factor
        
        # Convertir de vuelta a imagen
        blended_image = Image.fromarray(blended_np.astype(np.uint8))
        
        return blended_image
