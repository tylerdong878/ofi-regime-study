#include <arrow/api.h>
#include <arrow/io/api.h>
#include <ixwebsocket/IXNetSystem.h>
#include <ixwebsocket/IXWebSocket.h>
#include <parquet/arrow/writer.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <nlohmann/json.hpp>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "orderbook.hpp"

using json = nlohmann::json;

std::atomic<bool> g_running(true);

void on_sigint(int) { g_running = false; }

int main() {
    ix::initNetSystem();
    std::filesystem::create_directories("data");

    // in-memory column buffers (one vector per output column)
    std::vector<std::string> ts_col;
    std::vector<int64_t> recv_col;
    std::vector<double> bid_px[5], bid_sz[5], ask_px[5], ask_sz[5];

    // write the current buffers to a Parquet file, then leave them as-is
    auto flush = [&](const std::string& path) {
        if (ts_col.empty()) return;

        auto make_doubles = [](const std::vector<double>& v) {
            arrow::DoubleBuilder b;
            (void)b.AppendValues(v);
            std::shared_ptr<arrow::Array> a;
            (void)b.Finish(&a);
            return a;
        };

        arrow::StringBuilder ts_b;
        (void)ts_b.AppendValues(ts_col);
        std::shared_ptr<arrow::Array> ts_arr;
        (void)ts_b.Finish(&ts_arr);

        arrow::Int64Builder recv_b;
        (void)recv_b.AppendValues(recv_col);
        std::shared_ptr<arrow::Array> recv_arr;
        (void)recv_b.Finish(&recv_arr);

        std::vector<std::shared_ptr<arrow::Field>> fields = {
            arrow::field("timestamp", arrow::utf8()),
            arrow::field("recv_ns", arrow::int64()),
        };
        std::vector<std::shared_ptr<arrow::Array>> arrays = {ts_arr, recv_arr};

        for (int i = 0; i < 5; ++i) {
            std::string s = std::to_string(i + 1);
            fields.push_back(arrow::field("bid_px_" + s, arrow::float64()));
            arrays.push_back(make_doubles(bid_px[i]));
            fields.push_back(arrow::field("bid_sz_" + s, arrow::float64()));
            arrays.push_back(make_doubles(bid_sz[i]));
            fields.push_back(arrow::field("ask_px_" + s, arrow::float64()));
            arrays.push_back(make_doubles(ask_px[i]));
            fields.push_back(arrow::field("ask_sz_" + s, arrow::float64()));
            arrays.push_back(make_doubles(ask_sz[i]));
        }

        auto table = arrow::Table::Make(arrow::schema(fields), arrays);
        auto outfile = arrow::io::FileOutputStream::Open(path).ValueOrDie();
        arrow::Status st = parquet::arrow::WriteTable(*table, arrow::default_memory_pool(), outfile, 100000);
        if (!st.ok()) std::cerr << "parquet write failed:" << st.ToString() << "\n";
        std::cout << "wrote " << ts_col.size() << " rows -> " << path << "\n";
    };

    OrderBook book;
    std::vector<long long> latencies_ns;
    ix::WebSocket ws;
    ws.setUrl("wss://ws-feed.exchange.coinbase.com");

    auto clear_buffers = [&]() {
        ts_col.clear();
        recv_col.clear();
        latencies_ns.clear();
        for (int i = 0; i < 5; ++i) {
            bid_px[i].clear();
            bid_sz[i].clear();
            ask_px[i].clear();
            ask_sz[i].clear();
        }
    };

    auto next_path = []() {
        long long epoch = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();

        return std::string("data/btc_") + std::to_string(epoch) + ".parquet";
    };

    auto last_rotation = std::chrono::steady_clock::now();
    const auto rotation_interval = std::chrono::hours(1);

    ws.setOnMessageCallback([&](const ix::WebSocketMessagePtr& msg) {
        if (msg->type == ix::WebSocketMessageType::Open) {
            json sub = {{"type", "subscribe"},
                        {"product_ids", {"BTC-USD"}},
                        {"channels", {"level2_batch"}}};
            ws.send(sub.dump());
            return;
        }
        if (msg->type != ix::WebSocketMessageType::Message) return;

        auto t0 = std::chrono::steady_clock::now();
        json data = json::parse(msg->str);
        std::string type = data["type"];

        if (type == "snapshot") {
            std::vector<std::pair<double, double>> bids, asks;
            for (const auto& lvl : data["bids"])
                bids.push_back(
                    {std::stod(lvl[0].get<std::string>()), std::stod(lvl[1].get<std::string>())});
            for (const auto& lvl : data["asks"])
                asks.push_back(
                    {std::stod(lvl[0].get<std::string>()), std::stod(lvl[1].get<std::string>())});
            book.apply_snapshot(bids, asks);
        } else if (type == "l2update") {
            for (const auto& ch : data["changes"]) {
                book.apply_update(ch[0].get<std::string>(), std::stod(ch[1].get<std::string>()),
                                  std::stod(ch[2].get<std::string>()));
            }

            long long recv_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                                    std::chrono::system_clock::now().time_since_epoch())
                                    .count();
            auto bids = book.top_bids(5);
            auto asks = book.top_asks(5);
            if (bids.size() < 5 || asks.size() < 5) return;

            ts_col.push_back(data["time"].get<std::string>());
            recv_col.push_back(recv_ns);
            for (int i = 0; i < 5; ++i) {
                bid_px[i].push_back(bids[i].first);
                bid_sz[i].push_back(bids[i].second);
                ask_px[i].push_back(asks[i].first);
                ask_sz[i].push_back(asks[i].second);
            }

            auto t1 = std::chrono::steady_clock::now();
            latencies_ns.push_back(
                std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count());
            if (std::chrono::steady_clock::now() - last_rotation >= rotation_interval) {
                flush(next_path());
                clear_buffers();
                last_rotation = std::chrono::steady_clock::now();
            }
        }
    });

    std::signal(SIGINT, on_sigint);
    std::signal(SIGTERM, on_sigint);

    ws.start();
    std::cout << "capturing ... (Ctrl+C to stop)\n";
    while (g_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }
    ws.stop();
    flush(next_path());
    ix::uninitNetSystem();
    std::cout << "capture done\n";
    return 0;
}
