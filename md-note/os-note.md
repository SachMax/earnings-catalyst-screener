# Using os Module
to perform actions against your file such as gathering useful information from ur file and creating or moving directory

## `os.getcwd()`
to get the current working directory path
for ex, C:\Python\app\test

## `os.chdir`
to change directory, it only accepts string arg such as "C:\Python"

## `os.listdir`
to get files inside your current file working directory
for ex,
```python
import os


files = os.listdir(os.getcwd())
print(files)

# Output = ['.env', '.git', '.gitattributes', '.gitignore', '.ruff_cache', '.vscode', 'app', 'archives', 'data', 'md-note', 'migrations', 'models', 'README.md', 'tests'] 
```
you can also use a folder such as `"C:\Users\Sachio\OneDrive\Desktop\earnings-catalyst-screener\data"`
Be careful with path that contains `"\n" | "\t"`. You need to do double slash such as `"C:\\Python\\tut\\os"`

## `os.mkdir()`
to make a new directory, by default, its going to make a new directory inside the file you are working (only single dir)
for ex, `"Test"`
## `os.makedirs(, exist_ok = True)`
to create multiple directory inside a new directory 
for ex, `"Test/Temp/hello"`
the "exist_ok = True" arg is used to always create the directory even if the folder already exists

## os.rmdir("file_path")
 to remove a directory

## `os.path.join()`
 to concatenate multiple file paths (no limit, any type of files)

## `os.path.exists("file_name")`
return a bool whether path exists or not

## `os.path.isfile("file_Name")`
return a bool whether its a file or a folder

## `os.stat("file_name")`
return the file properties or info such as size and more

## `os.environ.get("PATH")`
pulling environment variables

## `os.getlogin()`
to return the user name