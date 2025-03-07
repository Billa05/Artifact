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

class VoiceProfileManager:
    """Manages voice profiles including creation, storage, and retrieval."""
    
    def __init__(self, profiles_dir: str = "voice_profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(exist_ok=True, parents=True)
        self.current_profile = None
        self.profiles = self._load_profiles()
        
    def _load_profiles(self) -> Dict:
        """Load all existing voice profiles."""
        profiles = {}
        for profile_dir in self.profiles_dir.glob("*"):
            if profile_dir.is_dir():
                profile_path = profile_dir / "profile.json"
                if profile_path.exists():
                    with open(profile_path, "r") as f:
                        profile_data = json.load(f)
                        profiles[profile_data["name"]] = profile_data
        return profiles
    
    def create_profile(self, name: str, description: str = "") -> str:
        """Create a new voice profile."""
        if name in self.profiles:
            return f"Profile '{name}' already exists."
        
        profile_dir = self.profiles_dir / name
        profile_dir.mkdir(exist_ok=True, parents=True)
        (profile_dir / "samples").mkdir(exist_ok=True)
        (profile_dir / "outputs").mkdir(exist_ok=True)
        
        profile_data = {
            "name": name,
            "description": description,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "samples": {},
            "styles": {}
        }
        
        with open(profile_dir / "profile.json", "w") as f:
            json.dump(profile_data, f, indent=4)
        
        self.profiles[name] = profile_data
        self.current_profile = name
        return f"Profile '{name}' created successfully."
    
    def add_sample(self, profile_name: str, sample_name: str, audio_path: str, transcription: str = "") -> str:
        """Add a voice sample to a profile."""
        if profile_name not in self.profiles:
            return f"Profile '{profile_name}' does not exist."
        
        profile_dir = self.profiles_dir / profile_name
        samples_dir = profile_dir / "samples"
        
        # Generate a filename
        ext = os.path.splitext(audio_path)[1]
        sample_filename = f"{sample_name.replace(' ', '_')}{ext}"
        sample_path = samples_dir / sample_filename
        
        # Copy the audio file
        audio, sr = torchaudio.load(audio_path)
        torchaudio.save(str(sample_path), audio, sr)
        
        # Update profile data
        self.profiles[profile_name]["samples"][sample_name] = {
            "path": str(sample_path),
            "transcription": transcription,
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save updated profile
        with open(profile_dir / "profile.json", "w") as f:
            json.dump(self.profiles[profile_name], f, indent=4)
            
        return f"Sample '{sample_name}' added to profile '{profile_name}'."
    
    def add_style(self, profile_name: str, style_name: str, sample_name: str) -> str:
        """Define a voice style based on a specific sample."""
        if profile_name not in self.profiles:
            return f"Profile '{profile_name}' does not exist."
            
        if sample_name not in self.profiles[profile_name]["samples"]:
            return f"Sample '{sample_name}' does not exist in profile '{profile_name}'."
        
        profile_dir = self.profiles_dir / profile_name
        
        # Link the style to the sample
        self.profiles[profile_name]["styles"][style_name] = {
            "sample": sample_name,
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save updated profile
        with open(profile_dir / "profile.json", "w") as f:
            json.dump(self.profiles[profile_name], f, indent=4)
            
        return f"Style '{style_name}' added to profile '{profile_name}'."
    
    def get_sample_path(self, profile_name: str, sample_name: str) -> Optional[str]:
        """Get the path to a specific sample."""
        if (profile_name in self.profiles and 
            sample_name in self.profiles[profile_name]["samples"]):
            return self.profiles[profile_name]["samples"][sample_name]["path"]
        return None
    
    def get_transcription(self, profile_name: str, sample_name: str) -> str:
        """Get the transcription for a specific sample."""
        if (profile_name in self.profiles and 
            sample_name in self.profiles[profile_name]["samples"]):
            return self.profiles[profile_name]["samples"][sample_name]["transcription"]
        return ""
    
    def get_style_sample(self, profile_name: str, style_name: str) -> Optional[str]:
        """Get the sample associated with a style."""
        if (profile_name in self.profiles and 
            style_name in self.profiles[profile_name]["styles"]):
            return self.profiles[profile_name]["styles"][style_name]["sample"]
        return None
    
    def list_profiles(self) -> List[str]:
        """List all available profiles."""
        return list(self.profiles.keys())
    
    def list_samples(self, profile_name: str) -> List[str]:
        """List all samples for a profile."""
        if profile_name in self.profiles:
            return list(self.profiles[profile_name]["samples"].keys())
        return []
    
    def list_styles(self, profile_name: str) -> List[str]:
        """List all styles for a profile."""
        if profile_name in self.profiles:
            return list(self.profiles[profile_name]["styles"].keys())
        return []
    
    def save_output(self, profile_name: str, output_name: str, audio_data: np.ndarray, 
                    sr: int, text: str, style: str = "") -> str:
        """Save a generated output."""
        if profile_name not in self.profiles:
            return f"Profile '{profile_name}' does not exist."
        
        profile_dir = self.profiles_dir / profile_name
        outputs_dir = profile_dir / "outputs"
        
        # Generate a filename
        output_filename = f"{output_name.replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.wav"
        output_path = outputs_dir / output_filename
        
        # Save the audio file
        sf.write(str(output_path), audio_data, sr)
        
        # Update profile with output metadata
        if "outputs" not in self.profiles[profile_name]:
            self.profiles[profile_name]["outputs"] = {}
            
        self.profiles[profile_name]["outputs"][output_name] = {
            "path": str(output_path),
            "text": text,
            "style": style,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save updated profile
        with open(profile_dir / "profile.json", "w") as f:
            json.dump(self.profiles[profile_name], f, indent=4)
            
        return str(output_path)
