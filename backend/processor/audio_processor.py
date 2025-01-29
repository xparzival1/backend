import torch
import torchaudio
import torchaudio.functional as F
from pathlib import Path
import uuid
import shutil
import numpy as np

class AudioProcessor:
    def __init__(self):
        pass
        
    async def process_sitar(self, wav: torch.Tensor, sr: int) -> torch.Tensor:
        """Process audio specifically for sitar characteristics."""
        # 1. Initial high-pass to remove sub-bass frequencies (reduces synth bass)
        audio = F.highpass_biquad(wav, sr, 250)
        
        # 2. Reduce synthetic pad frequencies using bandstop
        audio = F.lowpass_biquad(audio, sr, 500)  # Cut upper synthetic frequencies
        audio = F.highpass_biquad(audio, sr, 300)  # Cut lower synthetic frequencies
        
        # 3. Series of bandpass filters to isolate and boost sitar frequencies
        # Main string fundamentals
        audio = F.bandpass_biquad(audio, sr, 750, Q=0.5)  # Wider Q for main range
        
        # 4. Boost upper harmonics (2-5kHz range where sitar "jangle" lives)
        harmonics = audio.clone()
        harmonics = F.highpass_biquad(harmonics, sr, 2000)
        harmonics = F.lowpass_biquad(harmonics, sr, 5000)
        harmonics = harmonics * 3.0  # Boost these frequencies
        
        # 5. Additional high frequency enhancement
        brilliance = audio.clone()
        brilliance = F.highpass_biquad(brilliance, sr, 4000)
        brilliance = brilliance * 2.0  # Boost high frequencies
        
        # 6. Combine all processed signals
        audio = audio + harmonics + brilliance
        
        return audio

    async def process_tanpura(self, wav: torch.Tensor, sr: int) -> torch.Tensor:
        """Process audio specifically for tanpura drone characteristics."""
        # 1. Focus on low frequencies (drone fundamentals typically 40-200Hz)
        audio = F.lowpass_biquad(wav, sr, 400)  # Keep only low frequencies
        
        # 2. Additional low-pass to ensure removal of high melodic content
        audio = F.lowpass_biquad(audio, sr, 300)
        
        # 3. Boost specific drone frequencies
        drone_fundamental = audio.clone()
        drone_fundamental = F.bandpass_biquad(drone_fundamental, sr, 100, Q=1.0)  # Main drone
        drone_fundamental = drone_fundamental * 2.0  # Boost fundamental
        
        # 4. Add subtle harmonics for richness (but still low)
        harmonics = audio.clone()
        harmonics = F.bandpass_biquad(harmonics, sr, 200, Q=1.0)  # First harmonic
        harmonics = harmonics * 1.5  # Slight boost to harmonics
        
        # 5. Combine the processed signals
        audio = drone_fundamental + harmonics
        
        # 6. Smooth out any sharp transients
        audio = F.lowpass_biquad(audio, sr, 250)  # Final smoothing
        
        return audio

    async def process_sarangi(self, wav: torch.Tensor, sr: int) -> torch.Tensor:
        """Process audio specifically for sarangi characteristics."""
        # 1. Initial filtering to focus on sarangi's main frequency range
        audio = F.bandpass_biquad(wav, sr, 400, Q=0.7)  # Main body resonance
        
        # 2. Enhance mid-range frequencies where sarangi's character lives
        mids = audio.clone()
        mids = F.bandpass_biquad(mids, sr, 800, Q=1.0)  # Mid frequencies
        mids = mids * 2.0  # Boost mids
        
        # 3. Add bow noise characteristics
        bow_noise = audio.clone()
        bow_noise = F.highpass_biquad(bow_noise, sr, 1200)
        bow_noise = F.lowpass_biquad(bow_noise, sr, 2000)
        bow_noise = bow_noise * 0.7  # Subtle bow noise
        
        # 4. Enhance sympathetic string resonances
        sympathetic = audio.clone()
        sympathetic = F.bandpass_biquad(sympathetic, sr, 1000, Q=2.0)
        sympathetic = sympathetic * 1.2
        
        # 5. Combine all processed signals
        audio = audio + mids + bow_noise + sympathetic
        
        # 6. Final shaping to ensure natural decay
        audio = F.lowpass_biquad(audio, sr, 3000)  # Roll off harsh frequencies
        
        return audio
        
    async def process_audio(self, input_path: Path, output_dir: Path, stem_type: str = 'sitar'):
        """Process audio file with specific filtering based on instrument type."""
        try:
            # Load the original audio
            wav, sr = torchaudio.load(str(input_path))
            
            # Process based on stem type
            if stem_type == 'sitar':
                audio = await self.process_sitar(wav, sr)
            elif stem_type == 'tanpura':
                audio = await self.process_tanpura(wav, sr)
            elif stem_type == 'sarangi':
                audio = await self.process_sarangi(wav, sr)
            else:
                raise ValueError(f"Unsupported stem type: {stem_type}")
            
            # Apply dynamic range compression
            threshold = 0.3
            ratio = 4.0
            audio = torch.where(
                torch.abs(audio) > threshold,
                threshold + (torch.abs(audio) - threshold) / ratio * torch.sign(audio),
                audio
            )
            
            # Final normalization
            audio = audio / (torch.max(torch.abs(audio)) + 1e-6)
            
            # Save the processed audio
            torchaudio.save(str(input_path), audio, sr)
            
            return True
            
        except Exception as e:
            print(f"Error processing {stem_type} stem: {str(e)}")
            if input_path.exists():
                input_path.unlink()
            raise ValueError(f"{stem_type.capitalize()} stem processing failed: {str(e)}")