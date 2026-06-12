# Using PyTorch
`import torch`

## torch.tensor
### PATTERN 1: Direct Creation From Data
```python
data = [[1, 2, 3], [4, 5, 6]]
my_tensor = torch.tensor(data)
# output:
# tensor([[1, 2, 3],
#         [4, 5, 6]])
```

### PATTERN 2: Creation From A Desired Shape
You know the shape you need, but not the values yet.
This is how you initialize model weights
```python
shape = (2, 3) # needs to be a tuple
ones = torch.ones(shape) # fill 2x3 df with 1
zeros = torch.zeros(shape) # same but with 0
random = torch.randn(shape) # same but with random float number
# output :
# tensor([[ 2.5166,  0.6121,  0.6268],
#        [ 1.7970, -2.2272,  0.8111]])
```

### PATTERN 3: Creation by Mimicking Other Tensors
creating a new tensor with same shape and type
```python
data = [[1, 2], [4, 5]]
my_tensor = torch.tensor(data)
rand_like = torch.randn_like(my_tensor, dtype=float)
print(rand_like)
# output:
# tensor([[2.1044, 0.4485],
#         [0.8138, 0.7506]], dtype=torch.float64)
```

### Critical Attributes of Tensor
1. `.shape`
2. `.dtype`
3. `.device`

```python
data = [[1, 2, 3], [4, 5, 6]]
my_tensor = torch.tensor(data)
rand_like = torch.randn_like(my_tensor, dtype=float)
print(rand_like.shape) # torch.Size([2, 3])
print(rand_like.dtype) # torch.float64
print(rand_like.device) # cpu
```

### Most important setting in pytorch
the parameter `requires_grad: True` when you are creating a tensor, this allows the pytorch's autograd system to track every single operations that has happened to that certain parameter
- It builds a computational graph behind the scenes.
- Later, when you call .backward() on the final result (e.g., a loss), PyTorch automatically computes the gradients of that result with respect to every tensor that has requires_grad=True.
- kThese gradients are stored in the .grad attribute of each such tensor.

## operations in PyTorch
### Element-Wise Multiplication (`*`)
Multiplies matching position
```python
data =  torch.tensor([[1, 2], [3, 4]])
print(data * data)
# Output:
# tensor([[ 1,  4],
#         [ 9, 16]])
```
### Matrix Multiplication (`@`)
```python
# Prove using matrix A @ A^-1 = I
data = [[1.0, 2.0], [3.0, 4.0]]
data2 =  torch.tensor([[-2, 1], [1.5, -0.5]])
print(my_tensor @ data2)
# Output:
# tensor([[1., 0.],
#         [0., 1.]])
```

### Reduction Operation (mean/std/sum/...)
```python
scores = torch.tensor([[9.0, 6.0, 10.0], [8.0, 3.0, 8.0]])
avg_per_assignment = scores.mean(dim=0) # Based on column
avg_per_student = scores.mean(dim=1) # Based on row
print(avg_per_assignment)
print(avg_per_student)
# Output:
# tensor([8.5000, 4.5000, 9.0000])
# tensor([8.3333, 6.3333])
```

### Basic Indexing
works just like numpy
```python
data = torch.arange(12).reshape(3, 4)
print(data) # make a tensor with values 0:11
# tensor([[ 0,  1,  2,  3],
#         [ 4,  5,  6,  7],
#         [ 8,  9, 10, 11]])
print(data[:, 2])
# tensor([ 2,  6, 10])
```

### Dynamic Selection: `argmax`
```python
scores = torch.tensor([[10, 2, 5, 3, 20], [20, 30, 15, 4, 50]])
print(scores.argmax(dim=1)) # find the index of the highest value 
# Output: tensor([4, 4])
```

### to gather specific value in a tensor (`torch.gather()`)
same purpose as pandas.loc() function
```python
scores = torch.tensor([[70, 2, 5, 3, 20], [20, 30, 15, 4, 25], [1, 4, 6, 8, 90]])
indicies_to_select = torch.tensor([[0], [1], [4]])
selected_values = torch.gather(input=scores, dim=1, index=indicies_to_select) # index should also be a tensor
print(selected_values)
#  Output:
# tensor([[70],
#         [30],
#         [90]])
```

## The Basic step by step 
```python
import torch

# Input: 10 data points, each with 1 feature
N = 10 
D_in = 1   # input dimension y
D_out = 1  # output dimension x

X = torch.randn(N, D_in)          # shape (10,1) – no gradient needed
# True underlying relationship: y = 2*x + 1 + small noise
true_W = torch.tensor([[3.0]]) # shouldnt use the requires_grad
true_b = torch.tensor(1.0) # shouldnt use the required_grad, let the machine learns
y_true = X @ true_W + true_b + torch.randn(N, D_out) * 0.1 # same here

# set initial value, should use randn
W = torch.randn(1, 1, requires_grad=True)
b = torch.randn(1, requires_grad=True)
print("Initial W:", W.item())
print("Initial b:", b.item())
epochs = 100
learning_rate = 0.1

for epoch in range(epochs):
    # Forward pass
    y_pred = X @ W + b
    loss = torch.mean((y_pred - y_true) ** 2)
    
    # Backward pass, let the system compute grad it self for every parameter
    loss.backward()
    
    # Update parameters (W and b) without upfating the grad
    with torch.no_grad():
        W -= learning_rate * W.grad
        b -= learning_rate * b.grad
    
    # Zero gradients
    W.grad.zero_() 
    b.grad.zero_()
    # this is so that the grad stays the same, because if these lines aren't provided, the grad will be culmulated each time W updates
    
    if (epoch+1) % 5 == 0:
        print(f"Epoch {epoch+1:3d}, Loss: {loss.item():.4f}, W: {W.item():.4f}, b: {b.item():.4f}")

# Output:
# Initial W: 0.7318637371063232
# Initial b: 1.672831654548645
# Epoch   5, Loss: 0.6066, W: 2.5185, b: 1.3230
# Epoch  10, Loss: 0.0503, W: 2.8597, b: 1.1360
# Epoch  15, Loss: 0.0153, W: 2.9297, b: 1.0607
# Epoch  20, Loss: 0.0121, W: 2.9455, b: 1.0330
# Epoch  25, Loss: 0.0118, W: 2.9495, b: 1.0232
# Epoch  30, Loss: 0.0118, W: 2.9506, b: 1.0198
# Epoch  35, Loss: 0.0118, W: 2.9509, b: 1.0186
# Epoch  40, Loss: 0.0118, W: 2.9511, b: 1.0183
# Epoch  45, Loss: 0.0118, W: 2.9511, b: 1.0181
# Epoch  50, Loss: 0.0118, W: 2.9511, b: 1.0181
# Epoch  55, Loss: 0.0118, W: 2.9511, b: 1.0181
# Epoch  60, Loss: 0.0118, W: 2.9511, b: 1.0180
# Epoch  65, Loss: 0.0118, W: 2.9511, b: 1.0180
# Epoch  70, Loss: 0.0118, W: 2.9511, b: 1.0180
# Epoch  75, Loss: 0.0118, W: 2.9511, b: 1.0180
# Epoch  80, Loss: 0.0118, W: 2.9511, b: 1.0180
# Epoch  85, Loss: 0.0118, W: 2.9511, b: 1.0180
# Epoch  90, Loss: 0.0118, W: 2.9511, b: 1.0180
# Epoch  95, Loss: 0.0118, W: 2.9511, b: 1.0180
# Epoch 100, Loss: 0.0118, W: 2.9511, b: 1.0180
```
this method actually uses the foundation of MLE and optimization.

## torch.nn
backbone of every professional model
### torch.nn.linear (y = Wx + b)
Same with the previous but you don't need to set a loose parameter W and b because it already packages them inside a professional object.
```python
import torch

# Input: 10 data points, each with 1 feature
D_in = 1   # input dimension
D_out = 1  # output dimension

linear_layer = torch.nn.Linear(in_features=D_in, out_features=D_out)

print(f"w: {linear_layer.weight}\n")
print(f"b: {linear_layer.bias}\n")

X = torch.randn(10,1)
y_hat_nn = linear_layer(X)
print(y_hat_nn)
# Output:
# w: Parameter containing:
# tensor([[0.2932]], requires_grad=True)

# b: Parameter containing:
# tensor([0.7595], requires_grad=True)

# tensor([[0.5445],
#         [0.3922],
#         [0.6004],
#         [0.6270],
#         [0.8407],
#         [0.9696],
#         [0.5434],
#         [0.9256],
#         [0.9995],
#         [0.8892]], grad_fn=<AddmmBackward0>)
```

### torch.nn.ReLU (Rectified Linear Unit)
basically if an input is negative, make it 0.
```python
relu = torch.nn.ReLU()
sample = torch.tensor([-2.0, -0.5, 0.0, 0.5, 2.0])
activated_data = relu(sample)

print(f"Original: {sample}")
print(f"after ReLU: {activated_data}")

# Original: tensor([-2.0000, -0.5000,  0.0000,  0.5000,  2.0000])

# after ReLU: tensor([0.0000, 0.0000, 0.0000, 0.5000, 2.0000])
```

### torch.nn.GELU (Gaussian Error Linear Unit)
gently squashed negative values, approaching 0
```python
gelu = torch.nn.GELU()
sample = torch.tensor([-2.0, -0.5, 0.0, 0.5, 2.0])
activated_data = gelu(sample)

print(f"Original: {sample}")
print(f"after GELU: {activated_data}")

# Original: tensor([-2.0000, -0.5000,  0.0000,  0.5000,  2.0000])

# after GELU: tensor([-0.0455, -0.1543,  0.0000,  0.3457,  1.9545])
```

### torch.nn.Softmax ()
- used on final output layer for classification 
- to convert raw model scores (logit) into a probability distribution, it means the output value will be between [0, 1] and the sum is 1
```python
softmax = torch.nn.Softmax(dim=-1)
logits = torch.tensor([[1.0, 3.0, 0.5, 1.5], [-1.0, 2.0, 1.0, 0.0]])
probs = softmax(logits)
print(f"probabilities: {probs}")
print(f"item 1 sum: {probs[0].sum()}")

# probabilities: tensor([[0.0939, 0.6942, 0.0570, 0.1549],
#         [0.0321, 0.6439, 0.2369, 0.0871]])
# item 1 sum: 1.0
```

### torch.nn.Embedding (tokenization)
it makes words into numbers (tokenization), essential for LLM
```python
vocab_size = 10 # our language has 10 unique words
embedding_dim = 3 # We'll represent each word with a 3D vector

embedding_layer = torch.nn.Embedding(vocab_size, embedding_dim)

input_ids = torch.tensor([[1, 5, 0, 8]])
word_vectors = embedding_layer(input_ids)
print(word_vectors)
# tensor([[[-1.0864, -1.4390,  2.4351],
#          [ 0.1994,  0.1015, -0.8055],
#          [ 0.4417,  1.3233,  0.3600],
#          [-1.5227, -1.5058, -1.0645]]], grad_fn=<EmbeddingBackward0>)
```

### torch.nn.layerworm
Prevents values from exploding/vanishing, rescales to a stable range, same like preprocessing.StandardScaler in sklearn.
```python
norm_layer = torch.nn.LayerNorm(normalized_shape=3)
input_features = torch.tensor([[[1.0, 3.0, 0.5], [-1.0, 2.0, 1.0]]])
normalized_features = norm_layer(input_features)

print(normalized_features)
print(f"\nMean: {normalized_features.mean(dim=-1)}")
print(f"\nstd: {normalized_features.std(dim=-1)}")
# tensor([[[-0.4629,  1.3887, -0.9258],
#          [-1.3363,  1.0690,  0.2673]]], grad_fn=<NativeLayerNormBackward0>)

# Mean: tensor([[ 1.9868e-08, -5.9605e-08]], grad_fn=<MeanBackward1>)

# std: tensor([[1.2247, 1.2247]], grad_fn=<StdBackward0>)
```

### torch.nn.dropout 
Prevents overfitting by randomly zeros neurons during training
```python
dropout_layer = torch.nn.Dropout(p=0.5)
input_tensor = torch.ones(1, 10)

dropout_layer.train()
output_during_train = dropout_layer(input_tensor)

dropout_layer.eval()
output_durung_eval = dropout_layer(input_tensor)

print(f"\ntrain: {output_during_train}")
print(f"\neval: {output_durung_eval}")
# train: tensor([[0., 2., 2., 2., 2., 0., 2., 0., 0., 2.]])

# eval: tensor([[1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]])
``` 

## Model Blue Print
1. Inherit from torch.nn.Module
2. __init__:Define layers
3. forward:Connect layers
```python
import torch.nn as nn

# Inherit from nn.Module
class LinearRegressionModel(nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()
        # In the constructor, we DEFINE the layers we'll use.
        self.linear_layer = nn.Linear(in_features, out_features)

    def forward(self, x):
        # In the forward pass, we CONNECT the layers.
        return self.linear_layer(x)

# Instantiate the model
model = LinearRegressionModel(in_features=1, out_features=1)
```
