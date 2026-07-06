# Batch Scripting Notes

---

## Basic Commands

```bat
@echo off
REM to stop files repeating itself

title my first batch file

:a
REM this is just a marker

echo hello world
pause
REM to stop it from closing the program display

cls
REM to clear the first run (before pause)

echo first
echo second
pause

goto :a
REM basically go to that marker, therefore creating a loop
```

---

## The `start` Command

```bat
@echo off
title my second batch file

start https://google.com
REM opens google on your default browser

start testing.txt
REM opens the file because it's in the same folder as the batch file

REM if it's not in the same folder, simply use the absolute path
```

---

## User Input

```bat
@echo off
title My first Batch file

set input=1
REM without this, the program would still run

echo Press 1 to say hi
echo Press 2 to say bye

set /p input=
REM gets user input and stores it in variable "input"

if %input%==1 goto hi
if %input%==2 goto bye

:hi
echo hi
pause
exit

:bye
echo bye
pause
exit
```

---

## Directories, Delete, Copy, Rename

```bat
@echo off
title My first Batch file

echo hello! > hello.txt
REM overwrite hello.txt

echo hello! >> hello.txt
REM append instead of overwrite

del C:\onedrive\desktop\hello.txt
REM delete file

copy C:\onedrive\desktop\hello.txt C:\onedrive\desktop\hi.txt

ren C:\onedrive\desktop\hello.txt hi.txt
REM rename hello.txt to hi.txt
```

---

## Comparison Operators

```bat
@echo off
title My first Batch file

set /a num=15
REM arithmetic variable

set string=standard string
set /a number=1
set /p num=

:: Checks if num is between 10 and 20
if %num% GTR 10 if %num% LSS 20 (
    echo The number is between 10 and 20.
    pause
)

if not %num% GTR 10 if %num% LSS 20 (
    echo The number is not between 10 and 20.
    pause
)

set /a number=%num% * 10

if %number%==100 (
    echo Your number is 10
) else (
    echo Your number is not 10
)

pause

:: Operators
:: GTR = >
:: LSS = <
:: GEQ = >=
:: LEQ = <=
:: EQU = ==
:: NEQ = !=
```

---

## Custom Pause / Animation

```bat
@echo off
title My first Batch file

echo paused
ping localhost -n 2 >nul
cls

echo loading.
ping localhost -n 2 >nul
cls

echo loading..
ping localhost -n 2 >nul
cls

echo loading...
ping localhost -n 2 >nul
cls

echo loading.
ping localhost -n 2 >nul
cls

echo loading..
ping localhost -n 2 >nul
cls

echo loading...
ping localhost -n 2 >nul

echo done
pause
```

## How `ping` Creates a Delay

### 1. `ping`

The `ping` command sends a tiny packet of data to a network address and waits for a reply.

---

### 2. `localhost`

Instead of pinging a website, `localhost` tells your computer to ping itself.

Benefits:

- No internet connection required
- 100% reliable
- Nearly instant response

---

### 3. `-n`

The `-n` option specifies how many packets to send.

Example:

```bat
ping localhost -n 3 >nul
```

Timeline:

- Packet 1 → immediately
- Wait 1 second
- Packet 2
- Wait 1 second
- Packet 3
- Command exits

Total delay ≈ **2 seconds**

---

## Environment Variables

Example:

```bat
@echo off
title My first Batch file

echo %HOMEDRIVE%
pause
```

---

### Dynamic Variables

These are computed every time you use them.

| Variable | Description |
|-----------|-------------|
| `%CD%` | Current working directory |
| `%DATE%` | Current system date |
| `%TIME%` | Current system time |
| `%RANDOM%` | Random integer (0–32767) |
| `%ERRORLEVEL%` | Exit code of previous command |
| `%CMDCMDLINE%` | Full command used to launch cmd |
| `%CMDEXTVERSION%` | Internal cmd extension version |

---

### User & Profile Variables

| Variable | Description |
|-----------|-------------|
| `%USERNAME%` | Logged-in username |
| `%USERPROFILE%` | User home directory |
| `%HOMEDRIVE%` | Home drive |
| `%HOMEPATH%` | Home path |
| `%APPDATA%` | Roaming AppData |
| `%LOCALAPPDATA%` | Local AppData |

---

### Hardware & OS Variables

| Variable | Description |
|-----------|-------------|
| `%OS%` | Windows operating system |
| `%COMPUTERNAME%` | Computer name |
| `%NUMBER_OF_PROCESSORS%` | CPU cores |
| `%PROCESSOR_ARCHITECTURE%` | CPU architecture |
| `%PROCESSOR_IDENTIFIER%` | CPU model |
| `%PROCESSOR_LEVEL%` | Processor level |
| `%PROCESSOR_REVISION%` | Processor revision |

---

### System Directories

| Variable | Description |
|-----------|-------------|
| `%SystemDrive%` | Windows drive |
| `%SystemRoot%` | Windows folder |
| `%WINDIR%` | Same as SystemRoot |
| `%ALLUSERSPROFILE%` | ProgramData folder |
| `%PUBLIC%` | Public user folder |
| `%ProgramFiles%` | 64-bit Program Files |
| `%ProgramFiles(x86)%` | 32-bit Program Files |
| `%CommonProgramFiles%` | Shared 64-bit components |
| `%CommonProgramFiles(x86)%` | Shared 32-bit components |
| `%TEMP%` | Temporary folder |
| `%TMP%` | Same as TEMP |

---

### Command Execution Variables

| Variable | Description |
|-----------|-------------|
| `%PATH%` | Directories searched for executables |
| `%PATHEXT%` | Executable file extensions |
| `%COMSPEC%` | Path to `cmd.exe` |

---

## Logging Example

Append to a file:

```bat
echo [%date% %time%] Pipeline started>>run_log.txt
```

Overwrite a file:

```bat
echo Hello>output.txt
```

Append to a file:

```bat
echo Hello>>output.txt
```

---

## Error Handling

Check if the previous command failed:

```bat
python my_script.py

if errorlevel 1 (
    echo Script failed.
    exit /b
)
```

Using labels:

```bat
python my_script.py

if errorlevel 1 goto Error

echo Success
exit /b

:Error
echo Something went wrong.
exit /b
```

---

## Variables

```bat
set NAME=Sachio

echo %NAME%
```

Arithmetic variables:

```bat
set /a COUNT=5+3

echo %COUNT%
```

---

## Current Working Directory

```bat
cd /d C:\Users\Sachio\Desktop\earnings-catalyst-screener
```

The `/d` option changes both the drive and the folder.

---

## Calling Python

Using the active virtual environment:

```bat
set PYTHON=C:\Users\Sachio\Desktop\earnings-catalyst-screener\.venv\Scripts\python.exe

%PYTHON% app\explore_earnings.py
```

This is preferable to using the global Python installation because it guarantees all required packages are available.

---

## Useful Pattern for Large Pipelines

```bat
echo START Stage 1>>run_log.txt

%PYTHON% app\script.py

if errorlevel 1 goto Error

echo FINISH Stage 1>>run_log.txt
```

This makes debugging much easier because you always know exactly which stage failed.