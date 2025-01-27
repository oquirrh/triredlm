from transformers import AutoModelForCausalLM, AutoTokenizer

class LLM:
    def __init__(self, model_name="distilgpt2"): # Using distilgpt2 as a lighter alternative to distilbert
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        # Ensure the padding token is set if not already defined
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Set the model to evaluation mode
        self.model.eval()

    def generate_text(self, prompt, max_length=100):
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