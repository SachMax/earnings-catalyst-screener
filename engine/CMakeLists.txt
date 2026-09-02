cmake_minimum_required(VERSION 4.4) # sets the minimum required version of cmake for the project
project(Test 
        VERSION 0.0.17
        DESCRIPTION "The CMake Testing Platform"
        LANGUAGES CXX) # to specify the information for the project such as project name, version, description, homepage_url, languages
add_executable(Test main.cpp) 
target_compile_features(Test PRIVATE cxx_std_17)

# Variables and printing
message("hello") # basically this is the print function
set(NAME "QuantEngine") # to set a variable
message(${NAME}) # to access the variable

# this is a function
function(print var)
        message("${var} = ${${var}}" )
endfunction()

print(PROJECT_NAME)