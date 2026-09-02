#pragma once

#include <string>
#include <unordered_map>
#include <vector>
#include "Trade.hpp"
#include "Position.hpp"

class Portfolio {
    private:
        double cash_;
        std::unordered_map<std::string, Position> position_;
        std::vector<Trade> trade_history_;
        double realized_pnl_;
        std::unordered_map<std::string, double> current_prices_;


    public:
        explicit Portfolio(double cash);

        // const is to prevent any modification inside the function
        double cash() const;

        double realized_pnl() const;

        void update_price(const std::string& ticker, double price);

        double market_value() const;

        double unrealized_pnl() const;

        double equity() const;

        void buy(const std::string& ticker, int shares, double price);

        void sell(const std::string& ticker, int shares, double price);

        void print_positions () const;

        void print_trades() const;
    };
