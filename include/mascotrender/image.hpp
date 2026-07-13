#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace mascotrender {

enum class PixelFormat {
    bgra8_straight,
};

struct PixelBuffer {
    std::uint32_t width{};
    std::uint32_t height{};
    std::uint32_t stride_bytes{};
    PixelFormat format{PixelFormat::bgra8_straight};
    std::vector<std::byte> pixels;
};

struct EncodedImage {
    std::uint32_t width{};
    std::uint32_t height{};
    std::string media_type{"image/webp"};
    std::vector<std::byte> bytes;
};

struct RenderOptions {
    std::uint32_t width{512};
    std::uint32_t height{512};
    float webp_quality{90.0F};
    bool lossless{false};
};

}  // namespace mascotrender
