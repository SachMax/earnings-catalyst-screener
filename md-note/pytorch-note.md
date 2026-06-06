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