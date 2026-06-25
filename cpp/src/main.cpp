#include <iostream>
#include <fstream>
#include <iomanip>
#include <filesystem>
#include <thread>
#include <chrono>
#include <vector>
#include <utility>
#include <string>

#include <ixwebsocket/IXWebSocket.h>
#include <ixwebsocket/IXNetSystem.h>
#include <nlohmann/json.hpp>

#include "orderbook.hpp"

using json = nlohmann::json;

int main() {
    ix::initNetSystem();

    std::filesystem::create_directories("data");
    std::ofstream out("data/btc_cpp.csv");
    out << std::setprecision(10);

    out << "timestamp,recv_ns";
    for (int i = 1; i <= 5; ++i) {
        out << ",bid_px_" << i << ",bid_sz_" << i
            << ",ask_px_" << i << ",ask_sz_" << i;
    }
    out << "\n";

    OrderBook book;
    ix::WebSocket ws;
    ws.setUrl("wss://ws-feed.exchange.coinbase.com");

    ws.setOnMessageCallback([&](const ix::WebSocketMessagePtr& msg) {
        if (msg->type == ix::WebSocketMessageType::Open) {
            json sub = {
                {"type", "subscribe"},
                {"product_ids", {"BTC-USD"}},
                {"channels", {"level2_batch"}}
            };
            ws.send(sub.dump());
            return;
        }
        if (msg->type != ix::WebSocketMessageType::Message) return;

        json data = json::parse(msg->str);
        std::string type = data["type"];

        if (type == "snapshot") {
            std::vector<std::pair<double, double>> bids, asks;
            for (const auto& lvl : data["bids"])
                bids.push_back({std::stod(lvl[0].get<std::string>()),
                                std::stod(lvl[1].get<std::string>())});
            for (const auto& lvl : data["asks"])
                asks.push_back({std::stod(lvl[0].get<std::string>()),
                                std::stod(lvl[1].get<std::string>())});
            book.apply_snapshot(bids, asks);
        } else if (type == "l2update") {
            for (const auto& ch : data["changes"]) {
                book.apply_update(ch[0].get<std::string>(),
                                  std::stod(ch[1].get<std::string>()),
                                  std::stod(ch[2].get<std::string>()));
            }

            long long recv_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                                std::chrono::system_clock::now().time_since_epoch()).count();
            auto bids = book.top_bids(5);
            auto asks = book.top_asks(5);

            out << data["time"].get<std::string>() << "," << recv_ns;
            for (int i = 0; i < 5; ++i) {
                if (i < (int)bids.size()) out << "," << bids[i].first << "," << bids[i].second;
                else out << ",,";
                if (i < (int)asks.size()) out << "," << asks[i].first << "," << asks[i].second;
                else out << ",,";
            }
            out << "\n";
        }
    });

    ws.start();
    std::this_thread::sleep_for(std::chrono::seconds(30));
    ws.stop();

    out.close();
    ix::uninitNetSystem();
    std::cout << "capture done -> data/btc_cpp.csv\n";
    return 0;
}
