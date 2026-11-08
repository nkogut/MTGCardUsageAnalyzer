#pragma once
#include <string>
#include <string_view>
#include <vector>
#include <unordered_map>
#include <bitset>
#include <filesystem>

struct StringHash {
    using is_transparent = void;

    static inline size_t mum_hash_64(const char* data, size_t len) noexcept {
        constexpr uint64_t P1 = 0x9ddfea08eb382d69ULL;
        constexpr uint64_t P2 = 0x8cb92ba72f3d8dd7ULL;

        uint64_t h = len * P1;

        if (len <= 8) {
            uint64_t v = 0;
            std::memcpy(&v, data, len);
            return (h ^ v) * P2;
        }

        if (len <= 16) {
            uint64_t a, b;
            std::memcpy(&a, data, 8);
            std::memcpy(&b, data + len - 8, 8);
            return (h ^ a) * P1 + (b * P2);
        }

        // For card names larger than 16 chars: read 8 bytes each from start, middle, and end
        uint64_t a, b, c;
        std::memcpy(&a, data, 8);
        std::memcpy(&b, data + (len >> 1) - 4, 8);
        std::memcpy(&c, data + len - 8, 8);

        h ^= a * P1;
        h ^= b * P2;
        h ^= c * P1;
        return h ^ (h >> 32);
    }

    size_t operator()(std::string_view sv) const noexcept {
        return mum_hash_64(sv.data(), sv.length());
    }
    size_t operator()(const std::string& str) const noexcept {
        return mum_hash_64(str.data(), str.length());
    }
};

struct EntryFilters {
    bool use_date_filter;
    bool use_player_filter;
    bool use_card_whitelist;
    bool use_card_blacklist;
    time_t start_date;
    time_t end_date;
    std::string player;
    std::string_view player_view;
    uint8_t whitelist_size;
    std::vector<std::string> card_whitelist;
    std::vector<std::string> card_blacklist;
    std::vector<std::string_view> card_view_whitelist;
    std::vector<std::string_view> card_view_blacklist;

    EntryFilters(time_t start_date, time_t end_date, std::string&& player_str,
                 std::vector<std::string>&& whitelist, std::vector<std::string>&& blacklist);

    [[nodiscard]] bool date_is_okay(time_t date) const noexcept;
    [[nodiscard]] bool player_is_okay(std::string_view name) const noexcept;
    [[nodiscard]] bool card_is_blacklisted(std::string_view card) const noexcept;
    void update_whitelist_matches(std::string_view card, std::bitset<32>& matched) const noexcept;
};

struct Entry {
    std::string player;
    std::string url;
    time_t date;

    std::vector<std::pair<std::string_view, uint32_t>> main;
    std::vector<std::pair<std::string_view, uint32_t>> side;

    void clear() {
        player.clear();
        url.clear();
        main.clear();
        side.clear();
    }
};

struct staged_card_count {
    uint32_t main_count;
    uint32_t side_count;
    uint32_t num_main_decks;
    uint32_t num_side_boards;
};

struct card_count {
    uint32_t main_count = 0;
    uint32_t side_count = 0;
    uint32_t num_main_decks = 0;
    uint32_t num_side_boards = 0;
};

using card_count_map = std::unordered_map<std::string, card_count, StringHash, std::equal_to<>>;

enum deck_location { NONE = 0, MAIN = 1, SIDE = 2 };

bool get_decks(std::vector<Entry>& entries, card_count_map& card_counts, const std::filesystem::path& ds_path,
    time_t start_date, time_t end_date, std::string player, std::vector<std::string> whitelist,
    std::vector<std::string> blacklist);

std::string format_frequencies(const card_count_map& card_counts, deck_location location, size_t num_decks);
