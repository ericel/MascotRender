#include <optional>
#include <string>
#include <string_view>

#include <catch2/catch_test_macros.hpp>

#include "render/text_layout.hpp"

namespace {

[[nodiscard]] std::optional<mascotrender::detail::TextMetrics>
monospace_measure(std::string_view text, float font_size) {
  return mascotrender::detail::TextMetrics{
      0.0F, 0.0F, static_cast<float>(text.size()), font_size};
}

} // namespace

TEST_CASE("balanced wrapping improves a valid greedy split") {
  const auto fitted = mascotrender::detail::fit_text_balanced(
      "AAAA BBBB CC", 9.0F, 30.0F, 10.0F, 10.0F, 2U, 0.0F, monospace_measure);

  REQUIRE(fitted);
  REQUIRE(fitted->lines.size() == 2U);
  REQUIRE(fitted->lines[0] == "AAAA");
  REQUIRE(fitted->lines[1] == "BBBB CC");
}

TEST_CASE("balanced wrapping keeps one line when it fits") {
  const auto fitted = mascotrender::detail::fit_text_balanced(
      "ONE LINE", 20.0F, 20.0F, 10.0F, 10.0F, 3U, 0.0F, monospace_measure);

  REQUIRE(fitted);
  REQUIRE(fitted->lines.size() == 1U);
  REQUIRE(fitted->lines.front() == "ONE LINE");
}

TEST_CASE("outline inset participates in fitting") {
  const auto no_outline = mascotrender::detail::fit_text_balanced(
      "AAAA BBBB", 9.0F, 30.0F, 10.0F, 10.0F, 2U, 0.0F, monospace_measure);
  const auto outlined = mascotrender::detail::fit_text_balanced(
      "AAAA BBBB", 9.0F, 30.0F, 10.0F, 10.0F, 2U, 1.0F, monospace_measure);

  REQUIRE(no_outline);
  REQUIRE(no_outline->lines.size() == 1U);
  REQUIRE(outlined);
  REQUIRE(outlined->lines.size() == 2U);
}
