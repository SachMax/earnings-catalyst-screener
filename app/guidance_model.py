print("start")
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    DataCollatorWithPadding, 
    get_scheduler
    )
print("trans")
import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader
print("torch")
from datasets import Dataset, DatasetDict
print("dataset")
from tqdm.auto import tqdm
print("tqdm")
import pandas as pd
import sqlite3
print("sql")
from accelerate import Accelerator
print("accl")
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, matthews_corrcoef, log_loss, average_precision_score)
print("metr")
conn = sqlite3.connect("data/universe.db")
raw_data = pd.read_sql(f"""
    SELECT * FROM guidance_dataset
    WHERE text != '' and label is not NULL
    ORDER BY earnings_date ASC
""", conn, parse_dates=['earnings_date'])
conn.close()

# -------------------
# Dataset
# -------------------
split_idx = int(len(raw_data) * 0.8)

train_df = raw_data.iloc[:split_idx]
test_df = raw_data.iloc[split_idx:]

print("1. Loaded SQL data")

train_dataset = Dataset.from_pandas(train_df)
test_dataset = Dataset.from_pandas(test_df)
dataset_dict = DatasetDict({"train": train_dataset, "test": test_dataset})
# -------------------
# Tokenization
# -------------------
checkpoint = "ProsusAI/finbert"
tokenizer = AutoTokenizer.from_pretrained(checkpoint)

def tokenize_func (sentences):
    return tokenizer(sentences["text"], truncation=True)

print("2. Created HF datasets")

tokenized_data = dataset_dict.map(tokenize_func)
print("3. Finished tokenization")

tokenized_data = tokenized_data.remove_columns(['ticker', 'earnings_date', 'text'])
print("4. Removed columns")
tokenized_data = tokenized_data.rename_column('label', 'labels')
tokenized_data.set_format('torch')

Data_Collator = DataCollatorWithPadding(tokenizer=tokenizer)
DataTrainLoader = DataLoader(tokenized_data['train'], batch_size=8, shuffle=True, collate_fn=Data_Collator)
DataTestLoader = DataLoader(tokenized_data['test'], batch_size=8, shuffle=True, collate_fn=Data_Collator)
print("5. Created dataloader")
# Model
model = AutoModelForSequenceClassification.from_pretrained(checkpoint, num_labels=2, ignore_mismatched_sizes=True)
print("6. Loaded model")
Optimizer = AdamW(model.parameters(), lr=2e-5)

# Accelerate
accelerator = Accelerator()
print("7. Created accelerator")
model, Optimizer, DataTrainLoader, DataTestLoader = accelerator.prepare(model, Optimizer, DataTrainLoader, DataTestLoader)
print("8. Finished accelerator.prepare()")
epochs = 5

num_training_steps = epochs * len(DataTrainLoader)

lr_optimizer = get_scheduler(
    name="linear",
    optimizer=Optimizer,
    num_warmup_steps=0,
    num_training_steps=num_training_steps
)
progress_bar = tqdm(range(num_training_steps))
# -------------------
# Model Training
# -------------------

def model_evaluation (model, dataloader, accelerator):

    was_training = model.training
    model.eval()

    all_preds = []
    all_labels = []
    all_probs = []

    for batch in dataloader:
        with torch.no_grad():
            outputs = model(**batch)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)
        preds = torch.argmax(logits, dim=-1)
        
        all_preds.extend(accelerator.gather(preds).cpu().tolist())
        all_labels.extend(accelerator.gather(batch["labels"]).cpu().tolist())
        all_probs.extend(accelerator.gather(probs[:, 1]).cpu().tolist())
    
    model.train(was_training)

    return  {
        'accuracy'  : accuracy_score(all_labels, all_preds),
        'f1'        : f1_score(all_labels, all_preds, average='binary'),
        'precision' : precision_score(all_labels, all_preds, average='binary'),
        'recall'    : recall_score(all_labels, all_preds, average='binary'),
        'roc_auc'   : roc_auc_score(all_labels, all_probs),
        'mcc'       : matthews_corrcoef(all_labels, all_preds),
        'log_loss'  : log_loss(all_labels, all_probs),
        'pr_auc'    : average_precision_score(all_labels, all_probs)
    }


model.train()

best_f1 = 0.0
best_model_state = None

for epoch in range(epochs):

    running_loss = 0

    for batch in DataTrainLoader:

        Optimizer.zero_grad()
        outputs = model(**batch)
        loss = outputs.loss
        accelerator.backward(loss)
        Optimizer.step()

        lr_optimizer.step()
        progress_bar.update(1)
        running_loss += loss.item()

    train_dict = model_evaluation(model, DataTrainLoader, accelerator)

    print(
        f"Epoch {epoch + 1} | "
        f"Loss: {running_loss/len(DataTrainLoader):.4f} | "
    )
    print(f"Train Set {epoch + 1} Metrics:")
    print(f"  Accuracy:  {train_dict['accuracy']:.4f}")
    print(f"  F1 Score:  {train_dict['f1']:.4f}")
    print(f"  Precision: {train_dict['precision']:.4f}")
    print(f"  Recall:    {train_dict['recall']:.4f}")
    print(f"  ROC AUC:   {train_dict['roc_auc']:.4f}")
    print(f"  MCC:       {train_dict['mcc']:.4f}")
    print(f"  log_loss:  {train_dict['log_loss']:.4f}")
    print(f"  PR AUC:    {train_dict['pr_auc']:.4f}")

    if train_dict['f1'] > best_f1:
        best_f1 = train_dict['f1']
        best_model_state = accelerator.unwrap_model(model).state_dict()
        # Save immediately
        accelerator.unwrap_model(model).save_pretrained("./my_guidance_model")
        tokenizer.save_pretrained("./my_guidance_tokenizer")
        print(f"  → New best F1: {best_f1:.4f}, model saved.")

model.eval()
eval_dict = model_evaluation(model, DataTestLoader, accelerator)

print("Test Set Metrics:")
print(f"  Accuracy:  {eval_dict['accuracy']:.4f}")
print(f"  F1 Score:  {eval_dict['f1']:.4f}")
print(f"  Precision: {eval_dict['precision']:.4f}")
print(f"  Recall:    {eval_dict['recall']:.4f}")
print(f"  ROC AUC:   {eval_dict['roc_auc']:.4f}")
print(f"  MCC:       {eval_dict['mcc']:.4f}")
print(f"  log_loss:  {eval_dict['log_loss']:.4f}")
print(f"  PR AUC:    {eval_dict['pr_auc']:.4f}")