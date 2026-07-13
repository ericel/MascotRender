#pragma once

#include <cstdint>
#include <vector>

#include <mascotrender/image.hpp>
#include <mascotrender/result.hpp>

namespace mascotrender::detail {

[[nodiscard]] Result<EncodedImage> encode_webp(const PixelBuffer& pixels,
                                               const RenderOptions& options);

struct AnimationFrame {
    std::uint32_t timestamp_ms{};
    PixelBuffer pixels;
};

[[nodiscard]] Result<EncodedImage> encode_animated_webp(
    const std::vector<AnimationFrame>& frames, std::uint32_t duration_ms,
    std::uint32_t loop_count, const RenderOptions& options);

}  // namespace mascotrender::detail
