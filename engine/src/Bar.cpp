#include "Bar.hpp"
#include <cmath>

bool Bar::is_valid() const {

    // Numerical sanity
    if (!std::isfinite(open) ||
        !std::isfinite(high) ||
        !std::isfinite(low) ||
        !std::isfinite(close))
    {
        return false;
    }

    // Price positivity
    if (open < 0 || high < 0 || low < 0 || close < 0) return false; 

    // OHLC relationship
    if (high < open || high < low || high < close) return false;

    if (low > open || low > high || low > close) return false;

    // Volume check
    if (volume < 0) return false;

    return true;
}