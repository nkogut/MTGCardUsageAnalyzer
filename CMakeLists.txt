cmake_minimum_required(VERSION 3.22)
project(MTGODecklistAnalyzer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(POLICY CMP0135)
    cmake_policy(SET CMP0135 NEW)
endif()

include(FetchContent)
FetchContent_Declare(
    rapidjson
    URL https://github.com/Tencent/rapidjson/archive/refs/heads/master.zip
)

set(RAPIDJSON_BUILD_DOC OFF CACHE BOOL "Disable RapidJSON docs" FORCE)
set(RAPIDJSON_BUILD_EXAMPLES OFF CACHE BOOL "Disable RapidJSON examples" FORCE)
set(RAPIDJSON_BUILD_TESTS OFF CACHE BOOL "Disable RapidJSON tests" FORCE)

FetchContent_MakeAvailable(rapidjson)

set(CORE_SOURCES
    src/cpp/deck_parser.cpp
    src/cpp/utils.cpp
)

find_package(Python 3.8 COMPONENTS Interpreter Development.Module REQUIRED)
find_package(nanobind CONFIG REQUIRED)

nanobind_add_module(_deck_sax src/cpp/bindings.cpp ${CORE_SOURCES})
install(TARGETS _deck_sax LIBRARY DESTINATION mtgo_decklist_analyzer)

target_include_directories(_deck_sax PRIVATE src/cpp ${rapidjson_SOURCE_DIR}/include)
target_compile_definitions(_deck_sax PRIVATE RAPIDJSON_SSE42)

if(MSVC)
    target_compile_options(_deck_sax PRIVATE /permissive- /O2 /arch:AVX2)
else()
    target_compile_options(_deck_sax PRIVATE -O3 -msse4.2)
endif()
