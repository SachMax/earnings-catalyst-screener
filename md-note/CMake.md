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

### functions
```cmake
# Variables and printing
message("hello") # basically this is the print function
set(NAME "QuantEngine") # to set a variable
message(${NAME}) # to access the variable

# this is a function
function(print var)
        message("${var} = ${${var}}" )
endfunction()

set(Testing "yessir")
# multiple parameters function
function(mult_print)
        message("${ARGN}" ) # prints out your arguments as a list
        message("${ARGC}" ) # len(list(arguments))
        message("${ARGV0}" ) # to access the first argument
        message("${ARGV1}" ) # to access the 2nd argument
        message("${ARGV2}" ) # to access the 3rd argument
endfunction()

# you can also use loops
function(loop_print)
        foreach(var ${ARGN})
                message("${var} = ${${var}}")
        endforeach()
endfunction()
```

### macros
```cmake
# this is basically a function but the code inside is global
macro(loop_print)
        foreach(var ${ARGN})
                message("${var} = ${${var}}")
        endforeach()
endmacro()
```

## The Basics of Targets
### `add_executable()`
A Simple Analogy

Imagine you are building a LEGO set.
- The Target Name: The name of the finished model you want to build (e.g., "LegoCastle").
- The Source Files: The individual bags of bricks needed to build it (e.g., walls.cpp, roof.cpp).

`add_executable(LegoCastle walls.cpp roof.cpp)` is you telling the system: "Take these brick bags and build me that specific castle."

### `add_library()`
* Executables (add_executable): A target that results in an actual, runnable program (like an .exe file or an app binary). It must contain a main() function in its source files.

* Libraries (add_library): A target that outputs compiled code meant to be shared, but cannot be run by itself (like a .lib or .a file). instead, your main executable borrows code from it so you don't have to write everything from scratch.

The Two Types of Libraries in CMake \
STATIC library (.lib or .a): \
basically like copying the whole file into the main executable file.

SHARED library (.dll or .so or .dylib) : \
The library code stays external. Your executable just gets a pointer to it. The .dll/.so must sit next to the executable at runtime. 

#### ALIAS Libraries
```cmake
add_library(EngineMath STATIC math.cpp)

# Create an ALIAS (a namespaced nickname)
add_library(Engine::Math ALIAS EngineMath)
```

#### OBJECT Libraries
Generates raw .obj/.o files. Used to share compiled bytes between multiple targets.

### `add_subdirectory(src)`
physically jumps into the src/ folder, looks for a CMakeLists.txt file inside that folder, and executes everything inside it. Once it finishes reading that sub-file, it jumps back to the main file and continues downward.

### `target_sources()`
Instead of listing all your source files inside the add_executable() or add_library() commands, target_sources() allows you to define a target first and append source files to it later. 

### `target_include_directories()`
This is how you solve the famous C++ problem: "Where are my header files?"

Normally, if you don't use CMake, you have to pass a massive string of search paths to your compiler (like -I/path/to/folder). target_include_directories automates this.

example code: \
`target_include_directories(PhysicsEngine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})`
- ${CMAKE_CURRENT_SOURCE_DIR}: This is a built-in CMake variable that automatically evaluates to the absolute path of the folder where this specific CMakeLists.txt lives. If your physics files are in C:/Projects/MyGame/physics, that is what this variable becomes.

Why PUBLIC? This is the magic key. By marking this directory as PUBLIC, because this is PUBLIC, your main.cpp in another folder can cleanly type #include "physics.h", and the compiler will instantly find it. 

- PRIVATE behavior: "This folder path is a secret. Only PhysicsEngine is allowed to see it."

- INTERFACE behavior: "I don't need this folder path to compile myself, but anyone who links to me definitely needs it."

### `target_compile_features()`

example code: \
`target_compile_features(MyGame PRIVATE cxx_std_17)`

This command sets the language standard for your target object.

- What it tells the compiler: It appends the flag to your compiler telling it to use C++17 (like -std=c++17 in GCC/Clang or /std:c++17 in MSVC).

- Why PRIVATE? This means: "My game executable requires C++17 features to compile." Since an executable is the final product and nothing else links to it, PRIVATE is perfectly sufficient.

### `target_link_libraries()`

example code: \
`target_link_libraries(MyGame PRIVATE PhysicsEngine)`

Imagine you have main.cpp and physics.cpp. Once compilation is finished, the compiler has turned your files into raw machine code:
- main.cpp became main.o (or main.obj)
- physics.cpp became PhysicsEngine.a (or PhysicsEngine.lib)

Inside main.cpp, you called a function: applyGravity(). But main.o doesn't actually contain the code for applyGravity(); it just has a placeholder that says: "Call a function named applyGravity() that lives somewhere else."

If you try to build the project now without linking, the compiler throws a famous error: Linker Error: Unresolved External Symbol or Undefined reference to applyGravity().

What `target_link_libraries(MyGame PRIVATE PhysicsEngine)` does here:

Behind the scenes, it runs a command like this: `g++ main.o -o MyGame /path/to/PhysicsEngine.a`

The C++ Result: The linker takes the placeholder inside main.o and wires it directly to the real machine code inside PhysicsEngine.a. Your final executable MyGame is successfully created!


