# Using HuggingFace 
##  NLP and LLM
nlp is a field with several main problems such as:
- Text Classification, 
- Sentiment Analysis, 
- Translation, 
- Summarization, 
- Named Entity Recognition, 
- Question Answering, 
- Chatbots, 
and there are several solutions too such as: 
1. Rules 
2. Traditional Machine Learning 
3. Deep Learning:
    - CNNs
    - RNNs
    - LSTMs
    - Transformers:
        - LLM (most popular currently)

## Transformers
### `pipeline()` function
the most high-level API function: \
pre-processing -> model -> post-processing

Simple pipeline code:
```python
from transformers import pipeline

classifier = pipeline("sentiment-analysis")
classifier([
    "OMG, this sport is not really tiring",
    "Lets play again, it's so fun"
])
output:
[{'label': 'NEGATIVE', 'score': 0.9996267557144165},
 {'label': 'POSITIVE', 'score': 0.9998751878738403}]
```

there are a lot of default APIs you can input to the pipeline:
1. "sentiment-analysis"
2. "zero-shot-classification"
3. "text-generation"
4. "fill-mask": fill missing words
5. "summarization"
6. "ner" (name entity recognition)
7. and more, just search on the official web

the default model is GPT-2, but there are many models you can use

### `AutoTokenizer`
```python
from transformers import AutoTokenizer

checkpoint = "distilbert-base-uncased-finetuned-sst-2-english"

# downloads the tokenizer associated with BERT
tokenizer = AutoTokenizer.from_pretrained(checkpoint)

raw_inputs = [
    "I've been waiting for a HuggingFace course my whole life.",
    "I hate this so much!",
]
inputs = tokenizer(raw_inputs, padding=True, truncation=True, return_tensors="pt")
print(inputs)

output:
{
    'input_ids': tensor([
        [  101,  1045,  1005,  2310,  2042,  3403,  2005,  1037, 17662, 12172, 2607,  2026,  2878,  2166,  1012,   102],
        [  101,  1045,  5223,  2023,  2061,  2172,   999,   102,     0,     0,     0,     0,     0,     0,     0,     0]
    ]), 
    'attention_mask': tensor([
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    ])
}
```
- checkpoint: name of the pre-trained model
- models always only accept tensors
- padding parameter:
    ```python
    encoded_input = tokenizer(
    ["How are you?", "I'm fine, thank you!"], padding=True, return_tensors="pt"
    )
    print(encoded_input)

    {'input_ids': tensor([[  101,  1731,  1132,  1128,   136,   102,     0,     0,     0,     0],
         [  101,  1045,  1005,  1049,  2503,   117,  5763,  1128,   136,   102]]), 
    'token_type_ids': tensor([[0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]), 
    'attention_mask': tensor([[1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]])}
    ```
- truncation parameter is just to truncate sequences, if they are longer than the model can handle (512 tokens)

You can also decode the tokenized inputs with:
`tokenizer.decode(encoded_input["input_ids"])`

#### AutoTokenizer Pipeline
```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")

sequence = "Using a Transformer network is simple"
tokens = tokenizer.tokenize(sequence) # ['Using', 'a', 'transform', '##er', 'network', 'is', 'simple']

ids = tokenizer.convert_tokens_to_ids(tokens) # [7993, 170, 11303, 1200, 2443, 1110, 3014]
```

---
---

### download our pretrained model (`AutoModel`)
actually AutoModel is the base transformer, you need to use best AutoModel for certain cases.
- Model (retrieve the hidden states)
- ForCausalLM
- ForMaskedLM
- ForMultipleChoice
- ForQuestionAnswering
- ForSequenceClassification
- ForTokenClassification
- and others 🤗

```python
from transformers import AutoModelForSequenceClassification
#for example
inputs = {
    "input_ids":,
    "attention_mask": [1, 1, 1, 1, 1]
}

checkpoint = "distilbert-base-uncased-finetuned-sst-2-english"
model = AutoModelForSequenceClassification.from_pretrained(checkpoint)
outputs = model(**inputs) 
# **inputs = unpacks all key & vales in a dict
# outputs = model(input_ids=[101, 2054, 2003, 1037, 102], attention_mask=[1, 1, 1, 1, 1])

```

### to save/load your pre-trained model or tokenizer
- `model.save_pretrained("directory_on_my_computer")`
- `model = AutoModel.from_pretrained("directory_on_my_computer")`
- `tokenizer.save_pretrained("directory_on_my_computer")`

## Fine-tuning a Model
### Processing Data
```python
import torch
from torch.optim import AdamW
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Same as before
checkpoint = "bert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForSequenceClassification.from_pretrained(checkpoint)
sequences = [
    "I've been waiting for a HuggingFace course my whole life.",
    "This course is amazing!",
]
batch = tokenizer(sequences, padding=True, truncation=True, return_tensors="pt")

# This is new
batch["labels"] = torch.tensor([1, 1])

optimizer = AdamW(model.parameters())
loss = model(**batch).loss
loss.backward()
optimizer.step()
```

### Datasets
```python
from datasets import load_dataset
import torch
from transformers import AutoTokenizer

ds = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1")
checkpoint = "distilbert-base-uncased-finetuned-sst-2-english"
tokenizer = AutoTokenizer.from_pretrained(checkpoint)

def tokenize_func (sentence):
    return tokenizer(sentence['text'], padding=True, truncation=True, return_tensors="pt")

tokenized_ds = ds.map(tokenize_func)
tokenized_ds.column_names
# {'test': ['text', 'input_ids', 'token_type_ids', 'attention_mask'],
#  'train': ['text', 'input_ids', 'token_type_ids', 'attention_mask'],
#  'validation': ['text', 'input_ids', 'token_type_ids', 'attention_mask']}
tokenized_ds.remove_columns(['text'])
tokenized_ds.with_format("torch")
tokenized_ds
# DatasetDict({
#     test: Dataset({
#         features: ['text', 'input_ids', 'token_type_ids', 'attention_mask'],
#         num_rows: 4358
#     })
#     train: Dataset({
#         features: ['text', 'input_ids', 'token_type_ids', 'attention_mask'],
#         num_rows: 36718
#     })
#     validation: Dataset({
#         features: ['text', 'input_ids', 'token_type_ids', 'attention_mask'],
#         num_rows: 3760
#     })
# })
```

#### Fixed Padding
```python
import torch
from transformers import AutoTokenizer
from datasets import load_dataset
from torch.utils.data import DataLoader

ds = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1")
checkpoint = "distilbert-base-uncased-finetuned-sst-2-english"
tokenizer = AutoTokenizer.from_pretrained(checkpoint)

def tokenize_func (sentence):
    return tokenizer(sentence['text'], padding = "max_length", truncation=True, return_tensors="pt", max_length=128)

tokenized_ds = ds.map(tokenize_func, batched=True)
tokenized_ds = tokenized_ds.remove_columns(['text'])
tokenized_ds = tokenized_ds.with_format("torch")

train_ds = DataLoader(tokenized_ds['train'], batch_size=16, shuffle=True)

for step, batch in enumerate(train_ds):
    print(batch['input_ids'].shape)
    if step > 5:
        break
# torch.Size([16, 128])
# torch.Size([16, 128])
# torch.Size([16, 128])
# torch.Size([16, 128])
# torch.Size([16, 128])
# torch.Size([16, 128])
# torch.Size([16, 128])
```

#### Dynamic Padding
```python
import torch
from transformers import AutoTokenizer, DataCollatorWithPadding
from datasets import load_dataset
from torch.utils.data import DataLoader

ds = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1")
checkpoint = "distilbert-base-uncased-finetuned-sst-2-english"
tokenizer2 = AutoTokenizer.from_pretrained(checkpoint)

def tokenize_func_new (sentence):
    return tokenizer2(sentence['text'], truncation=True)

tokenized_ds2 = ds.map(tokenize_func_new, batched=True)
tokenized_ds2 = tokenized_ds2.remove_columns(['text'])
tokenized_ds2 = tokenized_ds2.with_format("torch")

data_collator = DataCollatorWithPadding(tokenizer2)
train_dataloader = DataLoader(tokenized_ds2['train'], batch_size=16, shuffle=True, collate_fn=data_collator)

for step, batch in enumerate(train_dataloader):
    print(batch['input_ids'].shape)
    if step > 5:
        break

# torch.Size([16, 319])
# torch.Size([16, 350])
# torch.Size([16, 118])
# torch.Size([16, 237])
# torch.Size([16, 235])
# torch.Size([16, 466])
# torch.Size([16, 259])
```

### Training and Eval
```python
import torch
from transformers import AutoTokenizer, DataCollatorWithPadding, AutoModelForSequenceClassification
from datasets import load_dataset
from torch.utils.data import DataLoader
from transformers import TrainingArguments, Trainer
import evaluate
import numpy as np

ds_glue = load_dataset("nyu-mll/glue", "cola")
checkpoint = "distilbert-base-uncased-finetuned-sst-2-english"
tokenizer2 = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForSequenceClassification.from_pretrained(checkpoint)

def tokenize_func_new (sentences):
    return tokenizer2(sentences['sentence'], truncation=True)

tokenized_ds2 = ds_glue.map(tokenize_func_new, batched=True)

data_collator = DataCollatorWithPadding(tokenizer2)
training_args = TrainingArguments(
    "test-trainer", 
    num_train_epochs=5, 
    learning_rate=2e-5, 
    weight_decay=0.01, 
    per_device_train_batch_size=16, 
    per_device_eval_batch_size=16,
    eval_strategy="epoch",   
    gradient_accumulation_steps=4,
    lr_scheduler_type="cosine",
    fp16=True
    #still many hyperparemeters
)

def compute_metrics(eval_preds):
    # 1. Load the accuracy metric
    metric = evaluate.load("glue", "cola")
    
    # 2. Unpack the predictions and the true labels
    logits, labels = eval_preds
    
    # 3. Convert raw model logits into class IDs (0 or 1)
    preds = np.argmax(logits, axis=-1)
    
    # 4. Compute and return the results as a dictionary
    return metric.compute(predictions=preds, references=labels)

trainer = Trainer(
    model,
    training_args,
    train_dataset=tokenized_ds2["train"],
    eval_dataset=tokenized_ds2["validation"],
    data_collator=data_collator,
    processing_class=tokenizer2,
    compute_metrics= compute_metrics,
)

trainer.train()

```
Output:

| Epoch | Training Loss | Validation Loss | Matthews Correlation |
|-------|---------------|-----------------|----------------------|
| 1     | No log        | 0.515513        | 0.356453             |
| 2     | No log        | 0.485889        | 0.426621             |
| 3     | No log        | 0.523402        | 0.458734             |
| 4     | 1.784129      | 0.551524        | 0.469735             |
| 5     | 1.784129      | 0.549046        | 0.468431             |
### Training Hyperparameters

`training_args = TrainingArguments(...)`: Initializes a configuration object containing instructions for the training loop.

* **`"test-trainer"`**: Name of the directory where checkpoints are saved.
* **`num_train_epochs=5`**: Total number of full training passes through data.
* **`learning_rate=2e-5`**: Maximum step size used during weight updates.
* **`weight_decay=0.01`**: Regularization penalty to prevent model overfitting.
* **`per_device_train_batch_size=16`**: Samples processed per GPU during training.
* **`per_device_eval_batch_size=16`**: Samples processed per GPU during evaluation.
* **`eval_strategy="epoch"`**: Cadence control for triggering validation cycles.
* **`gradient_accumulation_steps=4`**: Number of steps before updating weights.
* **`lr_scheduler_type="cosine"`**: Pattern used to decrease the learning rate.
* **`fp16=True`**: Activates semi-precision floats to reduce memory.

### Full Training Set
```python
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    DataCollatorWithPadding,
    get_scheduler
)
from torch.utils.data import DataLoader
from torch.optim import AdamW
from tqdm.auto import tqdm
import evaluate
import sys # since i use google colab, the python --version seems not updated -> cant import torchvision.io.VideoReader
sys.modules.pop("torchvision", None)
# -----------------------
# Dataset
# -----------------------

# loads the data set 
raw_datasets = load_dataset("nyu-mll/glue", "cola")
checkpoint = "distilbert-base-uncased-finetuned-sst-2-english"
tokenizer3 = AutoTokenizer.from_pretrained(checkpoint)

def tokenize_fn (phrases):
    return tokenizer3(phrases['sentence'], truncation=True)

tokenized_data = raw_datasets.map(tokenize_fn, batched=True)
tokenized_data = tokenized_data.remove_columns(['sentence', 'idx'])
tokenized_data = tokenized_data.rename_column('label', 'labels')
tokenized_data.set_format("torch")
Data_Collator = DataCollatorWithPadding(tokenizer=tokenizer3)

DataTrainLoader = DataLoader(tokenized_data['train'], shuffle=True, batch_size=8, collate_fn=Data_Collator)
DataEvalLoader = DataLoader(tokenized_data['validation'], batch_size=8, collate_fn=Data_Collator)

model = AutoModelForSequenceClassification.from_pretrained(checkpoint)

device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
model.to(device)

Optimizer = AdamW(model.parameters(), lr=2e-5)

epochs = 3

num_training_steps = epochs * len(DataTrainLoader)

lr_optimizer = get_scheduler(
    name="linear",
    optimizer=Optimizer,
    num_warmup_steps=0,
    num_training_steps=num_training_steps
)

progress_bar = tqdm(range(num_training_steps))

for epoch in range(epochs):

    model.train()

    metric_train = evaluate.load("glue", "cola")

    running_loss = 0

    for batch in DataTrainLoader:

        batch = {
            k: v.to(device)
            for k, v in batch.items()
        }

        Optimizer.zero_grad()

        outputs = model(**batch)

        loss = outputs.loss

        loss.backward()

        Optimizer.step()

        lr_optimizer.step()

        running_loss += loss.item()

        preds = torch.argmax(
            outputs.logits,
            dim=-1
        )

        metric_train.add_batch(
            predictions=preds,
            references=batch["labels"]
        )

    train_metrics = metric_train.compute()

    print(
        f"Epoch {epoch+1} | "
        f"Loss: {running_loss/len(DataTrainLoader):.4f} | "
        f"Metrics: {train_metrics}"
    )

# output:
# Epoch 1 | Loss: 0.5687 | Metrics: {'matthews_correlation': np.float64(0.23536268713446049)}
# Epoch 2 | Loss: 0.3540 | Metrics: {'matthews_correlation': np.float64(0.621151182595149)}
# Epoch 3 | Loss: 0.1879 | Metrics: {'matthews_correlation': np.float64(0.829995698058496)}

model.save_pretrained("./my_bert_model")

tokenizer3.save_pretrained("./my_bert_tokenizer")


# ------------------
# Evaluation
# ------------------
metric = evaluate.load("glue", "cola")
model.eval()
for batches in DataEvalLoader:
    batches = {k: v.to(device) for k, v in batches.items()}

    with torch.no_grad():
        eval_output = model(**batches)

    logits = eval_output.logits
    preds = torch.argmax(logits, dim=-1)
    metric.add_batch(predictions=preds, references=batches["labels"])
results = metric.compute()
print(results)
# output: {'matthews_correlation': np.float64(0.5069898363255262)}
```
