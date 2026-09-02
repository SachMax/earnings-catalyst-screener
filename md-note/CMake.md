# CMake

## Why CMake
### Problems CMake Solves
Problem 1: When you have 9 or more different files (like Portfolio.cpp, RiskManager.cpp, etc.), typing a massive terminal command every time you make a change is slow and prone to typos.

Problem 2: Compiling code takes time and computer power. If you have 1,000 files and you change one character inside Portfolio.cpp, it is a massive waste of time to re-compile the other 999 files that didn't change. 

Problem 3: 
If you write a Makefile (the instructions for the tool Make), it will work perfectly on Linux or Mac. But if a Windows developer downloads your project, they use Visual Studio, which doesn't understand Makefiles at all. They use a completely different build tool (MSBuild).

### What is CMake
CMake traditionally is not itself the compiler, and it's not quite the same thing as Make/Ninja either.

CMake is best thought of as a: build-system generator and project configuration system.

So:
- g++, is a compiler toolchain.
- Ninja / Make, are for build systems.
- CMake, configures/generates the build system.

```bash
CMake
   ↓
Build system #(Make, Ninja, Visual Studio)
   ↓
Compiler #(g++, clang++, cl.exe)
   ↓
Linker
   ↓
Executable
```
---
---


# CMake is a language
## Basic project setup
```cmake
cmake_minimum_required(VERSION 3.5) # sets the minimum required version of cmake for the project
project(Test 
        VERSION 0.0.17
        DESCRIPTION "The CMake Testing Platform"
        LANGUAGES CXX) # to specify the information for the project such as project name, version, description, homepage_url, languages
add_executable(Test main.cpp) 
target_compile_features(Test PRIVATE cxx_std_17)
```

## Functions and Macros
```cmake
# Variables and printing
message("hello") # basically this is the print function
set(NAME "QuantEngine") # to set a variable
message(${NAME}) # to access the variable

```