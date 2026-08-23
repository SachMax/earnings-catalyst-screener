#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

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
};

class Portfolio {
    private:
        double cash_;
        std::unordered_map<std::string, Position> position_;
        std::vector<Trade> trade_history_;

    public:
        explicit Portfolio(double cash) : cash_(cash) {}

        // const is to prevent any modification inside the function
        double cash() const {return cash_;}

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
            Trade curr_trade = {ticker, Side::Buy, shares, price};
            trade_history_.push_back(curr_trade);
        }

        void sell(const std::string& ticker, int shares, double price) {

        if (shares <= 0 || price <= 0) {
            std::cout << "invalid trade\n";
            return;
        }

        auto it = position_.find(ticker);

        if (it == position_.end()) {
            std::cout << "error";
            return;
        }
        else if (shares == it->second.shares) {
            position_.erase(it);
            cash_ += shares * price;
        }
        else if (shares < it->second.shares) {
            it->second.shares -= shares;
            cash_ += shares * price;
        }
        else {
            std::cout << "error";
            return;
        }
        Trade curr_trade = {ticker, Side::Sell, shares, price};
        trade_history_.push_back(curr_trade);
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
                std::cout << "Ticker: " << t.ticker 
                  << " | Side: "; (t.side == Side::Buy) ? std::cout << "BUY" : std::cout << "SELL";
                std::cout << " | Shares: " << t.shares
                  << " | Avg Price: $" << t.price
                  << "\n";
            }
        }

};

int main() {    
    Portfolio portfolio(100000);
    std::cout << portfolio.cash() << "\n";
    portfolio.buy("AAPL", 5, 301.5);
    portfolio.print_positions();
    portfolio.buy("AAPL", 2, 303.5);
    portfolio.buy("NVDA", 1, 201.5);
    std::cout << "\n" << portfolio.cash() << "\n";
    portfolio.print_positions();
    portfolio.sell("AAPL", 6, 320.3);
    portfolio.sell("NVDA", 1, 220.3);
    std::cout << "\n";
    portfolio.print_positions();
    std::cout << "\n" << portfolio.cash();

    std::cout << "\n";

    //evaluate
    // sell stock you don't own
    portfolio.sell("TSLA", 5, 500);
    std::cout << "\n";
    // sell more shares than you own
    portfolio.sell("AAPL", 500, 300);
    std::cout << "\n";
    // sell exactly all remaining shares
    portfolio.sell("AAPL", 1, 300);
    std::cout << "\n" << portfolio.cash() << "\n";
    portfolio.print_trades();
    }