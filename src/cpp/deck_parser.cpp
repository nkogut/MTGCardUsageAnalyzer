#include <rapidjson/filereadstream.h>
#include <iostream>
#include <filesystem>
#include <sstream>
#include <time.h>
#include <algorithm>
#include <iomanip>
#include "deck_parser.hpp"
#include "utils.hpp"

EntryFilters::EntryFilters(time_t start_date, time_t end_date, std::string player, std::vector<std::string> whitelist, std::vector<std::string> blacklist)
        : start_date(start_date), end_date(end_date), player(player), card_whitelist(whitelist), card_blacklist(blacklist),
          whitelist_size(static_cast<uint8_t>(whitelist.size())),
          use_date_filter(true),
          use_player_filter(!player.empty()),
          use_card_whitelist(!whitelist.empty()),
          use_card_blacklist(!blacklist.empty()) {}

    [[nodiscard]] inline bool EntryFilters::date_is_okay(time_t date) const noexcept {
        if (!use_date_filter) return true;
        return (date >= start_date && date <= end_date);
    }

    [[nodiscard]] inline bool EntryFilters::player_is_okay(std::string_view name) const noexcept {
        if (!use_player_filter) return true;
        return name == player;
    }

    [[nodiscard]] inline bool EntryFilters::card_is_okay(std::string_view card) const noexcept {
        if (!use_card_blacklist) [[likely]] return true;
        for (const std::string_view& blacklisted_card : card_blacklist) {
            if (card == blacklisted_card) return false;
        }
        return true;
    }

    [[nodiscard]] inline std::bitset<32> EntryFilters::card_is_in_whitelist(std::string_view card, std::bitset<32> matched) const noexcept {
        if (!use_card_whitelist) return matched;
        for (size_t idx = 0; idx < card_whitelist.size(); ++idx) {
                if (card == card_whitelist[idx]) {
                    matched.set(idx);
                    break;
                }
            }
        return matched;
    };

template <typename FilterPolicy>
struct SaxHandler : public rapidjson::BaseReaderHandler<rapidjson::UTF8<>, SaxHandler<FilterPolicy>> {
    enum class JsonKey { UNKNOWN, PLAYER, URL, DATE, MAIN, SIDE, CARD_NAME };

    const FilterPolicy& filters;
    rapidjson::MemoryPoolAllocator<> pool;
    std::vector<std::pair<std::string_view, staged_card_count>> card_count_stage;
    card_count_map& card_counts;
    std::vector<Entry>& entries;
    Entry curr_entry;
    std::string_view current_card_view;
    std::bitset<32> whitelist_matches;

    deck_location current_location = NONE;
    JsonKey active_key = JsonKey::UNKNOWN;
    int skip_depth = 0;

    SaxHandler(const FilterPolicy& f, std::vector<Entry>& out, card_count_map& counts)
        : entries(out), filters(f), pool(2048 * 1024), card_counts(counts) {
        this->card_count_stage.reserve(75);
        this->curr_entry.main.reserve(40);
        this->curr_entry.side.reserve(15);
    }

    inline bool to_skip() const noexcept {
        return skip_depth > 0;
    }

    std::string_view pool_copy(const char* str, rapidjson::SizeType length) {
        if (length == 0) return {};
        char* ptr = static_cast<char*>(pool.Malloc(length));
        std::memcpy(ptr, str, length);
        return std::string_view(ptr, length);
    }

    void clear_entry() {
        curr_entry.clear();
        whitelist_matches.reset();
        card_count_stage.clear();
        current_location = NONE;
        active_key = JsonKey::UNKNOWN;
    }

    bool Key(const char* str, rapidjson::SizeType length, bool copy) {
        if (to_skip()) return true;

        if (current_location != NONE) {
            active_key = JsonKey::CARD_NAME;
            current_card_view = pool_copy(str, length);
            if (!filters.card_is_okay(current_card_view)) skip_depth = 1;
            else whitelist_matches = filters.card_is_in_whitelist(current_card_view, whitelist_matches);
            return true;
        };

        switch (str[0]) {
            case 'd': active_key = JsonKey::DATE; break;
            case 'm': active_key = JsonKey::MAIN; break;
            case 's': active_key = JsonKey::SIDE; break;
            case 'p': active_key = JsonKey::PLAYER; break;
            case 'u': active_key = JsonKey::URL; break;
            default:  active_key = JsonKey::UNKNOWN; break;
        }
        return true;
    }

    bool String(const char* str, rapidjson::SizeType length, bool copy) {
        if (to_skip()) return true;

        if (active_key == JsonKey::PLAYER) {
            std::string_view val(str, length);
            if (!filters.player_is_okay(val)) skip_depth = 1;
            else curr_entry.player = std::string(str, length); // Convert to std::string for Python safety
        } else if (active_key == JsonKey::DATE) {
            curr_entry.date = Util::parse_date(str);
            if (!filters.date_is_okay(curr_entry.date)) skip_depth = 1;
        } else if (active_key == JsonKey::URL) {
            curr_entry.url = std::string(str, length);
        }
        return true;
    }

    bool Uint(unsigned i) {
        if (to_skip()) return true;
        if (current_location == MAIN) card_count_stage.emplace_back(current_card_view, staged_card_count{i, 0, 1, 0});
        else if (current_location == SIDE) card_count_stage.emplace_back(current_card_view, staged_card_count{0, i, 0, 1});
        return true;
    }

    bool StartObject() {
        if (to_skip()) { skip_depth++; return true; }
        if (active_key == JsonKey::MAIN) current_location = MAIN;
        else if (active_key == JsonKey::SIDE) current_location = SIDE;
        return true;
    }

    bool EndObject(rapidjson::SizeType) {
        if (to_skip()) {
            if (--skip_depth == 0) clear_entry();
            return true;
        }

        if (current_location != NONE) {
            current_location = NONE;
        } else {
            if (curr_entry.player.empty() || whitelist_matches.count() != filters.whitelist_size) {
                clear_entry();
                return true;
            }
            for (const auto& [name, counts] : card_count_stage) {

                auto it = card_counts.find(name);
                if (it == card_counts.end()) [[unlikely]] {
                    it = card_counts.try_emplace(std::string{name}).first;
                }

                auto& card_entry = it->second;
                card_entry.main_count     += counts.main_count;
                card_entry.side_count     += counts.side_count;
                card_entry.num_main_decks  += counts.num_main_decks;
                card_entry.num_side_boards += counts.num_side_boards;

                // Populate the Python-ready unordered_map
                if (counts.main_count > 0) {
                    curr_entry.main[std::string(name)] = counts.main_count;
                } else {
                    curr_entry.side[std::string(name)] = counts.side_count;
                }
            }

            entries.push_back(std::move(curr_entry));
            clear_entry();
        }
        return true;
    }

    bool Int(int i) { return Uint(static_cast<unsigned>(i)); }
    bool StartArray() { return true; }
    bool EndArray(rapidjson::SizeType) { return true; }
    bool Default() { return true; }
};

void print_freqs(card_count_map& card_counts, deck_location location, size_t num_decks) {
    std::vector<const card_count_map::value_type*> sorted_vec;
    sorted_vec.reserve(card_counts.size());

    float num_decks_float = static_cast<float>(num_decks);
    double inv_decks_per_point = 10000.0 / static_cast<double>(num_decks_float);

    for (const auto& card : card_counts) {
        uint32_t val = (location == MAIN) ? card.second.main_count : card.second.side_count;
        if (val > 0) sorted_vec.push_back(&card);
    }

    std::sort(sorted_vec.begin(), sorted_vec.end(), [location, inv_decks_per_point] (const auto* a, const auto* b) {
        const uint32_t num_in_location_a = (location == MAIN) ? a->second.num_main_decks : a->second.num_side_boards;
        const uint32_t num_in_location_b = (location == MAIN) ? b->second.num_main_decks : b->second.num_side_boards;

        const uint32_t displayed_pct_a = static_cast<uint32_t>((num_in_location_a * inv_decks_per_point) + 0.5);
        const uint32_t displayed_pct_b = static_cast<uint32_t>((num_in_location_b * inv_decks_per_point) + 0.5);

        if (displayed_pct_a != displayed_pct_b) return displayed_pct_a > displayed_pct_b;

        const uint64_t total_qty_a = (location == MAIN) ? a->second.main_count : a->second.side_count;
        const uint64_t total_qty_b = (location == MAIN) ? b->second.main_count : b->second.side_count;

        return total_qty_a > total_qty_b;
    });

    printf("\n--- %zu %s cards across %zu decks ---\n",
           sorted_vec.size(), (location == MAIN ? "Maindeck" : "Sideboard"), num_decks );

    char name_buf[128];
    for (const auto* ptr : sorted_vec) {
        float freq, main_qty, side_qty;
        freq = std::max(0.01, (location == MAIN) ?
               (static_cast<double>(ptr->second.num_main_decks) / num_decks_float) * 100.0 :
               (static_cast<double>(ptr->second.num_side_boards) / num_decks_float) * 100.0);
        main_qty = (ptr->second.num_main_decks > 0) ? ptr->second.main_count / static_cast<double>(ptr->second.num_main_decks) : 0.0;
        side_qty = (ptr->second.num_side_boards > 0) ? ptr->second.side_count / static_cast<double>(ptr->second.num_side_boards) : 0.0;

        size_t len = ptr->first.copy(name_buf, sizeof(name_buf) - 1);
        Util::title_case(name_buf, len);

        printf("%-35s | %% Decks (%s): %6.2f | Qty Main: %5.2f | Qty Side: %5.2f\n",
            name_buf, (location == MAIN ? "Main" : "Side"), freq, main_qty, side_qty);
    }
}

bool get_decks(std::vector<Entry>& entries, card_count_map& card_counts, const std::filesystem::path& ds_path,
    const time_t start_date, const time_t end_date, const std::string player, const std::vector<std::string>& whitelist,
    const std::vector<std::string>& blacklist) {
    FILE* fp = fopen(ds_path.string().c_str(), "rb");
    if (!fp) return false;

    alignas(64) char read_buffer[131072];
    rapidjson::FileReadStream is(fp, read_buffer, sizeof(read_buffer));
    EntryFilters entry_filters(start_date, end_date, player, whitelist, blacklist);
    rapidjson::Reader reader;

    SaxHandler handler(entry_filters, entries, card_counts);
    bool result = reader.Parse<rapidjson::kParseNoFlags>(is, handler);
    fclose(fp);
    return result;
}
