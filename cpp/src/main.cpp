#include <iostream>
#include <filesystem>
#include <thread>
#include <chrono>
#include <vector>
#include <utility>
#include <string>
#include <algorithm>
#include <cstdint>

#include <ixwebsocket/IXWebSocket.h>
#include <ixwebsocket/IXNetSystem.h>
#include <nlohmann/json.hpp>

#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/writer.h>

#include "orderbook.hpp"

using json = nlohmann::json;

int main() {
    ix::initNetSystem();
    std::filesystem::create_directories("data");

    // in-memory column buffers (one vector per output column)
    std::vector<std::string> ts_col;
    std::vector<int64_t> recv_col;
    std::vector<double> bid_px[5], bid_sz[5], ask_px[5], ask_sz[5];

    OrderBook book;
    std::vector<long long> latencies_ns;
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

        auto t0 = std::chrono::steady_clock::now();
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
        }
    });

    auto start = std::chrono::steady_clock::now();
    ws.start();
    std::this_thread::sleep_for(std::chrono::seconds(30));
    ws.stop();
    auto end = std::chrono::steady_clock::now();

    // build Arrow arrays from buffered columns
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
    auto outfile =
        arrow::io::FileOutputStream::Open("data/btc_cpp.parquet").ValueOrDie();
    arrow::Status st = parquet::arrow::WriteTable(
        *table, arrow::default_memory_pool(), outfile, 100000);
    if (!st.ok()) std::cerr << "parquet write failed: " << st.ToString() << "\n";

    // benchmark report
    std::sort(latencies_ns.begin(), latencies_ns.end());
    size_t n = latencies_ns.size();
    if (n > 0) {
        double elapsed_s = std::chrono::duration<double>(end - start).count();
        double p50_us = latencies_ns[n/2] / 1000.0;
        double p99_us = latencies_ns[(size_t)(n * 0.99)] / 1000.0;
        std::cout << "messages processed: " << n << "\n";
        std::cout << "throughput: " << (n / elapsed_s) << " msg/sec\n";
        std::cout << "latency p50: " << p50_us << " us\n";
        std::cout << "latency p99: " << p99_us << " us\n";
    }
    ix::uninitNetSystem();
    std::cout << "capture done -> data/btc_cpp.parquet\n";
    return 0;
}
