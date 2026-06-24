#include <cassert>
#include <iostream>
#include <utility>

#include "orderbook.hpp"

int main() {
    OrderBook book;
    book.apply_snapshot(
        {{100.0, 2.0}, {99.0, 5.0}, {98.0, 1.0}},
        {{101.0, 3.0}, {102.0, 4.0}, {103.0, 1.0}}
    );

    auto bids = book.top_bids(2);
    assert(bids[0] == std::make_pair(100.0, 2.0));
    assert(bids[1] == std::make_pair(99.0, 5.0));

    auto asks = book.top_asks(2);
    assert(asks[0] == std::make_pair(101.0, 3.0));
    assert(asks[1] == std::make_pair(102.0, 4.0));

    book.apply_update("buy", 100.0, 9.0);   // update existign level
    book.apply_update("buy", 100.5, 1.0);   // add a new, better bid
    book.apply_update("sell", 101.0, 0.0);  // delete the best ask

    bids = book.top_bids(2);
    assert(bids[0] == std::make_pair(100.5, 1.0));
    assert(bids[1] == std::make_pair(100.0, 9.0));

    asks = book.top_asks(2);
    assert(asks[0] == std::make_pair(102.0, 4.0));
    assert(asks[1] == std::make_pair(103.0, 1.0));

    std::cout << "All order book tests passed\n";
    return 0;
}
