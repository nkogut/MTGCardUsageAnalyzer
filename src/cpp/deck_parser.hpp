#pragma once

#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <filesystem>
#include <map>
#include <unordered_map>
#include <functional>
#include <bitset>
#include <rapidjson/document.h>

enum deck_location { MAIN, SIDE, NONE };
enum request_type { FREQUENCIES, DECKLISTS };

// Perfectly mirrors your Python TypedDict
struct Entry {
    time_t date{};
    std::string player{};
    std::string url{};
    std::unordered_map<std::string, int> main{};
    std::unordered_map<std::string, int> side{};

    void clear() {
        player.clear();
        url.clear();
        date = 0;
        main.clear();
        side.clear();
    }
};

struct EntryFilters {
    const time_t start_date;
    const time_t end_date;
    const uint8_t whitelist_size;
    const bool use_date_filter;
    const bool use_player_filter;
    const bool use_card_whitelist;
    const bool use_card_blacklist;
    const std::string player;
    const std::vector<std::string> card_whitelist;
    const std::vector<std::string> card_blacklist;

    EntryFilters(time_t start_date, time_t end_date, std::string player, std::vector<std::string> whitelist, std::vector<std::string> blacklist);

    [[nodiscard]] inline bool date_is_okay(time_t date) const noexcept;
    [[nodiscard]] inline bool player_is_okay(std::string_view name) const noexcept;
    [[nodiscard]] inline bool card_is_okay(std::string_view card) const noexcept;
    [[nodiscard]] inline std::bitset<32> card_is_in_whitelist(std::string_view card, std::bitset<32> matched) const noexcept;
};

// Flattened: No more unique_ptr arrays
struct card_count {
    uint32_t main_count = 0;
    uint32_t side_count = 0;
    uint32_t num_main_decks = 0;
    uint32_t num_side_boards = 0;
};

struct staged_card_count {
    uint32_t main_count = 0;
    uint32_t side_count = 0;
    uint32_t num_main_decks = 0;
    uint32_t num_side_boards = 0;
};

struct StringHash {
    using is_transparent = void;
    size_t operator()(std::string_view str_view) const noexcept {
        return std::hash<std::string_view>{}(str_view);
    }
    size_t operator()(const std::string& str) const noexcept {
        return std::hash<std::string>{}(str);
    }
};

using card_count_map = std::unordered_map<std::string, card_count, StringHash, std::equal_to<> >;

void print_freqs(card_count_map& card_counts, deck_location location, size_t num_decks);
bool get_decks(std::vector<Entry>& entries, card_count_map& card_counts, const std::filesystem::path& ds_path,
    const time_t start_date, const time_t end_date, const std::string player, const std::vector<std::string>& whitelist,
    const std::vector<std::string>& blacklist);
