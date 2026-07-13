#pragma once

#include <cstdint>
#include <filesystem>
#include <mascotrender/image.hpp>
#include <mascotrender/result.hpp>
#include <vector>

#include "model/scene.hpp"

namespace mascotrender::detail {

class IRenderBackend {
public:
    virtual ~IRenderBackend() = default;

    [[nodiscard]] virtual Result<PixelBuffer> render_sample(
        std::uint32_t width, std::uint32_t height) const = 0;

    [[nodiscard]] virtual Result<PixelBuffer> render_scene(
        const Scene& scene, std::uint32_t width, std::uint32_t height,
        const FrameState& frame) const = 0;
};

}  // namespace mascotrender::detail
