# Build py extension: pip install --no-build-isolation -e . -v

# Build and run test runner:
# cmake -B build
# cmake --build build --config Release
# .\build\Release\test_runner.exe


cmake_minimum_required(VERSION 3.18...3.28)
project(MTGODecklistAnalyzer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
FetchContent_Declare(
    rapidjson
    URL https://github.com/Tencent/rapidjson/archive/refs/heads/master.zip
)
FetchContent_GetProperties(rapidjson)
if(NOT rapidjson_POPULATED)
    FetchContent_MakeAvailable(rapidjson)
endif()

# Shared source files used by both targets
set(CORE_SOURCES
    src/cpp/deck_parser.cpp
    src/cpp/utils.cpp
)

if(SKBUILD)
    find_package(Python 3.8 COMPONENTS Interpreter Development.Module REQUIRED)
    find_package(nanobind CONFIG REQUIRED)

    nanobind_add_module(_deck_sax src/cpp/bindings.cpp ${CORE_SOURCES})
    target_include_directories(_deck_sax PRIVATE src/cpp ${rapidjson_SOURCE_DIR}/include)

    if(MSVC)
        target_compile_options(_deck_sax PRIVATE /permissive-)
        target_compile_definitions(_deck_sax PRIVATE RAPIDJSON_SSE42)
    else()
        target_compile_options(_deck_sax PRIVATE -O3 -msse4.2)
        target_compile_definitions(_deck_sax PRIVATE RAPIDJSON_SSE42)
    endif()

    install(TARGETS _deck_sax LIBRARY DESTINATION mtgo_decklist_analyzer)

else()
    add_executable(test_runner src/cpp/test_runner.cpp ${CORE_SOURCES})
    target_include_directories(test_runner PRIVATE src/cpp ${rapidjson_SOURCE_DIR}/include)

    if(MSVC)
        target_compile_options(test_runner PRIVATE /permissive-)
        target_compile_definitions(test_runner PRIVATE RAPIDJSON_SSE42)
    else()
        target_compile_options(test_runner PRIVATE -O3 -msse4.2)
        target_compile_definitions(test_runner PRIVATE RAPIDJSON_SSE42)
    endif()
endif()
