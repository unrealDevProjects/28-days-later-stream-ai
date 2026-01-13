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

default_prompt = "Zombie dead, horror aesthetic"
default_negative_prompt = "blurry, low resolution, pixelated, low quality, distorted face, oversized head, giant face, deformed proportions, bad anatomy"

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
            800, min=2, max=15, title="Width", disabled=True, hide=True, id="width"
        )
        height: int = Field(
            800, min=2, max=15, title="Height", disabled=True, hide=True, id="height"
        )

    def __init__(self, args: Args, device: torch.device, torch_dtype: torch.dtype):
        params = self.InputParams()
        
        # t_index_list FIJO - nunca cambia durante la ejecución
        # Esto evita llamadas a prepare() que bloquean la GPU
        # IMPORTANTE: En Stable Diffusion, índices más BAJOS = MÁS efecto/transformación
        #             índices más ALTOS = MENOS efecto, respeta más la imagen original
        # Opciones:
        #   [40, 49] = efecto muy suave, respeta mucho la pose y estructura original
        #   [35, 45] = efecto suave, menos variación
        #   [30, 40] = efecto medio, variación moderada
        #   [20, 35] = efecto alto - más transformación (puede perder la pose)
        #   [10, 25] = efecto máximo - mucha transformación
        # Para que siga la pose, usamos valores MÁS ALTOS
        self.t_index_list = [27, 32]  # Efecto suave - respeta la pose y estructura original
        
        # Para mejor calidad de imagen, deshabilitamos tiny VAE (usa VAE completo)
        # Si quieres más velocidad a cambio de calidad, puedes usar args.taesd
        use_tiny_vae_for_quality = False  # False = mejor calidad, True = más velocidad
        
        self.stream = StreamDiffusionWrapper(
            model_id_or_path=base_model,
            use_tiny_vae=use_tiny_vae_for_quality if not args.taesd else args.taesd,
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
            num_inference_steps=50,  # Máximo permitido por el scheduler LCM
            guidance_scale=1.3,  # Ligeramente aumentado para más detalle sin perder la pose
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
                num_inference_steps=50,  # Máximo permitido por el scheduler LCM
                guidance_scale=1.3,  # Ligeramente aumentado para más detalle sin perder la pose
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
        
        # Post-procesamiento para mejorar calidad: sharpening suave
        from PIL import ImageFilter
        # Aplicar un sharpening muy suave para mejorar detalles sin artefactos
        blended_image = blended_image.filter(ImageFilter.UnsharpMask(radius=1, percent=100, threshold=3))
        
        return blended_image
