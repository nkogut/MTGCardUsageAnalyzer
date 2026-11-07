#pragma once
#include <ctime>
#include <string>
#include <cctype>

std::string strip(const std::string& s);
std::string formatDate(time_t t);

inline time_t parseDate(const char* str) {
    int year  = (str[0] - '0') * 1000 + (str[1] - '0') * 100 + (str[2] - '0') * 10 + (str[3] - '0');
    int month = (str[5] - '0') * 10   + (str[6] - '0');
    int day   = (str[8] - '0') * 10   + (str[9] - '0');

    static constexpr int normalYearOffsets[] = { 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334 };

    int totalDays = (year - 1970) * 365 + ((year - 1969) / 4);
    int isLeap = (year % 4 == 0 && month > 2);
    totalDays += normalYearOffsets[month - 1] + day + isLeap;

    return static_cast<time_t>(totalDays) * 86400;
}

inline void titleCase(char* buf, size_t len) {
    buf[len] = '\0';
    bool nextIsCap = true;

    for (size_t i = 0; i < len; ++i) {
        unsigned char c = static_cast<unsigned char>(buf[i]);
        if (c == ' ' || c == '-') {
            nextIsCap = true;
        } else if (nextIsCap) {
            buf[i] = (char)std::toupper(c);
            nextIsCap = false;
        } else {
            buf[i] = (char)std::tolower(c);
        }
    }
}
