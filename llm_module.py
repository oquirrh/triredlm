from transformers import AutoModelForCausalLM, AutoTokenizer
import subprocess

class LLM:
    def __init__(self, model_type="ollama", model_name="distilgpt2"):
        self.model_type = model_type
        self.model_name = model_name
        
        if self.model_type == "ollama":
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            # Ensure the padding token is set if not already defined
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Set the model to evaluation mode
            self.model.eval()
        elif self.model_type == "gemini":
            self.model = None  # Placeholder for Gemini model
            self.tokenizer = None  # Placeholder for Gemini tokenizer
            # Initialize Gemini model here if needed
        else:
            raise ValueError("Unsupported model type. Choose 'ollama' or 'gemini'.")

    def generate_text(self, prompt, max_length=100):
        if self.model_type == "ollama":
            # Encode the prompt with padding
            inputs = self.tokenizer(prompt, return_tensors="pt", padding=True)

            # Generate text with the specified max_length
            outputs = self.model.generate(
                inputs.input_ids,
                attention_mask=inputs.attention_mask,
                max_length=max_length,
                pad_token_id=self.tokenizer.pad_token_id
            )

            # Decode and return the generated text, skipping special tokens
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return generated_text
        elif self.model_type == "gemini":
            # Call the Gemini model using subprocess or appropriate API
            command = f"ollama run {self.model_name} '{prompt}' --max-length {max_length}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout.strip()
        else:
            raise ValueError("Unsupported model type. Choose 'ollama' or 'gemini'.")