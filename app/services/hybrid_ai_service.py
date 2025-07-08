from typing import Any, Dict, List, Optional, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from flask import current_app
import gensim
import os
from .parser_service import extract_skills

class HybridAIService:
    def __init__(self):
        # Initialize the Sentence-BERT model for semantic similarity
        self.sbert_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        # Load Skill2Vec model
        skill2vec_path = os.path.join(current_app.root_path, 'services', 'ai_models', 'skill2vec_trained.model')
        try:
            self.skill2vec = gensim.models.Word2Vec.load(skill2vec_path)
        except Exception as e:
            current_app.logger.error(f"Error loading Skill2Vec model from {skill2vec_path}: {e}")
            self.skill2vec = None
        # Placeholder for other hybrid AI model components or configurations
        pass

    def match_resumes_to_jobs(self, resume_text: str, job_descriptions: list) -> list:
        # Placeholder for AI matching logic
        # This method should return a list of scores or rankings
        return []

    def calculate_hybrid_score(self, text1: str, text2: str) -> Dict[str, Any]:
        # Convert texts to embeddings
        embedding1 = self.sbert_model.encode(text1)
        embedding2 = self.sbert_model.encode(text2)

        semantic_similarity = float(embedding1.dot(embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2)))
        # Map semantic similarity from -1 to 1 range to 0 to 1 range
        semantic_similarity = (semantic_similarity + 1) / 2

        # Extract skills using the new method
        resume_skills = self.extract_skills_dict(text1)
        job_skills = self.extract_skills_dict(text2)

        current_app.logger.info(f"Extracted Resume Skills: {resume_skills}")
        current_app.logger.info(f"Extracted Job Skills: {job_skills}")

        # Calculate Skill2Vec embeddings and similarity
        resume_skill2vec_embedding = self._skill2vec_embed_fallback(resume_skills)
        job_skill2vec_embedding = self._skill2vec_embed_fallback(job_skills)

        skill2vec_similarity = float(np.dot(resume_skill2vec_embedding, job_skill2vec_embedding) / 
                                     (np.linalg.norm(resume_skill2vec_embedding) * np.linalg.norm(job_skill2vec_embedding))) if (np.linalg.norm(resume_skill2vec_embedding) * np.linalg.norm(job_skill2vec_embedding)) != 0 else 0.0
        # Map skill2vec similarity from -1 to 1 range to 0 to 1 range
        skill2vec_similarity = (skill2vec_similarity + 1) / 2

        # Combine semantic and skill-based similarity with weights from notebook (0.8 SBERT, 0.2 Skill2Vec)
        hybrid_score = (semantic_similarity * 0.7) + (skill2vec_similarity * 0.3)

        # Determine prediction based on hybrid score
        hybrid_prediction = "match" if hybrid_score > 0.7 else "no_match"

        return {
            "hybrid_score": hybrid_score,
            "semantic_score": semantic_similarity,
            "skill_similarity": skill2vec_similarity, # Now truly skill2vec similarity
            "sbert_similarity": semantic_similarity,
            "skill2vec_similarity": skill2vec_similarity,
            "resume_skills": list(resume_skills),
            "job_skills": list(job_skills),
            "hybrid_prediction": hybrid_prediction
        }

    def extract_skills_dict(self, text: str) -> List[str]:
        # Use the extract_skills function from parser_service to get skills
        return extract_skills(text)

    def _skill2vec_embed_fallback(self, skills):
        vectors = []
        if self.skill2vec and hasattr(self.skill2vec, 'wv'):
            for skill in skills:
                skill_norm = skill.strip().lower()
                if skill_norm in self.skill2vec.wv:
                    vectors.append(self.skill2vec.wv[skill_norm])
                else:
                    words = skill_norm.split()
                    word_vecs = [self.skill2vec.wv[w] for w in words if w in self.skill2vec.wv]
                    if word_vecs:
                        vectors.append(np.mean(word_vecs, axis=0))
        if vectors:
            return np.mean(vectors, axis=0)
        else:
            # Return a zero vector of the correct size if no skills or model not loaded
            return np.zeros(self.skill2vec.vector_size) if self.skill2vec else np.zeros(100) # Assuming 100 as default vector size if model not loaded

def get_hybrid_ai_service():
    return HybridAIService()