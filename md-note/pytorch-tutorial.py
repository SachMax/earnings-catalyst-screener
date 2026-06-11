import torch

dropout_layer = torch.nn.Dropout(p=0.5)
input_tensor = torch.ones(1, 10)

dropout_layer.train()
output_during_train = dropout_layer(input_tensor)

dropout_layer.eval()
output_durung_eval = dropout_layer(input_tensor)

print(f"\ntrain: {output_during_train}")
print(f"\neval: {output_durung_eval}")
