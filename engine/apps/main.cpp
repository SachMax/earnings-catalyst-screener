
#include "Portfolio.hpp"

#include <iostream>

int main()
{
    Portfolio portfolio(100000.0);

    portfolio.buy("AAPL", 10, 200.0);
    portfolio.buy("NVDA", 5, 300.0);

    portfolio.update_price("AAPL", 220.0);
    portfolio.update_price("NVDA", 280.0);

    std::cout << "Cash: " << portfolio.cash() << '\n';
    std::cout << "Market value: "
              << portfolio.market_value() << '\n';
    std::cout << "Unrealized P&L: "
              << portfolio.unrealized_pnl() << '\n';
    std::cout << "Equity: "
              << portfolio.equity() << '\n';

    return 0;
}