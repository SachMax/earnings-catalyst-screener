
#pragma once

#include <cstdint>
#include <string>

struct Bar {
    std::string timestamp;

    double open;
    double high;
    double low;
    double close;

    std::int64_t volume;

    bool is_valid() const;
};