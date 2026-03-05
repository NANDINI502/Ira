"""
Voice Service
Speech-to-text (Whisper) and text-to-speech (Piper)
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional
import asyncio
from loguru import logger

from app.config import settings


class VoiceService:
    """Service for voice input/output"""
    
    def __init__(self):
        self.whisper_model = settings.WHISPER_MODEL_PATH
        self.piper_model = settings.PIPER_MODEL_PATH
        self.piper_config = settings.PIPER_CONFIG_PATH
        
    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text using Whisper"""
        
        # Save audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            audio_path = f.name
        
        try:
            # Use Python whisper directly
            result = await self._run_whisper_python(audio_path)
            return result.strip()
            
        finally:
            # Cleanup temp file
            os.unlink(audio_path)
    
    async def synthesize(self, text: str) -> bytes:
        """Convert text to speech using Piper"""
        
        if not self.piper_model.exists():
            raise FileNotFoundError(
                f"Piper model not found at {self.piper_model}. "
                "Please download a Piper voice model."
            )
        
        # Find piper executable
        piper_exe = self._find_piper_executable()
        
        if not piper_exe:
            raise FileNotFoundError(
                "Piper executable not found. Please install Piper TTS."
            )
        
        # Create temp file for output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        
        try:
            # Run Piper
            cmd = [
                str(piper_exe),
                "--model", str(self.piper_model),
                "--config", str(self.piper_config),
                "--output_file", output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate(input=text.encode())
            
            # Read output audio
            with open(output_path, "rb") as f:
                audio_data = f.read()
            
            return audio_data
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    async def _run_whisper_cpp(self, exe_path: str, audio_path: str) -> str:
        """Run whisper.cpp for transcription"""
        
        cmd = [
            exe_path,
            "-m", str(self.whisper_model),
            "-f", audio_path,
            "--no-timestamps",
            "-l", "en"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Whisper error: {stderr.decode()}")
            raise RuntimeError("Whisper transcription failed")
        
        return stdout.decode()
    
    async def _run_whisper_python(self, audio_path: str) -> str:
        """Fallback to openai-whisper Python package"""
        try:
            import whisper
            
            # Load model if not cached
            if not hasattr(self, '_whisper_model'):
                self._whisper_model = whisper.load_model("base.en")
            
            result = self._whisper_model.transcribe(audio_path)
            return result["text"]
            
        except ImportError:
            raise RuntimeError(
                "Neither whisper.cpp nor openai-whisper is available. "
                "Please install one of them."
            )
    
    def _find_whisper_executable(self) -> Optional[str]:
        """Find whisper.cpp executable"""
        possible_paths = [
            settings.MODELS_DIR / "whisper" / "main.exe",
            settings.MODELS_DIR / "whisper" / "whisper.exe",
            Path("C:/whisper.cpp/build/bin/Release/main.exe"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        # Check PATH
        result = subprocess.run(
            ["where", "whisper"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
        
        return None
    
    def _find_piper_executable(self) -> Optional[str]:
        """Find Piper executable"""
        possible_paths = [
            settings.MODELS_DIR / "piper" / "piper" / "piper.exe",  # Nested from zip extraction
            settings.MODELS_DIR / "piper" / "piper.exe",
            Path("C:/piper/piper.exe"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        # Check PATH
        result = subprocess.run(
            ["where", "piper"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
        
        return None
    
    def check_availability(self) -> dict:
        """Check which voice services are available"""
        return {
            "whisper": {
                "available": self._find_whisper_executable() is not None or self._check_whisper_python(),
                "model_exists": self.whisper_model.exists()
            },
            "piper": {
                "available": self._find_piper_executable() is not None,
                "model_exists": self.piper_model.exists()
            }
        }
    
    def _check_whisper_python(self) -> bool:
        """Check if Python whisper is available"""
        try:
            import whisper
            return True
        except ImportError:
            return False
