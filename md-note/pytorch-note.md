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

### Important Stuff in Tensors
1. the parameter `requires_grad: True` when you are creating a tensor, 