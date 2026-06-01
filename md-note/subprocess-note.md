# Using the Python subprocess Module

## Overvie of subprocess Module
- for launching process from/within python, process can be a app or even a powershell
- `run()` recommended but `Popen()` for edge cases requiring more control
## Basic Usage of the subprocess Module
```python
import subprocess
subprocess.run(["python", "file_name"])
```