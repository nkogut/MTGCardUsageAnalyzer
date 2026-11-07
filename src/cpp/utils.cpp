#include "utils.hpp"
#include <cctype>
#include <iomanip>
#include <sstream>

std::string strip(const std::string& s) {
    const char* ws = " \t\n\r\f\v";

    size_t start = s.find_first_not_of(ws);
    if (start == std::string::npos)
        return {};

    size_t end = s.find_last_not_of(ws);
    return s.substr(start, end - start + 1);
}

std::string formatDate(time_t t) {
    tm timeInfo{};
    #if defined(_WIN32)
        localtime_s(&timeInfo, &t);
    #else
        localtime_r(&t, &timeInfo);
    #endif

    std::ostringstream oss;
    oss << std::put_time(&timeInfo, "%Y-%m-%d");
    return oss.str();
}
