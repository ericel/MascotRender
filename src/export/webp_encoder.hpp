#pragma once

#include <mascotrender/image.hpp>
#include <mascotrender/result.hpp>

namespace mascotrender::detail {

[[nodiscard]] Result<EncodedImage> encode_webp(
    const PixelBuffer& pixels, const RenderOptions& options);

}  // namespace mascotrender::detail
