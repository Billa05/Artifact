import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import gradio as gr
import numpy as np
import soundfile as sf
import torch
import torchaudio
from transformers import pipeline
from voice_profile_manager import VoiceProfileManager
from cached_path import cached_path

# Import F5 TTS components
from f5_tts.model import DiT
from f5_tts.infer.utils_infer import (
    load_vocoder,
    load_model,
    preprocess_ref_audio_text,
    infer_process,
    remove_silence_for_generated_wav,
    save_spectrogram,
)

# Constants
SAMPLE_RATE = 24000
DEFAULT_MODEL_PATH = str(cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors"))
DEFAULT_VOCAB_PATH = str(cached_path("hf://SWivid/F5-TTS/F5TTS_Base/vocab.txt"))
DEFAULT_MODEL_CONFIG = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
PRESETS = {
    "Neutral": {"text": "This is a neutral sample of my voice for reference purposes.", "style_description": "Clear and balanced tone with even pacing."},
    "Enthusiastic": {"text": "I'm incredibly excited about this amazing new technology!", "style_description": "Energetic, upbeat tone with varied pitch and faster pace."},
    "Professional": {"text": "Welcome to our comprehensive analysis of the quarterly results.", "style_description": "Authoritative, measured tone with precise articulation."},
    "Calm": {"text": "Take a deep breath and relax as we explore these concepts together.", "style_description": "Slow, soothing pace with gentle, lower-pitched voice."},
    "Narrative": {"text": "The story begins on a misty morning, as the sun rose over the distant hills.", "style_description": "Engaging storytelling voice with dramatic pauses and emphasis."}
}

# Load base components
whisper = pipeline("automatic-speech-recognition", model="openai/whisper-base")
vocoder = load_vocoder()


class VoiceCloner:
    """Core voice cloning functionality using F5 TTS."""
    
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, 
                 vocab_path: str = DEFAULT_VOCAB_PATH,
                 model_config: dict = DEFAULT_MODEL_CONFIG):
        self.model_path = model_path
        self.vocab_path = vocab_path
        self.model_config = model_config
        self.model = None
        
    def load_model(self) -> None:
        """Load the TTS model."""
        if self.model is None:
            self.model = load_model(DiT, self.model_config, self.model_path, vocab_file=self.vocab_path)
    
    def generate_speech(self, 
                        ref_audio_path: str,
                        ref_text: str,
                        text_to_generate: str,
                        remove_silence: bool = True,
                        speed: float = 1.0,
                        nfe_steps: int = 32,
                        cross_fade_duration: float = 0.15) -> Tuple[int, np.ndarray]:
        """Generate speech based on reference audio and input text."""
        self.load_model()
        
        # Preprocess reference audio and text
        ref_audio, ref_text = preprocess_ref_audio_text(ref_audio_path, ref_text)
        
        # Generate speech
        audio_wave, sample_rate, _ = infer_process(
            ref_audio,
            ref_text,
            text_to_generate,
            self.model,
            vocoder,
            cross_fade_duration=cross_fade_duration,
            nfe_step=nfe_steps,
            speed=speed
        )
        
        # Remove silence if requested
        if remove_silence:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                sf.write(f.name, audio_wave, sample_rate)
                remove_silence_for_generated_wav(f.name)
                final_wave, _ = torchaudio.load(f.name)
            audio_wave = final_wave.squeeze().cpu().numpy()
            
        return sample_rate, audio_wave
    
    def generate_multi_style_speech(self, 
                                   text_with_styles: str,
                                   style_to_sample_map: Dict[str, Dict],
                                   remove_silence: bool = True) -> Tuple[int, np.ndarray]:
        """Generate speech with multiple styles indicated in the text."""
        self.load_model()
        
        # Parse text to find style markers
        segments = self._parse_style_segments(text_with_styles)
        
        # Generate audio for each segment
        generated_segments = []
        
        for style, text in segments:
            if style not in style_to_sample_map:
                style = "default"  # Fallback to default style
            
            sample_info = style_to_sample_map.get(style)
            if not sample_info:
                continue
                
            ref_audio_path = sample_info["path"]
            ref_text = sample_info["transcription"]
            
            # Generate speech for this segment
            ref_audio, ref_text = preprocess_ref_audio_text(ref_audio_path, ref_text)
            
            audio_wave, sample_rate, _ = infer_process(
                ref_audio,
                ref_text,
                text,
                self.model,
                vocoder,
                cross_fade_duration=0.15,
                nfe_step=32,
                speed=1.0
            )
            
            # Remove silence if requested
            if remove_silence:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                    sf.write(f.name, audio_wave, sample_rate)
                    remove_silence_for_generated_wav(f.name)
                    segment_wave, _ = torchaudio.load(f.name)
                audio_wave = segment_wave.squeeze().cpu().numpy()
            
            generated_segments.append(audio_wave)
        
        # Concatenate all segments
        if generated_segments:
            final_audio = np.concatenate(generated_segments)
            return sample_rate, final_audio
        else:
            return None, None
    
    def _parse_style_segments(self, text: str) -> List[Tuple[str, str]]:
        """Parse text with style markers like {StyleName} into segments."""
        pattern = r'\{(.*?)\}(.*?)(?=\{|$)'
        matches = re.findall(pattern, text + '{', re.DOTALL)
        
        segments = []
        for style, content in matches:
            style = style.strip()
            content = content.strip()
            if content:
                segments.append((style, content))
                
        # If no style markers found, treat entire text as default style
        if not segments and text.strip():
            segments.append(("default", text.strip()))
            
        return segments
    
    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio using Whisper model."""
        result = whisper(audio_path)
        return result["text"]


class VoiceCloningApp:
    """Main application class for the voice cloning system."""
    
    def __init__(self):
        self.profile_manager = VoiceProfileManager()
        self.voice_cloner = VoiceCloner()
        self.app = self._build_interface()
    
    def _build_interface(self) -> gr.Blocks:
        """Build the Gradio interface."""
        app = gr.Blocks(title="Voice Cloning Studio")
        
        with app:
            gr.Markdown("""
            # Voice Cloning Studio
            Create high-quality speech in your own voice for content creation.
            
            ## Get Started:
            1. Create a voice profile or select an existing one
            2. Record or upload voice samples
            3. Generate speech in your voice with optional style variations
            """)
            
            # Profile Management Tab
            with gr.Tab("Profile Management"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Create New Profile")
                        new_profile_name = gr.Textbox(label="Profile Name")
                        new_profile_desc = gr.Textbox(label="Description", lines=2)
                        create_profile_btn = gr.Button("Create Profile", variant="primary")
                        profile_status = gr.Textbox(label="Status", interactive=False)
                    
                    with gr.Column():
                        gr.Markdown("### Select Existing Profile")
                        profile_dropdown = gr.Dropdown(
                            choices=self.profile_manager.list_profiles(),
                            label="Select Profile",
                            interactive=True
                        )
                        refresh_profiles_btn = gr.Button("Refresh Profiles")
                        profile_info = gr.JSON(label="Profile Details")
            
            # Voice Sampling Tab
            with gr.Tab("Voice Sampling"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Record or Upload Voice Samples")
                        sample_profile_dropdown = gr.Dropdown(
                            choices=self.profile_manager.list_profiles(),
                            label="Select Profile",
                            interactive=True
                        )
                        sample_name = gr.Textbox(label="Sample Name")
                        
                        with gr.Tabs():
                            with gr.Tab("Record"):
                                audio_recorder = gr.Audio(
                                    sources=["microphone"],
                                    type="filepath",
                                    label="Record Audio"
                                )
                            with gr.Tab("Upload"):
                                audio_uploader = gr.Audio(
                                    sources=["upload"],
                                    type="filepath",
                                    label="Upload Audio"
                                )
                        
                        sample_text = gr.Textbox(
                            label="Transcription",
                            placeholder="Leave blank for automatic transcription",
                            lines=3
                        )
                        
                        with gr.Accordion("Sample Presets", open=False):
                            preset_dropdown = gr.Dropdown(
                                choices=list(PRESETS.keys()),
                                label="Select Preset"
                            )
                            preset_description = gr.Textbox(
                                label="Style Description", 
                                interactive=False,
                                value=""
                            )
                        
                        add_sample_btn = gr.Button("Add Sample", variant="primary")
                        sample_status = gr.Textbox(label="Status", interactive=False)
                    
                    with gr.Column():
                        gr.Markdown("### Manage Voice Samples")
                        sample_list = gr.Dropdown(
                            label="Available Samples",
                            interactive=True
                        )
                        refresh_samples_btn = gr.Button("Refresh Samples")
                        preview_sample = gr.Audio(label="Preview Sample")
                        sample_transcription = gr.Textbox(
                            label="Sample Transcription",
                            interactive=False,
                            lines=3
                        )
                        
                        with gr.Row():
                            add_style_name = gr.Textbox(label="Style Name")
                            add_style_btn = gr.Button("Create Style from Sample")
                        style_status = gr.Textbox(label="Style Status", interactive=False)
            
            # Speech Generation Tab
            with gr.Tab("Speech Generation"):
                with gr.Row():
                    with gr.Column(scale=2):
                        gen_profile_dropdown = gr.Dropdown(
                            choices=self.profile_manager.list_profiles(),
                            label="Select Profile",
                            interactive=True
                        )
                        
                        with gr.Tabs():
                            with gr.Tab("Basic Generation"):
                                style_dropdown = gr.Dropdown(
                                    label="Voice Style",
                                    interactive=True
                                )
                                input_text = gr.Textbox(
                                    label="Text to Generate",
                                    placeholder="Enter the text you want to convert to speech...",
                                    lines=5
                                )
                                
                                with gr.Accordion("Advanced Settings", open=False):
                                    remove_silence_checkbox = gr.Checkbox(
                                        label="Remove Silence",
                                        value=True
                                    )
                                    speed_slider = gr.Slider(
                                        label="Speech Speed",
                                        minimum=0.5,
                                        maximum=2.0,
                                        value=1.0,
                                        step=0.1
                                    )
                                    quality_slider = gr.Slider(
                                        label="Quality (NFE Steps)",
                                        minimum=8,
                                        maximum=64,
                                        value=32,
                                        step=8
                                    )
                                
                                generate_btn = gr.Button("Generate Speech", variant="primary")
                            
                            with gr.Tab("Multi-Style Generation"):
                                gr.Markdown("""
                                ### Multi-Style Text Format
                                Use style markers to change voice styles within your text:
                                
                                ```
                                {Neutral} This is spoken in a neutral tone.
                                {Enthusiastic} While this is spoken with enthusiasm!
                                {Calm} And this is spoken calmly.
                                ```
                                """)
                                
                                multi_style_text = gr.Textbox(
                                    label="Multi-Style Text",
                                    lines=8
                                )
                                
                                with gr.Accordion("Available Styles", open=True):
                                    style_list = gr.JSON(
                                        label="Styles"
                                    )
                                    refresh_styles_btn = gr.Button("Refresh Styles")
                                    
                                multi_remove_silence = gr.Checkbox(
                                    label="Remove Silence",
                                    value=True
                                )
                                
                                generate_multi_btn = gr.Button("Generate Multi-Style Speech", variant="primary")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### Generated Speech")
                        output_name = gr.Textbox(label="Output Name")
                        output_audio = gr.Audio(label="Generated Speech")
                        save_output_btn = gr.Button("Save Output")
                        output_status = gr.Textbox(label="Status", interactive=False)
                        
                        with gr.Accordion("Export Options", open=False):
                            export_format = gr.Radio(
                                choices=["WAV", "MP3", "OGG"],
                                label="Export Format",
                                value="WAV"
                            )
                            gr.Markdown("Coming soon: Additional export options")
            
            # History & Exports Tab
            with gr.Tab("History & Exports"):
                with gr.Row():
                    history_profile_dropdown = gr.Dropdown(
                        choices=self.profile_manager.list_profiles(),
                        label="Select Profile",
                        interactive=True
                    )
                    refresh_history_btn = gr.Button("Refresh History")
                
                with gr.Row():
                    with gr.Column():
                        history_outputs = gr.Dropdown(
                            label="Saved Outputs",
                            interactive=True
                        )
                    with gr.Column():
                        history_audio = gr.Audio(label="Output Audio")
                        history_text = gr.Textbox(
                            label="Output Text",
                            interactive=False,
                            lines=3
                        )
            
            # Connect event handlers
            
            # Profile Management
            create_profile_btn.click(
                self.create_profile,
                inputs=[new_profile_name, new_profile_desc],
                outputs=[profile_status, profile_dropdown, sample_profile_dropdown, 
                        gen_profile_dropdown, history_profile_dropdown]
            )

            refresh_profiles_btn.click(
                self.refresh_profiles,
                outputs=[profile_dropdown, sample_profile_dropdown, 
                        gen_profile_dropdown, history_profile_dropdown]
            )
            
            profile_dropdown.change(
                fn=self.load_profile_info,
                inputs=[profile_dropdown],
                outputs=[profile_info]
            )
            
            # Voice Sampling
            preset_dropdown.change(
                fn=self.load_preset_info,
                inputs=[preset_dropdown],
                outputs=[preset_description, sample_text]
            )
            
            add_sample_btn.click(
                fn=self.add_sample,
                inputs=[
                    sample_profile_dropdown,
                    sample_name,
                    audio_recorder,
                    audio_uploader,
                    sample_text
                ],
                outputs=[sample_status, sample_list]
            )
            
            refresh_samples_btn.click(
                fn=self.refresh_samples,
                inputs=[sample_profile_dropdown],
                outputs=[sample_list]
            )
            
            sample_profile_dropdown.change(
                fn=self.refresh_samples,
                inputs=[sample_profile_dropdown],
                outputs=[sample_list]
            )
            
            sample_list.change(
                fn=self.load_sample,
                inputs=[sample_profile_dropdown, sample_list],
                outputs=[preview_sample, sample_transcription]
            )
            
            add_style_btn.click(
                fn=self.add_style,
                inputs=[sample_profile_dropdown, add_style_name, sample_list],
                outputs=[style_status]
            )
            
            # Speech Generation
            gen_profile_dropdown.change(
                fn=self.load_styles,
                inputs=[gen_profile_dropdown],
                outputs=[style_dropdown, style_list]
            )
            
            refresh_styles_btn.click(
                fn=self.load_styles,
                inputs=[gen_profile_dropdown],
                outputs=[style_dropdown, style_list]
            )
            
            generate_btn.click(
                fn=self.generate_speech,
                inputs=[
                    gen_profile_dropdown,
                    style_dropdown,
                    input_text,
                    remove_silence_checkbox,
                    speed_slider,
                    quality_slider
                ],
                outputs=[output_audio]
            )
            
            generate_multi_btn.click(
                fn=self.generate_multi_style_speech,
                inputs=[
                    gen_profile_dropdown,
                    multi_style_text,
                    multi_remove_silence
                ],
                outputs=[output_audio]
            )
            
            save_output_btn.click(
                fn=self.save_output,
                inputs=[
                    gen_profile_dropdown,
                    output_name,
                    output_audio,
                    input_text,
                    style_dropdown
                ],
                outputs=[output_status]
            )
            
            # History & Exports
            refresh_history_btn.click(
                fn=self.refresh_history,
                inputs=[history_profile_dropdown],
                outputs=[history_outputs]
            )
            
            history_profile_dropdown.change(
                fn=self.refresh_history,
                inputs=[history_profile_dropdown],
                outputs=[history_outputs]
            )
            
            history_outputs.change(
                fn=self.load_history_item,
                inputs=[history_profile_dropdown, history_outputs],
                outputs=[history_audio, history_text]
            )
        
        return app
    
    # Event handler implementations
    
    def refresh_profiles(self): 
        """Refresh the profile dropdown lists."""
        profiles = self.profile_manager.list_profiles()
        # Return all dropdowns that need to be updated with profile lists
        # Don't set any value to avoid the "not in choices" error
        return (gr.update(choices=profiles, value=None), 
                gr.update(choices=profiles, value=None),
                gr.update(choices=profiles, value=None), 
                gr.update(choices=profiles, value=None))

    def create_profile(self, name, description):
        """Create a new profile."""
        if not name:
            return "Please enter a profile name.", gr.update(), gr.update(), gr.update(), gr.update()
        
        result = self.profile_manager.create_profile(name, description)
        profiles = self.profile_manager.list_profiles()
        
        # Only set value to name if it's actually in the profiles list
        value = name if name in profiles else None
        
        return (result, 
                gr.update(choices=profiles, value=value),
                gr.update(choices=profiles, value=value),
                gr.update(choices=profiles, value=value),
                gr.update(choices=profiles, value=value))
    
    def load_profile_info(self, profile_name: str) -> Dict:
        """Load and return profile information."""
        if not profile_name or profile_name not in self.profile_manager.profiles:
            return {}
        return self.profile_manager.profiles[profile_name]
    
    def load_preset_info(self, preset_name: str) -> Tuple[str, str]:
        """Load preset information."""
        if not preset_name or preset_name not in PRESETS:
            return "", ""
        return PRESETS[preset_name]["style_description"], PRESETS[preset_name]["text"]
    
    def add_sample(self, profile_name: str, sample_name: str, 
               recorded_audio: str, uploaded_audio: str, 
               transcription: str):
        """Add a voice sample to a profile."""
        if not profile_name:
            return "Please select a profile.", gr.update(choices=[])
        
        if not sample_name:
            return "Please enter a sample name.", gr.update(choices=[])
        
        # Use either recorded or uploaded audio
        audio_path = recorded_audio if recorded_audio else uploaded_audio
        if not audio_path:
            return "Please record or upload audio.", gr.update(choices=[])
        
        # Auto-transcribe if no transcription provided
        if not transcription.strip():
            try:
                transcription = self.voice_cloner.transcribe_audio(audio_path)
            except Exception as e:
                return f"Transcription failed: {str(e)}", gr.update(choices=[])
        
        try:
            result = self.profile_manager.add_sample(
                profile_name, sample_name, audio_path, transcription
            )
            
            samples = self.profile_manager.list_samples(profile_name)
            
            # Only set value to sample_name if it's actually in the samples list
            value = sample_name if sample_name in samples else None
            
            return result, gr.update(choices=samples, value=value)
        except Exception as e:
            return f"Error adding sample: {str(e)}", gr.update(choices=[])
    
    def refresh_samples(self, profile_name: str):
        """Refresh the list of samples for a profile."""
        if not profile_name:
            return gr.update(choices=[], value=None)
        
        samples = self.profile_manager.list_samples(profile_name)
        return gr.update(choices=samples, value=None)
    
    def load_sample(self, profile_name: str, sample_name: str) -> Tuple[Optional[str], str]:
        """Load a sample for preview."""
        if not profile_name or not sample_name:
            return None, ""
        
        sample_path = self.profile_manager.get_sample_path(profile_name, sample_name)
        if not sample_path:
            return None, ""
        
        transcription = self.profile_manager.get_transcription(profile_name, sample_name)
        return sample_path, transcription
    
    def add_style(self, profile_name: str, style_name: str, sample_name: str) -> str: 
        """Add a voice style based on a sample."""
        if not profile_name:
            return "Please select a profile."
        
        if not style_name:
            return "Please enter a style name."
        
        if not sample_name:
            return "Please select a sample."
        
        return self.profile_manager.add_style(profile_name, style_name, sample_name)
    
    def load_styles(self, profile_name: str):
        """Load styles for a profile."""
        if not profile_name:
            return gr.update(choices=[], value=None), {}
        
        styles = self.profile_manager.list_styles(profile_name)
        
        # Always include "Default" in the choices
        choices = ["Default"] + styles
        
        # Create a dictionary mapping styles to their sample information
        style_info = {}
        for style in styles:
            sample = self.profile_manager.get_style_sample(profile_name, style)
            if sample:
                style_info[style] = {
                    "sample": sample,
                    "transcription": self.profile_manager.get_transcription(profile_name, sample)
                }
        
        return gr.update(choices=choices, value="Default"), style_info
    
    def generate_speech(
        self,
        profile_name: str,
        style_name: str,
        text: str,
        remove_silence: bool,
        speed: float,
        quality: int
    ) -> Union[Tuple[int, np.ndarray], None]:
        """Generate speech using a profile and style."""
        if not profile_name:
            gr.Warning("Please select a profile.")
            return None
        
        if not text.strip():
            gr.Warning("Please enter text to generate speech.")
            return None
        
        try:
            # Get sample to use based on style or default
            sample_name = None
            if style_name:
                sample_name = self.profile_manager.get_style_sample(profile_name, style_name)
                
            if not sample_name:
                # Use default/latest sample
                samples = self.profile_manager.list_samples(profile_name)
                if not samples:
                    gr.Warning("No voice samples found for this profile.")
                    return None
                sample_name = samples[-1]  # Use the latest sample
            
            # Get sample details
            sample_path = self.profile_manager.get_sample_path(profile_name, sample_name)
            transcription = self.profile_manager.get_transcription(profile_name, sample_name)
            
            # Generate speech
            sample_rate, audio_data = self.voice_cloner.generate_speech(
                sample_path,
                transcription,
                text,
                remove_silence=remove_silence,
                speed=speed,
                nfe_steps=quality,
                cross_fade_duration=0.15
            )
            
            return sample_rate, audio_data
            
        except Exception as e:
            gr.Warning(f"Error generating speech: {str(e)}")
            return None
    
    def generate_multi_style_speech(
        self,
        profile_name: str,
        multi_style_text: str,
        remove_silence: bool
    ) -> Union[Tuple[int, np.ndarray], None]:
        """Generate speech with multiple styles."""
        if not profile_name:
            gr.Warning("Please select a profile.")
            return None
        
        if not multi_style_text.strip():
            gr.Warning("Please enter text to generate speech.")
            return None
        
        try:
            # Build style to sample map
            style_to_sample_map = {}
            
            # Add default style using the latest sample
            samples = self.profile_manager.list_samples(profile_name)
            if not samples:
                gr.Warning("No voice samples found for this profile.")
                return None
            
            default_sample = samples[-1]
            style_to_sample_map["default"] = {
                "path": self.profile_manager.get_sample_path(profile_name, default_sample),
                "transcription": self.profile_manager.get_transcription(profile_name, default_sample)
            }
            
            # Add other styles
            styles = self.profile_manager.list_styles(profile_name)
            for style in styles:
                sample_name = self.profile_manager.get_style_sample(profile_name, style)
                if sample_name:
                    style_to_sample_map[style] = {
                        "path": self.profile_manager.get_sample_path(profile_name, sample_name),
                        "transcription": self.profile_manager.get_transcription(profile_name, sample_name)
                    }
            
            # Generate multi-style speech
            sample_rate, audio_data = self.voice_cloner.generate_multi_style_speech(
                multi_style_text,
                style_to_sample_map,
                remove_silence=remove_silence
            )
            
            if sample_rate is None or audio_data is None:
                gr.Warning("Failed to generate speech.")
                return None
                
            return sample_rate, audio_data
            
        except Exception as e:
            gr.Warning(f"Error generating multi-style speech: {str(e)}")
            return None
    
    def save_output(
        self,
        profile_name: str,
        output_name: str,
        audio_output: Tuple[int, np.ndarray],
        text: str,
        style_name: str
    ) -> str:
        """Save a generated output."""
        if not profile_name:
            return "Please select a profile."
        
        if not output_name:
            output_name = f"output_{time.strftime('%Y%m%d_%H%M%S')}"
            
        if not audio_output or len(audio_output) != 2:
            return "No audio to save."
        
        try:
            sample_rate, audio_data = audio_output
            
            saved_path = self.profile_manager.save_output(
                profile_name,
                output_name,
                audio_data,
                sample_rate,
                text,
                style_name or "default"
            )
            
            return f"Output saved as {os.path.basename(saved_path)}"
            
        except Exception as e:
            return f"Error saving output: {str(e)}"
    
    def refresh_history(self, profile_name: str):
        """Refresh the list of saved outputs."""
        if not profile_name or profile_name not in self.profile_manager.profiles:
            return gr.update(choices=[], value=None)
        
        if "outputs" not in self.profile_manager.profiles[profile_name]:
            return gr.update(choices=[], value=None)
        
        outputs = list(self.profile_manager.profiles[profile_name]["outputs"].keys())
        return gr.update(choices=outputs, value=None)
    
    def load_history_item(self, profile_name: str, output_name: str) -> Tuple[Optional[str], str]:
        """Load a history item for preview."""
        if not profile_name or not output_name:
            return None, ""
            
        if (profile_name not in self.profile_manager.profiles or 
            "outputs" not in self.profile_manager.profiles[profile_name] or
            output_name not in self.profile_manager.profiles[profile_name]["outputs"]):
            return None, ""
            
        output_data = self.profile_manager.profiles[profile_name]["outputs"][output_name]
        return output_data["path"], output_data["text"]
    
    def launch(self, **kwargs):
        """Launch the app."""
        return self.app.launch(**kwargs)


def main():
    """Main entry point."""
    app = VoiceCloningApp()
    app.launch(share=False)


if __name__ == "__main__":
    main()