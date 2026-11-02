#include <iostream>
#include <filesystem>
#include <vector>
#include <string>
#include <time.h>
#include "deck_parser.hpp"

int main(int argc, char** argv) {
    std::filesystem::path ds_path = "Data/modern.json";
    if (argc > 1) {
        ds_path = argv[1];
    }

    std::time_t start_date{0};
    std::time_t end_date = time(nullptr);
    std::string player = "";
    std::vector<std::string> whitelist = {};
    std::vector<std::string> blacklist = {};

    std::vector<Entry> entries;
    card_count_map card_counts;
    entries.reserve(8192);
    card_counts.reserve(8192);

    std::cout << "Parsing " << ds_path << "..." << std::endl;
    bool success = get_decks(entries, card_counts, ds_path, start_date, end_date, player, whitelist, blacklist);

    if (!success) {
        std::cerr << "Error: Failed to parse dataset. File may not exist." << std::endl;
        return 1;
    }

    std::cout << "Successfully parsed " << entries.size() << " decks." << std::endl;
    print_freqs(card_counts, MAIN, entries.size());

    return 0;
}
