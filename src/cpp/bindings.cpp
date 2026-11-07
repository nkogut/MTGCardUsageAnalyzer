#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/filesystem.h>
#include <nanobind/stl/pair.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include "deck_parser.hpp"

namespace nb = nanobind;
using namespace nb::literals;

NB_MODULE(_deck_sax, m) {
    m.def("analyze_metagame", [](const std::filesystem::path& ds_path, time_t start_date, time_t end_date,
                                  const std::string& player, const std::vector<std::string>& whitelist,
                                  const std::vector<std::string>& blacklist, bool return_decks) {
        std::vector<Entry> entries;
        card_count_map card_counts;

        get_decks(entries, card_counts, ds_path, start_date, end_date, player, whitelist, blacklist);

        std::string freq_report;
        if (entries.empty()) freq_report = "\n0 decks found.\n";
        else {
            freq_report = format_frequencies(card_counts, MAIN, entries.size()) +
                          format_frequencies(card_counts, SIDE, entries.size());
        }

        if (!return_decks) return std::make_pair(nb::bytes("[]", 2), freq_report);

        // Return a json string to python containing the filtered decks - only if needed for downstream tasks
        rapidjson::StringBuffer buffer;
        buffer.Reserve(1024 * 1024 * 32);
        rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

        writer.StartArray();
        for (const auto& entry : entries) {
            writer.StartObject();
            writer.Key("player"); writer.String(entry.player.c_str());
            writer.Key("url"); writer.String(entry.url.c_str());
            writer.Key("date"); writer.Uint64(entry.date);

            writer.Key("main");
            writer.StartObject();
            for (const auto& [card, count] : entry.main) {
                writer.Key(card.data(), static_cast<rapidjson::SizeType>(card.length()));
                writer.Uint(count);
            }
            writer.EndObject();

            writer.Key("side");
            writer.StartObject();
            for (const auto& [card, count] : entry.side) {
                writer.Key(card.data(), static_cast<rapidjson::SizeType>(card.length()));
                writer.Uint(count);
            }
            writer.EndObject();
            writer.EndObject();
        }
        writer.EndArray();

        return std::make_pair(nb::bytes(buffer.GetString(), buffer.GetSize()), freq_report);
    }, "ds_path"_a, "start_date"_a, "end_date"_a, "player"_a, "whitelist"_a, "blacklist"_a, "return_decks"_a);
}
