#include <iostream>
#include <thread>
#include <chrono>

#include <ixwebsocket/IXWebSocket.h>
#include <ixwebsocket/IXNetSystem.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

int main() {
    ix::initNetSystem();

    ix::WebSocket ws;
    ws.setUrl("wss://ws-feed.exchange.coinbase.com");

    ws.setOnMessageCallback([&ws](const ix::WebSocketMessagePtr& msg) {
        if (msg->type == ix::WebSocketMessageType::Open) {
            json sub = {
                {"type", "subscribe"},
                {"product_ids", {"BTC-USD"}},
                {"channels", {"level2_batch"}}
            };
            ws.send(sub.dump());
        } else if (msg->type == ix::WebSocketMessageType::Message) {
            std::cout << msg->str.substr(0, 200) << "\n";
        } else if (msg->type == ix::WebSocketMessageType::Error) {
            std::cout << "error: " << msg->errorInfo.reason << "\n";
        }
    });

    ws.start();
    std::this_thread::sleep_for(std::chrono::seconds(5));
    ws.stop();

    ix::uninitNetSystem();
    return 0;
}
