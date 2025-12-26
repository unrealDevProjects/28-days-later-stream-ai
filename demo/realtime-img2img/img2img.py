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

from config import Args
from pydantic import BaseModel, Field
from PIL import Image
import math

# Suprimir warnings específicos de diffusers sobre el rango de valores de imagen
warnings.filterwarnings("ignore", category=FutureWarning, module="diffusers.image_processor")

base_model = "stabilityai/sd-turbo"
taesd_model = "madebyollin/taesd"

default_prompt = "Portrait of hyperrealistic zombie, decaying flesh, exposed bone, rotting skin, bloodshot eyes, menacing glare, detailed, cinematic lighting, 8k, photorealistic, extreme details, unreal engine 5, masterpiece, professional photography, realistic textures, horror aesthetic, no cartoon, no stylized"
default_negative_prompt = "black and white, blurry, low resolution, pixelated,  pixel art, low quality, low fidelity"

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
        # negative_prompt: str = Field(
        #     default_negative_prompt,
        #     title="Negative Prompt",
        #     field="textarea",
        #     id="negative_prompt",
        # )
        denoise_strength: float = Field(
            0.0,  # Valor por defecto inicial (se animará automáticamente a 0.11 cuando se inicie)
            min=0.0,
            max=1.0,
            step=0.01,
            title="Denoise Strength (Step Schedule Intensity)",
            description="Controla la intensidad de la transformación. 0.0 = máxima transformación (como Step 49), 1.0 = sin efecto (imagen original)",
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
        self.debug_mode = args.debug  # Guardar flag de debug para logs condicionales
        params = self.InputParams()
        
        # Configuraciones de t_index_list para diferentes intensidades
        # Valores más bajos de t_index = menos transformación (más cerca de la imagen original)
        # Valores más altos de t_index = más transformación (más efecto del prompt)
        # El rango típico es 0-49, donde 0 es sin transformación y 49 es máxima
        # 0.0 = sin efecto (imagen original), 1.0 = máxima transformación
        # Progresión muy suave y gradual desde valores muy bajos
        # IMPORTANTE: Valores más bajos de t_index = MÁS transformación (más efecto)
        # Valores más altos de t_index = MENOS transformación (menos efecto)
        # 0.0 = máximo efecto, 1.0 = sin efecto
        # Progresión lineal y suave (INVERTIDA)
        # Array con menos puntos intermedios para reducir llamadas a prepare()
        # Esto crea "zonas" más amplias y reduce las actualizaciones frecuentes
        self.t_index_configs = {
            0.0: [44, 49],      # Máxima transformación (máximo efecto)
            0.1: [35, 41],      # Transformación alta
            0.2: [25, 32],      # Transformación media
            0.3: [20, 27],      # Transformación media-baja
            0.4: [15, 22],      # Transformación baja-media
            0.5: [10, 16],      # Transformación baja (default)
            0.6: [7, 12],       # Transformación muy baja
            0.7: [4, 8],        # Transformación casi imperceptible
            0.8: [2, 5],        # Transformación muy baja
            0.9: [1, 3],        # Transformación casi imperceptible
            1.0: [0, 1],        # Sin efecto (mínima transformación, casi original)
        }
        
        # Usar configuración inicial por defecto (0.0 = máxima transformación)
        # Se animará automáticamente a 0.11 cuando se inicie el stream
        default_t_index = self.t_index_configs[0.0]
        
        self.stream = StreamDiffusionWrapper(
            model_id_or_path=base_model,
            use_tiny_vae=args.taesd,
            device=device,
            dtype=torch_dtype,
            t_index_list=default_t_index,
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
            cfg_type="none",  # Volver a "none" ya que usaremos t_index_list para controlar
            use_safety_checker=args.safety_checker,
            # enable_similar_image_filter=True,
            # similar_image_filter_threshold=0.98,
            engine_dir=args.engine_dir,
        )

        self.last_prompt = default_prompt
        self.last_denoise_strength = 0.0  # Inicializar a 0.0 para que coincida con el frontend
        self.current_t_index = list(default_t_index)
        self.num_inference_steps = 50  # Guardar para re-uso
        self.last_valid_image = None  # Cachear la última imagen válida para evitar cortes
        
        self.stream.prepare(
            prompt=default_prompt,
            negative_prompt=default_negative_prompt,
            num_inference_steps=self.num_inference_steps,
            guidance_scale=1.2,
        )
    
    def _update_t_index_only(self, new_t_index: list) -> None:
        """Actualiza solo los valores relacionados con t_index_list sin re-preparar el prompt"""
        stream = self.stream.stream
        
        # Actualizar t_list
        stream.t_list = new_t_index
        stream.denoising_steps_num = len(new_t_index)
        
        # Recalcular sub_timesteps basado en el nuevo t_list
        stream.sub_timesteps = []
        for t in stream.t_list:
            stream.sub_timesteps.append(stream.timesteps[t])
        
        sub_timesteps_tensor = torch.tensor(
            stream.sub_timesteps, dtype=torch.long, device=stream.device
        )
        stream.sub_timesteps_tensor = torch.repeat_interleave(
            sub_timesteps_tensor,
            repeats=stream.frame_bff_size if stream.use_denoising_batch else 1,
            dim=0,
        )
        
        # Recalcular c_skip y c_out
        c_skip_list = []
        c_out_list = []
        for timestep in stream.sub_timesteps:
            c_skip, c_out = stream.scheduler.get_scalings_for_boundary_condition_discrete(timestep)
            c_skip_list.append(c_skip)
            c_out_list.append(c_out)
        
        stream.c_skip = (
            torch.stack(c_skip_list)
            .view(len(stream.t_list), 1, 1, 1)
            .to(dtype=stream.dtype, device=stream.device)
        )
        stream.c_out = (
            torch.stack(c_out_list)
            .view(len(stream.t_list), 1, 1, 1)
            .to(dtype=stream.dtype, device=stream.device)
        )
        
        # Recalcular alpha_prod_t_sqrt y beta_prod_t_sqrt
        alpha_prod_t_sqrt_list = []
        beta_prod_t_sqrt_list = []
        for timestep in stream.sub_timesteps:
            alpha_prod_t_sqrt = stream.scheduler.alphas_cumprod[timestep].sqrt()
            beta_prod_t_sqrt = (1 - stream.scheduler.alphas_cumprod[timestep]).sqrt()
            alpha_prod_t_sqrt_list.append(alpha_prod_t_sqrt)
            beta_prod_t_sqrt_list.append(beta_prod_t_sqrt)
        
        alpha_prod_t_sqrt = (
            torch.stack(alpha_prod_t_sqrt_list)
            .view(len(stream.t_list), 1, 1, 1)
            .to(dtype=stream.dtype, device=stream.device)
        )
        beta_prod_t_sqrt = (
            torch.stack(beta_prod_t_sqrt_list)
            .view(len(stream.t_list), 1, 1, 1)
            .to(dtype=stream.dtype, device=stream.device)
        )
        
        stream.alpha_prod_t_sqrt = torch.repeat_interleave(
            alpha_prod_t_sqrt,
            repeats=stream.frame_bff_size if stream.use_denoising_batch else 1,
            dim=0,
        )
        stream.beta_prod_t_sqrt = torch.repeat_interleave(
            beta_prod_t_sqrt,
            repeats=stream.frame_bff_size if stream.use_denoising_batch else 1,
            dim=0,
        )
        
        # Actualizar batch_size
        if self.stream.use_denoising_batch:
            self.stream.batch_size = len(new_t_index) * self.stream.frame_buffer_size
            # Actualizar buffers de ruido si es necesario
            if hasattr(stream, 'x_t_latent_buffer') and stream.x_t_latent_buffer is not None:
                if stream.denoising_steps_num > 1:
                    stream.x_t_latent_buffer = torch.zeros(
                        (
                            (stream.denoising_steps_num - 1) * stream.frame_bff_size,
                            4,
                            stream.latent_height,
                            stream.latent_width,
                        ),
                        dtype=stream.dtype,
                        device=stream.device,
                    )
                else:
                    stream.x_t_latent_buffer = None
            
            if hasattr(stream, 'init_noise'):
                stream.init_noise = torch.randn(
                    (self.stream.batch_size, 4, stream.latent_height, stream.latent_width),
                    generator=stream.generator,
                ).to(device=stream.device, dtype=stream.dtype)
            
            if hasattr(stream, 'stock_noise'):
                stream.stock_noise = torch.zeros_like(stream.init_noise)

    def _get_t_index_for_strength(self, strength: float) -> list:
        """Obtiene el t_index_list apropiado para el valor de strength con interpolación suave"""
        # Encontrar los dos puntos más cercanos
        keys = sorted(self.t_index_configs.keys())
        
        if strength <= keys[0]:
            return self.t_index_configs[keys[0]]
        if strength >= keys[-1]:
            return self.t_index_configs[keys[-1]]
        
        # Interpolación entre los dos puntos más cercanos
        for i in range(len(keys) - 1):
            if keys[i] <= strength <= keys[i + 1]:
                # Interpolación lineal entre los dos t_index_list
                t1 = self.t_index_configs[keys[i]]
                t2 = self.t_index_configs[keys[i + 1]]
                
                # Interpolar cada valor del t_index_list
                ratio = (strength - keys[i]) / (keys[i + 1] - keys[i])
                interpolated = [
                    int(t1[j] + ratio * (t2[j] - t1[j]))
                    for j in range(len(t1))
                ]
                return interpolated
        
        return self.t_index_configs[0.5]  # Fallback

    def predict(self, params: "Pipeline.InputParams") -> Image.Image:
        # Evitar procesamiento si el valor no ha cambiado significativamente
        # Esto previene llamadas innecesarias durante la animación
        strength_changed = abs(params.denoise_strength - self.last_denoise_strength) > 0.005
        
        # Procesar incluso con valores muy bajos para permitir la animación desde 0.0
        # Solo saltar procesamiento si es exactamente 0.0 o negativo
        if params.denoise_strength <= 0.0:
            # Devolver la imagen original sin ningún procesamiento solo si es exactamente 0
            return params.image
        
        image_tensor = self.stream.preprocess_image(params.image)
        
        # Obtener t_index_list basado en denoise_strength
        # Asegurar progresión suave desde 0.0
        target_t_index = self._get_t_index_for_strength(params.denoise_strength)
        
        # Solo actualizar si el prompt cambió o si el t_index_list realmente cambió
        # Comparar directamente el contenido del t_index_list, no el strength
        # Esto evita llamadas innecesarias a prepare() cuando el strength cambia
        # pero el t_index_list resultante es el mismo
        prompt_changed = params.prompt != self.last_prompt
        
        # Comparar listas correctamente (comparar contenido, no referencia)
        # Solo actualizar si el t_index_list realmente cambió
        t_index_changed = (
            len(target_t_index) != len(self.current_t_index) or 
            any(target_t_index[i] != self.current_t_index[i] for i in range(len(target_t_index)))
        )
        
        # Logs solo en modo debug para mejor rendimiento en tiempo real
        if self.debug_mode and t_index_changed:
            print(f"Denoise Strength: {params.denoise_strength:.5f} -> t_index: {target_t_index}")
        
        # Solo actualizar si realmente cambió algo significativo
        try:
            if prompt_changed or t_index_changed:
                # Actualizar t_list ANTES de preparar - prepare() usará este valor
                self.stream.stream.t_list = list(target_t_index)
                self.stream.stream.denoising_steps_num = len(target_t_index)
                
                # Re-preparar - esto recalculará batch_size y todos los tensores correctamente
                self.stream.prepare(
                    prompt=params.prompt,
                    negative_prompt=default_negative_prompt,
                    num_inference_steps=self.num_inference_steps,
                    guidance_scale=1.2,
                )
                
                # Actualizar estado después de preparar
                self.last_prompt = params.prompt
                self.last_denoise_strength = params.denoise_strength
                self.current_t_index = list(target_t_index)  # Guardar copia de la lista
            elif strength_changed:
                # Si solo cambió el strength pero el t_index es el mismo, actualizar solo el strength
                self.last_denoise_strength = params.denoise_strength
            
            # Procesar la imagen
            output_image = self.stream(image=image_tensor, prompt=params.prompt)
            
            # Cachear la imagen válida
            if output_image is not None:
                self.last_valid_image = output_image
            
            return output_image
            
        except Exception as e:
            # Si hay un error durante el procesamiento, devolver la última imagen válida
            # Solo loguear errores críticos (no cada frame fallido)
            import logging
            logging.error(f"Error en predict: {e}")
            if self.last_valid_image is not None:
                return self.last_valid_image
            # Si no hay imagen cacheada, devolver la imagen original
            return params.image
