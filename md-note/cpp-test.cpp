#include <algorithm>
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

// store ticker and score
struct Signal {
    std::string ticker;
    double score;
};

// store shares and entry_price 
struct Position {
    int shares;
    double entry_price;
};

class Portfolio {

private:

    double cash_;

    // // hash table mapping ticker -> Position
    std::unordered_map<std::string, Position> positions_;

public:
    // initialize cash_
    explicit Portfolio(double initial_cash)
        : cash_(initial_cash) {}

    void buy(
        const Signal& signal,
        int shares,
        double price
    ) {
        
        // assign to positions_
        positions_[signal.ticker] = {
            shares,
            price
        };

        // substract total cash_ with shares bought
        cash_ -= shares * price;
    }

    double cash() const {
        return cash_;
    }
};

int main() {

    std::vector<Signal> signals;

    // create an array containing Signal structs with .ticker and .score
    // append Signal objects to the vector
    signals.push_back({"NVDA", 0.91});
    signals.push_back({"AMD", 0.82});
    signals.push_back({"AAPL", 0.74});

    std::sort(
        signals.begin(),
        signals.end(),
        [](const Signal& a, const Signal& b) {
            return a.score > b.score;
        }
    );

    // initialize initial cash_
    Portfolio portfolio(100000);

    // loops on signals
    for (const auto& signal : signals) {

        std::cout
            << signal.ticker
            << " "
            << signal.score
            << '\n';
    }

    // buy the first struct which is nvda. hence cash_(100k) -= 10 * 180.5
    portfolio.buy(
        signals[0],
        10,
        180.50
    );

    std::cout
        << "Cash: "
        << portfolio.cash()
        << '\n';
}