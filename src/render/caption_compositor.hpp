#pragma once

#include <mascotrender/image.hpp>
#include <mascotrender/result.hpp>

#include "render/filament_backend.hpp"

namespace mascotrender::detail {

// Composites a straight-alpha BGRA screen-space overlay over a straight-alpha
// RGBA Filament frame and returns RGBA. Captions and semantic effects share
// this backend boundary.
[[nodiscard]] Result<FilamentFrame>
composite_overlay(FilamentFrame base, const PixelBuffer &overlay);

} // namespace mascotrender::detail
