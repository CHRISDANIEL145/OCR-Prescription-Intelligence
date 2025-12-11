import spacy
from transformers import pipeline
import re

class InitiateNER:
    """
    Named Entity Recognition using spaCy and Hugging Face Transformers
    Replaces Spark NLP with pure Python solution
    """

    def __init__(self, gpu=False):
        """
        Initialize NER model
        Args:
            gpu: Boolean to use GPU (requires CUDA)
        """
        self.gpu = gpu
        print("Loading spaCy model...")

        try:
            # Load pre-trained spaCy model for English
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("spaCy model not found. Downloading...")
            import subprocess
            subprocess.check_call(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")

        # Load Hugging Face medical NER pipeline for better medical entity extraction
        device = 0 if gpu else -1  # -1 for CPU
        print("Loading medical NER transformer model...")
        try:
            self.medical_ner = pipeline(
                "token-classification",
                model="d4data/biomedical-ner-all",
                device=device,
                aggregation_strategy="simple"
            )
        except Exception as e:
            print(f"Warning: Could not load medical NER model: {e}")
            print("Falling back to spaCy NER only")
            self.medical_ner = None

        print("NER Model initialized successfully!")

    def extract_entities(self, text):
        """
        Extract entities from prescription text
        Args:
            text: Input prescription text

        Returns:
            dict: Extracted entities (medications, doses, instructions)
        """
        entities = {
            'medications': [],
            'doses': [],
            'instructions': [],
            'routes': [],
            'frequencies': []
        }

        # Clean and preprocess text
        text = text.strip()

        # Use spaCy for general NER
        doc = self.nlp(text)

        # Extract entities using spaCy
        for ent in doc.ents:
            if ent.label_ in ["PRODUCT", "ORG"]:  # Medications often tagged as PRODUCT
                entities['medications'].append(ent.text)

        # Use medical NER if available
        if self.medical_ner:
            try:
                medical_entities = self.medical_ner(text)
                for entity in medical_entities:
                    label = entity['entity_group']
                    text_val = entity['word']

                    if label.lower() in ["medication", "drug"]:
                        entities['medications'].append(text_val)
                    elif label.lower() == "dose":
                        entities['doses'].append(text_val)
                    elif label.lower() == "route":
                        entities['routes'].append(text_val)
                    elif label.lower() == "frequency":
                        entities['frequencies'].append(text_val)
            except Exception as e:
                print(f"Medical NER error: {e}")

        # Extract dose patterns using regex
        dose_pattern = r'\d+\s*(mg|ml|g|mcg|units?|tablets?|capsules?)'
        doses = re.findall(dose_pattern, text, re.IGNORECASE)
        entities['doses'].extend(doses)

        # Extract frequency patterns
        frequency_keywords = ['once daily', 'twice daily', 'thrice daily', 'every 6 hours', 
                            'every 8 hours', 'every 12 hours', 'as needed', 'bd', 'tid', 'qid']
        for freq in frequency_keywords:
            if freq.lower() in text.lower():
                entities['frequencies'].append(freq)

        # Extract route patterns
        route_keywords = ['oral', 'iv', 'im', 'subcutaneous', 'topical', 'inhalation', 
                         'rectal', 'transdermal', 'po', 'sc']
        for route in route_keywords:
            if route.lower() in text.lower():
                entities['routes'].append(route)

        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))

        return entities

    def process_prescription(self, text):
        """
        Process complete prescription and extract structured information
        Args:
            text: Prescription text

        Returns:
            dict: Structured prescription data
        """
        entities = self.extract_entities(text)

        prescription_data = {
            'raw_text': text,
            'medications': entities['medications'],
            'doses': entities['doses'],
            'routes': entities['routes'],
            'frequencies': entities['frequencies'],
            'instructions': entities['instructions']
        }

        return prescription_data


# Initialize NER model when module loads
try:
    ner_model = InitiateNER(gpu=False)  # Set gpu=True if you have CUDA
except Exception as e:
    print(f"Error initializing NER: {e}")
    ner_model = None
