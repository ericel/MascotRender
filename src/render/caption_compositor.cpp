#include "render/caption_compositor.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>

namespace mascotrender::detail {
namespace {

[[nodiscard]] Error composite_error(std::string message) {
  return Error{ErrorCode::invalid_argument, std::move(message)};
}

[[nodiscard]] std::uint8_t byte(std::byte value) {
  return std::to_integer<std::uint8_t>(value);
}

} // namespace

Result<FilamentFrame> composite_caption(FilamentFrame base,
                                        const PixelBuffer &caption) {
  const auto expected_stride = base.width * 4U;
  const auto expected_size = static_cast<std::size_t>(expected_stride) *
                             static_cast<std::size_t>(base.height);
  if (base.width == 0U || base.height == 0U ||
      base.rgba.size() != expected_size || caption.width != base.width ||
      caption.height != base.height || caption.stride_bytes < expected_stride ||
      caption.pixels.size() <
          static_cast<std::size_t>(caption.stride_bytes) * caption.height) {
    return Result<FilamentFrame>::failure(
        composite_error("Caption and Filament frame dimensions must match"));
  }

  for (std::uint32_t y = 0U; y < base.height; ++y) {
    for (std::uint32_t x = 0U; x < base.width; ++x) {
      const auto base_index =
          (static_cast<std::size_t>(y) * base.width + x) * 4U;
      const auto caption_index =
          static_cast<std::size_t>(y) * caption.stride_bytes + x * 4U;
      const std::uint32_t overlay_alpha = byte(caption.pixels[caption_index + 3U]);
      if (overlay_alpha == 0U) {
        continue;
      }
      const std::uint32_t base_alpha = base.rgba[base_index + 3U];
      const std::uint32_t inverse_alpha = 255U - overlay_alpha;
      const std::uint32_t output_alpha =
          overlay_alpha + (base_alpha * inverse_alpha + 127U) / 255U;

      // Caption storage is BGRA; Filament storage is RGBA.
      const std::uint8_t overlay_channels[3] = {
          byte(caption.pixels[caption_index + 2U]),
          byte(caption.pixels[caption_index + 1U]),
          byte(caption.pixels[caption_index])};
      for (std::size_t channel = 0U; channel < 3U; ++channel) {
        const std::uint32_t premultiplied =
            static_cast<std::uint32_t>(overlay_channels[channel]) *
                overlay_alpha +
            (static_cast<std::uint32_t>(base.rgba[base_index + channel]) *
                 base_alpha * inverse_alpha +
             127U) /
                255U;
        base.rgba[base_index + channel] = static_cast<std::uint8_t>(
            (premultiplied + output_alpha / 2U) / output_alpha);
      }
      base.rgba[base_index + 3U] = static_cast<std::uint8_t>(output_alpha);
    }
  }
  return Result<FilamentFrame>::success(std::move(base));
}

} // namespace mascotrender::detail
