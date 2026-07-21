#include <string_view>

#include <catch2/catch_test_macros.hpp>

#include <mascotrender/version.hpp>

TEST_CASE("library reports its package version") {
    STATIC_REQUIRE(mascotrender::library_version.major == 0);
    STATIC_REQUIRE(mascotrender::library_version.minor == 7);
    STATIC_REQUIRE(mascotrender::library_version.patch == 0);
    REQUIRE(std::string_view{mascotrender::version_string()} == "0.7.0");
}
