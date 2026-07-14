#pragma once

#include <cstddef>
#include <optional>
#include <vector>

#include "model/scene.hpp"
#include "render/text_layout.hpp"

namespace mascotrender::detail {

struct PositionedTextLine {
  float x{};
  float y{};
};

// Backend-neutral result of caption fitting, collision scoring, and placement.
// Renderers consume these exact coordinates instead of implementing their own
// placement rules.
struct ResolvedCaption {
  Rect area;
  FittedText fitted;
  std::vector<PositionedTextLine> positions;
  float outline_width{};
  std::size_t candidate_index{};
};

[[nodiscard]] std::optional<ResolvedCaption>
resolve_caption(const TextBlock &block, float scale_x, float scale_y,
                const MeasureText &measure);

} // namespace mascotrender::detail
