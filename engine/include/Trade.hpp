#pragma once

#include <string>

enum class Side {
    Buy,
    Sell
};

struct Trade {
    std::string ticker;
    Side side;
    int shares;
    double price;
    double trade_pnl;
    double trade_pnl_pct;
};