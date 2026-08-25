#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>
#include <iomanip>

struct Position {
    int shares;
    double average_price;
};

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

class Portfolio {
    private:
        double cash_;
        std::unordered_map<std::string, Position> position_;
        std::vector<Trade> trade_history_;
        double realized_pnl_;
        std::unordered_map<std::string, double> current_prices_;


    public:
        explicit Portfolio(double cash): cash_(cash), realized_pnl_(0.0) {}

        // const is to prevent any modification inside the function
        double cash() const {return cash_;}

        double realized_pnl() const {return realized_pnl_;} 

        void update_price(const std::string& ticker, double price) {
            if (price <= 0) {
                std::cout << "invalid price\n";
                return;
            }
            current_prices_[ticker] = price;
        }

        double market_value() const {
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

        double unrealized_pnl() const {
            double unrealized_pnl_ = 0.0;
            for (const auto& [ticker, second] : position_) {
                auto price_it = current_prices_.find(ticker);

                if (price_it != current_prices_.end()) {
                    unrealized_pnl_ += (price_it->second - second.average_price) * second.shares;
                }
            }
            return unrealized_pnl_;
        }

        double equity() const {
            return cash_ + market_value();
        }

        void buy(const std::string& ticker, int shares, double price) {
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

        void sell(const std::string& ticker, int shares, double price) {

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
        
        void print_positions () const {
            for (auto const& [ticker, position] : position_) {
                std::cout << "Ticker: " << ticker 
                  << " | Shares: " << position.shares 
                  << " | Avg Price: $" << position.average_price 
                  << "\n";
            }
        }

        void print_trades() const {
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

};

int main() {    
    // Portfolio portfolio(100000);
    // std::cout << portfolio.cash() << "\n";
    // portfolio.buy("AAPL", 5, 301.5);
    // portfolio.print_positions();
    // portfolio.buy("AAPL", 2, 303.5);
    // portfolio.buy("NVDA", 1, 201.5);
    // std::cout << "\n" << portfolio.cash() << "\n";
    // portfolio.print_positions();
    // portfolio.sell("AAPL", 6, 320.3);
    // portfolio.sell("NVDA", 1, 220.3);
    // std::cout << "\n";
    // portfolio.print_positions();
    // std::cout << "\n" << portfolio.cash();

    // std::cout << "\n";

    // //evaluate
    // // sell stock you don't own
    // portfolio.sell("TSLA", 5, 500);
    // std::cout << "\n";
    // // sell more shares than you own
    // portfolio.sell("AAPL", 500, 300);
    // std::cout << "\n";
    // // sell exactly all remaining shares
    // portfolio.sell("AAPL", 1, 300);
    // std::cout << "\n" << portfolio.cash() << "\n";
    // portfolio.print_trades();
    // std::cout
    // << "\nTotal Realized P&L: $"
    // << portfolio.realized_pnl()
    // << '\n';
    Portfolio portfolio(100000);

    portfolio.buy("AAPL", 10, 200);
    portfolio.buy("NVDA", 5, 300);

    portfolio.update_price("AAPL", 220);
    portfolio.update_price("NVDA", 280);

    std::cout << "Cash: $" << portfolio.cash() << '\n';
    std::cout << "Market Value: $" << portfolio.market_value() << '\n';
    std::cout << "Unrealized P&L: $" << portfolio.unrealized_pnl() << '\n';
    std::cout << "Equity: $" << portfolio.equity() << '\n';
    }