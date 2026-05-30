# Using numpy Module

## Multidimensional Arrays
### Making a numpy array
```python
import numpy as np
array = np.array([1,2,3]) # simple
```

### dimensions in numpy
```python
import numpy as np
array0 = np.array([1]) #0d
array1 = np.array([1,2,3]) #1d
array2 = np.array([[1,2,3], [1,2,3], [1,2,3]]) #2d or matrix
print(array.ndim) # output = 0
print(array2.shape) # output = (3, 3) return a tuple
print(array2[0][0]) # output = 1 (chain indexing), catching the a00 element in the matrix basically
print(array2[0,0]) # output = 1 (multidimensional indexing, much faster)
```

## Slicing
###
```python
# array[start:end:step]
array2 = np.array([[1,2,3], [1,2,3], [1,2,3]])
print(array2[0:3]) #returns all row in this case
print(array2[0:3:2]) #returns 1st and last rows
print(array[:,0]) # returns a list of every row with index 0
print(array[0:2, 0:2]) # returns a 2x2 matrix 
```

## Numpy Operations
All arithmetic operations is going to be apply for each index. Hence,
### arithmetic operations
```python
array1 = np.array([1,2,3])
array1 + 1 #= [2,3,4] same with *,-,/,**
```

### vectorized math func
```python
array1 = np.array([1,2,3])
print(np.sqrt(array1)) # returns an np array with sqrt of each element of the array
```

### comparison operators
returns a bool
```python
array1 = np.array([1,2,3])
print(array1 > 1) #= [False True True]
#for all python comparison operators such as <, >, ==, !=, and etc
```
you can also do this:
```python
array1 = np.array([1,2,3])
array1[array1 > 1] = 0
print(array1) #= [1,0,0]  
```

## broadcasting
this literally means basic matrix multiplication
```python
array1 = np.array([1,2,3]) # 1x3 matrix
array2 = np.array([[1],[2],[3]]) # 3x1 matrix
print(array1 * array2)
# output:
[[1 2 3]
 [2 4 6]
 [3 6 9]]
```

## aggregate funcs
.mean(), .sum(), .agg(), .var(), .std(), and etc

## Filtering
Super Important
```python
array1 = np.array([[1,2,3,4,5], [6,7,8,9,10]])
array2 = array1[(array1 > 6) | (array1 < 3)] #brackets are important, you can also use & instead of |
print(array2) #=[ 1  2  7  8  9 10]
print(array1[array1%2 == 0]) #returns all even numbers
```
### the .where() func
```python
# .where(condition, array, value thats going to replace the numbers)
array1 = np.array([[1,2,3,4,5], [6,7,8,9,10]])
print(np.where(array1 > 7, array1, 0))
# output:
[[ 0  0  0  0  0]
 [ 0  0  8  9 10]]
```

## random numbers
```python
rng = np.random_default.rng(seed = 1) # you can also set a seed to reproduce the same output
print(rng.integers(low=1, high=7, size = (3, 2)))#returns a 3x2 matrix filled with random numbers between 1 to 6 
```