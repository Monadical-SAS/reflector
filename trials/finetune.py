import subprocess

# subprocess.run("openai tools fine_tunes.prepare_data -f " + "finetuning_dataset.jsonl")
#
# export OPENAI_API_KEY=
#
# openai api fine_tunes.create -t <TRAIN_FILE_ID_OR_PATH> -m <BASE_MODEL>
#
# openai api fine_tunes.list


import torch
from transformers import GPT2Tokenizer, GPT2LMHeadModel, GPT2Config, Trainer, TrainingArguments

# Load the GPT-2 tokenizer and model
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
model = GPT2LMHeadModel.from_pretrained("gpt2")

# Load and preprocess your dataset
dataset = [...]  # Your dataset of transcriptions and corresponding titles

# Tokenize and encode the dataset
encoded_dataset = tokenizer(dataset, truncation=True, padding=True)

# Define the fine-tuning training arguments
training_args = TrainingArguments(
    output_dir="./fine_tuned_model",
    overwrite_output_dir=True,
    num_train_epochs=3,
    per_device_train_batch_size=4,
    save_steps=1000,
    save_total_limit=2,
    prediction_loss_only=True,
)

# Define the fine-tuning trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=encoded_dataset,
)

# Fine-tune the GPT-2 model
trainer.train()

# Save the fine-tuned model
trainer.save_model("./fine_tuned_model")
