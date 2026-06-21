#include <iostream>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

int main() {
    json msg = json::parse(R"({"type": "l2update", "product_id": "BTC-USD"})");
    std::cout << "parsed type: " << msg["type"] << "\n";
    return 0;
}
