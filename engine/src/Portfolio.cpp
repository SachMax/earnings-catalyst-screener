#include "Portfolio.hpp"
#include <iostream>
#include <iomanip>

Portfolio::Portfolio(double cash): cash_(cash), realized_pnl_(0.0) {}

// const is to prevent any modification inside the function
double Portfolio::cash() const {return cash_;}

double Portfolio::realized_pnl() const {return realized_pnl_;} 

void Portfolio::update_price(const std::string& ticker, double price) {
    if (price <= 0) {
        std::cout << "invalid price\n";
        return;
    }
    current_prices_[ticker] = price;
}

double Portfolio::market_value() const {
    double market_value = 0.0;
    for (const auto& [ticker, position] : position_) {
        // find ticker inside current_prices
        auto it = current_prices_.find(ticker);
        if (it != current_prices_.end()) {
            market_value += position.shares * it->second;
        }
    } 
    return market_value;
}

double Portfolio::unrealized_pnl() const {
    double pnl = 0.0;
    for (const auto& [ticker, position] : position_) {
        auto price_it = current_prices_.find(ticker);

        if (price_it != current_prices_.end()) {
            pnl += (price_it->second - position.average_price) * position.shares;
        }
    }
    return pnl;
}

double Portfolio::equity() const {
    return cash_ + market_value();
}

void Portfolio::buy(const std::string& ticker, int shares, double price) {
    if (shares <= 0 || price <= 0) {
        std::cout << "invalid trade\n";
        return;
    }
    if (shares * price > cash_) {
        std::cout << "insufficient cash\n";
        return;
    }
    auto it = position_.find(ticker);
    if (it != position_.end()) {
        it->second.average_price = ((it->second.shares * it->second.average_price)
        + shares * price)/(it->second.shares + shares) ;
        it->second.shares += shares;
    }
    else {
        position_[ticker] = {shares, price};
    }
    cash_ -= (shares * price);
    Trade curr_trade = {ticker, Side::Buy, shares, price, 0.0, 0.0};
    trade_history_.push_back(curr_trade);
    current_prices_[ticker] = price;
}

void Portfolio::sell(const std::string& ticker, int shares, double price) {

    // 1. Validate inputs
    if (shares <= 0 || price <= 0) {
        std::cout << "invalid trade\n";
        return;
    }

    // 2. Find position
    auto it = position_.find(ticker);

    // 3. Check position exists
    if (it == position_.end()) {
        std::cout << "error\n";
        return;
    }

    // 4. Check enough shares
    if (shares > it->second.shares) {
        std::cout << "error\n";
        return;
    }

    // 5. Calculate THIS trade's P&L
    double trade_pnl =
        (price - it->second.average_price) * shares;

    double trade_pnl_pct =
        ((price - it->second.average_price)
        / it->second.average_price) * 100.0;

    // 6. Update cumulative realized P&L
    realized_pnl_ += trade_pnl;

    // 7. Update position
    if (shares == it->second.shares) {
        position_.erase(it);
    }
    else {
        it->second.shares -= shares;
    }

    // 8. Receive cash
    cash_ += shares * price;

    // 9. Record successful trade
    Trade curr_trade = {
        ticker,
        Side::Sell,
        shares,
        price,
        trade_pnl,
        trade_pnl_pct
    };

    trade_history_.push_back(curr_trade);
    current_prices_[ticker] = price;
}

void Portfolio::print_positions () const {
    for (auto const& [ticker, position] : position_) {
        std::cout << "Ticker: " << ticker 
            << " | Shares: " << position.shares 
            << " | Avg Price: $" << position.average_price 
            << "\n";
    }
}

void Portfolio::print_trades() const {
    for (auto const& t : trade_history_) {
        std::cout
            << "Ticker: " << t.ticker
            << " | Side: "
            << ((t.side == Side::Buy) ? "BUY" : "SELL")
            << " | Shares: " << t.shares
            << " | Price: $" << t.price
            << " | Realized P&L: $"
            << std::fixed << std::setprecision(2)
            << t.trade_pnl << " ("
            << std::fixed << std::setprecision(2)
            << t.trade_pnl_pct << "%)"
            << '\n';
    }
}