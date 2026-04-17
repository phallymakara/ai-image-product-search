import torch
import open_clip
from PIL import Image
import io
import logging
from typing import List
from core.config import settings

class VectorService:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """Loads the CLIP model into memory."""
        try:
            logging.info(f"Loading CLIP model {settings.CLIP_MODEL_NAME}...")
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                settings.CLIP_MODEL_NAME, 
                pretrained=settings.CLIP_PRETRAINED_DATASET
            )
            self.model.to(self.device)
            self.model.eval()
            self.tokenizer = open_clip.get_tokenizer(settings.CLIP_MODEL_NAME)
            logging.info("CLIP model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load CLIP model: {str(e)}")
            raise e

    def get_image_embedding(self, image_bytes: bytes) -> List[float]:
        """Generates a normalized vector embedding for an image."""
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                # Normalize the features
                image_features /= image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy()[0].tolist()
        except Exception as e:
            logging.error(f"Error generating image embedding: {str(e)}")
            return []

    def get_text_embedding(self, text: str) -> List[float]:
        """Generates a normalized vector embedding for text."""
        try:
            text_input = self.tokenizer([text]).to(self.device)
            
            with torch.no_grad():
                text_features = self.model.encode_text(text_input)
                # Normalize the features
                text_features /= text_features.norm(dim=-1, keepdim=True)
                
            return text_features.cpu().numpy()[0].tolist()
        except Exception as e:
            logging.error(f"Error generating text embedding: {str(e)}")
            return []

    def classify_image(self, image_bytes: bytes, categories: List[str]) -> str:
        """Performs zero-shot classification on an image."""
        if not categories:
            return "uncategorized"
            
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            text_input = self.tokenizer(categories).to(self.device)
            
            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                text_features = self.model.encode_text(text_input)
                
                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features /= text_features.norm(dim=-1, keepdim=True)
                
                # Calculate similarity
                similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
                values, indices = similarity[0].topk(1)
                
                return categories[indices[0]]
        except Exception as e:
            logging.error(f"Error during zero-shot classification: {str(e)}")
            return "uncategorized"

# Singleton instance
vector_service = VectorService()
