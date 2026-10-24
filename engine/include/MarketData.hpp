#pragma once

#include "Bar.hpp"

#include <string>
#include <vector>

class MarketData {
public:
    // function declaration, return std::vector<Bar>
    static std::vector<Bar> load_csv(const std::string& filepath);
};