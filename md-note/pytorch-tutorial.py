import torch

# Input: 10 data points, each with 1 feature
N = 10
D_in = 1   # input dimension
D_out = 1  # output dimension

X = torch.randn(N, D_in)          # shape (10,1) – no gradient needed
# True underlying relationship: y = 2*x + 1 + small noise
true_W = torch.tensor([[3.0]])
true_b = torch.tensor(1.0)
y_true = X @ true_W + true_b + torch.randn(N, D_out) * 0.1

# Backward pass: compute gradients of loss w.r.t W and b
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
    
    # Backward pass
    loss.backward()
    
    # Update parameters
    with torch.no_grad():
        W -= learning_rate * W.grad
        b -= learning_rate * b.grad
    
    # Zero gradients
    W.grad.zero_()
    b.grad.zero_()
    
    if (epoch+1) % 5 == 0:
        print(f"Epoch {epoch+1:3d}, Loss: {loss.item():.4f}, W: {W.item():.4f}, b: {b.item():.4f}")