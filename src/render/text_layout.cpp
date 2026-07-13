#include "render/text_layout.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstddef>
#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace mascotrender::detail {
namespace {

[[nodiscard]] std::vector<std::string> split_words(std::string_view content) {
  std::vector<std::string> output;
  std::string current;
  for (const char character : content) {
    if (std::isspace(static_cast<unsigned char>(character)) != 0) {
      if (!current.empty()) {
        output.push_back(std::move(current));
        current.clear();
      }
    } else {
      current.push_back(character);
    }
  }
  if (!current.empty()) {
    output.push_back(std::move(current));
  }
  return output;
}

struct Segment {
  std::string text;
  TextMetrics metrics;
  bool measured{};
};

[[nodiscard]] std::size_t segment_index(std::size_t start, std::size_t end,
                                        std::size_t count) {
  return start * count + end;
}

[[nodiscard]] std::optional<FittedText>
fit_at_size(const std::vector<std::string> &tokens, float font_size,
            std::uint32_t maximum_lines, float usable_width,
            float usable_height, const MeasureText &measure) {
  const auto count = tokens.size();
  std::vector<Segment> segments(count * count);
  for (std::size_t start = 0; start < count; ++start) {
    std::string line;
    for (std::size_t end = start; end < count; ++end) {
      if (!line.empty()) {
        line.push_back(' ');
      }
      line += tokens[end];
      auto metrics = measure(line, font_size);
      if (!metrics) {
        return std::nullopt;
      }
      auto &segment = segments[segment_index(start, end, count)];
      segment = Segment{line, *metrics, true};
    }
  }

  const auto line_limit = std::min<std::size_t>(maximum_lines, count);
  constexpr double epsilon = 1.0e-9;
  for (std::size_t line_count = 1; line_count <= line_limit; ++line_count) {
    const auto state_count = (line_count + 1U) * (count + 1U);
    std::vector<double> costs(state_count,
                              std::numeric_limits<double>::infinity());
    std::vector<std::size_t> previous(state_count, count + 1U);
    const auto state = [count](std::size_t lines, std::size_t end) {
      return lines * (count + 1U) + end;
    };
    costs[state(0U, 0U)] = 0.0;

    for (std::size_t lines = 1; lines <= line_count; ++lines) {
      for (std::size_t end = lines; end <= count; ++end) {
        for (std::size_t start = lines - 1U; start < end; ++start) {
          const auto prior = costs[state(lines - 1U, start)];
          if (!std::isfinite(prior)) {
            continue;
          }
          const auto &segment = segments[segment_index(start, end - 1U, count)];
          if (!segment.measured || segment.metrics.width > usable_width) {
            continue;
          }
          const auto unused = static_cast<double>(usable_width) -
                              static_cast<double>(segment.metrics.width);
          const auto candidate = prior + unused * unused;
          const auto index = state(lines, end);
          if (candidate + epsilon < costs[index]) {
            costs[index] = candidate;
            previous[index] = start;
          }
        }
      }
    }

    if (!std::isfinite(costs[state(line_count, count)])) {
      continue;
    }

    std::vector<std::pair<std::size_t, std::size_t>> ranges(line_count);
    auto end = count;
    for (auto line = line_count; line > 0U; --line) {
      const auto start = previous[state(line, end)];
      if (start > count) {
        return std::nullopt;
      }
      ranges[line - 1U] = {start, end - 1U};
      end = start;
    }

    FittedText fitted;
    fitted.font_size = font_size;
    fitted.lines.reserve(line_count);
    fitted.metrics.reserve(line_count);
    float tallest = 0.0F;
    for (const auto &[start, last] : ranges) {
      const auto &segment = segments[segment_index(start, last, count)];
      fitted.lines.push_back(segment.text);
      fitted.metrics.push_back(segment.metrics);
      tallest = std::max(tallest, segment.metrics.height);
    }
    fitted.line_height = std::max(tallest, font_size * 1.2F);
    if (fitted.line_height * static_cast<float>(line_count) <= usable_height) {
      return fitted;
    }
  }
  return std::nullopt;
}

} // namespace

std::optional<FittedText>
fit_text_balanced(std::string_view content, float area_width, float area_height,
                  float minimum_font_size, float maximum_font_size,
                  std::uint32_t maximum_lines, float inset,
                  const MeasureText &measure) {
  const auto tokens = split_words(content);
  const auto usable_width = area_width - inset * 2.0F;
  const auto usable_height = area_height - inset * 2.0F;
  if (tokens.empty() || maximum_lines == 0U || usable_width <= 0.0F ||
      usable_height <= 0.0F || !measure) {
    return std::nullopt;
  }

  const auto maximum = static_cast<int>(std::floor(maximum_font_size));
  const auto minimum = static_cast<int>(std::ceil(minimum_font_size));
  for (auto size = maximum; size >= minimum; --size) {
    if (auto fitted =
            fit_at_size(tokens, static_cast<float>(size), maximum_lines,
                        usable_width, usable_height, measure)) {
      return fitted;
    }
  }
  return std::nullopt;
}

} // namespace mascotrender::detail
