import torch

# torch.tensor

#1 direct creation from data
data = [[1, 2, 3], [4, 5, 6]]
my_tensor = torch.tensor(data)
# output:
# tensor([[1, 2, 3],
#         [4, 5, 6]])

#2 creation from a desired shape
shape = (2, 3)
ones = torch.ones(shape)
random = torch.random(shape)
print(ones)
print(random)