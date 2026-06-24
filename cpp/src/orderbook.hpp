#pragma once

#include <map>
#include <vector>
#include <utility>
#include <string>

class OrderBook {
public:
    void apply_snapshot(const std::vector<std::pair<double, double>>& bids,
                        const std::vector<std::pair<double, double>>& asks) {
        bids_.clear();
        asks_.clear();
        for (const auto& [price, size] : bids) bids_[price] = size;
        for (const auto& [price, size] : asks) asks_[price] = size;
    }

    void apply_update(const std::string& side, double price, double size) {
        std::map<double, double>& book = (side == "buy") ? bids_ : asks_;
        if (size == 0.0) {
            book.erase(price);
        } else {
            book[price] = size;
        }
    }

    std::vector<std::pair<double, double>> top_bids(int n) const {
        std::vector<std::pair<double, double>> result;
        for (auto it = bids_.rbegin(); it != bids_.rend() && (int)result.size() < n; ++it) {
            result.push_back({it->first, it->second});
        }
        return result;
    }

    std::vector<std::pair<double, double>> top_asks(int n) const {
        std::vector<std::pair<double, double>> result;
        for (auto it = asks_.begin(); it != asks_.end() && (int)result.size() < n; ++it) {
            result.push_back({it->first, it->second});
        }
        return result;
    }

private:
    std::map<double, double> bids_;
    std::map<double, double> asks_;
};
