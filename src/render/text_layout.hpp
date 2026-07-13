#pragma once

#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace mascotrender::detail {

struct TextMetrics {
  float x{};
  float y{};
  float width{};
  float height{};
};

struct FittedText {
  float font_size{};
  float line_height{};
  std::vector<std::string> lines;
  std::vector<TextMetrics> metrics;
};

using MeasureText = std::function<std::optional<TextMetrics>(
    std::string_view text, float font_size)>;

// Finds the largest whole-point size that fits, then chooses the fewest lines
// and minimizes squared unused width. Equal-cost layouts use the earliest cut,
// which makes the result stable without relying on container iteration order.
[[nodiscard]] std::optional<FittedText>
fit_text_balanced(std::string_view content, float area_width, float area_height,
                  float minimum_font_size, float maximum_font_size,
                  std::uint32_t maximum_lines, float inset,
                  const MeasureText &measure);

} // namespace mascotrender::detail
