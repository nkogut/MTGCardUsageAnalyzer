#pragma once

#include <time.h>
#include <cctype>
#include <sstream>
#include <iomanip>

class Util {
    public:

    [[nodiscard]] static inline time_t parse_date(const char* str) {
        tm time_from_string{};
        std::istringstream ss(str);
        ss >> std::get_time(&time_from_string, "%Y-%m-%d");
        if (ss.fail()) {
            return 0;
        }
        return mktime(&time_from_string);
    }

    static inline void title_case(char* buf, size_t len) {
        buf[len] = '\0';
        bool next_is_cap = true;

        for (size_t i = 0; i < len; ++i) {
            unsigned char c = static_cast<unsigned char>(buf[i]);
            if (c == ' ' || c == '-') {
                next_is_cap = true;
            } else if (next_is_cap) {
                buf[i] = (char)std::toupper(c);
                next_is_cap = false;
            } else {
                buf[i] = (char)std::tolower(c);
            }
        }
    }
};
