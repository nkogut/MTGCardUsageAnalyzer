#include <rapidjson/reader.h>
#include <rapidjson/error/en.h>
#include <iostream>
#include <filesystem>
#include <algorithm>
#include "deck_parser.hpp"
#include "utils.hpp"
#include <mimalloc-new-delete.h>
#include <format>

#ifdef _MSC_VER
#define STRNICMP _strnicmp
#else
#define STRNICMP strncasecmp
#include <strings.h>
#endif

EntryFilters::EntryFilters(time_t start_date, time_t end_date, std::string&& player_str,
             std::vector<std::string>&& whitelist, std::vector<std::string>&& blacklist) :
    use_date_filter(true),
    use_player_filter(!player_str.empty()),
    use_card_whitelist(!whitelist.empty()),
    use_card_blacklist(!blacklist.empty()),
    start_date(start_date),
    end_date(end_date),
    player(std::move(player_str)),
    player_view(this->player),
    whitelist_size(static_cast<uint8_t>(whitelist.size())),
    card_whitelist(std::move(whitelist)),
    card_blacklist(std::move(blacklist)) {

    // Create new representations of whitelist/blacklist using string_view for faster comparison
    card_view_whitelist.reserve(card_whitelist.size());
    for (const auto& str : card_whitelist) {
        card_view_whitelist.emplace_back(str);
    }

    card_view_blacklist.reserve(card_blacklist.size());
    for (const auto& str : card_blacklist) {
        card_view_blacklist.emplace_back(str);
    }
}

[[nodiscard]] inline bool EntryFilters::date_is_okay(time_t date) const noexcept {
    if (!use_date_filter) return true;
    return (date >= start_date && date <= end_date);
}

[[nodiscard]] inline bool EntryFilters::player_is_okay(std::string_view name) const noexcept {
    if (!use_player_filter) return true;
    if (name.length() != player_view.length()) return false;
    return STRNICMP(name.data(), player_view.data(), name.length()) == 0;
}

[[nodiscard]] inline bool EntryFilters::card_is_blacklisted(std::string_view card) const noexcept {
    if (!use_card_blacklist) [[likely]] return false;
    for (const std::string_view blacklisted_card : card_view_blacklist) {
        if (card.length() == blacklisted_card.length() &&
            (card.front() | 0x20) == (blacklisted_card.front() | 0x20) &&
            STRNICMP(card.data(), blacklisted_card.data(), card.length()) == 0) return true;
    }
    return false;
}

inline void EntryFilters::update_whitelist_matches(std::string_view card, std::bitset<32>& matched) const noexcept {
    if (!use_card_whitelist) return;
    for (size_t idx = 0; idx < card_view_whitelist.size(); ++idx) {
        if (card.length() == card_view_whitelist[idx].length() &&
            STRNICMP(card.data(), card_view_whitelist[idx].data(), card.length()) == 0) {
            matched.set(idx);
            break;
        }
    }
}

template <typename FilterPolicy>
struct SaxHandler : public rapidjson::BaseReaderHandler<rapidjson::UTF8<>, SaxHandler<FilterPolicy>> {
    enum class JsonKey { UNKNOWN, PLAYER, URL, DATE, MAIN, SIDE, CARD_NAME };

    const FilterPolicy& filters;
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
        : entries(out), filters(f), card_counts(counts) {
        this->card_count_stage.reserve(75);

        // Sizes to reserve are empirically chosen using modern.json
        // mainboard - 50th percentile: 22, 95th percentile: 29
        // sideboard - 50th percentile: 8, 95th percentile: 12
        this->curr_entry.main.reserve(22);
        this->curr_entry.side.reserve(8);
    }

    inline bool to_skip() const noexcept {
        return skip_depth > 0;
    }

    void clear_entry() {
        // Clear all deck metadata whether it was written back or not
        curr_entry.clear();
        whitelist_matches.reset();
        card_count_stage.clear();
        current_location = NONE;
        active_key = JsonKey::UNKNOWN;
    }

    bool Key(const char* str, rapidjson::SizeType length, bool copy) {
    if (to_skip()) return true;

    if (current_location != NONE) [[likely]] {
        current_card_view = std::string_view(str, length);
        if (filters.use_card_blacklist && filters.card_is_blacklisted(current_card_view)) skip_depth = 1;
        else if (filters.use_card_whitelist) filters.update_whitelist_matches(current_card_view, whitelist_matches);
        return true;
    }

    switch (str[0]) {
        case 'm': active_key = JsonKey::MAIN; break;
        case 's': active_key = JsonKey::SIDE; break;
        case 'd': active_key = JsonKey::DATE; break;
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
            curr_entry.date = parseDate(str);
            if (!filters.date_is_okay(curr_entry.date)) skip_depth = 1;
        } else if (active_key == JsonKey::URL) {
            curr_entry.url = std::string(str, length);
        }
        return true;
    }

bool Uint(unsigned i) {
    if (to_skip()) return true;

    for (auto it = card_count_stage.rbegin(); it != card_count_stage.rend(); ++it) {
        if (it->first == current_card_view) {
            if (current_location == MAIN) {
                it->second.main_count += i;
                it->second.num_main_decks = 1;
            } else if (current_location == SIDE) {
                it->second.side_count += i;
                it->second.num_side_boards = 1;
            }
            return true;
        }
    }

    staged_card_count counts{0, 0, 0, 0};
    if (current_location == MAIN) {
        counts.main_count = i;
        counts.num_main_decks = 1;
    } else if (current_location == SIDE) {
        counts.side_count = i;
        counts.num_side_boards = 1;
    }
    card_count_stage.emplace_back(current_card_view, counts);

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
                // Reject the deck
                clear_entry();
                return true;
            }

            // Accept the deck. Store data for each card in the deck
            for (const auto& [name, counts] : card_count_stage) {
                // Create a new entry for this card if it has not appeared for this time bucket yet
                auto it = card_counts.find(name);
                if (it == card_counts.end()) [[unlikely]] {
                    it = card_counts.emplace(std::string(name), card_count{}).first;
                }

                auto& card_entry = it->second;
                card_entry.main_count      += counts.main_count;
                card_entry.side_count      += counts.side_count;
                card_entry.num_main_decks  += counts.num_main_decks;
                card_entry.num_side_boards += counts.num_side_boards;

                // Add this card to the stored copy of its deck
                std::string_view permanent_view = it->first;
                if (counts.main_count > 0) {
                    curr_entry.main.emplace_back(permanent_view, counts.main_count);
                } else {
                    curr_entry.side.emplace_back(permanent_view, counts.side_count);
                }
            }

            entries.push_back(std::move(curr_entry));
            clear_entry();
            curr_entry.main.reserve(28);
            curr_entry.side.reserve(12);
        }
        return true;
    }

    bool Int(int i) { return Uint(static_cast<unsigned>(i)); }
    bool StartArray() { return true; }
    bool EndArray(rapidjson::SizeType) { return true; }
    bool Default() { return true; }
};

bool get_decks(std::vector<Entry>& entries, card_count_map& card_counts, const std::filesystem::path& ds_path,
    const time_t start_date, const time_t end_date, std::string player, std::vector<std::string> whitelist,
    std::vector<std::string> blacklist) {
    card_counts.reserve(8192);
    entries.reserve(65536);

    FILE* fp;
    #if defined(_WIN32)
        _wfopen_s(&fp, ds_path.wstring().c_str(), L"rb");
    #else
        fp = fopen(ds_path.c_str(), "rb");
    #endif

    if (!fp) return false;

    fseek(fp, 0, SEEK_END);
    size_t file_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);

    std::vector<char> file_buffer(file_size + 1);
    size_t read_bytes = fread(file_buffer.data(), 1, file_size, fp);
    file_buffer[read_bytes] = '\0';
    fclose(fp);

    rapidjson::InsituStringStream stream(file_buffer.data());
    rapidjson::Reader reader;

    EntryFilters entry_filters(start_date, end_date, std::move(player), std::move(whitelist), std::move(blacklist));
    SaxHandler handler(entry_filters, entries, card_counts);

    // Use In-situ parsing - modifies buffer in place to avoid mallocing each piece of data it reads
    rapidjson::ParseResult parse_result = reader.Parse<rapidjson::kParseInsituFlag>(stream, handler);
    if (parse_result.IsError()) {
        fprintf(stderr, "JSON parse error %d: %s\nAt character offset %zu\n",
            parse_result.Code(), rapidjson::GetParseError_En(parse_result.Code()), parse_result.Offset());
        return false;
    }
    return true;
}

std::string format_frequencies(const card_count_map& card_counts, deck_location location, size_t num_decks) {
    // Generates a string displaying all card frequency stats
    // Can be printed directly in CLI/GUI

    if (num_decks == 0) return "\n0 decks found.\n";

    std::vector<const card_count_map::value_type*> sorted_vec;
    sorted_vec.reserve(card_counts.size());

    double inv_decks_per_point = 10000.0 / static_cast<double>(num_decks);

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

        const uint32_t total_qty_a = (location == MAIN) ? a->second.main_count : a->second.side_count;
        const uint32_t total_qty_b = (location == MAIN) ? b->second.main_count : b->second.side_count;

        return total_qty_a > total_qty_b;
    });

    std::string report = std::format("\n--- {} {} cards across {} decks ---\n",
        sorted_vec.size(),
        (location == MAIN ? "Maindeck" : "Sideboard"),
        num_decks);

    report += std::format("{:<33} ||| {:>6} | {:>5}\n", "Card", "%Decks", "Qty");

    char name_buf[128];

    for (const auto* card_entry : sorted_vec) {
        size_t len = card_entry->first.copy(name_buf, sizeof(name_buf) - 1);
        titleCase(name_buf, len);
        name_buf[len] = '\0';

        uint32_t decks = (location == MAIN) ? card_entry->second.num_main_decks : card_entry->second.num_side_boards;
        uint32_t qty = (location == MAIN) ? card_entry->second.main_count : card_entry->second.side_count;

        float num_decks_float = static_cast<float>(decks);
        float pct_decks = (num_decks_float / static_cast<float>(num_decks)) * 100.0f;
        float avg_q = (static_cast<float>(qty) / num_decks_float);

        report += std::format("{:<33} ||| {:>6.2f} | {:>5.2f}\n", name_buf, pct_decks, avg_q);
    }

    return report;
}
