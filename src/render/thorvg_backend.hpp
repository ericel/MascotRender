#pragma once

#include <optional>

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
        const Scene& scene,
        std::uint32_t width, std::uint32_t height) const override;

private:
    std::optional<Error> initialization_error_;
};

}  // namespace mascotrender::detail
