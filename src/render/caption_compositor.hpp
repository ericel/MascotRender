#pragma once

#include <mascotrender/image.hpp>
#include <mascotrender/result.hpp>

#include "render/filament_backend.hpp"

namespace mascotrender::detail {

// Composites a straight-alpha BGRA caption overlay over a straight-alpha RGBA
// Filament frame and returns RGBA. Keeping this at the backend boundary avoids
// making Filament a dependency of the scene/text system.
[[nodiscard]] Result<FilamentFrame>
composite_caption(FilamentFrame base, const PixelBuffer &caption);

} // namespace mascotrender::detail
