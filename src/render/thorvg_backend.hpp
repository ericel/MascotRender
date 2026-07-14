#pragma once

#include <optional>
#include <string>

#include "render/irender_backend.hpp"

namespace mascotrender::detail {

class ThorvgBackend final : public IRenderBackend {
public:
    ThorvgBackend();
    ~ThorvgBackend() override;

    ThorvgBackend(const ThorvgBackend&) = delete;
    ThorvgBackend& operator=(const ThorvgBackend&) = delete;

    [[nodiscard]] Result<PixelBuffer> render_sample(
        std::uint32_t width, std::uint32_t height) const override;

    [[nodiscard]] Result<PixelBuffer> render_scene(
        const Scene& scene, std::uint32_t width, std::uint32_t height,
        const FrameState& frame) const override;

    // Renders only the screen-space caption layer on transparent pixels. This
    // is the shared 2D compositor input for both vector and Filament scenes.
    [[nodiscard]] Result<PixelBuffer> render_caption_overlay(
        const Scene& scene, std::uint32_t width, std::uint32_t height,
        const FrameState& frame = {}) const;

    // Renders one selected SVG layer at output resolution without mascot or
    // camera transforms. Screen-space effects use this path across backends.
    [[nodiscard]] Result<PixelBuffer>
    render_layer_overlay(const Scene &scene, const std::string &layer_id,
                         std::uint32_t width, std::uint32_t height) const;

  private:
    std::optional<Error> initialization_error_;
};

}  // namespace mascotrender::detail
