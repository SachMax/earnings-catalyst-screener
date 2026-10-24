
cmake_minimum_required(VERSION 3.20)

project(TradingEngine
    VERSION 1.0
    LANGUAGES CXX
)

# Build the portfolio code as a reusable library.
add_library(TradingEngine
    src/Portfolio.cpp
)

# Make the public header directory available to the library
# and to targets that use it.
target_include_directories(TradingEngine
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Require C++17 for this target and its consumers.
target_compile_features(TradingEngine
    PUBLIC
        cxx_std_17
)

# Build a separate application that uses the library.
add_executable(TradingApp
    apps/main.cpp
)

# Link the application to the library.
target_link_libraries(TradingApp
    PRIVATE
        TradingEngine
)