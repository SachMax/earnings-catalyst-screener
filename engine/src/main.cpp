#include <iostream>
#include "C:\Users\Sachio\Desktop\earnings-catalyst-screener\engine\include\Portfolio.hpp"

int main() {
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