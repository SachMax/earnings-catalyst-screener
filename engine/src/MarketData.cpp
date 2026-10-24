
#include "MarketData.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>

std::vector<Bar> MarketData::load_csv(const std::string& filepath)
{
    std::ifstream file(filepath); //declare input stream named file

    if (!file.is_open()) {
        throw std::runtime_error("Could not open CSV file: " + filepath);
    }

    std::vector<Bar> bars;
    std::string line;
    int line_num = 1;

    // Read and skip the header row.
    if (!std::getline(file, line)) {
        throw std::runtime_error("CSV file is empty: " + filepath);
    }

    while (std::getline(file, line)) {
        ++line_num;
        if (line.empty()) {
            continue;
        }

        std::stringstream ss(line);
        std::string field;

        Bar bar{};

        // Timestamp
        if (!std::getline(ss, bar.timestamp, ',')) {
            throw std::runtime_error("Invalid CSV row " + std::to_string(line_num) + ": missing timestamp");
        }

        // Open
        if (!std::getline(ss, field, ',')) {
            throw std::runtime_error("Invalid CSV row " + std::to_string(line_num) + ": missing open");
        }
        bar.open = std::stod(field);

        // High
        if (!std::getline(ss, field, ',')) {
            throw std::runtime_error("Invalid CSV row " + std::to_string(line_num) + ": missing high");
        }
        bar.high = std::stod(field);

        // Low
        if (!std::getline(ss, field, ',')) {
            throw std::runtime_error("Invalid CSV row " + std::to_string(line_num) + ": missing low");
        }
        bar.low = std::stod(field);

        // Close
        if (!std::getline(ss, field, ',')) {
            throw std::runtime_error("Invalid CSV row " + std::to_string(line_num) + ": missing close");
        }
        bar.close = std::stod(field);

        // Volume
        if (!std::getline(ss, field, ',')) {
            throw std::runtime_error("Invalid CSV row " + std::to_string(line_num) + ": missing volume");
        }
        bar.volume = std::stoll(field);

        if (!bar.is_valid()) {
            throw std::runtime_error("Invalid CSV row " + std::to_string(line_num) + ": data not valid");
        }
        bars.push_back(bar);
    }

    return bars;
}