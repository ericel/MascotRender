#include "render/caption_layout.hpp"

#include <algorithm>
#include <limits>
#include <utility>

namespace mascotrender::detail {
namespace {

[[nodiscard]] float overlap_area(const Rect &left, const Rect &right) {
  const auto width =
      std::max(0.0F, std::min(left.x + left.width, right.x + right.width) -
                         std::max(left.x, right.x));
  const auto height =
      std::max(0.0F, std::min(left.y + left.height, right.y + right.height) -
                         std::max(left.y, right.y));
  return width * height;
}

[[nodiscard]] Rect fitted_bounds(const Rect &area, const FittedText &fitted,
                                 float outline_width) {
  const auto total_height =
      fitted.line_height * static_cast<float>(fitted.lines.size());
  const auto first_y = area.y + (area.height - total_height) * 0.5F;
  auto left = std::numeric_limits<float>::infinity();
  auto top = std::numeric_limits<float>::infinity();
  auto right = -std::numeric_limits<float>::infinity();
  auto bottom = -std::numeric_limits<float>::infinity();
  for (std::size_t index = 0; index < fitted.metrics.size(); ++index) {
    const auto &metrics = fitted.metrics[index];
    const auto glyph_left =
        area.x + (area.width - metrics.width) * 0.5F - outline_width;
    const auto glyph_top =
        first_y + static_cast<float>(index) * fitted.line_height +
        (fitted.line_height - metrics.height) * 0.5F - outline_width;
    left = std::min(left, glyph_left);
    top = std::min(top, glyph_top);
    right = std::max(right, glyph_left + metrics.width + outline_width * 2.0F);
    bottom =
        std::max(bottom, glyph_top + metrics.height + outline_width * 2.0F);
  }
  return Rect{left, top, right - left, bottom - top};
}

} // namespace

std::optional<ResolvedCaption>
resolve_caption(const TextBlock &block, float scale_x, float scale_y,
                const MeasureText &measure) {
  const auto scale = std::min(scale_x, scale_y);
  const auto outline_width = block.outline_width * scale;
  std::optional<ResolvedCaption> selected;
  auto selected_score = std::numeric_limits<float>::infinity();

  for (std::size_t candidate_index = 0;
       candidate_index < block.candidate_areas.size(); ++candidate_index) {
    const auto &candidate = block.candidate_areas[candidate_index];
    const Rect area{candidate.x * scale_x, candidate.y * scale_y,
                    candidate.width * scale_x, candidate.height * scale_y};
    auto fitted = fit_text_balanced(
        block.content, area.width, area.height, block.min_font_size * scale,
        block.max_font_size * scale, block.max_lines, outline_width, measure);
    if (!fitted) {
      continue;
    }

    float score = 0.0F;
    if (block.auto_placement) {
      const auto text_bounds = fitted_bounds(area, *fitted, outline_width);
      auto collision_overlap = 0.0F;
      for (const auto &avoid : block.avoid_regions) {
        const Rect scaled_avoid{avoid.x * scale_x, avoid.y * scale_y,
                                avoid.width * scale_x,
                                avoid.height * scale_y};
        collision_overlap += overlap_area(text_bounds, scaled_avoid);
      }
      if (block.strict_collision && collision_overlap > 0.01F) {
        continue;
      }
      score += collision_overlap * 20.0F;
      const auto source_font_size = fitted->font_size / scale;
      score += (block.max_font_size - source_font_size) * 10.0F;
      score += static_cast<float>(fitted->lines.size()) * 5.0F;
      score += static_cast<float>(candidate_index) * 3.0F;
    }
    if (selected && score >= selected_score) {
      continue;
    }

    std::vector<PositionedTextLine> positions;
    positions.reserve(fitted->lines.size());
    const auto total_height =
        fitted->line_height * static_cast<float>(fitted->lines.size());
    const auto first_y = area.y + (area.height - total_height) * 0.5F;
    for (std::size_t index = 0; index < fitted->lines.size(); ++index) {
      const auto &metrics = fitted->metrics[index];
      const auto x =
          area.x + (area.width - metrics.width) * 0.5F - metrics.x;
      const auto line_y =
          first_y + static_cast<float>(index) * fitted->line_height;
      const auto y = line_y + (fitted->line_height - metrics.height) * 0.5F -
                     metrics.y;
      positions.push_back(PositionedTextLine{x, y});
    }
    selected = ResolvedCaption{area, std::move(*fitted), std::move(positions),
                               outline_width, candidate_index};
    selected_score = score;
  }
  return selected;
}

} // namespace mascotrender::detail
